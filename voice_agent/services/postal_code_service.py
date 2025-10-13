"""
Postal Code Service - Handles postal code validation and fuzzy matching.
Wraps the fuzzy_postal_code module for clean service-oriented architecture.
"""

import sys
import os
from typing import Dict, List, Tuple, Optional
from loguru import logger

try:
    from voice_agent.lib.fuzzy_postal_code import FastPostalCodeSearch
    FUZZY_SEARCH_AVAILABLE = True
except ImportError:
    FUZZY_SEARCH_AVAILABLE = False
    logger.warning("⚠️ Fuzzy postal code search module not available")


class PostalCodeService:
    """
    Service for postal code validation and fuzzy matching.
    Provides a clean interface for postal code operations.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls, connection_string: Optional[str] = None):
        """Singleton pattern to ensure only one instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize the postal code service.
        
        Args:
            connection_string: PostgreSQL connection string for postal code database
        """
        if self._initialized:
            return
        
        self.connection_string = connection_string or os.getenv(
            'POSTAL_CODE_DB_CONNECTION',
            "postgresql://postgres.jluuralqpnexhxlcuewz:HIiamjami1234@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
        )
        
        self.searcher = None
        self._init_searcher()
        
        PostalCodeService._initialized = True
    
    def _init_searcher(self):
        """Initialize the fuzzy search engine."""
        if not FUZZY_SEARCH_AVAILABLE:
            logger.warning("⚠️ Fuzzy search not available - postal code service will use basic validation")
            return
        
        try:
            self.searcher = FastPostalCodeSearch(self.connection_string)
            logger.info("✅ Postal code service initialized with fuzzy search")
        except Exception as e:
            logger.error(f"❌ Failed to initialize fuzzy postal code searcher: {e}")
            self.searcher = None
    
    def normalize_postcode(self, postcode: str) -> str:
        """
        Normalize a postcode to standard format.
        
        Args:
            postcode: Raw postcode string
            
        Returns:
            Normalized postcode (uppercase, no spaces)
        """
        if not postcode:
            return ""
        
        if FUZZY_SEARCH_AVAILABLE and self.searcher:
            return FastPostalCodeSearch.normalize_postcode(postcode)
        else:
            # Fallback normalization
            import re
            return re.sub(r'[^A-Z0-9]', '', postcode.upper())
    
    def validate_postcode(self, postcode: str) -> Tuple[bool, str]:
        """
        Validate if a postcode is in correct UK format.
        
        Args:
            postcode: Postcode to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not postcode or not postcode.strip():
            return False, "Postcode is required"
        
        # UK postcode regex pattern
        uk_postcode_pattern = r'^[A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2}$'
        
        import re
        normalized = self.normalize_postcode(postcode)
        
        # Add space for validation (UK format: "AA9A 9AA")
        if len(normalized) >= 5:
            spaced = f"{normalized[:-3]} {normalized[-3:]}"
            if re.match(uk_postcode_pattern, spaced, re.IGNORECASE):
                return True, ""
        
        return False, f"Invalid UK postcode format: {postcode}"
    
    def fuzzy_search(
        self,
        search_term: str,
        top_n: int = 20,
        max_candidates: int = 2000,
        use_dynamic_distance: bool = True,
        use_weighted_scoring: bool = True,
        parallel_threshold: int = 500
    ) -> Dict:
        """
        Perform fuzzy search for postal codes.
        
        Args:
            search_term: Postcode to search for
            top_n: Number of results to return
            max_candidates: Maximum candidates to evaluate
            use_dynamic_distance: Auto-adjust search distance
            use_weighted_scoring: Boost prefix matches
            parallel_threshold: Min candidates for parallel processing
            
        Returns:
            Dictionary with results and metadata
        """
        if not self.searcher:
            return {
                'results': [],
                'metadata': {
                    'error': 'Fuzzy search not available',
                    'search_time_ms': 0
                }
            }
        
        try:
            result = self.searcher.get_fuzzy_results(
                search_term=search_term,
                top_n=top_n,
                max_candidates=max_candidates,
                use_dynamic_distance=use_dynamic_distance,
                use_weighted_scoring=use_weighted_scoring,
                parallel_threshold=parallel_threshold
            )
            return result
        except Exception as e:
            logger.error(f"❌ Fuzzy search error: {e}")
            return {
                'results': [],
                'metadata': {
                    'error': str(e),
                    'search_time_ms': 0
                }
            }
    
    def get_best_match(
        self,
        search_term: str,
        min_score: float = 80.0,
        auto_select_threshold: float = 95.0
    ) -> Tuple[Optional[str], Optional[float], bool]:
        """
        Get the best matching postcode with auto-selection logic.
        
        Args:
            search_term: Postcode to search for
            min_score: Minimum acceptable match score
            auto_select_threshold: Score threshold for auto-selection
            
        Returns:
            Tuple of (best_postcode, score, was_auto_selected)
        """
        # First try exact match
        normalized = self.normalize_postcode(search_term)
        
        # Perform fuzzy search
        result = self.fuzzy_search(search_term, top_n=5)
        
        if not result.get('results'):
            return None, None, False
        
        best_match, best_score = result['results'][0]
        
        # Auto-select if score is high enough
        if best_score >= auto_select_threshold:
            logger.info(f"✅ Auto-selected postcode: {best_match} (score: {best_score:.1f}%)")
            return best_match, best_score, True
        
        # Check if score meets minimum threshold
        if best_score >= min_score:
            logger.info(f"🟡 Best match found: {best_match} (score: {best_score:.1f}%), requires confirmation")
            return best_match, best_score, False
        
        logger.warning(f"⚠️ No good match found for: {search_term} (best score: {best_score:.1f}%)")
        return None, None, False
    
    def get_top_matches(
        self,
        search_term: str,
        top_n: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Get top N matching postcodes.
        
        Args:
            search_term: Postcode to search for
            top_n: Number of results to return
            
        Returns:
            List of (postcode, score) tuples
        """
        result = self.fuzzy_search(search_term, top_n=top_n)
        return result.get('results', [])
    
    def shutdown(self):
        """Shutdown the service and cleanup resources."""
        if self.searcher and hasattr(self.searcher, 'shutdown'):
            self.searcher.shutdown()
            logger.info("✅ Postal code service shut down")


# Global instance for easy access
_postal_code_service = None


def get_postal_code_service(connection_string: Optional[str] = None) -> PostalCodeService:
    """
    Get or create the global postal code service instance.
    
    Args:
        connection_string: Optional database connection string
        
    Returns:
        PostalCodeService instance
    """
    global _postal_code_service
    if _postal_code_service is None:
        _postal_code_service = PostalCodeService(connection_string)
    return _postal_code_service

