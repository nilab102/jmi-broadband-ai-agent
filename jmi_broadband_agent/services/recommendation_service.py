"""
Recommendation Service - Provides AI-powered broadband deal recommendations.
Analyzes scraped data and user preferences to suggest best deals.
"""

from typing import Dict, List, Optional, Any
from loguru import logger
import re


class RecommendationService:
    """
    Service for generating AI-powered broadband recommendations.
    Analyzes deals based on price, speed, contract terms, and user preferences.
    """
    
    def __init__(self):
        """Initialize the recommendation service."""
        self.weights = {
            'price': 0.35,
            'speed': 0.30,
            'contract': 0.15,
            'provider': 0.10,
            'features': 0.10
        }
        logger.info("✅ Recommendation service initialized")
    
    def generate_recommendations(
        self,
        scraped_data: Dict,
        user_preferences: Optional[Dict] = None,
        top_n: int = 5
    ) -> List[Dict]:
        """
        Generate top N recommendations from scraped data.
        
        Args:
            scraped_data: Scraped broadband deals data
            user_preferences: Optional user preferences (budget, min_speed, etc.)
            top_n: Number of recommendations to return
            
        Returns:
            List of recommended deals with scores
        """
        deals = scraped_data.get('deals', [])
        if not deals:
            logger.warning("⚠️ No deals available for recommendations")
            return []
        
        try:
            # Score each deal
            scored_deals = []
            for deal in deals:
                score = self._calculate_deal_score(deal, user_preferences)
                scored_deals.append({
                    'deal': deal,
                    'score': score,
                    'recommendation_reason': self._generate_reason(deal, score)
                })
            
            # Sort by score (highest first)
            scored_deals.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"✅ Generated {len(scored_deals)} recommendations")
            return scored_deals[:top_n]
            
        except Exception as e:
            logger.error(f"❌ Error generating recommendations: {e}")
            return []
    
    def _calculate_deal_score(
        self,
        deal: Dict,
        preferences: Optional[Dict] = None
    ) -> float:
        """
        Calculate a composite score for a deal.
        
        Args:
            deal: Deal dictionary
            preferences: User preferences
            
        Returns:
            Score between 0 and 100
        """
        preferences = preferences or {}
        
        # Extract deal attributes
        price = self._extract_price(deal)
        speed = self._extract_speed(deal)
        contract_months = self._extract_contract_months(deal)
        provider = deal.get('provider', {}).get('name', '')
        
        # Calculate component scores (0-100 scale)
        price_score = self._score_price(price, preferences.get('max_budget'))
        speed_score = self._score_speed(speed, preferences.get('min_speed'))
        contract_score = self._score_contract(contract_months, preferences.get('preferred_contract'))
        provider_score = self._score_provider(provider, preferences.get('preferred_providers'))
        features_score = self._score_features(deal, preferences)
        
        # Weighted composite score
        composite_score = (
            price_score * self.weights['price'] +
            speed_score * self.weights['speed'] +
            contract_score * self.weights['contract'] +
            provider_score * self.weights['provider'] +
            features_score * self.weights['features']
        )
        
        return round(composite_score, 2)
    
    def _extract_price(self, deal: Dict) -> Optional[float]:
        """Extract monthly price from deal."""
        try:
            price_str = deal.get('pricing', {}).get('monthly_cost', '')
            match = re.search(r'[\d.]+', price_str)
            if match:
                return float(match.group())
        except (ValueError, TypeError, AttributeError):
            pass
        return None
    
    def _extract_speed(self, deal: Dict) -> Optional[float]:
        """Extract speed from deal."""
        try:
            speed_str = deal.get('speed', {}).get('numeric', '')
            return float(speed_str)
        except (ValueError, TypeError):
            pass
        return None
    
    def _extract_contract_months(self, deal: Dict) -> Optional[int]:
        """Extract contract length in months."""
        try:
            contract_str = deal.get('contract', {}).get('length_numeric', '')
            return int(contract_str)
        except (ValueError, TypeError):
            pass
        return None
    
    def _score_price(self, price: Optional[float], max_budget: Optional[float]) -> float:
        """Score based on price (lower is better)."""
        if price is None:
            return 50.0  # Neutral score if price unknown
        
        # Price range: £20-£70 typical
        min_price, max_price = 20.0, 70.0
        
        # Normalize price (lower is better)
        if price <= min_price:
            score = 100.0
        elif price >= max_price:
            score = 0.0
        else:
            score = 100.0 * (1 - (price - min_price) / (max_price - min_price))
        
        # Apply budget constraint if specified
        if max_budget and price > max_budget:
            score *= 0.5  # Penalize over-budget deals
        
        return score
    
    def _score_speed(self, speed: Optional[float], min_speed: Optional[float]) -> float:
        """Score based on speed (higher is better)."""
        if speed is None:
            return 50.0  # Neutral score if speed unknown
        
        # Speed range: 10-1000 Mbps
        min_val, max_val = 10.0, 1000.0
        
        # Normalize speed (higher is better)
        if speed >= max_val:
            score = 100.0
        elif speed <= min_val:
            score = 20.0  # Low but not zero
        else:
            score = 20.0 + 80.0 * (speed - min_val) / (max_val - min_val)
        
        # Apply minimum speed requirement if specified
        if min_speed and speed < min_speed:
            score *= 0.3  # Heavy penalty for not meeting minimum
        
        return score
    
    def _score_contract(self, months: Optional[int], preferred: Optional[int]) -> float:
        """Score based on contract length."""
        if months is None:
            return 50.0  # Neutral score if unknown
        
        # Typical range: 12-24 months
        if preferred:
            # Score based on how close to preference
            diff = abs(months - preferred)
            score = max(0, 100.0 - (diff * 10))
        else:
            # Default: 12 months is ideal, 18 is okay, 24+ is less desirable
            if months <= 12:
                score = 100.0
            elif months <= 18:
                score = 75.0
            elif months <= 24:
                score = 50.0
            else:
                score = 25.0
        
        return score
    
    def _score_provider(self, provider: str, preferred_providers: Optional[List[str]]) -> float:
        """Score based on provider."""
        if not provider:
            return 50.0
        
        # If user has preferred providers
        if preferred_providers:
            if any(pref.lower() in provider.lower() for pref in preferred_providers):
                return 100.0
            return 30.0  # Penalty for non-preferred provider
        
        # Default provider reliability scores (based on typical reviews)
        provider_scores = {
            'bt': 75,
            'virgin media': 80,
            'sky': 85,
            'talktalk': 65,
            'plusnet': 70,
            'vodafone': 70,
            'ee': 80,
            'hyperoptic': 90,
            'community fibre': 95
        }
        
        provider_lower = provider.lower()
        for name, score in provider_scores.items():
            if name in provider_lower:
                return float(score)
        
        return 50.0  # Unknown provider
    
    def _score_features(self, deal: Dict, preferences: Optional[Dict]) -> float:
        """Score based on additional features."""
        score = 50.0  # Base score
        
        features = deal.get('features', {})
        
        # Bonus for unlimited usage
        usage = features.get('usage', '')
        if usage and 'unlimited' in usage.lower():
            score += 20.0
        
        # Bonus for phone calls
        phone_calls = features.get('phone_calls', '')
        if phone_calls and 'unlimited' in phone_calls.lower():
            score += 15.0
        
        # Bonus for callouts/special offers
        callouts = features.get('callouts', [])
        if callouts and len(callouts) > 0:
            score += 10.0
        
        # Connection type bonus (fibre is better)
        connection_type = features.get('connection_type', '')
        if connection_type:
            if 'fibre' in connection_type.lower():
                score += 10.0
            if 'full fibre' in connection_type.lower():
                score += 5.0  # Extra bonus for FTTP
        
        return min(score, 100.0)  # Cap at 100
    
    def _generate_reason(self, deal: Dict, score: float) -> str:
        """Generate a human-readable recommendation reason."""
        reasons = []
        
        price = self._extract_price(deal)
        speed = self._extract_speed(deal)
        provider = deal.get('provider', {}).get('name', 'Unknown')
        
        # Score-based reasoning
        if score >= 90:
            reasons.append("Excellent overall value")
        elif score >= 75:
            reasons.append("Great deal")
        elif score >= 60:
            reasons.append("Good option")
        
        # Price reasoning
        if price and price < 30:
            reasons.append("very affordable")
        elif price and price < 40:
            reasons.append("competitive price")
        
        # Speed reasoning
        if speed and speed >= 500:
            reasons.append("ultra-fast speeds")
        elif speed and speed >= 100:
            reasons.append("fast speeds")
        
        # Features reasoning
        features = deal.get('features', {})
        if features.get('usage', '').lower() == 'unlimited':
            reasons.append("unlimited data")
        
        if not reasons:
            reasons.append("suitable option")
        
        return f"{provider}: " + ", ".join(reasons)
    
    def compare_deals(self, deal1: Dict, deal2: Dict) -> Dict:
        """
        Compare two deals side by side.
        
        Args:
            deal1: First deal
            deal2: Second deal
            
        Returns:
            Comparison dictionary
        """
        comparison = {
            'deal1': {
                'provider': deal1.get('provider', {}).get('name', 'Unknown'),
                'price': self._extract_price(deal1),
                'speed': self._extract_speed(deal1),
                'contract': self._extract_contract_months(deal1),
                'score': self._calculate_deal_score(deal1)
            },
            'deal2': {
                'provider': deal2.get('provider', {}).get('name', 'Unknown'),
                'price': self._extract_price(deal2),
                'speed': self._extract_speed(deal2),
                'contract': self._extract_contract_months(deal2),
                'score': self._calculate_deal_score(deal2)
            }
        }
        
        # Determine winner
        if comparison['deal1']['score'] > comparison['deal2']['score']:
            comparison['winner'] = 'deal1'
            comparison['reason'] = f"Deal 1 has better overall value (score: {comparison['deal1']['score']} vs {comparison['deal2']['score']})"
        elif comparison['deal2']['score'] > comparison['deal1']['score']:
            comparison['winner'] = 'deal2'
            comparison['reason'] = f"Deal 2 has better overall value (score: {comparison['deal2']['score']} vs {comparison['deal1']['score']})"
        else:
            comparison['winner'] = 'tie'
            comparison['reason'] = "Both deals have similar value"
        
        return comparison


# Global instance for easy access
_recommendation_service = None


def get_recommendation_service() -> RecommendationService:
    """
    Get or create the global recommendation service instance.
    
    Returns:
        RecommendationService instance
    """
    global _recommendation_service
    if _recommendation_service is None:
        _recommendation_service = RecommendationService()
    return _recommendation_service

