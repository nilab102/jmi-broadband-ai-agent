"""
Provider Matching - Fuzzy matching for broadband provider names.
Handles typos and variations in provider names using fuzzy search.
"""

from typing import Optional, List, Dict
from loguru import logger


class ProviderMatcher:
    """
    Fuzzy matcher for broadband provider names.
    Handles typos, abbreviations, and variations in provider names.
    """
    
    def __init__(self, valid_providers: List[str], fuzzy_searcher=None):
        """
        Initialize provider matcher.
        
        Args:
            valid_providers: List of valid provider names
            fuzzy_searcher: Optional fuzzy search service
        """
        self.valid_providers = valid_providers or []
        self.fuzzy_searcher = fuzzy_searcher
        self.cache: Dict[str, Optional[str]] = {}
        
    def fuzzy_match(self, provider_input: str, threshold: float = 50.0) -> Optional[str]:
        """
        Fuzzy match provider name using fuzzy search infrastructure.
        
        Args:
            provider_input: Raw provider name input from user
            threshold: Minimum similarity threshold (default: 50%)
            
        Returns:
            Best matching provider name or None if no match above threshold
        """
        if not provider_input or not provider_input.strip():
            return None
        
        # Check cache first
        cache_key = f"{provider_input.strip().lower()}_{threshold}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Check for exact match first (case-insensitive)
        provider_lower = provider_input.strip().lower()
        for valid_provider in self.valid_providers:
            if provider_lower == valid_provider.lower():
                self.cache[cache_key] = valid_provider
                return valid_provider

        # Check for common abbreviations and partial matches (fallback when fuzzy search unavailable)
        provider_abbreviations = {
            'virgin': 'Virgin Media',
            'vergin': 'Virgin Media',  # Common typo
            'bt': 'BT',
            'sky': 'Sky',
            'talktalk': 'TalkTalk',
            'talk talk': 'TalkTalk',
            'plusnet': 'Plusnet',
            'vodafone': 'Vodafone',
            'hyperoptic': 'Hyperoptic',
            'community fibre': 'Community Fibre',
            '4th utility': '4th Utility',
            'lightspeed': 'Lightspeed',
            'airband': 'Airband',
            'now broadband': 'NOW Broadband',
            'muuvo': 'Muuvo'
        }

        # Check abbreviations
        if provider_lower in provider_abbreviations:
            self.cache[cache_key] = provider_abbreviations[provider_lower]
            return provider_abbreviations[provider_lower]

        # Check if input is contained in any valid provider name
        for valid_provider in self.valid_providers:
            if provider_lower in valid_provider.lower():
                self.cache[cache_key] = valid_provider
                return valid_provider

        # Check if any valid provider name starts with the input
        for valid_provider in self.valid_providers:
            if valid_provider.lower().startswith(provider_lower):
                self.cache[cache_key] = valid_provider
                return valid_provider

        # Check for common typos using simple edit distance (for short inputs)
        if len(provider_lower) <= 10:  # Only for reasonably short inputs
            for valid_provider in self.valid_providers:
                valid_lower = valid_provider.lower()
                # Check for single character differences
                if len(valid_lower) == len(provider_lower):
                    # Same length - check for 1-2 character differences
                    diff_count = sum(1 for a, b in zip(valid_lower, provider_lower) if a != b)
                    if diff_count <= 2:
                        self.cache[cache_key] = valid_provider
                        return valid_provider
                elif abs(len(valid_lower) - len(provider_lower)) == 1:
                    # Length difference of 1 - check if one is substring of the other
                    if provider_lower in valid_lower or valid_lower in provider_lower:
                        self.cache[cache_key] = valid_provider
                        return valid_provider

        # Use fuzzy search if available
        if not self.fuzzy_searcher:
            logger.warning("⚠️ Fuzzy search not available for provider matching")
            self.cache[cache_key] = None
            return None
        
        try:
            # Use fuzzy search with provider names as search space
            result = self.fuzzy_searcher.get_fuzzy_results(
                search_term=provider_input,
                top_n=1,  # Only need the top match
                max_candidates=50,  # Limit for performance
                use_dynamic_distance=True,
                use_weighted_scoring=True,
                parallel_threshold=20
            )
            
            if result['results']:
                matched_provider, score = result['results'][0]
                
                # Check if score is above threshold
                if score >= threshold:
                    logger.info(f"🔍 Fuzzy matched '{provider_input}' to '{matched_provider}' (score: {score:.1f}%)")
                    self.cache[cache_key] = matched_provider
                    return matched_provider
                else:
                    logger.info(f"🔍 Provider '{provider_input}' below threshold (score: {score:.1f}%, threshold: {threshold}%)")
                    self.cache[cache_key] = None
                    return None
            else:
                self.cache[cache_key] = None
                return None
        
        except Exception as e:
            logger.error(f"❌ Error in fuzzy provider matching: {e}")
            self.cache[cache_key] = None
            return None
    
    def extract_provider_with_fuzzy(self, match: str) -> str:
        """
        Extract provider name using fuzzy matching.
        Used as a processor function in parameter patterns.
        
        Args:
            match: The matched string from regex pattern
            
        Returns:
            Best matching provider name or empty string if no match
        """
        if not match or not match.strip():
            return ""
        
        # Use fuzzy matching to find the best provider match
        matched_provider = self.fuzzy_match(match.strip(), threshold=50.0)
        
        if matched_provider:
            logger.info(f"🔍 Extracted provider via fuzzy matching: '{match}' -> '{matched_provider}'")
            return matched_provider
        else:
            logger.info(f"🔍 No provider match found for: '{match}'")
            return ""
    
    def extract_providers_with_fuzzy(self, match: str) -> str:
        """
        Extract multiple provider names using fuzzy matching.
        Handles comma-separated provider lists.
        
        Args:
            match: The matched string from regex pattern (may contain multiple providers)
            
        Returns:
            Comma-separated string of matched provider names or empty string if no matches
        """
        if not match or not match.strip():
            return ""
        
        # Split by comma and process each provider
        provider_parts = [p.strip() for p in match.split(',') if p.strip()]
        matched_providers = []
        
        for provider in provider_parts:
            if provider:
                matched_provider = self.fuzzy_match(provider, threshold=50.0)
                if matched_provider:
                    matched_providers.append(matched_provider)
        
        if matched_providers:
            result = ','.join(matched_providers)
            logger.info(f"🔍 Extracted providers via fuzzy matching: '{match}' -> '{result}'")
            return result
        else:
            logger.info(f"🔍 No provider matches found for: '{match}'")
            return ""
    
    def clear_cache(self):
        """Clear the provider matching cache."""
        self.cache.clear()
        logger.info("🗑️ Provider matching cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache size and hit rate
        """
        return {
            'cache_size': len(self.cache),
            'valid_providers_count': len(self.valid_providers)
        }


def create_provider_matcher(valid_providers: List[str], fuzzy_searcher=None) -> ProviderMatcher:
    """
    Factory function to create a ProviderMatcher instance.
    
    Args:
        valid_providers: List of valid provider names
        fuzzy_searcher: Optional fuzzy search service
        
    Returns:
        ProviderMatcher instance
    """
    return ProviderMatcher(
        valid_providers=valid_providers,
        fuzzy_searcher=fuzzy_searcher
    )

