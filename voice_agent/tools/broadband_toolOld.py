#!/usr/bin/env python3
"""
Broadband Tool for voice-agent voice backend.
Handles natural language queries about broadband requirements, generates comparison URLs,
scrapes data, and provides AI-powered recommendations with fuzzy postal code validation.
"""

import re
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import quote_plus
from datetime import datetime
from loguru import logger
from pipecat.processors.frameworks.rtvi import RTVIProcessor
from pipecat.adapters.schemas.function_schema import FunctionSchema

# Import the URL generator and constants
from voice_agent.broadband_url_generator import (
    BroadbandURLGenerator, BroadbandConstants,
    BroadbandSearchParams, ParameterValidator, URLEncoder,
    InvalidPostcodeError, InvalidSpeedError, InvalidContractLengthError,
    InvalidPhoneCallsError, InvalidProductTypeError, InvalidProviderError,
    InvalidSortOptionError, InvalidNewLineError
)

# Import the scraper
from jmi_scrapper import BroadbandScraper

# Import fuzzy search (will be initialized by the server)
try:
    from fuzzy_postal_code import FastPostalCodeSearch
    FUZZY_SEARCH_AVAILABLE = True
except ImportError:
    FUZZY_SEARCH_AVAILABLE = False
    logger.warning("⚠️ Fuzzy postal code search not available - will use basic validation")

# Import AI parameter extraction service
try:
    from .parameter_extraction_service import get_parameter_extractor, BroadbandParameters
    AI_EXTRACTION_AVAILABLE = True
except ImportError as e:
    AI_EXTRACTION_AVAILABLE = False
    logger.warning(f"⚠️ AI parameter extraction not available - will use regex fallback: {e}")

from .base_tool import BaseTool


class BroadbandTool(BaseTool):
    """
    Tool for handling broadband comparison queries with natural language processing,
    URL generation, data scraping, and AI-powered recommendations.
    """

    def __init__(self, rtvi_processor: RTVIProcessor, task=None, initial_current_page: str = "broadband"):
        super().__init__(rtvi_processor, task, initial_current_page)
        self.page_name = "broadband"
        self.available_buttons = [
            "search_deals", "get_recommendations", "compare_providers",
            "find_cheapest", "find_fastest", "refine_search", "list_providers"
        ]

        # Initialize components
        self.url_generator = BroadbandURLGenerator()
        self.scraper = BroadbandScraper(headless=True, timeout=30000)

        # Conversation state management
        self.conversation_state: Dict[str, Dict[str, Any]] = {}
        self.scraped_data_cache: Dict[str, Dict[str, Any]] = {}
        self.recommendation_cache: Dict[str, List[Dict[str, Any]]] = {}

        # Filter state management
        self.filter_state: Dict[str, Dict[str, Any]] = {}

        # Fuzzy search system (will be initialized by server)
        self.fuzzy_searcher = None

        # Get fuzzy searcher from router module if available
        try:
            import voice_agent.core.router as router_module
            if hasattr(router_module, 'fuzzy_searcher'):
                self.fuzzy_searcher = router_module.fuzzy_searcher
                logger.info("✅ Fuzzy postal code search connected to broadband tool")
        except Exception as e:
            logger.warning(f"⚠️ Could not connect to fuzzy searcher: {e}")

        # Provider fuzzy matching cache
        self.provider_fuzzy_cache = {}

        # AI Parameter Extractor (preferred method)
        self.ai_extractor = None
        if AI_EXTRACTION_AVAILABLE:
            try:
                self.ai_extractor = get_parameter_extractor()
                logger.info("✅ AI parameter extraction enabled")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize AI parameter extractor: {e}")

        # Parameter extraction patterns (fallback for regex-based extraction)
        self.parameter_patterns = self._initialize_parameter_patterns()

        # Load provider names for fuzzy matching
        from voice_agent.broadband_url_generator import BroadbandConstants
        self.valid_providers = BroadbandConstants.VALID_PROVIDERS

    def _create_structured_output(self, user_id: str, action_type: str, param: str, value: str,
                                 interaction_type: str, **additional_fields) -> Dict[str, Any]:
        """Create clean structured output for broadband tool, excluding unnecessary fields."""
        session = self._initialize_user_session(user_id)

        # Base output without unnecessary fields
        base_output = {
            "Action_type": action_type,
            "param": param,
            "value": value,
            "page": session.get("current_page", self.initial_current_page),
            "previous_page": session.get("previous_page"),
            "interaction_type": interaction_type,
            "timestamp": self._get_timestamp(),
            "user_id": user_id,
            "success": True,
            "error_message": None
        }

        # Add additional fields (these override defaults if they exist)
        merged_output = {**base_output, **additional_fields}

        # Convert list/dict values to JSON strings, but keep specific fields as proper JSON objects
        json_object_fields = {
            "scraped_data", "recommendations", "criteria", "total_recommendations",
            "providers_compared", "matching_deals", "total_matches", "cheapest_deal",
            "fastest_deal", "total_deals_analyzed", "current_parameters", "refinement_options",
            "required_parameters", "extracted_params", "generated_url", "generated_params",
            "filtered_data", "applied_filters", "total_filtered", "postcode_suggestions"
        }

        for key, value in merged_output.items():
            if isinstance(value, (list, dict)):
                if key in json_object_fields:
                    # Keep these fields as proper JSON objects, not strings
                    continue
                else:
                    merged_output[key] = json.dumps(value)

        return merged_output

    def _validate_uk_postcode_format(self, postcode: str) -> bool:
        """
        Validate UK postcode format using official regex pattern.
        This checks if the postcode matches UK postcode structure before fuzzy search.
        
        Pattern covers:
        - GIR 0AA (special case)
        - Standard UK formats (A9 9AA, A99 9AA, AA9 9AA, AA99 9AA, A9A 9AA, AA9A 9AA)
        
        Args:
            postcode: Postcode string to validate
            
        Returns:
            True if valid UK postcode format, False otherwise
        """
        if not postcode or not postcode.strip():
            return False
        
        # UK postcode regex pattern (allows spaces)
        uk_postcode_pattern = r'^((GIR\s*0AA)|[A-Z]{1}\d{1}\s*\d{1}[A-Z]{2}|[A-Z]{2}\d{1}\s*\d{1}[A-Z]{2}|[A-Z]{1}\d{2}\s*\d{1}[A-Z]{2}|[A-Z]{2}\d{2}\s*\d{1}[A-Z]{2}|[A-Z]{2}\d{1}[A-Z]{1}\s*\d{1}[A-Z]{2}|[A-Z]{1}\d{1}[A-Z]{1}\s*\d{1}[A-Z]{2})$'
        
        # Normalize: uppercase and normalize spaces
        normalized = postcode.strip().upper()
        
        # Try with current spacing
        if re.match(uk_postcode_pattern, normalized, re.IGNORECASE):
            return True
        
        # Try without spaces (in case user didn't include space)
        no_space = normalized.replace(' ', '')
        # Add space before last 3 characters (standard UK format)
        if len(no_space) >= 5:
            formatted = no_space[:-3] + ' ' + no_space[-3:]
            if re.match(uk_postcode_pattern, formatted, re.IGNORECASE):
                return True
        
        return False

    def _initialize_parameter_patterns(self) -> Dict[str, List[Tuple[str, str, callable]]]:
        """
        Initialize regex patterns for extracting parameters from natural language.
        Returns patterns grouped by parameter type.
        """
        return {
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
                (r'fast|superfast|ultrafast', 'speed_in_mb', self._interpret_speed_adjective),
            ],
            'contract_length': [
                # Broad patterns to capture multiple contract lengths (must come first)
                (r'(?:contract[:\s]*)?(\d+(?:\s*(?:or|and|,)\s*\d+)+.*?months?)', 'contract_length', self._extract_contract_lengths),
                (r'(?:contract[:\s]*)?(\d+.*?months?\s*,.*?months?)', 'contract_length', self._extract_contract_lengths),
                # Single contract lengths (existing patterns)
                (r'(\d+)\s*month\s*contract', 'contract_length', self._normalize_contract_single),
                (r'contract[:\s]*(\d+)\s*month', 'contract_length', self._normalize_contract_single),
                (r'(\d+)\s*months?', 'contract_length', self._normalize_contract_single),
            ],
            'phone_calls': [
                (r'phone\s*calls?[:\s]*(\w+)', 'phone_calls', lambda x: x.title()),
                (r'(evening|weekend|anytime|unlimited)\s*calls?', 'phone_calls', self._interpret_phone_calls),
                (r'no\s*(inclusive\s*)?calls?', 'phone_calls', lambda x: "No inclusive"),
                (r'cheapest\s*calls?', 'phone_calls', lambda x: "Cheapest"),
            ],
            'providers': [
                # Use fuzzy matching function instead of regex
                (r'(\w+(?:\s+\w+)*)\s*broadband', 'providers', self._extract_provider_with_fuzzy),
                (r'with\s+(\w+(?:\s+\w+)*)', 'providers', self._extract_provider_with_fuzzy),
                (r'from\s+(\w+(?:\s+\w+)*)', 'providers', self._extract_provider_with_fuzzy),
                # Fallback patterns for direct provider names
                (r'(\w+(?:\s+\w+)*)', 'providers', self._extract_provider_with_fuzzy),
            ],
            'product_type': [
                (r'(broadband|phone|tv)\s*only', 'product_type', self._interpret_product_type),
                (r'(broadband|phone|tv)\s*and\s*(broadband|phone|tv)', 'product_type', self._interpret_product_type),
            ],
            'sort_by': [
                (r'sort\s*by\s*(\w+)', 'sort_by', lambda x: x.title()),
                (r'cheapest|fastest|recommended', 'sort_by', self._interpret_sort_preference),
            ],
            # Filter modification patterns
            'filter_speed': [
                (r'(?:set\s+)?speed\s*(?:to\s+)?(\d+)\s*mb?', 'filter_speed', lambda x: f"{x}Mb"),
                (r'(?:change\s+)?speed\s*(?:to\s+)?(\d+)\s*mb?', 'filter_speed', lambda x: f"{x}Mb"),
                (r'(\d+)\s*mb?\s*speed', 'filter_speed', lambda x: f"{x}Mb"),
            ],
            'filter_providers': [
                (r'(?:set\s+)?providers?\s*(?:to\s+)?([A-Za-z\s,]+)', 'filter_providers', self._extract_providers_with_fuzzy),
                (r'(?:change\s+)?providers?\s*(?:to\s+)?([A-Za-z\s,]+)', 'filter_providers', self._extract_providers_with_fuzzy),
                (r'only\s+([A-Za-z\s,]+)', 'filter_providers', self._extract_providers_with_fuzzy),
            ],
            'filter_contract': [
                (r'(?:set\s+)?contract\s*(?:to\s+)?(\d+)\s*months?', 'filter_contract', lambda x: f"{x} months"),
                (r'(?:change\s+)?contract\s*(?:to\s+)?(\d+)\s*months?', 'filter_contract', lambda x: f"{x} months"),
            ],
            'filter_phone_calls': [
                (r'(?:set\s+)?phone\s*calls?\s*(?:to\s+)?(\w+)', 'filter_phone_calls', lambda x: x.title()),
                (r'(?:change\s+)?phone\s*calls?\s*(?:to\s+)?(\w+)', 'filter_phone_calls', lambda x: x.title()),
            ],
            'new_line': [
                (r'new\s*line[:\s]*(\w+)', 'new_line', lambda x: "NewLine" if x.lower() in ["yes", "true", "new", "line"] else ""),
                (r'include\s*new\s*line', 'new_line', lambda x: "NewLine"),
                (r'new\s*line\s*cost', 'new_line', lambda x: "NewLine"),
                (r'existing\s*line|no\s*new\s*line', 'new_line', lambda x: ""),
            ],
            'filter_new_line': [
                (r'(?:set\s+)?new\s*line\s*(?:to\s+)?(\w+)', 'filter_new_line', lambda x: "NewLine" if x.lower() in ["yes", "true", "new", "line"] else ""),
                (r'(?:change\s+)?new\s*line\s*(?:to\s+)?(\w+)', 'filter_new_line', lambda x: "NewLine" if x.lower() in ["yes", "true", "new", "line"] else ""),
            ],
            'current_provider': [
                # Direct current provider mentions
                (r'current\s*provider\s*(?:is\s*)?([A-Za-z\s]+)', 'current_provider', self._extract_provider_with_fuzzy),
                (r'existing\s*provider\s*(?:is\s*)?([A-Za-z\s]+)', 'current_provider', self._extract_provider_with_fuzzy),
                (r'my\s*current\s*provider\s*(?:is\s*)?([A-Za-z\s]+)', 'current_provider', self._extract_provider_with_fuzzy),
                (r'switching\s*from\s+([A-Za-z\s]+)', 'current_provider', self._extract_provider_with_fuzzy),
                (r'currently\s*with\s+([A-Za-z\s]+)', 'current_provider', self._extract_provider_with_fuzzy),
                (r'leaving\s+([A-Za-z\s]+)', 'current_provider', self._extract_provider_with_fuzzy),
                # URL parameter style
                (r'currentProvider[:=]\s*([A-Za-z0-9\s%]+)', 'current_provider', self._extract_provider_with_fuzzy),
            ]
        }

    def _fuzzy_match_provider(self, provider_input: str, threshold: float = 50.0) -> Optional[str]:
        """
        Fuzzy match provider name using the existing fuzzy search infrastructure.

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
        if cache_key in self.provider_fuzzy_cache:
            return self.provider_fuzzy_cache[cache_key]

        # Check for exact match first (case-insensitive)
        provider_lower = provider_input.strip().lower()
        for valid_provider in self.valid_providers:
            if provider_lower == valid_provider.lower():
                self.provider_fuzzy_cache[cache_key] = valid_provider
                return valid_provider

        # Use fuzzy search if available
        if not FUZZY_SEARCH_AVAILABLE or not self.fuzzy_searcher:
            logger.warning("⚠️ Fuzzy search not available for provider matching")
            self.provider_fuzzy_cache[cache_key] = None
            return None

        try:
            # Use fuzzy search with the provider names as the search space
            # We'll adapt the postcode search for provider matching
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
                    self.provider_fuzzy_cache[cache_key] = matched_provider
                    return matched_provider
                else:
                    logger.info(f"🔍 Provider '{provider_input}' below threshold (score: {score:.1f}%, threshold: {threshold}%)")
                    self.provider_fuzzy_cache[cache_key] = None
                    return None
            else:
                self.provider_fuzzy_cache[cache_key] = None
                return None

        except Exception as e:
            logger.error(f"❌ Error in fuzzy provider matching: {e}")
            self.provider_fuzzy_cache[cache_key] = None
            return None

    def _extract_provider_with_fuzzy(self, match: str) -> str:
        """
        Extract provider name using fuzzy matching.
        This is used as a processor function in parameter patterns.

        Args:
            match: The matched string from regex pattern

        Returns:
            Best matching provider name or empty string if no match
        """
        if not match or not match.strip():
            return ""

        # Use fuzzy matching to find the best provider match
        matched_provider = self._fuzzy_match_provider(match.strip(), threshold=50.0)

        if matched_provider:
            logger.info(f"🔍 Extracted provider via fuzzy matching: '{match}' -> '{matched_provider}'")
            return matched_provider
        else:
            logger.info(f"🔍 No provider match found for: '{match}'")
            return ""

    def _extract_providers_with_fuzzy(self, match: str) -> str:
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
                matched_provider = self._fuzzy_match_provider(provider, threshold=50.0)
                if matched_provider:
                    matched_providers.append(matched_provider)

        if matched_providers:
            result = ','.join(matched_providers)
            logger.info(f"🔍 Extracted providers via fuzzy matching: '{match}' -> '{result}'")
            return result
        else:
            logger.info(f"🔍 No provider matches found for: '{match}'")
            return ""

    def _interpret_speed_adjective(self, match: str) -> str:
        """Interpret speed adjectives to actual speed values."""
        speed_map = {
            'fast': '30Mb',
            'superfast': '55Mb',
            'ultrafast': '100Mb'
        }
        return speed_map.get(match.lower(), '30Mb')

    def _interpret_phone_calls(self, match) -> str:
        """Interpret phone call preferences."""
        # Handle both string and tuple inputs from regex
        if isinstance(match, tuple):
            match = match[0] if match else ''

        call_map = {
            'evening': 'Evening and Weekend',
            'weekend': 'Evening and Weekend',
            'anytime': 'Anytime',
            'unlimited': 'Anytime'
        }
        return call_map.get(match.lower(), match.title())

    def _interpret_product_type(self, match) -> str:
        """Interpret product type combinations."""
        # Handle both string and tuple inputs from regex
        if isinstance(match, tuple):
            # For regex groups, filter out empty strings and join
            match_str = ' and '.join([str(m) for m in match if m and str(m).strip()])
        else:
            match_str = str(match).strip()

        # Clean the string and split
        match_str = match_str.lower()
        types = [t.strip() for t in match_str.split(' and ') if t.strip()]

        if len(types) == 1:
            return types[0]
        elif len(types) == 2:
            return f"{types[0]},{types[1]}"
        else:
            return "broadband,phone"

    def _interpret_sort_preference(self, match: str) -> str:
        """Interpret sort preferences."""
        sort_map = {
            'cheapest': 'Avg. Monthly Cost',
            'fastest': 'Speed',
            'recommended': 'Recommended'
        }
        return sort_map.get(match.lower(), 'Recommended')

    def _extract_contract_lengths(self, match: str) -> str:
        """
        Extract and format multiple contract lengths from natural language.

        Handles patterns like:
        - "1 or 12 months" -> "1 month,12 months"
        - "12 or 24 months" -> "12 months,24 months"
        - "12 and 24 months" -> "12 months,24 months"
        - "12, 24 months" -> "12 months,24 months"
        - "12 months, 24 months" -> "12 months,24 months"
        - "1 month, 12 months, 18 months, 24 months" -> "1 month,12 months,18 months,24 months"

        Args:
            match: The matched string from regex pattern

        Returns:
            Formatted contract length string for URL generation
        """
        if not match or not match.strip():
            return ""

        # Convert to lowercase for easier processing
        match_lower = match.lower().strip()

        # Split by common separators and clean up
        # Handle: commas, "or", "and", mixed separators
        parts = re.split(r'\s*(?:,|or|and)\s*', match_lower)

        # Extract numbers from each part
        valid_lengths = []
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Extract number from this part
            num_match = re.search(r'(\d+)', part)
            if num_match:
                length_int = int(num_match.group(1))
                # Format with correct singular/plural form
                formatted_length = f"{length_int} month" if length_int == 1 else f"{length_int} months"
                # Only accept valid contract lengths
                if formatted_length in BroadbandConstants.VALID_CONTRACT_LENGTHS:
                    valid_lengths.append(formatted_length)

        if not valid_lengths:
            return ""

        # Remove duplicates and sort
        valid_lengths = list(set(valid_lengths))
        valid_lengths.sort(key=lambda x: int(x.split()[0]))

        # Join with commas (no spaces around commas, as expected by URL generator)
        return ','.join(valid_lengths)

    def _normalize_contract_single(self, match) -> str:
        """
        Normalize single contract length while preserving singular/plural form.

        Args:
            match: The captured group from regex (the number as string)

        Returns:
            Normalized contract length string ("1 month" or "X months")
        """
        number = int(match)
        return f"{number} month" if number == 1 else f"{number} months"

    def _normalize_contract_length(self, contract_length: str) -> str:
        """
        Normalize contract length parameter to ensure correct URL formatting.
        Removes spaces around commas and validates the format.

        Args:
            contract_length: Contract length string (may contain spaces around commas)

        Returns:
            Normalized contract length string suitable for URL generation.
            Returns empty string if no contract length specified (no filter applied).
        """
        if not contract_length or not contract_length.strip():
            return ''

        # If it already contains commas without spaces, return as-is
        if ',' in contract_length and ' ,' not in contract_length and ', ' not in contract_length:
            return contract_length

        # Use the same logic as _extract_contract_lengths to normalize
        return self._extract_contract_lengths(contract_length) or contract_length

    def extract_parameters_from_query(self, query: str, skip_postcode_validation: bool = False) -> Dict[str, str]:
        """
        Extract broadband parameters from natural language query.
        Uses AI-powered extraction (preferred) with regex fallback.

        Args:
            query: Natural language query
            skip_postcode_validation: If True, skip automatic postcode validation (for fuzzy search workflow)

        Returns:
            Dictionary of extracted parameters
        """
        
        # Try AI extraction first (preferred method)
        if self.ai_extractor:
            try:
                logger.info(f"🤖 Using AI parameter extraction for: {query[:50]}...")
                
                # Get context from conversation state if available
                context = None
                # Note: user_id would come from the actual call context in production
                
                # Use synchronous extraction
                ai_params = self.ai_extractor.extract_parameters_sync(query, context=context)
                
                # Check confidence
                if ai_params.confidence and ai_params.confidence >= 0.5:
                    # Convert to dictionary and apply defaults
                    extracted = ai_params.to_dict()
                    
                    # Set defaults for missing parameters
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
        return self._extract_parameters_regex(query, skip_postcode_validation)
    
    def _extract_parameters_regex(self, query: str, skip_postcode_validation: bool = False) -> Dict[str, str]:
        """
        Legacy regex-based parameter extraction (fallback method).

        Args:
            query: Natural language query
            skip_postcode_validation: If True, skip automatic postcode validation (for fuzzy search workflow)

        Returns:
            Dictionary of extracted parameters
        """
        query_lower = query.lower()
        extracted = {}

        # Extract parameters using patterns
        for param_type, patterns in self.parameter_patterns.items():
            for pattern, key, processor in patterns:
                match = re.search(pattern, query_lower, re.IGNORECASE)
                if match:
                    processed_value = processor(match.group(1) if match.groups() else match.group(0))
                    if processed_value:
                        # Only set if not already set (for regular params) or always set (for filter params)
                        if key not in extracted:
                            extracted[key] = processed_value
                        elif key.startswith('filter_'):
                            # For filter parameters, always update
                            extracted[key] = processed_value
                        break

        # Handle special cases and defaults
        if 'postcode' not in extracted:
            # Extract postcode from query (without fuzzy search for now)
            postcode_match = self._extract_postcode_from_query(query)
            if postcode_match:
                extracted['postcode'] = postcode_match

        # Set defaults for missing parameters
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
            if key not in extracted:
                extracted[key] = default_value

        # DON'T validate postcode automatically - let the fuzzy search workflow handle it
        # This allows us to show suggestions to the user first

        logger.info(f"📡 Regex extracted parameters from query '{query}': {extracted}")
        return extracted

    def _extract_postcode_from_query(self, query: str) -> Optional[str]:
        """
        Extract postcode-like string from query without validation.
        This is the first step before fuzzy search.
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

    async def _search_postcode_with_fuzzy(self, user_id: str, raw_postcode: str, context: str = None) -> Tuple[bool, str, Optional[str]]:
        """
        Search for postcode using fuzzy matching and AUTO-SELECT the best match.
        NEW BEHAVIOR: Automatically selects 100% match or highest score - NO confirmation needed.
        
        Workflow:
        1. Validate UK postcode format with regex
        2. If invalid format, return error
        3. If valid, run fuzzy search against database
        4. Auto-select: 100% match OR highest scored match
        5. Store selected postcode directly in conversation state
        6. Return success (no user confirmation needed)
        
        Args:
            user_id: User ID for session management
            raw_postcode: Raw postcode input from user (may have typos)
            context: Additional context
            
        Returns:
            Tuple of (success: bool, message: str, selected_postcode: Optional[str])
        """
        # STEP 1: Validate UK postcode format with regex
        if not self._validate_uk_postcode_format(raw_postcode):
            logger.warning(f"❌ Invalid UK postcode format: {raw_postcode}")
            error_msg = f"❌ Invalid UK postcode format: '{raw_postcode}'. Please provide a valid UK postcode (e.g., E14 9WB, SW1A 1AA)."
            return (False, error_msg, None)
        
        logger.info(f"✅ Postcode format validated: {raw_postcode}")
        
        # STEP 2: Check if fuzzy search is available
        if not FUZZY_SEARCH_AVAILABLE or not self.fuzzy_searcher:
            logger.warning("⚠️ Fuzzy search not available - cannot validate against database")
            error_msg = f"⚠️ Fuzzy search not available. Cannot validate postcode '{raw_postcode}' against database."
            return (False, error_msg, None)

        try:
            logger.info(f"🔍 Running fuzzy search for postcode: {raw_postcode}")
            
            # STEP 3: Run fuzzy search with optimal parameters
            result = self.fuzzy_searcher.get_fuzzy_results(
                search_term=raw_postcode,
                top_n=10,  # Get top 10 matches for logging
                max_candidates=2000,
                use_dynamic_distance=True,
                use_weighted_scoring=True,
                parallel_threshold=500
            )
            
            if not result['results']:
                logger.warning(f"❌ No matching postcodes found for: {raw_postcode}")
                error_msg = f"❌ No matching postcodes found in database for '{raw_postcode}'. Please check and provide a valid UK postcode."
                return (False, error_msg, None)
            
            matches = result['results']
            metadata = result.get('metadata', {})
            
            # STEP 4: Auto-select best match
            # Check for 100% match first
            selected_postcode = None
            selection_reason = ""
            
            best_match = matches[0]  # Highest scored match
            best_postcode, best_score = best_match
            
            if best_score >= 100.0:
                # Perfect match found
                selected_postcode = best_postcode
                selection_reason = f"100% exact match"
                logger.info(f"🎯 100% match found: {selected_postcode}")
            else:
                # Use highest scored match from database
                selected_postcode = best_postcode
                selection_reason = f"highest match ({best_score:.1f}%)"
                logger.info(f"🎯 Best match selected: {selected_postcode} (score: {best_score:.1f}%)")
            
            # STEP 5: Store selected postcode in conversation state
            if user_id not in self.conversation_state:
                self.conversation_state[user_id] = {}
            
            self.conversation_state[user_id]['confirmed_postcode'] = selected_postcode
            self.conversation_state[user_id]['postcode_fuzzy_search'] = {
                'raw_input': raw_postcode,
                'selected_postcode': selected_postcode,
                'selection_reason': selection_reason,
                'score': best_score,
                'all_matches': matches[:5],  # Store top 5 for reference
                'metadata': metadata,
                'timestamp': datetime.now().isoformat(),
                'auto_selected': True
            }
            
            # Create structured output for websocket
            structured_output = self._create_structured_output(
                user_id=user_id,
                action_type="postcode_auto_selected",
                param="raw_postcode,selected_postcode,score",
                value=f"{raw_postcode},{selected_postcode},{best_score}",
                interaction_type="auto_selection",
                clicked=True,
                element_name="postcode_auto_select",
                context=context,
                raw_postcode=raw_postcode,
                selected_postcode=selected_postcode,
                selection_reason=selection_reason,
                score=best_score,
                search_time_ms=metadata.get('search_time_ms', 0)
            )
            
            await self.send_websocket_message(
                message_type="fuzzy_search_action",
                action="postcode_auto_selected",
                data=structured_output
            )
            
            # STEP 6: Return success message
            if best_score >= 100.0:
                success_msg = f"✅ Postcode confirmed: **{selected_postcode}** (exact match)"
            else:
                success_msg = f"✅ Postcode matched: **{selected_postcode}** (best match: {best_score:.1f}% confidence)"
            
            logger.info(f"✅ Auto-selected postcode: {selected_postcode} for input '{raw_postcode}'")
            
            return (True, success_msg, selected_postcode)
            
        except Exception as e:
            logger.error(f"❌ Error in fuzzy postcode search: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            error_msg = f"❌ Error searching for postcode: {str(e)}"
            return (False, error_msg, None)

    async def _handle_postcode_confirmation(self, user_id: str, confirmed_postcode: str = None, 
                                           original_postcode: str = None, context: str = None) -> str:
        """
        Handle user confirmation of postcode selection.
        This processes user's choice from fuzzy search results.
        
        Args:
            user_id: User ID
            confirmed_postcode: The postcode user confirmed (direct input or selection)
            original_postcode: Original postcode that triggered fuzzy search
            context: Additional context
            
        Returns:
            Confirmation message with next steps
        """
        try:
            # Check if we have fuzzy search state
            if user_id not in self.conversation_state or 'postcode_fuzzy_search' not in self.conversation_state[user_id]:
                # Check for old postcode_suggestions format (backward compatibility)
                if user_id in self.conversation_state and 'postcode_suggestions' in self.conversation_state[user_id]:
                    suggestions = self.conversation_state[user_id]['postcode_suggestions']
                    if confirmed_postcode:
                        # Direct postcode provided
                        selected_postcode = confirmed_postcode
                    else:
                        return "❌ Please specify which postcode to use."
                else:
                    return "❌ No postcode search in progress. Please provide a postcode first."
            else:
                fuzzy_state = self.conversation_state[user_id]['postcode_fuzzy_search']
                matches = fuzzy_state['matches']
                
                # Parse user's confirmation
                selected_postcode = None
                
                if confirmed_postcode:
                    # First check if it looks like a UK postcode (direct input)
                    # UK postcode pattern (to avoid false positives with selection numbers)
                    postcode_pattern = r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d?[A-Z]{0,2}$'
                    if re.match(postcode_pattern, confirmed_postcode.upper().replace(' ', '')[:10]):
                        # This looks like a direct postcode
                        confirmed_upper = confirmed_postcode.upper().replace(' ', '')
                        for postcode, score in matches:
                            if postcode.replace(' ', '') == confirmed_upper:
                                selected_postcode = postcode
                                break
                        
                        if not selected_postcode:
                            # User provided a new postcode - run fuzzy search again
                            return await self._search_postcode_with_fuzzy(user_id, confirmed_postcode, context)
                    else:
                        # Check if it's a selection command (e.g., "1", "first", "number 2")
                        selection_match = re.search(r'^(?:choose\s+)?(?:select\s+)?(?:number\s+)?(\d+)|^(?:the\s+)?(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)', 
                                                  confirmed_postcode.lower())
                        
                        if selection_match:
                            # Extract the number
                            if selection_match.group(1):  # Numeric selection
                                index = int(selection_match.group(1)) - 1
                            else:  # Word selection
                                word_to_num = {
                                    'first': 0, 'second': 1, 'third': 2, 'fourth': 3, 'fifth': 4,
                                    'sixth': 5, 'seventh': 6, 'eighth': 7, 'ninth': 8, 'tenth': 9
                                }
                                word = selection_match.group(2)
                                index = word_to_num.get(word, 0)
                            
                            # Validate index
                            if 0 <= index < len(matches):
                                selected_postcode = matches[index][0]
                            else:
                                return f"❌ Invalid selection. Please choose a number between 1 and {len(matches)}."
                        else:
                            # Unclear input - try as direct postcode
                            confirmed_upper = confirmed_postcode.upper().replace(' ', '')
                            for postcode, score in matches:
                                if postcode.replace(' ', '') == confirmed_upper:
                                    selected_postcode = postcode
                                    break
                            
                            if not selected_postcode:
                                # User provided a new postcode - run fuzzy search again
                                return await self._search_postcode_with_fuzzy(user_id, confirmed_postcode, context)
                else:
                    return "❌ Please specify which postcode to use (e.g., 'choose number 1' or provide the exact postcode)."
            
            # Store confirmed postcode in conversation state
            self.conversation_state[user_id]['confirmed_postcode'] = selected_postcode
            self.conversation_state[user_id]['postcode_fuzzy_search']['awaiting_confirmation'] = False
            self.conversation_state[user_id]['postcode_fuzzy_search']['confirmed_postcode'] = selected_postcode
            
            # Create structured output
            structured_output = self._create_structured_output(
                user_id=user_id,
                action_type="postcode_confirmed",
                param="confirmed_postcode",
                value=selected_postcode,
                interaction_type="postcode_confirmation",
                clicked=True,
                element_name="confirm_postcode",
                context=context,
                confirmed_postcode=selected_postcode,
                original_input=fuzzy_state.get('raw_input', original_postcode)
            )
            
            await self.send_websocket_message(
                message_type="confirmation_action",
                action="postcode_confirmed",
                data=structured_output
            )
            
            # Check if there are pending search parameters
            pending_params = self.conversation_state[user_id].get('pending_search_params', {})
            
            if pending_params and any(pending_params.values()):
                # Auto-generate URL with confirmed postcode and pending parameters
                all_params = {
                    'postcode': selected_postcode,
                    'speed_in_mb': pending_params.get('speed_in_mb', '30Mb'),
                    'contract_length': pending_params.get('contract_length', ''),
                    'phone_calls': pending_params.get('phone_calls', 'Show me everything'),
                    'product_type': pending_params.get('product_type', 'broadband,phone'),
                    'providers': pending_params.get('providers', ''),
                    'current_provider': pending_params.get('current_provider', ''),
                    'sort_by': pending_params.get('sort_by', 'Recommended'),
                    'new_line': pending_params.get('new_line', '')
                }
                
                try:
                    # Ensure contract_length is normalized
                    if 'contract_length' in all_params and all_params['contract_length']:
                        all_params['contract_length'] = self._normalize_contract_length(all_params['contract_length'])

                    url = self.url_generator.generate_url(**all_params)
                    
                    # Create structured output for URL generation
                    structured_output_url = self._create_structured_output(
                        user_id=user_id,
                        action_type="url_generated",
                        param="url,postcode",
                        value=f"{url},{selected_postcode}",
                        interaction_type="url_generation",
                        clicked=False,
                        element_name="generate_url",
                        context=context,
                        extracted_params=all_params,
                        generated_url=url
                    )
                    
                    await self.send_websocket_message(
                        message_type="url_action",
                        action="url_generated",
                        data=structured_output_url
                    )
                    
                    response = f"✅ **Postcode Confirmed: {selected_postcode}**\n\n"
                    response += f"🎉 Perfect! I've generated your broadband comparison URL!\n\n"
                    response += f"**Your Search Parameters:**\n"
                    response += f"• Postcode: {selected_postcode}\n"
                    response += f"• Speed: {all_params['speed_in_mb']}\n"
                    response += f"• Contract: {all_params['contract_length']}\n"
                    response += f"• Phone Calls: {all_params['phone_calls']}\n\n"
                    response += f"**Generated URL:** {url}\n\n"
                    response += f"💡 You can now ask me to:\n"
                    response += f"• Show recommendations for these parameters\n"
                    response += f"• Compare specific providers\n"
                    response += f"• Find the cheapest/fastest deals"
                    
                    # Clear pending params
                    self.conversation_state[user_id]['pending_search_params'] = {}
                    
                    return response
                    
                except Exception as e:
                    logger.error(f"❌ Error generating URL after confirmation: {e}")
                    # Fall through to manual next steps message
            
            # No pending params - show next steps
            response = f"✅ **Postcode Confirmed: {selected_postcode}**\n\n"
            response += f"Great! I'll use **{selected_postcode}** for your broadband search.\n\n"
            response += f"📝 **Next Steps:**\n"
            response += f"• I can now search for broadband deals in {selected_postcode}\n"
            response += f"• You can also specify:\n"
            response += f"  - Speed preference (e.g., 30Mb, 100Mb)\n"
            response += f"  - Contract length (e.g., 12 months, 24 months)\n"
            response += f"  - Providers (e.g., BT, Sky, Virgin)\n\n"
            response += f"💡 Say something like: 'show me 100Mb deals with 12 month contract'"
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in postcode confirmation: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"❌ Error confirming postcode: {str(e)}"

    def _extract_postcode_with_fuzzy(self, query: str) -> Optional[str]:
        """
        DEPRECATED: Old method for automatic fuzzy postcode extraction.
        Use _search_postcode_with_fuzzy() instead for the new workflow.
        """
        return self._extract_postcode_from_query(query)

    def _validate_postcode_with_fuzzy(self, postcode: str) -> Optional[str]:
        """
        DEPRECATED: Old method for automatic postcode validation.
        Use _search_postcode_with_fuzzy() instead for the new workflow.
        """
        # For backward compatibility, just return the postcode as-is
        return postcode

    async def _handle_list_providers(self, user_id: str, context: str = None) -> str:
        """Handle listing all available providers."""
        try:
            providers = BroadbandConstants.VALID_PROVIDERS

            # Create structured output for AI
            structured_output = self._create_structured_output(
                user_id=user_id,
                action_type="providers_listed",
                param="total_providers",
                value=str(len(providers)),
                interaction_type="provider_listing",
                clicked=True,
                element_name="list_providers",
                context=context,
                providers_list=providers,
                total_providers=len(providers)
            )

            await self.send_websocket_message(
                message_type="providers_action",
                action="providers_listed",
                data=structured_output
            )

            # Format response for user
            response = f"📱 **Available Broadband Providers ({len(providers)} total):**\n\n"
            for i, provider in enumerate(providers[:20], 1):  # Show first 20
                response += f"**{i}. {provider}**\n"

            if len(providers) > 20:
                response += f"\n... and {len(providers) - 20} more providers\n"

            response += "\n💡 You can specify providers like 'hyperoptic, bt' or 'all providers'"

            return response

        except Exception as e:
            return f"❌ Error listing providers: {str(e)}"

    def get_tool_definition(self) -> FunctionSchema:
        """Get the tool definition for the LLM."""
        return FunctionSchema(
            name="broadband_action",
            description="Handle broadband comparison queries with natural language processing, URL generation, and AI-powered recommendations. Only available on the broadband page. NEW: Postcode validation is AUTOMATIC - validates format with regex, searches database using fuzzy matching, and auto-selects best match (100% match or highest score). NO user confirmation needed!",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "User ID for session management"
                },
                "action_type": {
                    "type": "string",
                    "enum": [
                        "query", "generate_url", "scrape_data", "get_recommendations",
                        "compare_providers", "refine_search", "get_cheapest",
                        "get_fastest", "clarify_missing_params", "list_providers",
                        "filter_data", "open_url"
                    ],
                    "description": "Type of broadband action. Use 'query' for natural language queries (includes automatic postcode validation and matching). Use 'open_url' to open a URL in a new tab. Postcode auto-selection happens automatically in the background."
                },
                "url": {
                    "type": "string",
                    "description": "URL to open in a new tab (for open_url action)"
                },
                "query": {
                    "type": "string",
                    "description": "Natural language query about broadband requirements"
                },
                "postcode": {
                    "type": "string",
                    "description": "UK postcode (any format). Will be automatically validated with regex and matched against database using fuzzy search. Best match is auto-selected."
                },
                "speed_in_mb": {
                    "type": "string",
                    "enum": ["10Mb", "30Mb", "55Mb", "100Mb"],
                    "description": "Speed requirement"
                },
                "contract_length": {
                    "type": "string",
                    "description": "Contract length preference. Valid values: '1 month', '12 months', '18 months', '24 months', or empty string for no filter. Can specify multiple values comma-separated (e.g., '1 month,12 months,24 months')"
                },
                "phone_calls": {
                    "type": "string",
                    "enum": BroadbandConstants.VALID_PHONE_CALLS,
                    "description": "Phone calls preference"
                },
                "product_type": {
                    "type": "string",
                    "enum": BroadbandConstants.VALID_PRODUCT_TYPES,
                    "description": "Product type preference"
                },
                "providers": {
                    "type": "string",
                    "description": "Provider preference (comma-separated)"
                },
                "current_provider": {
                    "type": "string",
                    "description": "User's existing broadband provider (optional, for switching providers)"
                },
                "sort_by": {
                    "type": "string",
                    "enum": BroadbandConstants.VALID_SORT_OPTIONS,
                    "description": "Sort preference"
                },
                "new_line": {
                    "type": "string",
                    "description": "New line cost option. Leave empty for existing line, set to 'NewLine' to include new line installation cost"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context for the action"
                },
                "filter_speed": {
                    "type": "string",
                    "enum": ["10Mb", "30Mb", "55Mb", "100Mb"],
                    "description": "Speed filter to apply"
                },
                "filter_providers": {
                    "type": "string",
                    "description": "Provider filter to apply (comma-separated)"
                },
                "filter_contract": {
                    "type": "string",
                    "description": "Contract length filter to apply. Valid values: '1 month', '12 months', '18 months', '24 months', or empty string. Supports multiple comma-separated values"
                },
                "filter_phone_calls": {
                    "type": "string",
                    "enum": BroadbandConstants.VALID_PHONE_CALLS,
                    "description": "Phone calls filter to apply"
                },
                "filter_new_line": {
                    "type": "string",
                    "description": "New line filter to apply"
                }
            },
            required=["user_id", "action_type"]
        )

    async def execute(self, user_id: str, action_type: str, query: str = None,
                     postcode: str = None, speed_in_mb: str = None,
                     contract_length: str = None, phone_calls: str = None,
                     product_type: str = None, providers: str = None,
                     current_provider: str = None, sort_by: str = None, new_line: str = None, context: str = None,
                     confirmed_postcode: str = None, original_postcode: str = None,
                     filter_speed: str = None, filter_providers: str = None,
                     filter_contract: str = None, filter_phone_calls: str = None,
                     filter_new_line: str = None, url: str = None, **kwargs) -> str:
        """Execute broadband action."""
        try:
            # Initialize user session
            self._initialize_user_session(user_id)
            current_page = self.get_user_current_page(user_id)

            print(f"🔧 BROADBAND TOOL EXECUTE: User: {user_id}, Action: {action_type}, Page: {current_page}")
            logger.info(f"📡 Broadband action - User: {user_id}, Action: {action_type}, Query: {query}")

            # Validate page
            expected_pages = [self.page_name, self.page_name.replace("/", "-")]
            if current_page not in expected_pages:
                print(f"❌ BROADBAND TOOL: Wrong page - expected {expected_pages}, got {current_page}")
                return f"❌ Broadband operations are only available on the {self.page_name} page. Current page: {current_page}"

            # Route actions
            if action_type == "fuzzy_search_postcode":
                # AUTO-SELECT fuzzy search - validates format and auto-selects best match
                if not postcode:
                    return "❌ Please provide a postcode to search for."
                
                success, message, selected_postcode = await self._search_postcode_with_fuzzy(user_id, postcode, context)
                
                if not success:
                    # Return error message (invalid format or no matches)
                    return message
                
                # Success - postcode auto-selected, continue with pending parameters if any
                pending_params = self.conversation_state.get(user_id, {}).get('pending_search_params', {})
                
                if pending_params and any(pending_params.values()):
                    # Auto-generate URL with selected postcode and pending parameters
                    all_params = {
                        'postcode': selected_postcode,
                        'speed_in_mb': pending_params.get('speed_in_mb', '30Mb'),
                        'contract_length': pending_params.get('contract_length', ''),
                        'phone_calls': pending_params.get('phone_calls', 'Show me everything'),
                        'product_type': pending_params.get('product_type', 'broadband,phone'),
                        'providers': pending_params.get('providers', ''),
                        'current_provider': pending_params.get('current_provider', ''),
                        'sort_by': pending_params.get('sort_by', 'Recommended'),
                        'new_line': pending_params.get('new_line', '')
                    }
                    
                    try:
                        # Normalize contract_length
                        if 'contract_length' in all_params and all_params['contract_length']:
                            all_params['contract_length'] = self._normalize_contract_length(all_params['contract_length'])
                        
                        url = self.url_generator.generate_url(**all_params)
                        
                        # Clear pending params
                        self.conversation_state[user_id]['pending_search_params'] = {}
                        
                        return f"{message}\n\n🎉 I've generated your broadband comparison URL!\n\n**Generated URL:** {url}\n\n**Parameters:**\n" + \
                               "\n".join([f"• {k}: {v}" for k, v in all_params.items() if v])
                    except Exception as e:
                        logger.error(f"❌ Error generating URL: {e}")
                        return f"{message}\n\n❌ Error generating URL: {str(e)}"
                else:
                    # Just return the selection message
                    return message
            elif action_type == "confirm_postcode":
                # DEPRECATED: Kept for backward compatibility only
                return await self._handle_postcode_confirmation(user_id, confirmed_postcode, original_postcode, context)
            elif action_type == "query":
                # If query is None but other parameters are provided, use explicit parameters
                if not query and (postcode or speed_in_mb or contract_length or phone_calls or product_type or providers or sort_by):
                    # Use explicit parameters
                    params = {
                        'postcode': postcode,
                        'speed_in_mb': speed_in_mb or '30Mb',
                        'contract_length': contract_length or '',
                        'phone_calls': phone_calls or 'Show me everything',
                        'product_type': product_type or 'broadband,phone',
                        'providers': providers or '',
                        'current_provider': current_provider or '',
                        'sort_by': sort_by or 'Recommended',
                        'new_line': new_line or ''
                    }

                    # Filter out None values
                    params = {k: v for k, v in params.items() if v is not None}

                    # Normalize contract_length to ensure correct URL formatting
                    if 'contract_length' in params and params['contract_length']:
                        params['contract_length'] = self._normalize_contract_length(params['contract_length'])

                    if 'postcode' not in params:
                        return await self._handle_clarify_missing_params(user_id, "I need your postcode to find broadband deals.")

                    try:
                        url = self.url_generator.generate_url(**params)

                        # Create structured output for AI
                        structured_output = self._create_structured_output(
                            user_id=user_id,
                            action_type="url_generated",
                            param="url,postcode",
                            value=f"{url},{params['postcode']}",
                            interaction_type="url_generation",
                            clicked=False,
                            element_name="generate_url",
                            context=context,
                            extracted_params=params,
                            generated_url=url
                        )

                        await self.send_websocket_message(
                            message_type="url_action",
                            action="url_generated",
                            data=structured_output
                        )

                        return f"✅ I've generated a broadband comparison URL for you!\n\n**URL:** {url}\n\n**Parameters:**\n" + \
                               "\n".join([f"• {k}: {v}" for k, v in params.items()])
                    except Exception as e:
                        return f"❌ Error generating URL: {str(e)}"
                else:
                    # Use natural language processing
                    return await self._handle_natural_language_query(user_id, query, context)
            elif action_type == "generate_url":
                return await self._handle_generate_url(
                    user_id, postcode, speed_in_mb, contract_length,
                    phone_calls, product_type, providers, current_provider, sort_by, new_line, context
                )
            elif action_type == "scrape_data":
                return await self._handle_scrape_data(
                    user_id, postcode, speed_in_mb, contract_length,
                    phone_calls, product_type, providers, current_provider, new_line, context
                )
            elif action_type == "get_recommendations":
                return await self._handle_get_recommendations(
                    user_id, postcode, speed_in_mb, contract_length,
                    phone_calls, product_type, providers, current_provider, new_line, context
                )
            elif action_type == "compare_providers":
                return await self._handle_compare_providers(user_id, providers, postcode, speed_in_mb, current_provider, new_line, context)
            elif action_type == "refine_search":
                return await self._handle_refine_search(user_id, contract_length, context)
            elif action_type == "get_cheapest":
                return await self._handle_get_cheapest(user_id, postcode, current_provider, new_line, context)
            elif action_type == "get_fastest":
                return await self._handle_get_fastest(user_id, postcode, current_provider, new_line, context)
            elif action_type == "clarify_missing_params":
                return await self._handle_clarify_missing_params(user_id, context)
            elif action_type == "list_providers":
                return await self._handle_list_providers(user_id, context)
            elif action_type == "postcode_suggestions":
                # Legacy support for old postcode_suggestions action
                return await self._handle_postcode_suggestions(user_id, original_postcode, context)
            elif action_type == "filter_data":
                return await self._handle_filter_data(user_id, filter_speed, filter_providers, filter_contract, filter_phone_calls, filter_new_line, context)
            elif action_type == "open_url":
                return await self._handle_open_url(user_id, url, context)
            else:
                return f"❌ Invalid action type: {action_type}"

        except Exception as e:
            logger.error(f"❌ Error executing broadband tool: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"❌ Error processing broadband request: {str(e)}"

    async def _handle_natural_language_query(self, user_id: str, query: str, context: str = None) -> str:
        """Handle natural language broadband queries with AUTO-SELECT fuzzy postcode search."""
        # Extract parameters from query
        extracted_params = self.extract_parameters_from_query(query, skip_postcode_validation=True)

        # Check if we have enough information
        if 'postcode' not in extracted_params or not extracted_params['postcode']:
            return await self._handle_clarify_missing_params(user_id, "I need your postcode to find broadband deals.")

        # NEW AUTO-SELECT WORKFLOW: Check if there's already a confirmed postcode
        user_state = self.conversation_state.get(user_id, {})
        confirmed_postcode = user_state.get('confirmed_postcode')
        
        if not confirmed_postcode:
            # No confirmed postcode yet - trigger AUTO-SELECT fuzzy search
            raw_postcode = extracted_params['postcode']
            logger.info(f"🔍 New postcode detected: {raw_postcode} - triggering auto-select fuzzy search")
            
            # Run fuzzy search with auto-selection
            success, message, selected_postcode = await self._search_postcode_with_fuzzy(user_id, raw_postcode, context)
            
            if not success or not selected_postcode:
                # Fuzzy search failed (invalid format or no matches)
                return message
            
            # Auto-selected successfully - use the selected postcode
            confirmed_postcode = selected_postcode
            logger.info(f"✅ Auto-selected postcode: {confirmed_postcode}")
        else:
            # Already have a confirmed postcode - use it
            logger.info(f"✅ Using existing confirmed postcode: {confirmed_postcode}")
        
        # Use the confirmed/selected postcode
        extracted_params['postcode'] = confirmed_postcode

        # Check if this is a filter modification request
        has_filters = any(key.startswith('filter_') for key in extracted_params.keys())
        if has_filters:
            return await self._handle_filter_data(user_id,
                filter_speed=extracted_params.get('filter_speed'),
                filter_providers=extracted_params.get('filter_providers'),
                filter_contract=extracted_params.get('filter_contract'),
                filter_phone_calls=extracted_params.get('filter_phone_calls')
            )

        # Generate URL with extracted parameters (including confirmed postcode)
        try:
            # Ensure contract_length is normalized
            if 'contract_length' in extracted_params and extracted_params['contract_length']:
                extracted_params['contract_length'] = self._normalize_contract_length(extracted_params['contract_length'])

            url = self.url_generator.generate_url(**extracted_params)

            # Store conversation state
            self.conversation_state[user_id] = {
                'query': query,
                'extracted_params': extracted_params,
                'generated_url': url,
                'last_action': 'query',
                'timestamp': datetime.now().isoformat()
            }

            # Create structured output
            structured_output = self._create_structured_output(
                user_id=user_id,
                action_type="url_generated",
                param="url,postcode",
                value=f"{url},{extracted_params['postcode']}",
                interaction_type="url_generation",
                clicked=False,
                element_name="generate_url",
                context=context,
                extracted_params=extracted_params,
                generated_url=url
            )

            await self.send_websocket_message(
                message_type="url_action",
                action="url_generated",
                data=structured_output
            )

            response = f"✅ I've analyzed your query and generated a broadband comparison URL!\n\n" \
                      f"**Extracted Requirements:**\n" \
                      f"• Postcode: {extracted_params.get('postcode', 'Not specified')}\n" \
                      f"• Speed: {extracted_params.get('speed_in_mb', 'Not specified')}\n" \
                      f"• Contract: {extracted_params.get('contract_length', 'Not specified')}\n" \
                      f"• Phone Calls: {extracted_params.get('phone_calls', 'Not specified')}\n\n" \
                      f"**Generated URL:** {url}\n\n" \
                      f"You can now ask me to:\n" \
                      f"• Show recommendations for these parameters\n" \
                      f"• Compare specific providers\n" \
                      f"• Find the cheapest/fastest deals\n" \
                      f"• Refine your search criteria"

            return response

        except Exception as e:
            return f"❌ Error generating URL: {str(e)}"

    async def _handle_generate_url(self, user_id: str, postcode: str = None, speed_in_mb: str = None,
                                  contract_length: str = None, phone_calls: str = None, product_type: str = None,
                                  providers: str = None, current_provider: str = None, sort_by: str = None, new_line: str = None, context: str = None) -> str:
        """Handle URL generation with explicit parameters."""
        try:
            # Validate postcode
            if not postcode:
                return await self._handle_clarify_missing_params(user_id, "Please provide your postcode.")

            # Set defaults for optional parameters
            params = {
                'postcode': postcode,
                'speed_in_mb': speed_in_mb or '30Mb',
                'contract_length': contract_length or '',
                'phone_calls': phone_calls or 'Show me everything',
                'product_type': product_type or 'broadband,phone',
                'providers': providers or '',
                'current_provider': current_provider or '',
                'sort_by': sort_by or 'Recommended',
                'new_line': new_line or ''
            }

            # Normalize contract_length to ensure correct URL formatting
            if params['contract_length']:
                params['contract_length'] = self._normalize_contract_length(params['contract_length'])

            url = self.url_generator.generate_url(**params)

            structured_output = self._create_structured_output(
                user_id=user_id,
                action_type="url_generated",
                param="url",
                value=url,
                interaction_type="url_generation",
                clicked=True,
                element_name="generate_url",
                context=context,
                generated_params=params
            )

            await self.send_websocket_message(
                message_type="url_action",
                action="url_generated",
                data=structured_output
            )

            return f"✅ Broadband comparison URL generated!\n\n**URL:** {url}\n\n**Parameters:**\n" + \
                   "\n".join([f"• {k}: {v}" for k, v in params.items() if v])

        except Exception as e:
            return f"❌ Error generating URL: {str(e)}"

    async def _handle_scrape_data(self, user_id: str, postcode: str = None, speed_in_mb: str = None,
                                 contract_length: str = None, phone_calls: str = None, product_type: str = None,
                                 providers: str = None, current_provider: str = None, new_line: str = None, context: str = None) -> str:
        """Handle data scraping for recommendations."""
        try:
            # Normalize contract_length (defaults to empty string - no filter)
            normalized_contract = self._normalize_contract_length(contract_length or '')

            # Generate URL first
            url = self.url_generator.generate_url(
                postcode=postcode or 'E14 9WB',
                speed_in_mb=speed_in_mb or '30Mb',
                contract_length=normalized_contract,
                phone_calls=phone_calls or 'Show me everything',
                product_type=product_type or 'broadband,phone',
                providers=providers or '',
                current_provider=current_provider or '',
                sort_by='Recommended',
                new_line=new_line or ''
            )

            # Check cache first
            cache_key = f"{postcode}_{speed_in_mb}_{contract_length}_{providers}"
            if cache_key in self.scraped_data_cache:
                data = self.scraped_data_cache[cache_key]
            else:
                # Scrape data using real scraping (async)
                data = await self.scraper.scrape_url_fast_async(url)

                # Check if scraping was successful
                if data and 'error' not in data and data.get('total_deals', 0) > 0:
                    self.scraped_data_cache[cache_key] = data
                elif data and 'error' in data:
                    # Handle API failure gracefully with specific error message
                    error_msg = data.get('error', 'Unknown error occurred')
                    note = data.get('note', '')

                    if 'Browser scraping not available' in error_msg:
                        # Special handling for browser scraping limitations
                        error_response = f"❌ Data scraping is currently limited in this environment. However, I've generated the comparison URL for you. {note}"
                    else:
                        error_response = f"❌ Unable to fetch broadband data: {error_msg}. Please try again later or check your connection."

                    # Store the error data for other methods to handle
                    self.scraped_data_cache[cache_key] = data
                    return error_response
                else:
                    # Handle empty results or other failures
                    error_response = "❌ No broadband deals found for your criteria. Please try adjusting your search parameters."
                    # Store the data for other methods to handle
                    self.scraped_data_cache[cache_key] = data
                    return error_response

            # Store in conversation state
            if user_id not in self.conversation_state:
                self.conversation_state[user_id] = {}
            self.conversation_state[user_id]['scraped_data'] = data

            # Create structured output for AI
            structured_output = self._create_structured_output(
                user_id=user_id,
                action_type="data_scraped",
                param="total_deals,location",
                value=f"{data.get('total_deals', 0)},{data.get('metadata', {}).get('location', 'Unknown')}",
                interaction_type="data_scraping",
                clicked=True,
                element_name="scrape_data",
                context=context,
                scraped_data=data,
                total_deals=data.get('total_deals', 0),
                location=data.get('metadata', {}).get('location', 'Unknown'),
                filters_applied=data.get('filters_applied', {})
            )

            await self.send_websocket_message(
                message_type="data_action",
                action="data_scraped",
                data=structured_output
            )

            total_deals = data.get('total_deals', 0)
            if total_deals > 0:
                return {
                    'status': 'success',
                    'message': f'Successfully scraped {total_deals} broadband deals',
                    'data': {
                        'total_deals': total_deals,
                        'location': data.get('metadata', {}).get('location', 'Unknown'),
                        'filters_applied': data.get('filters_applied', {}),
                        'deals': data.get('deals', [])
                    },
                    'suggestions': [
                        'Get recommendations based on your preferences',
                        'Compare specific providers',
                        'Find the cheapest or fastest deals'
                    ]
                }
            else:
                return {
                    'status': 'no_results',
                    'message': 'No deals found for the specified criteria',
                    'suggestions': [
                        'Try adjusting your search parameters',
                        'Change the speed requirement',
                        'Modify the contract length',
                        'Select different providers'
                    ]
                }

        except Exception as e:
            return f"❌ Error scraping data: {str(e)}"

    async def _handle_get_recommendations(self, user_id: str, postcode: str = None, speed_in_mb: str = None,
                                         contract_length: str = None, phone_calls: str = None, product_type: str = None,
                                         providers: str = None, current_provider: str = None, new_line: str = None, context: str = None) -> str:
        """Handle AI-powered recommendations based on scraped data."""
        try:
            # Get scraped data
            if user_id not in self.conversation_state or 'scraped_data' not in self.conversation_state[user_id]:
                # Auto-scrape data if not available
                postcode = postcode or 'E14 9WB'  # Default postcode if not provided
                await self._handle_scrape_data(
                    user_id, postcode, speed_in_mb, contract_length,
                    phone_calls, product_type, providers, current_provider, new_line, context
                )

                # Check if scraping was successful
                if user_id not in self.conversation_state or 'scraped_data' not in self.conversation_state[user_id]:
                    return "❌ Unable to fetch broadband data. Please check your postcode and try again."

            data = self.conversation_state[user_id]['scraped_data']
            if not data or 'error' in data or data.get('total_deals', 0) == 0:
                if data and 'error' in data and 'Browser scraping not available' in data.get('error', ''):
                    return "❌ Data scraping is currently limited in this environment. Please use the generated URL to view deals directly."
                else:
                    return "❌ Unable to fetch broadband data for recommendations."

            deals = data.get('deals', [])

            if not deals:
                return "❌ No deals available for recommendations."

            # Generate recommendations based on user preferences
            recommendations = self._generate_recommendations(deals, {
                'speed': speed_in_mb,
                'contract': contract_length,
                'providers': providers,
                'phone_calls': phone_calls
            })

            # Cache recommendations
            cache_key = f"{user_id}_{postcode}_{speed_in_mb}"
            self.recommendation_cache[cache_key] = recommendations

            # Store in conversation state
            self.conversation_state[user_id]['recommendations'] = recommendations

            # Create structured output for AI
            structured_output = self._create_structured_output(
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

            await self.send_websocket_message(
                message_type="recommendation_action",
                action="recommendations_generated",
                data=structured_output
            )

            # Return structured data for the AI
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
            return f"❌ Error generating recommendations: {str(e)}"

    def _generate_recommendations(self, deals: List[Dict], preferences: Dict[str, str]) -> List[Dict[str, Any]]:
        """Generate AI-powered recommendations based on user preferences."""
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

    async def _handle_compare_providers(self, user_id: str, providers: str, postcode: str = None, speed_in_mb: str = None, current_provider: str = None, new_line: str = None, context: str = None) -> str:
        """Handle provider comparison."""
        if not providers:
            return "❌ Please specify providers to compare."

        provider_list = [p.strip() for p in providers.split(',')]

        if user_id not in self.conversation_state or 'scraped_data' not in self.conversation_state[user_id]:
            # Auto-scrape data if not available
            postcode = postcode or 'E14 9WB'  # Default postcode if not provided
            scrape_result = await self._handle_scrape_data(
                user_id, postcode, speed_in_mb, None, None, None, providers, current_provider, new_line, context
            )

            # If scraping returned an error message, return it
            if scrape_result and isinstance(scrape_result, str) and scrape_result.startswith("❌"):
                return scrape_result

        data = self.conversation_state[user_id]['scraped_data']
        if not data or 'error' in data or data.get('total_deals', 0) == 0:
            if data and 'error' in data and 'Browser scraping not available' in data.get('error', ''):
                return "❌ Data scraping is currently limited in this environment. Please use the generated URL to view deals directly."
            else:
                return "❌ Unable to fetch broadband data for provider comparison."

        deals = data.get('deals', [])

        # Filter deals by providers
        matching_deals = [deal for deal in deals if deal['provider']['name'] in provider_list]

        if not matching_deals:
            return f"❌ No deals found for providers: {', '.join(provider_list)}"

        # Create structured output for AI
        structured_output = self._create_structured_output(
            user_id=user_id,
            action_type="provider_comparison",
            param="providers_compared,total_matches",
            value=f"{', '.join(provider_list)},{len(matching_deals)}",
            interaction_type="provider_comparison",
            clicked=True,
            element_name="compare_providers",
            context=context,
            providers_compared=provider_list,
            matching_deals=matching_deals,
            total_matches=len(matching_deals)
        )

        await self.send_websocket_message(
            message_type="comparison_action",
            action="provider_comparison",
            data=structured_output
        )

        # Return structured data for the AI
        return {
            'status': 'success',
            'message': f'Found {len(matching_deals)} deals for providers: {", ".join(provider_list)}',
            'data': {
                'providers_compared': provider_list,
                'matching_deals': matching_deals[:10],  # Top 10 matching deals
                'total_matches': len(matching_deals)
            },
            'suggestions': [
                'Compare specific deals',
                'Find the cheapest option among these',
                'Show fastest deals from these providers'
            ]
        }

    async def _handle_refine_search(self, user_id: str, contract_length: str = None, context: str = None) -> str:
        """Handle search refinement."""
        if user_id not in self.conversation_state:
            # No previous search found - treat as new search with provided parameters
            logger.info(f"🔄 No previous search found for user {user_id}, performing new search with contract_length: {contract_length}")

            # If we have contract_length, perform a new search
            if contract_length:
                # Normalize contract length
                normalized_contract = self._normalize_contract_length(contract_length) if contract_length else None

                # We need a postcode to perform the search - check if one is available in context or use default
                postcode = self.conversation_state.get(user_id, {}).get('confirmed_postcode', 'E14 9WB')

                # Create minimal extracted params for the new search
                extracted_params = {
                    'postcode': postcode,
                    'contract_length': normalized_contract
                }

                # Generate URL and store state
                try:
                    url = self.url_generator.generate_url(**extracted_params)

                    # Store conversation state for future refinements
                    self.conversation_state[user_id] = {
                        'query': f"Refine search with contract: {contract_length}",
                        'extracted_params': extracted_params,
                        'generated_url': url,
                        'last_action': 'refine_search',
                        'timestamp': datetime.now().isoformat()
                    }

                    return self._create_structured_output(
                        user_id=user_id,
                        action_type="url_generated",
                        param="url,contract_length",
                        value=f"{url},{contract_length}",
                        interaction_type="url_generation",
                        clicked=False,
                        element_name="refine_search",
                        context=context,
                        extracted_params=extracted_params,
                        generated_url=url
                    )
                except Exception as e:
                    logger.error(f"❌ Error generating URL for refine search: {e}")
                    return f"❌ Error generating broadband comparison URL: {str(e)}"
            else:
                return "❌ No previous search found and no contract length provided for new search. Please provide search parameters first."

        state = self.conversation_state[user_id]

        # Prepare data for structured output
        current_params = {}
        refinement_options = {
            'speed': 'I want 100Mb speed or make it faster',
            'contract': 'change to 24 months or shorter contract',
            'providers': 'include BT and Sky or only Virgin Media',
            'price_range': 'under £30 per month or cheapest available',
            'phone_calls': 'add evening calls or no phone line'
        }

        if 'extracted_params' in state:
            params = state['extracted_params']
            current_params = {
                'postcode': params.get('postcode', 'Not set'),
                'speed': params.get('speed_in_mb', 'Not set'),
                'contract': params.get('contract_length', 'Not set'),
                'phone_calls': params.get('phone_calls', 'Not set')
            }

        # Create structured output for AI
        structured_output = self._create_structured_output(
            user_id=user_id,
            action_type="refinement_options",
            param="refinement_available",
            value="true",
            interaction_type="refinement",
            clicked=True,
            element_name="refine_search",
            context=context,
            current_parameters=current_params,
            refinement_options=refinement_options
        )

        await self.send_websocket_message(
            message_type="refinement_action",
            action="refinement_options",
            data=structured_output
        )

        # Return structured data for search refinement
        return {
            'status': 'refinement_options',
            'message': 'Here are your search refinement options',
            'data': {
                'current_parameters': current_params,
                'refinement_options': refinement_options
            },
            'suggestions': [
                'Specify what you want to change',
                'Use natural language like "make it faster"',
                'Try different combinations'
            ]
        }

    async def _handle_get_cheapest(self, user_id: str, postcode: str = None, current_provider: str = None, new_line: str = None, context: str = None) -> str:
        """Handle cheapest deal requests."""
        if user_id not in self.conversation_state or 'scraped_data' not in self.conversation_state[user_id]:
            # Scrape data if not available
            postcode = postcode or 'E14 9WB'  # Default postcode if not provided
            scrape_result = await self._handle_scrape_data(user_id, postcode, None, None, None, None, None, current_provider, new_line, context)

            # If scraping returned an error message, return it
            if scrape_result and isinstance(scrape_result, str) and scrape_result.startswith("❌"):
                return scrape_result

        if user_id not in self.conversation_state or 'scraped_data' not in self.conversation_state[user_id]:
            return "❌ Unable to fetch broadband data at this time."

        data = self.conversation_state[user_id]['scraped_data']
        if 'error' in data:
            if 'Browser scraping not available' in data.get('error', ''):
                return "❌ Data scraping is currently limited in this environment. Please use the generated URL to view deals directly."
            else:
                return f"❌ Unable to fetch broadband data: {data.get('error', 'Unknown error')}"

        deals = data.get('deals', [])

        if not deals:
            return "❌ No deals available to find cheapest option."

        # Sort by monthly cost
        sorted_deals = sorted(deals,
                            key=lambda x: float(x['pricing']['monthly_cost'].replace('£', '').replace(',', '')))

        cheapest = sorted_deals[0]

        # Create structured output for AI
        structured_output = self._create_structured_output(
            user_id=user_id,
            action_type="cheapest_deal",
            param="provider,monthly_cost",
            value=f"{cheapest['provider']['name']},{cheapest['pricing']['monthly_cost']}",
            interaction_type="cheapest_search",
            clicked=True,
            element_name="get_cheapest",
            context=context,
            cheapest_deal=cheapest,
            total_deals_analyzed=len(deals)
        )

        await self.send_websocket_message(
            message_type="cheapest_action",
            action="cheapest_deal_found",
            data=structured_output
        )

        # Return structured data for the AI
        return {
            'status': 'success',
            'message': f'Found the cheapest broadband deal: {cheapest["provider"]["name"]} - {cheapest["title"]}',
            'data': {
                'cheapest_deal': cheapest,
                'total_deals_analyzed': len(deals)
            },
            'suggestions': [
                'Compare this with other deals',
                'Check if this meets your speed requirements',
                'See if there are better value options'
            ]
        }

    async def _handle_get_fastest(self, user_id: str, postcode: str = None, current_provider: str = None, new_line: str = None, context: str = None) -> str:
        """Handle fastest deal requests."""
        if user_id not in self.conversation_state or 'scraped_data' not in self.conversation_state[user_id]:
            # Scrape data if not available
            postcode = postcode or 'E14 9WB'  # Default postcode if not provided
            scrape_result = await self._handle_scrape_data(user_id, postcode, None, None, None, None, None, current_provider, new_line, context)

            # If scraping returned an error message, return it
            if scrape_result and isinstance(scrape_result, str) and scrape_result.startswith("❌"):
                return scrape_result

        if user_id not in self.conversation_state or 'scraped_data' not in self.conversation_state[user_id]:
            return "❌ Unable to fetch broadband data at this time."

        data = self.conversation_state[user_id]['scraped_data']
        if 'error' in data:
            if 'Browser scraping not available' in data.get('error', ''):
                return "❌ Data scraping is currently limited in this environment. Please use the generated URL to view deals directly."
            else:
                return f"❌ Unable to fetch broadband data: {data.get('error', 'Unknown error')}"

        deals = data.get('deals', [])

        if not deals:
            return "❌ No deals available to find fastest option."

        # Sort by speed (highest first)
        sorted_deals = sorted(deals,
                            key=lambda x: int(x['speed']['numeric']),
                            reverse=True)

        fastest = sorted_deals[0]

        # Create structured output for AI
        structured_output = self._create_structured_output(
            user_id=user_id,
            action_type="fastest_deal",
            param="provider,speed",
            value=f"{fastest['provider']['name']},{fastest['speed']['display']}",
            interaction_type="fastest_search",
            clicked=True,
            element_name="get_fastest",
            context=context,
            fastest_deal=fastest,
            total_deals_analyzed=len(deals)
        )

        await self.send_websocket_message(
            message_type="fastest_action",
            action="fastest_deal_found",
            data=structured_output
        )

        # Return structured data for the AI
        return {
            'status': 'success',
            'message': f'Found the fastest broadband deal: {fastest["provider"]["name"]} - {fastest["title"]}',
            'data': {
                'fastest_deal': fastest,
                'total_deals_analyzed': len(deals)
            },
            'suggestions': [
                'Compare this with cheaper options',
                'Check if this speed is available in your area',
                'See if there are better value high-speed deals'
            ]
        }

    async def _handle_clarify_missing_params(self, user_id: str, context: str = None) -> str:
        """Handle missing parameter clarification."""
        # Create structured output for AI
        structured_output = self._create_structured_output(
            user_id=user_id,
            action_type="clarification_needed",
            param="missing_parameters",
            value="postcode,speed,contract,phone_calls",
            interaction_type="clarification",
            clicked=False,
            element_name="clarify_missing_params",
            context=context,
            required_parameters={
                'postcode': 'Your postcode or location (any format accepted)',
                'speed': 'Speed preference (e.g., 30Mb, 55Mb, 100Mb)',
                'contract': 'Contract length (e.g., 12 months, 24 months)',
                'phone_calls': 'Phone calls (e.g., evening and weekend, anytime, none)'
            }
        )

        await self.send_websocket_message(
            message_type="clarification_action",
            action="clarification_needed",
            data=structured_output
        )

        # Return structured data for parameter clarification
        return {
            'status': 'needs_clarification',
            'message': 'I need more information to help you find the best broadband deals',
            'data': {
                'required_parameters': {
                    'postcode': 'Your postcode or location (any format accepted)',
                    'speed': 'Speed preference (e.g., 30Mb, 55Mb, 100Mb)',
                    'contract': 'Contract length (e.g., 12 months, 24 months)',
                    'phone_calls': 'Phone calls (e.g., evening and weekend, anytime, none)'
                }
            },
            'suggestions': [
                'Provide your postcode and preferences',
                'Use natural language like "Find deals in E14 9WB with 100Mb speed"',
                'Specify what you want to change or refine'
            ]
        }

    async def _handle_postcode_suggestions(self, user_id: str, original_postcode: str, context: str = None) -> str:
        """Handle postcode suggestions from fuzzy search."""
        try:
            # Get suggestions from conversation state
            suggestions = self.conversation_state.get(user_id, {}).get('postcode_suggestions', [])

            if not suggestions:
                return "❌ No postcode suggestions available."

            # Create structured output for AI
            structured_output = self._create_structured_output(
                user_id=user_id,
                action_type="postcode_suggestions",
                param="original_postcode,suggestion_count",
                value=f"{original_postcode},{len(suggestions)}",
                interaction_type="postcode_suggestions",
                clicked=True,
                element_name="postcode_suggestions",
                context=context,
                original_postcode=original_postcode,
                postcode_suggestions=suggestions
            )

            await self.send_websocket_message(
                message_type="suggestions_action",
                action="postcode_suggestions",
                data=structured_output
            )

            # Format response for user
            response = f"🤔 **Did you mean one of these postcodes?**\n\n"
            response += f"**You entered:** `{original_postcode}`\n\n"
            response += "**Top suggestions:**\n\n"

            for i, (postcode, score) in enumerate(suggestions[:5], 1):
                response += f"**{i}. {postcode}** (confidence: {score:.1f}%)\n"

            response += "\n💡 Please confirm which postcode you'd like to use, or provide a different one."

            return response

        except Exception as e:
            return f"❌ Error showing postcode suggestions: {str(e)}"

    async def _handle_filter_data(self, user_id: str, filter_speed: str = None, filter_providers: str = None,
                                 filter_contract: str = None, filter_phone_calls: str = None, filter_new_line: str = None, context: str = None) -> str:
        """Handle filtering of scraped data with new criteria."""
        try:
            # Get current scraped data
            if user_id not in self.conversation_state or 'scraped_data' not in self.conversation_state[user_id]:
                return "❌ Please scrape data first before applying filters."

            data = self.conversation_state[user_id]['scraped_data']
            if not data or 'error' in data or data.get('total_deals', 0) == 0:
                return "❌ No data available to filter."

            deals = data.get('deals', [])

            if not deals:
                return "❌ No deals available to filter."

            # Get current filter state
            if user_id not in self.filter_state:
                self.filter_state[user_id] = {}

            # Update filters
            if filter_speed:
                self.filter_state[user_id]['speed'] = filter_speed
            if filter_providers:
                self.filter_state[user_id]['providers'] = filter_providers
            if filter_contract:
                self.filter_state[user_id]['contract'] = filter_contract
            if filter_phone_calls:
                self.filter_state[user_id]['phone_calls'] = filter_phone_calls
            if filter_new_line:
                self.filter_state[user_id]['new_line'] = filter_new_line

            # Apply filters to deals
            filtered_deals = self._apply_filters(deals, self.filter_state[user_id])

            # Create structured output for AI
            structured_output = self._create_structured_output(
                user_id=user_id,
                action_type="data_filtered",
                param="total_filtered",
                value=str(len(filtered_deals)),
                interaction_type="data_filtering",
                clicked=True,
                element_name="filter_data",
                context=context,
                filtered_data=filtered_deals,
                applied_filters=self.filter_state[user_id],
                total_filtered=len(filtered_deals)
            )

            await self.send_websocket_message(
                message_type="filter_action",
                action="data_filtered",
                data=structured_output
            )

            # Return structured data for the AI
            return {
                'status': 'success',
                'message': f'Filtered to {len(filtered_deals)} deals',
                'data': {
                    'total_filtered': len(filtered_deals),
                    'filtered_deals': filtered_deals[:10],  # Top 10 filtered deals
                    'applied_filters': self.filter_state[user_id],
                    'total_original': len(deals)
                },
                'suggestions': [
                    'Get recommendations from filtered results',
                    'Compare filtered deals',
                    'Find cheapest/fastest from filtered results',
                    'Apply additional filters'
                ]
            }

        except Exception as e:
            return f"❌ Error filtering data: {str(e)}"

    def _apply_filters(self, deals: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
        """Apply filters to the deals list."""
        filtered_deals = deals

        # Filter by speed
        if 'speed' in filters:
            target_speed = int(filters['speed'].replace('Mb', ''))
            filtered_deals = [deal for deal in filtered_deals if int(deal['speed']['numeric']) >= target_speed]

        # Filter by providers
        if 'providers' in filters and filters['providers']:
            provider_list = [p.strip() for p in filters['providers'].split(',')]
            filtered_deals = [deal for deal in filtered_deals if deal['provider']['name'] in provider_list]

        # Filter by contract length
        if 'contract' in filters:
            target_contract = filters['contract']
            filtered_deals = [deal for deal in filtered_deals if target_contract in deal['contract']['length_months']]

        # Filter by phone calls
        if 'phone_calls' in filters and filters['phone_calls'] != 'Show me everything':
            target_calls = filters['phone_calls']
            filtered_deals = [deal for deal in filtered_deals if target_calls.lower() in deal['features']['phone_calls'].lower()]

        # Filter by new line option
        # Note: This filter may not be applicable to scraped deal data as it depends on the URL parameter
        # The new_line parameter affects the URL generation, not the individual deals
        if 'new_line' in filters and filters['new_line']:
            # This is a URL-level parameter, so we can't filter existing deals by it
            # The filtering would need to be done at the scraping level with different URLs
            pass

        return filtered_deals

    async def _handle_open_url(self, user_id: str, url: str = None, context: str = None) -> str:
        """Handle opening a URL in a new tab."""
        try:
            if not url:
                return "❌ Please provide a URL to open."

            # Validate URL format
            if not url.startswith(('http://', 'https://')):
                # Add https:// if no protocol specified
                url = f"https://{url}"

            # Create structured output for AI
            structured_output = self._create_structured_output(
                user_id=user_id,
                action_type="url_opened",
                param="url",
                value=url,
                interaction_type="url_open",
                clicked=True,
                element_name="open_url",
                context=context,
                url=url
            )

            await self.send_websocket_message(
                message_type="url_action",
                action="open_url",
                data=structured_output
            )

            logger.info(f"🔗 Opening URL for user {user_id}: {url}")
            return f"✅ Opening URL: {url}"

        except Exception as e:
            logger.error(f"❌ Error opening URL: {e}")
            return f"❌ Error opening URL: {str(e)}"


def create_broadband_tool(rtvi_processor: RTVIProcessor, task=None, initial_current_page: str = "broadband") -> BroadbandTool:
    """Factory function to create a BroadbandTool instance."""
    return BroadbandTool(rtvi_processor, task, initial_current_page)