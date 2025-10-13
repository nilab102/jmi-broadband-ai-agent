"""
Parameter Extraction - Extract broadband parameters from natural language queries.
Uses AI-powered extraction with regex fallback for robustness.
"""

import re
from typing import Dict, Optional, List, Tuple, Any
from loguru import logger

from .helpers import (
    interpret_speed_adjective,
    interpret_phone_calls,
    interpret_product_type,
    interpret_sort_preference,
    extract_contract_lengths,
    normalize_contract_single
)


class ParameterExtractor:
    """
    Extract broadband parameters from natural language queries.
    Supports both AI-powered extraction and regex-based fallback.
    """
    
    def __init__(self, ai_extractor=None, provider_matcher=None):
        """
        Initialize parameter extractor.
        
        Args:
            ai_extractor: Optional AI extraction service
            provider_matcher: Optional ProviderMatcher instance for fuzzy matching
        """
        self.ai_extractor = ai_extractor
        self.provider_matcher = provider_matcher
        self.patterns: Dict[str, List[Tuple[str, str, Any]]] = {}
        
    def initialize_patterns(self):
        """
        Initialize regex patterns for parameter extraction.
        Must be called after provider_matcher is set.
        """
        if not self.provider_matcher:
            logger.warning("⚠️ Provider matcher not set - provider extraction will be limited")
        
        self.patterns = {
            'postcode': [
                # Most specific UK postcode patterns first
                (r'\b([A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2})\b', 'postcode', lambda x: x.strip().upper()),
                (r'\b([A-Z]{1,2}[0-9]{1,2}[A-Z0-9]{0,3})\b', 'postcode', lambda x: x.strip().upper()),
                # Location at end patterns
                (r'\b([A-Za-z]+(?:\s+[A-Za-z]+)?)\s*$', 'postcode', lambda x: x.strip().upper()),
                (r'\b([A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2})\s*$', 'postcode', lambda x: x.strip().upper()),
                # Fallback patterns
                (r'\b([A-Za-z0-9]{2,7})\b', 'postcode', lambda x: x.strip().upper()),
                (r'postcode[:\s]*([A-Za-z0-9\s]{2,10})', 'postcode', lambda x: x.strip().upper()),
            ],
            'speed_in_mb': [
                (r'(\d+)\s*mb?\s*speed', 'speed_in_mb', lambda x: f"{x}Mb"),
                (r'speed[:\s]*(\d+)\s*mb?', 'speed_in_mb', lambda x: f"{x}Mb"),
                (r'(\d+)\s*mb?\s*broadband', 'speed_in_mb', lambda x: f"{x}Mb"),
                (r'(\d+)\s*meg', 'speed_in_mb', lambda x: f"{x}Mb"),
                (r'fast|superfast|ultrafast', 'speed_in_mb', interpret_speed_adjective),
            ],
            'contract_length': [
                # Broad patterns to capture multiple contract lengths (must come first)
                (r'(?:contract[:\s]*)?(\d+(?:\s*(?:or|and|,)\s*\d+)+.*?months?)', 'contract_length', extract_contract_lengths),
                (r'(?:contract[:\s]*)?(\d+.*?months?\s*,.*?months?)', 'contract_length', extract_contract_lengths),
                # Single contract lengths (existing patterns)
                (r'(\d+)\s*month\s*contract', 'contract_length', normalize_contract_single),
                (r'contract[:\s]*(\d+)\s*month', 'contract_length', normalize_contract_single),
                (r'(\d+)\s*months?', 'contract_length', normalize_contract_single),
            ],
            'phone_calls': [
                (r'phone\s*calls?[:\s]*(\w+)', 'phone_calls', lambda x: x.title()),
                (r'(evening|weekend|anytime|unlimited)\s*calls?', 'phone_calls', interpret_phone_calls),
                (r'no\s*(inclusive\s*)?calls?', 'phone_calls', lambda x: "No inclusive"),
                (r'cheapest\s*calls?', 'phone_calls', lambda x: "Cheapest"),
            ],
            'product_type': [
                (r'(broadband|phone|tv)\s*only', 'product_type', interpret_product_type),
                (r'(broadband|phone|tv)\s*and\s*(broadband|phone|tv)', 'product_type', interpret_product_type),
            ],
            'sort_by': [
                (r'sort\s*by\s*(\w+)', 'sort_by', lambda x: x.title()),
                (r'cheapest|fastest|recommended', 'sort_by', interpret_sort_preference),
            ],
            'new_line': [
                # Direct new line requests
                (r'new\s*line[:\s]*(\w+)', 'new_line', lambda x: "NewLine" if x.lower() in ["yes", "true", "new", "line", "installation", "cost"] else ""),
                (r'include\s*new\s*line', 'new_line', lambda x: "NewLine"),
                (r'new\s*line\s*cost', 'new_line', lambda x: "NewLine"),
                (r'new\s*line\s*installation', 'new_line', lambda x: "NewLine"),
                # Common conversational patterns
                (r'add\s*new\s*line', 'new_line', lambda x: "NewLine"),
                (r'with\s*new\s*line', 'new_line', lambda x: "NewLine"),
                (r'want\s*new\s*line', 'new_line', lambda x: "NewLine"),
                (r'need\s*new\s*line', 'new_line', lambda x: "NewLine"),
                (r'new\s*line\s*please', 'new_line', lambda x: "NewLine"),
                (r'new\s*line\s*option', 'new_line', lambda x: "NewLine"),
                # Negation patterns (set to empty)
                (r'existing\s*line|no\s*new\s*line', 'new_line', lambda x: ""),
            ],
            # Filter modification patterns
            'filter_speed': [
                (r'(?:set\s+)?speed\s*(?:to\s+)?(\d+)\s*mb?', 'filter_speed', lambda x: f"{x}Mb"),
                (r'(?:change\s+)?speed\s*(?:to\s+)?(\d+)\s*mb?', 'filter_speed', lambda x: f"{x}Mb"),
                (r'(\d+)\s*mb?\s*speed', 'filter_speed', lambda x: f"{x}Mb"),
            ],
            'filter_contract': [
                (r'(?:set\s+)?contract\s*(?:to\s+)?(\d+)\s*months?', 'filter_contract', lambda x: f"{x} months"),
                (r'(?:change\s+)?contract\s*(?:to\s+)?(\d+)\s*months?', 'filter_contract', lambda x: f"{x} months"),
            ],
            'filter_phone_calls': [
                (r'(?:set\s+)?phone\s*calls?\s*(?:to\s+)?(\w+)', 'filter_phone_calls', lambda x: x.title()),
                (r'(?:change\s+)?phone\s*calls?\s*(?:to\s+)?(\w+)', 'filter_phone_calls', lambda x: x.title()),
            ],
            'filter_new_line': [
                (r'(?:set\s+)?new\s*line\s*(?:to\s+)?(\w+)', 'filter_new_line', lambda x: "NewLine" if x.lower() in ["yes", "true", "new", "line"] else ""),
                (r'(?:change\s+)?new\s*line\s*(?:to\s+)?(\w+)', 'filter_new_line', lambda x: "NewLine" if x.lower() in ["yes", "true", "new", "line"] else ""),
            ],
        }
        
        # Add provider patterns if provider matcher is available
        if self.provider_matcher:
            self.patterns['providers'] = [
                (r'(\w+(?:\s+\w+)*)\s*broadband', 'providers', self.provider_matcher.extract_provider_with_fuzzy),
                (r'with\s+(\w+(?:\s+\w+)*)', 'providers', self.provider_matcher.extract_provider_with_fuzzy),
                (r'from\s+(\w+(?:\s+\w+)*)', 'providers', self.provider_matcher.extract_provider_with_fuzzy),
                (r'(\w+(?:\s+\w+)*)', 'providers', self.provider_matcher.extract_provider_with_fuzzy),
            ]
            
            self.patterns['filter_providers'] = [
                (r'(?:set\s+)?providers?\s*(?:to\s+)?([A-Za-z\s,]+)', 'filter_providers', self.provider_matcher.extract_providers_with_fuzzy),
                (r'(?:change\s+)?providers?\s*(?:to\s+)?([A-Za-z\s,]+)', 'filter_providers', self.provider_matcher.extract_providers_with_fuzzy),
                (r'only\s+([A-Za-z\s,]+)', 'filter_providers', self.provider_matcher.extract_providers_with_fuzzy),
            ]
            
            self.patterns['current_provider'] = [
                (r'current\s*provider\s*(?:is\s*)?([A-Za-z\s]+)', 'current_provider', self.provider_matcher.extract_provider_with_fuzzy),
                (r'existing\s*provider\s*(?:is\s*)?([A-Za-z\s]+)', 'current_provider', self.provider_matcher.extract_provider_with_fuzzy),
                (r'my\s*current\s*provider\s*(?:is\s*)?([A-Za-z\s]+)', 'current_provider', self.provider_matcher.extract_provider_with_fuzzy),
                (r'switching\s*from\s+([A-Za-z\s]+)', 'current_provider', self.provider_matcher.extract_provider_with_fuzzy),
                (r'currently\s*with\s+([A-Za-z\s]+)', 'current_provider', self.provider_matcher.extract_provider_with_fuzzy),
                (r'leaving\s+([A-Za-z\s]+)', 'current_provider', self.provider_matcher.extract_provider_with_fuzzy),
                (r'currentProvider[:=]\s*([A-Za-z0-9\s%]+)', 'current_provider', self.provider_matcher.extract_provider_with_fuzzy),
            ]
        
        logger.info(f"✅ Parameter patterns initialized with {len(self.patterns)} parameter types")
    
    def extract_parameters(self, query: str, skip_postcode_validation: bool = False) -> Dict[str, str]:
        """
        Extract broadband parameters from natural language query.
        Uses AI-powered extraction (preferred) with regex fallback.

        Args:
            query: Natural language query
            skip_postcode_validation: If True, skip automatic postcode validation

        Returns:
            Dictionary of extracted parameters
        """
        # Validate query parameter
        if not query or not isinstance(query, str) or not query.strip():
            logger.warning("⚠️ Empty or invalid query provided for parameter extraction")
            return self._get_default_params()

        # Try AI extraction first (preferred method)
        if self.ai_extractor:
            try:
                logger.info(f"🤖 Using AI parameter extraction for: {query[:50]}...")

                # Use synchronous extraction
                ai_params = self.ai_extractor.extract_parameters_sync(query, context=None)

                # Check confidence
                if ai_params.confidence and ai_params.confidence >= 0.5:
                    # Convert to dictionary and apply defaults
                    extracted = ai_params.to_dict()

                    # Set defaults for missing parameters
                    extracted = self._apply_defaults(extracted)

                    # Remove 'intent' key as it's not used in URL generation
                    extracted.pop('intent', None)

                    logger.info(f"✅ AI extraction successful (confidence: {ai_params.confidence:.2f}): {extracted}")
                    return extracted
                else:
                    logger.warning(f"⚠️ AI extraction confidence too low ({ai_params.confidence}), falling back to regex")

            except Exception as e:
                logger.warning(f"⚠️ AI extraction failed, falling back to regex: {e}")

        # Fallback to regex-based extraction
        logger.info(f"📡 Using regex-based parameter extraction for: {query[:50]}...")
        return self._extract_with_regex(query, skip_postcode_validation)
    
    def _extract_with_regex(self, query: str, skip_postcode_validation: bool = False) -> Dict[str, str]:
        """
        Legacy regex-based parameter extraction (fallback method).

        Args:
            query: Natural language query
            skip_postcode_validation: If True, skip automatic postcode validation

        Returns:
            Dictionary of extracted parameters
        """
        # Additional validation for regex extraction
        if not query or not isinstance(query, str) or not query.strip():
            logger.warning("⚠️ Empty or invalid query provided for regex extraction")
            return self._get_default_params()

        query_lower = query.lower()
        extracted = {}

        # Extract parameters using patterns
        for param_type, patterns in self.patterns.items():
            for pattern, key, processor in patterns:
                match = re.search(pattern, query_lower, re.IGNORECASE)
                if match:
                    try:
                        processed_value = processor(match.group(1) if match.groups() else match.group(0))
                        if processed_value:
                            # Only set if not already set (for regular params) or always set (for filter params)
                            if key not in extracted:
                                extracted[key] = processed_value
                            elif key.startswith('filter_'):
                                # For filter parameters, always update
                                extracted[key] = processed_value
                            break
                    except Exception as e:
                        logger.warning(f"⚠️ Error processing pattern for {key}: {e}")
                        continue

        # Handle special cases and defaults
        if 'postcode' not in extracted:
            # Extract postcode from query (without fuzzy search for now)
            postcode_match = self._extract_postcode_from_query(query)
            if postcode_match:
                extracted['postcode'] = postcode_match

        # Apply defaults
        extracted = self._apply_defaults(extracted)

        logger.info(f"📡 Regex extracted parameters from query '{query[:50]}...': {extracted}")
        return extracted

    def _get_default_params(self) -> Dict[str, str]:
        """
        Get default parameters when extraction fails or query is invalid.

        Returns:
            Dictionary with default broadband parameters
        """
        return {
            'postcode': '',
            'speed_in_mb': '30Mb',
            'contract_length': '',
            'phone_calls': 'Show me everything',
            'product_type': 'broadband,phone',
            'providers': '',
            'current_provider': '',
            'sort_by': 'Recommended',
            'new_line': ''
        }

    def _extract_postcode_from_query(self, query: str) -> Optional[str]:
        """
        Extract postcode-like string from query without validation.
        This is the first step before fuzzy search.
        
        Args:
            query: Natural language query
            
        Returns:
            Postcode-like string or None if not found
        """
        # Simple pattern to find postcode-like strings
        patterns = [
            r'\b([A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2})\b',  # Full UK postcode format
            r'\b([A-Z]{1,2}[0-9]{1,2}[A-Z0-9]{0,3})\b',  # Partial postcode
            r'\b([A-Za-z]{1,2}[0-9]{1,2}\s?[0-9]?[A-Za-z]{0,3})\b',  # Flexible postcode-like
        ]
        
        query_upper = query.upper()
        for pattern in patterns:
            match = re.search(pattern, query_upper)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _apply_defaults(self, extracted: Dict[str, Any]) -> Dict[str, str]:
        """
        Apply default values for missing parameters.
        
        Args:
            extracted: Dictionary of extracted parameters
            
        Returns:
            Dictionary with defaults applied
        """
        defaults = {
            'speed_in_mb': '30Mb',
            'contract_length': '',
            'phone_calls': 'Show me everything',
            'product_type': 'broadband,phone',
            'providers': '',
            'current_provider': '',
            'sort_by': 'Recommended',
            'new_line': ''
        }
        
        for key, default_value in defaults.items():
            if key not in extracted or extracted[key] is None:
                extracted[key] = default_value
        
        return extracted


def create_parameter_extractor(ai_extractor=None, provider_matcher=None) -> ParameterExtractor:
    """
    Factory function to create a ParameterExtractor instance.
    
    Args:
        ai_extractor: Optional AI extraction service
        provider_matcher: Optional ProviderMatcher instance
        
    Returns:
        ParameterExtractor instance with patterns initialized
    """
    extractor = ParameterExtractor(
        ai_extractor=ai_extractor,
        provider_matcher=provider_matcher
    )
    extractor.initialize_patterns()
    return extractor

