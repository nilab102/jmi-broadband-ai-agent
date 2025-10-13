"""
Recommendation Engine - AI-powered broadband deal recommendations.
Generates scored recommendations based on user preferences and deal characteristics.
"""

from typing import Dict, List, Any, Optional
from loguru import logger


class RecommendationEngine:
    """
    AI-powered recommendation engine for broadband deals.
    Scores and ranks deals based on user preferences.
    """
    
    def __init__(self, recommendation_service=None):
        """
        Initialize recommendation engine.
        
        Args:
            recommendation_service: Optional recommendation service
        """
        self.recommendation_service = recommendation_service
    
    async def handle_get_recommendations(
        self,
        user_id: str,
        postcode: str = None,
        speed_in_mb: str = None,
        contract_length: str = None,
        phone_calls: str = None,
        product_type: str = None,
        providers: str = None,
        current_provider: str = None,
        new_line: str = None,
        context: str = None,
        conversation_state: Dict = None,
        recommendation_cache: Dict = None,
        scrape_data_fn=None,
        send_websocket_fn=None,
        create_output_fn=None
    ) -> str:
        """
        Handle AI-powered recommendations based on scraped data.
        
        Args:
            user_id: User ID
            postcode: Postcode
            speed_in_mb: Speed requirement
            contract_length: Contract length
            phone_calls: Phone calls preference
            product_type: Product type
            providers: Providers filter
            current_provider: Current provider
            new_line: New line option
            context: Additional context
            conversation_state: Conversation state dictionary
            recommendation_cache: Cache for recommendations
            scrape_data_fn: Function to scrape data
            send_websocket_fn: Function to send WebSocket messages
            create_output_fn: Function to create structured output
            
        Returns:
            Dictionary with recommendations or error message
        """
        try:
            # Get scraped data
            if not conversation_state or user_id not in conversation_state or 'scraped_data' not in conversation_state[user_id]:
                # Auto-scrape data if not available
                if scrape_data_fn:
                    postcode = postcode or 'E14 9WB'
                    await scrape_data_fn(
                        user_id=user_id,
                        postcode=postcode,
                        speed_in_mb=speed_in_mb,
                        contract_length=contract_length,
                        phone_calls=phone_calls,
                        product_type=product_type,
                        providers=providers,
                        current_provider=current_provider,
                        new_line=new_line,
                        context=context
                    )
                else:
                    return "❌ Unable to fetch broadband data. Please scrape data first."
                
                # Check if scraping was successful
                if not conversation_state or user_id not in conversation_state or 'scraped_data' not in conversation_state[user_id]:
                    return "❌ Unable to fetch broadband data. Please check your postcode and try again."
            
            data = conversation_state[user_id]['scraped_data']
            if not data or 'error' in data or data.get('total_deals', 0) == 0:
                if data and 'error' in data and 'Browser scraping not available' in data.get('error', ''):
                    return "❌ Data scraping is currently limited in this environment. Please use the generated URL to view deals directly."
                else:
                    return "❌ Unable to fetch broadband data for recommendations."
            
            deals = data.get('deals', [])
            
            if not deals:
                return "❌ No deals available for recommendations."
            
            # Generate recommendations based on user preferences
            recommendations = self.generate_recommendations(deals, {
                'speed': speed_in_mb,
                'contract': contract_length,
                'providers': providers,
                'phone_calls': phone_calls
            })
            
            # Cache recommendations
            if recommendation_cache is not None:
                cache_key = f"{user_id}_{postcode}_{speed_in_mb}"
                recommendation_cache[cache_key] = recommendations
            
            # Store in conversation state
            if conversation_state:
                conversation_state[user_id]['recommendations'] = recommendations
            
            # Create structured output
            if send_websocket_fn and create_output_fn:
                structured_output = create_output_fn(
                    user_id=user_id,
                    action_type="recommendations_generated",
                    param="total_recommendations,criteria",
                    value=f"{len(recommendations)},{postcode or 'unknown'},{speed_in_mb or 'unknown'}",
                    interaction_type="recommendation",
                    clicked=True,
                    element_name="get_recommendations",
                    context=context,
                    recommendations=recommendations,
                    total_recommendations=len(recommendations),
                    criteria={
                        'postcode': postcode,
                        'speed': speed_in_mb,
                        'contract': contract_length,
                        'providers': providers,
                        'phone_calls': phone_calls
                    }
                )
                
                await send_websocket_fn(
                    message_type="recommendation_action",
                    action="recommendations_generated",
                    data=structured_output
                )
            
            # Return structured data
            return {
                'status': 'success',
                'message': f'Generated {len(recommendations)} broadband recommendations',
                'data': {
                    'total_recommendations': len(recommendations),
                    'recommendations': recommendations[:5],  # Top 5 recommendations
                    'criteria': {
                        'postcode': postcode,
                        'speed': speed_in_mb,
                        'contract': contract_length,
                        'providers': providers,
                        'phone_calls': phone_calls
                    }
                },
                'suggestions': [
                    'Compare specific deals',
                    'Find the cheapest option',
                    'Show fastest deals',
                    'Refine your search criteria'
                ]
            }
        
        except Exception as e:
            logger.error(f"❌ Error generating recommendations: {e}")
            return f"❌ Error generating recommendations: {str(e)}"
    
    def generate_recommendations(self, deals: List[Dict], preferences: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Generate AI-powered recommendations based on user preferences.
        
        Args:
            deals: List of broadband deals
            preferences: User preferences dictionary
            
        Returns:
            List of recommendations sorted by score
        """
        recommendations = []
        
        for deal in deals:
            score = 0
            reasons = []
            
            # Speed scoring
            deal_speed = int(deal['speed']['numeric'])
            preferred_speed = preferences.get('speed') or '30Mb'
            if preferred_speed and 'Mb' in preferred_speed:
                target_speed = int(preferred_speed.replace('Mb', ''))
                if deal_speed >= target_speed:
                    score += 3
                    reasons.append("Meets speed requirement")
                elif deal_speed >= target_speed * 0.8:
                    score += 2
                    reasons.append("Close to speed requirement")
                else:
                    score += 1
                    reasons.append("Below preferred speed")
            
            # Contract length preference
            deal_contract = deal['contract']['length_months']
            preferred_contract = preferences.get('contract') or ''
            if preferred_contract and preferred_contract in deal_contract:
                score += 2
                reasons.append("Matches contract preference")
            
            # Provider preference
            preferred_providers = preferences.get('providers') or ''
            if preferred_providers:
                provider_list = [p.strip() for p in preferred_providers.split(',')]
                if deal['provider']['name'] in provider_list:
                    score += 2
                    reasons.append("Preferred provider")
            
            # Price scoring (lower is better)
            monthly_cost = float(deal['pricing']['monthly_cost'].replace('£', '').replace(',', ''))
            if monthly_cost <= 25:
                score += 3
                reasons.append("Great value")
            elif monthly_cost <= 35:
                score += 2
                reasons.append("Good value")
            else:
                score += 1
                reasons.append("Premium price")
            
            # Setup cost bonus
            setup_cost = deal['pricing']['setup_costs']
            if setup_cost == '£0.00':
                score += 1
                reasons.append("No setup fee")
            
            # Phone calls preference
            preferred_calls = preferences.get('phone_calls') or 'Show me everything'
            if preferred_calls and preferred_calls != 'Show me everything':
                deal_calls = deal['features']['phone_calls']
                if preferred_calls.lower() in deal_calls.lower():
                    score += 1
                    reasons.append("Matches call preference")
            
            recommendations.append({
                'deal': deal,
                'score': score,
                'reasons': reasons
            })
        
        # Sort by score (highest first)
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return recommendations


def create_recommendation_engine(recommendation_service=None) -> RecommendationEngine:
    """
    Factory function to create a RecommendationEngine instance.
    
    Args:
        recommendation_service: Optional recommendation service
        
    Returns:
        RecommendationEngine instance
    """
    return RecommendationEngine(recommendation_service)

