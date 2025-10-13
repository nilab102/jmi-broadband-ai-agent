#!/usr/bin/env python3
"""
Broadband Tool for voice-agent backend - REFACTORED VERSION.
Slim orchestrator that delegates to modular functions.

Handles natural language queries about broadband requirements, generates comparison URLs,
scrapes data, and provides AI-powered recommendations with fuzzy postal code validation.

ARCHITECTURE:
- This file is now a slim orchestrator (~400 lines vs original 2,330 lines)
- All business logic moved to /jmi_broadband_agent/functions/broadband/ modules
- Uses dependency injection for testability
- Delegates to handler functions instead of internal methods
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

# Import URL generator and constants (for tool definition)
from jmi_broadband_agent.broadband_url_generator import BroadbandConstants

# Import services
from jmi_broadband_agent.services import (
    get_postal_code_service,
    get_scraper_service,
    get_url_generator_service,
    get_recommendation_service
)

# Import modular broadband functions
from jmi_broadband_agent.functions.broadband import (
    # Classes
    ParameterExtractor,
    PostcodeValidator,
    ProviderMatcher,
    RecommendationEngine,
    # Handler functions
    handle_generate_url,
    handle_natural_language_query,
    handle_scrape_data,
    handle_list_providers,
    handle_clarify_missing_params,
    handle_compare_providers,
    handle_get_cheapest,
    handle_get_fastest,
    handle_filter_data,
    handle_refine_search,
    handle_open_url,
    # Helpers
    create_structured_output,
    normalize_contract_length,
    validate_uk_postcode_format,
    interpret_speed_adjective,
    interpret_phone_calls,
    interpret_product_type,
    interpret_sort_preference,
    extract_contract_lengths,
    normalize_contract_single
)

# AI parameter extraction is now handled by the modular ParameterExtractor class
# which gracefully falls back to regex extraction if AI is not available
AI_EXTRACTION_AVAILABLE = False  # Not needed anymore with modular architecture

from jmi_broadband_agent.tools.base_tool import BaseTool


class BroadbandTool(BaseTool):
    """
    Slim orchestrator for broadband comparison queries.
    Delegates to modular handler functions for all operations.
    """

    def __init__(self, rtvi_processor: RTVIProcessor, task=None, initial_current_page: str = "broadband"):
        super().__init__(rtvi_processor, task, initial_current_page)
        self.page_name = "broadband"
        self.available_buttons = [
            "search_deals", "get_recommendations", "compare_providers",
            "find_cheapest", "find_fastest", "refine_search", "list_providers"
        ]

        # Initialize services
        self.postal_code_service = get_postal_code_service()
        self.scraper_service = get_scraper_service(headless=True, timeout=30000)
        self.url_generator_service = get_url_generator_service()
        self.recommendation_service = get_recommendation_service()
        
        # AI parameter extraction is handled by the ParameterExtractor class
        # which gracefully falls back to regex if AI services are unavailable

        # Initialize modular components
        self.provider_matcher = ProviderMatcher(
            valid_providers=BroadbandConstants.VALID_PROVIDERS,
            fuzzy_searcher=self.postal_code_service.searcher if self.postal_code_service else None
        )
        
        self.parameter_extractor = ParameterExtractor(
            ai_extractor=None,  # AI extraction handled internally by ParameterExtractor
            provider_matcher=self.provider_matcher
        )
        self.parameter_extractor.initialize_patterns()
        
        self.postcode_validator = PostcodeValidator(
            postal_code_service=self.postal_code_service,
            conversation_state=self.user_sessions  # Use inherited user_sessions
        )
        
        self.recommendation_engine = RecommendationEngine(
            recommendation_service=self.recommendation_service
        )

        # Initialize parameter patterns for regex extraction
        self.parameter_patterns = self._initialize_parameter_patterns()

        # State management (use inherited user_sessions for conversation state)
        self.conversation_state = self.user_sessions
        self.scraped_data_cache: Dict[str, Dict[str, Any]] = {}
        self.recommendation_cache: Dict[str, list] = {}
        self.filter_state: Dict[str, Dict[str, Any]] = {}

        logger.info("✅ BroadbandTool initialized with modular architecture")

    def _create_structured_output(self, user_id: str, action_type: str, param: str, value: str,
                                 interaction_type: str, **additional_fields) -> Dict[str, Any]:
        """
        Wrapper for create_structured_output helper function.
        Adds current_page and previous_page from session.
        """
        session = self._initialize_user_session(user_id)

        return create_structured_output(
            user_id=user_id,
            action_type=action_type,
            param=param,
            value=value,
            interaction_type=interaction_type,
            current_page=session.get("current_page", self.initial_current_page),
            previous_page=session.get("previous_page"),
            **additional_fields
        )

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
            'providers': [
                # Use fuzzy matching function instead of regex
                (r'(\w+(?:\s+\w+)*)\s*broadband', 'providers', self._extract_provider_with_fuzzy),
                (r'with\s+(\w+(?:\s+\w+)*)', 'providers', self._extract_provider_with_fuzzy),
                (r'from\s+(\w+(?:\s+\w+)*)', 'providers', self._extract_provider_with_fuzzy),
                # Fallback patterns for direct provider names
                (r'(\w+(?:\s+\w+)*)', 'providers', self._extract_provider_with_fuzzy),
            ],
            'product_type': [
                (r'(broadband|phone|tv)\s*only', 'product_type', interpret_product_type),
                (r'(broadband|phone|tv)\s*and\s*(broadband|phone|tv)', 'product_type', interpret_product_type),
            ],
            'sort_by': [
                (r'sort\s*by\s*(\w+)', 'sort_by', lambda x: x.title()),
                (r'cheapest|fastest|recommended', 'sort_by', interpret_sort_preference),
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

        # Check for exact match first (case-insensitive)
        provider_lower = provider_input.strip().lower()
        for valid_provider in BroadbandConstants.VALID_PROVIDERS:
            if provider_lower == valid_provider.lower():
                return valid_provider

        # Use fuzzy search if available
        if not self.postal_code_service or not self.postal_code_service.searcher:
            logger.warning("⚠️ Fuzzy search not available for provider matching")
            return None

        try:
            # Use fuzzy search with the provider names as the search space
            result = self.postal_code_service.searcher.get_fuzzy_results(
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
                    return matched_provider
                else:
                    logger.info(f"🔍 Provider '{provider_input}' below threshold (score: {score:.1f}%, threshold: {threshold}%)")
                    return None
            else:
                return None

        except Exception as e:
            logger.error(f"❌ Error in fuzzy provider matching: {e}")
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

    def extract_parameters_from_query(self, query: str, skip_postcode_validation: bool = False) -> Dict[str, str]:
        """
        Extract broadband parameters from natural language query.
        Delegates to the modular ParameterExtractor instance.

        Args:
            query: Natural language query
            skip_postcode_validation: If True, skip automatic postcode validation (for fuzzy search workflow)

        Returns:
            Dictionary of extracted parameters
        """
        # Delegate to the modular parameter extractor
        return self.parameter_extractor.extract_parameters(query, skip_postcode_validation)
    
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
        if 'new_line' in filters and filters['new_line']:
            pass  # This is a URL-level parameter, filtering would need different URLs

        return filtered_deals

    async def _handle_clarify(self, user_id: str, message: str = None, context: str = None) -> str:
        """Wrapper for handle_clarify_missing_params."""
        return await handle_clarify_missing_params(
                user_id=user_id,
            custom_message=message,
                context=context,
            send_websocket_fn=self.send_websocket_message,
            create_output_fn=self._create_structured_output
        )
    
    async def _handle_filter(self, user_id: str, **kwargs) -> str:
        """Wrapper for handle_filter_data."""
        return await handle_filter_data(
                user_id=user_id,
            conversation_state=self.conversation_state,
            filter_state=self.filter_state,
            send_websocket_fn=self.send_websocket_message,
            create_output_fn=self._create_structured_output,
            **kwargs
        )

    async def _handle_parameter_update(
        self,
        user_id: str,
        postcode: str = None,
        speed_in_mb: str = None,
        contract_length: str = None,
        phone_calls: str = None,
        providers: str = None,
        current_provider: str = None,
        sort_by: str = None,
        new_line: str = None,
        product_type: str = None,
        context: str = None
    ) -> str:
        """
        Handle parameter updates in conversational flow.
        Accumulates parameters and auto-generates URLs when sufficient info is available.

        Args:
            user_id: User ID
            postcode: Postcode (if provided)
            speed_in_mb: Speed requirement (if provided)
            contract_length: Contract length (if provided)
            phone_calls: Phone calls preference (if provided)
            providers: Provider preference (if provided)
            current_provider: Current provider (if provided)
            sort_by: Sort preference (if provided)
            new_line: New line option (if provided)
            product_type: Product type (if provided)
            context: Additional context

        Returns:
            Response message with current status
        """
        try:
            # Initialize user session if needed
            session = self._initialize_user_session(user_id)

            # Get current broadband parameters from session
            current_params = session.get('broadband_params', {})

            # Update parameters with new values (only if provided)
            updated_params = current_params.copy()

            if postcode:
                updated_params['postcode'] = postcode
                logger.info(f"📍 Updated postcode for user {user_id}: {postcode}")

            if speed_in_mb:
                updated_params['speed_in_mb'] = speed_in_mb
                logger.info(f"⚡ Updated speed for user {user_id}: {speed_in_mb}")

            if contract_length:
                # Normalize contract length
                if contract_length:
                    contract_length = normalize_contract_length(contract_length)
                updated_params['contract_length'] = contract_length
                logger.info(f"📅 Updated contract for user {user_id}: {contract_length}")

            if phone_calls:
                updated_params['phone_calls'] = phone_calls
                logger.info(f"📞 Updated phone calls for user {user_id}: {phone_calls}")

            if providers:
                # Apply fuzzy matching to correct provider names
                corrected_providers = []
                for provider in providers.split(','):
                    provider = provider.strip()
                    if provider:
                        matched_provider = self.provider_matcher.fuzzy_match(provider)
                        if matched_provider:
                            corrected_providers.append(matched_provider)
                            logger.info(f"🔍 Corrected provider '{provider}' to '{matched_provider}'")
                        else:
                            corrected_providers.append(provider)
                            logger.warning(f"⚠️ Could not match provider '{provider}'")

                updated_params['providers'] = ','.join(corrected_providers)
                logger.info(f"🏢 Updated providers for user {user_id}: {updated_params['providers']}")

            if current_provider:
                # Apply fuzzy matching to correct current provider name
                matched_provider = self.provider_matcher.fuzzy_match(current_provider)
                if matched_provider:
                    updated_params['current_provider'] = matched_provider
                    logger.info(f"🔍 Corrected current provider '{current_provider}' to '{matched_provider}'")
                else:
                    updated_params['current_provider'] = current_provider
                    logger.warning(f"⚠️ Could not match current provider '{current_provider}'")
                logger.info(f"🏠 Updated current provider for user {user_id}: {updated_params['current_provider']}")

            if sort_by:
                updated_params['sort_by'] = sort_by
                logger.info(f"📊 Updated sort by for user {user_id}: {sort_by}")

            if new_line:
                updated_params['new_line'] = new_line
                logger.info(f"🆕 Updated new line for user {user_id}: {new_line}")

            if product_type:
                updated_params['product_type'] = product_type
                logger.info(f"📦 Updated product type for user {user_id}: {product_type}")

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
                if key not in updated_params:
                    updated_params[key] = default_value

            # Store updated parameters in session
            session['broadband_params'] = updated_params
            self.user_sessions[user_id] = session

            # Check if we have minimum required parameters (postcode + speed)
            has_postcode = updated_params.get('postcode')
            has_speed = updated_params.get('speed_in_mb')

            response_parts = []

            if has_postcode and has_speed:
                # We have enough info to generate a URL
                logger.info(f"🎯 Sufficient parameters for URL generation: postcode={has_postcode}, speed={has_speed}")

                # Validate postcode if it's new
                if postcode and not session.get('postcode_validated'):
                    # Validate postcode format
                    if not self._validate_uk_postcode_format(has_postcode):
                        return await self._handle_clarify(
                            user_id,
                            f"'{has_postcode}' doesn't look like a valid UK postcode. Please provide a valid postcode (e.g., E14 9WB).",
                            context
                        )

                    # Mark as validated
                    session['postcode_validated'] = True
                    self.user_sessions[user_id] = session

                # Generate URL
                url = self.url_generator_service.generate_url(updated_params)

                # Send WebSocket message for URL generation
                if self.send_websocket_message and self._create_structured_output:
                    structured_output = self._create_structured_output(
                        user_id=user_id,
                        action_type="url_generated",
                        param="url,postcode",
                        value=f"{url},{updated_params['postcode']}",
                        interaction_type="url_generation",
                        clicked=False,
                        element_name="auto_generate_url",
                        context=context,
                        generated_params=updated_params,
                        generated_url=url
                    )

                    await self.send_websocket_message(
                        message_type="url_action",
                        action="url_generated",
                        data=structured_output
                    )

                response_parts.append(f"✅ **URL Updated!**\n\n**Current Settings:**")
                response_parts.append(f"• Postcode: {updated_params['postcode']}")
                response_parts.append(f"• Speed: {updated_params['speed_in_mb']}")
                if updated_params.get('contract_length'):
                    response_parts.append(f"• Contract: {updated_params['contract_length']}")
                if updated_params.get('phone_calls') and updated_params['phone_calls'] != 'Show me everything':
                    response_parts.append(f"• Phone Calls: {updated_params['phone_calls']}")
                if updated_params.get('providers'):
                    response_parts.append(f"• Preferred Providers: {updated_params['providers']}")
                if updated_params.get('current_provider'):
                    response_parts.append(f"• Current Provider: {updated_params['current_provider']}")
                if updated_params.get('sort_by') and updated_params['sort_by'] != 'Recommended':
                    response_parts.append(f"• Sort By: {updated_params['sort_by']}")
                if updated_params.get('new_line'):
                    response_parts.append(f"• New Line: {updated_params['new_line']}")
                if updated_params.get('product_type') and updated_params['product_type'] != 'broadband,phone':
                    response_parts.append(f"• Product Type: {updated_params['product_type']}")

                response_parts.append(f"\n**Comparison URL:** {url}")
                response_parts.append(f"\n💡 **Next steps you can ask me:**")
                response_parts.append(f"• 'Show me recommendations' - Get personalized suggestions")
                response_parts.append(f"• 'Compare providers' - Compare specific broadband providers")
                response_parts.append(f"• 'Find cheapest deals' - Show the lowest priced options")
                response_parts.append(f"• 'Change to 100Mb speed' - Update your speed preference")
                response_parts.append(f"• '12 month contract' - Update contract length")
                response_parts.append(f"• 'Sort by price' - Change sorting preference")
                response_parts.append(f"• 'Include new line' - Add new line installation")
                response_parts.append(f"• 'Just broadband only' - Change product type")
                response_parts.append(f"• 'My current provider is BT' - Set current provider")

            else:
                # Missing required parameters
                response_parts.append("📝 **Parameters Updated!**")
                response_parts.append(f"\n**Current Settings:**")

                if has_postcode:
                    response_parts.append(f"• Postcode: {updated_params['postcode']}")
                else:
                    response_parts.append(f"• Postcode: Not set")

                if has_speed:
                    response_parts.append(f"• Speed: {updated_params['speed_in_mb']}")
                else:
                    response_parts.append(f"• Speed: Not set (default: 30Mb)")

                if updated_params.get('contract_length'):
                    response_parts.append(f"• Contract: {updated_params['contract_length']}")
                if updated_params.get('phone_calls') and updated_params['phone_calls'] != 'Show me everything':
                    response_parts.append(f"• Phone Calls: {updated_params['phone_calls']}")
                if updated_params.get('providers'):
                    response_parts.append(f"• Preferred Providers: {updated_params['providers']}")
                if updated_params.get('current_provider'):
                    response_parts.append(f"• Current Provider: {updated_params['current_provider']}")
                if updated_params.get('sort_by') and updated_params['sort_by'] != 'Recommended':
                    response_parts.append(f"• Sort By: {updated_params['sort_by']}")
                if updated_params.get('new_line'):
                    response_parts.append(f"• New Line: {updated_params['new_line']}")
                if updated_params.get('product_type') and updated_params['product_type'] != 'broadband,phone':
                    response_parts.append(f"• Product Type: {updated_params['product_type']}")

                missing = []
                if not has_postcode:
                    missing.append("postcode")
                if not has_speed:
                    missing.append("speed preference")

                if missing:
                    response_parts.append(f"\n⚠️ **Still need:** {', '.join(missing)}")
                    response_parts.append(f"\n💡 **Example:** 'I want 55Mb speed' or 'Postcode is E14 9WB'")

            return "\n".join(response_parts)

        except Exception as e:
            logger.error(f"❌ Error handling parameter update: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"❌ Error updating broadband parameters: {str(e)}"
    
    async def _handle_scrape(self, user_id: str, **kwargs) -> str:
        """Wrapper for handle_scrape_data."""
        return await handle_scrape_data(
                        user_id=user_id,
            url_generator=self.url_generator_service,
            scraper_service=self.scraper_service,
            scraped_data_cache=self.scraped_data_cache,
            conversation_state=self.conversation_state,
            send_websocket_fn=self.send_websocket_message,
            create_output_fn=self._create_structured_output,
            **kwargs
        )

    def get_tool_definition(self) -> FunctionSchema:
        """Get the tool definition for the LLM."""
        return FunctionSchema(
            name="broadband_action",
            description="Handle broadband comparison queries with natural language processing, URL generation, and AI-powered recommendations. Only available on the broadband page. CONVERSATIONAL MODE: Supports building broadband requirements piece by piece. Provide parameters individually (postcode, speed, contract, etc.) and URLs auto-generate when sufficient info is available. Postcode validation is AUTOMATIC - validates format with regex, searches database using fuzzy matching, and auto-selects best match (100% match or highest score). NO user confirmation needed!",
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
                    "description": "Type of broadband action. Use 'query' for natural language queries (includes automatic postcode validation and matching). Use 'open_url' to open a URL in a new tab."
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
                    "description": "UK postcode (any format). Will be automatically validated and matched against database."
                },
                "speed_in_mb": {
                    "type": "string",
                    "enum": ["10Mb", "30Mb", "55Mb", "100Mb"],
                    "description": "Speed requirement"
                },
                "contract_length": {
                    "type": "string",
                    "description": "Contract length preference. Valid: '1 month', '12 months', '18 months', '24 months', or empty for no filter. Can specify multiple comma-separated."
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
                    "description": "User's existing broadband provider (optional)"
                },
                "sort_by": {
                    "type": "string",
                    "enum": BroadbandConstants.VALID_SORT_OPTIONS,
                    "description": "Sort preference"
                },
                "new_line": {
                    "type": "string",
                    "description": "New line cost option. Leave empty for existing line, set to 'NewLine' for new line installation."
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
                    "description": "Contract length filter to apply"
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

    async def execute(self, user_id: str, action_type: str, **kwargs) -> str:
        """
        Execute broadband action by delegating to modular handler functions.
        
        This method is now a slim orchestrator that routes requests to appropriate
        handler functions with dependency injection.
        """
        try:
            # Initialize user session
            self._initialize_user_session(user_id)
            current_page = self.get_user_current_page(user_id)

            logger.info(f"📡 Broadband action - User: {user_id}, Action: {action_type}, Page: {current_page}")

            # Validate page
            expected_pages = [self.page_name, self.page_name.replace("/", "-")]
            if current_page not in expected_pages:
                return f"❌ Broadband operations are only available on the {self.page_name} page. Current page: {current_page}"

            # Extract common parameters
            context = kwargs.get('context')
            
            # Route to appropriate handler with dependency injection
            if action_type == "query":
                # Handle both natural language queries and parameter-based queries
                query = kwargs.get('query')

                # If we have a natural language query, process it normally
                if query and isinstance(query, str) and query.strip():
                    return await handle_natural_language_query(
                        user_id=user_id,
                        query=query,
                        context=context,
                        parameter_extractor=self.parameter_extractor,
                        postcode_validator=self.postcode_validator,
                        url_generator=self.url_generator_service,
                        conversation_state=self.conversation_state,
                        send_websocket_fn=self.send_websocket_message,
                        create_output_fn=self._create_structured_output,
                        handle_clarify_fn=self._handle_clarify,
                        handle_filter_fn=self._handle_filter
                    )

                # If no query but individual parameters provided, handle as parameter update
                else:
                    return await self._handle_parameter_update(
                        user_id=user_id,
                        postcode=kwargs.get('postcode'),
                        speed_in_mb=kwargs.get('speed_in_mb'),
                        contract_length=kwargs.get('contract_length'),
                        phone_calls=kwargs.get('phone_calls'),
                        providers=kwargs.get('providers'),
                        current_provider=kwargs.get('current_provider'),
                        sort_by=kwargs.get('sort_by'),
                        new_line=kwargs.get('new_line'),
                        product_type=kwargs.get('product_type'),
                        context=context
                    )
            
            elif action_type == "generate_url":
                return await handle_generate_url(
                user_id=user_id,
                    postcode=kwargs.get('postcode'),
                    speed_in_mb=kwargs.get('speed_in_mb'),
                    contract_length=kwargs.get('contract_length'),
                    phone_calls=kwargs.get('phone_calls'),
                    product_type=kwargs.get('product_type'),
                    providers=kwargs.get('providers'),
                    current_provider=kwargs.get('current_provider'),
                    sort_by=kwargs.get('sort_by'),
                    new_line=kwargs.get('new_line'),
                context=context,
                    url_generator=self.url_generator_service,
                    send_websocket_fn=self.send_websocket_message,
                    create_output_fn=self._create_structured_output,
                    handle_clarify_fn=self._handle_clarify
                )
            
            elif action_type == "scrape_data":
                return await self._handle_scrape(
                    user_id,
                    postcode=kwargs.get('postcode'),
                    speed_in_mb=kwargs.get('speed_in_mb'),
                    contract_length=kwargs.get('contract_length'),
                    phone_calls=kwargs.get('phone_calls'),
                    product_type=kwargs.get('product_type'),
                    providers=kwargs.get('providers'),
                    current_provider=kwargs.get('current_provider'),
                    new_line=kwargs.get('new_line'),
                    context=context
                )
            
            elif action_type == "get_recommendations":
                return await self.recommendation_engine.handle_get_recommendations(
                user_id=user_id,
                    postcode=kwargs.get('postcode'),
                    speed_in_mb=kwargs.get('speed_in_mb'),
                    contract_length=kwargs.get('contract_length'),
                    phone_calls=kwargs.get('phone_calls'),
                    product_type=kwargs.get('product_type'),
                    providers=kwargs.get('providers'),
                    current_provider=kwargs.get('current_provider'),
                    new_line=kwargs.get('new_line'),
                context=context,
                    conversation_state=self.conversation_state,
                    recommendation_cache=self.recommendation_cache,
                    scrape_data_fn=self._handle_scrape,
                    send_websocket_fn=self.send_websocket_message,
                    create_output_fn=self._create_structured_output
                )
            
            elif action_type == "compare_providers":
                return await handle_compare_providers(
                user_id=user_id,
                    providers=kwargs.get('providers'),
                    postcode=kwargs.get('postcode'),
                    speed_in_mb=kwargs.get('speed_in_mb'),
                    current_provider=kwargs.get('current_provider'),
                    new_line=kwargs.get('new_line'),
                context=context,
                    conversation_state=self.conversation_state,
                    scrape_data_fn=self._handle_scrape,
                    send_websocket_fn=self.send_websocket_message,
                    create_output_fn=self._create_structured_output
                )
            
            elif action_type == "get_cheapest":
                return await handle_get_cheapest(
                user_id=user_id,
                    postcode=kwargs.get('postcode'),
                    current_provider=kwargs.get('current_provider'),
                    new_line=kwargs.get('new_line'),
                context=context,
                    conversation_state=self.conversation_state,
                    scrape_data_fn=self._handle_scrape,
                    send_websocket_fn=self.send_websocket_message,
                    create_output_fn=self._create_structured_output
                )
            
            elif action_type == "get_fastest":
                return await handle_get_fastest(
            user_id=user_id,
                    postcode=kwargs.get('postcode'),
                    current_provider=kwargs.get('current_provider'),
                    new_line=kwargs.get('new_line'),
            context=context,
                    conversation_state=self.conversation_state,
                    scrape_data_fn=self._handle_scrape,
                    send_websocket_fn=self.send_websocket_message,
                    create_output_fn=self._create_structured_output
                )
            
            elif action_type == "refine_search":
                return await handle_refine_search(
                        user_id=user_id,
                    contract_length=kwargs.get('contract_length'),
                        context=context,
                    conversation_state=self.conversation_state,
                    url_generator=self.url_generator_service,
                    send_websocket_fn=self.send_websocket_message,
                    create_output_fn=self._create_structured_output
                )
            
            elif action_type == "list_providers":
                return await handle_list_providers(
            user_id=user_id,
            context=context,
                    valid_providers=BroadbandConstants.VALID_PROVIDERS,
                    send_websocket_fn=self.send_websocket_message,
                    create_output_fn=self._create_structured_output
                )
            
            elif action_type == "filter_data":
                return await self._handle_filter(
                    user_id,
                    filter_speed=kwargs.get('filter_speed'),
                    filter_providers=kwargs.get('filter_providers'),
                    filter_contract=kwargs.get('filter_contract'),
                    filter_phone_calls=kwargs.get('filter_phone_calls'),
                    filter_new_line=kwargs.get('filter_new_line'),
                    context=context
                )
            
            elif action_type == "open_url":
                return await handle_open_url(
            user_id=user_id,
                    url=kwargs.get('url'),
            context=context,
                    send_websocket_fn=self.send_websocket_message,
                    create_output_fn=self._create_structured_output
                )
            
            else:
                return f"❌ Invalid action type: {action_type}"

        except Exception as e:
            logger.error(f"❌ Error executing broadband tool: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"❌ Error processing broadband request: {str(e)}"


def create_broadband_tool(rtvi_processor: RTVIProcessor, task=None, initial_current_page: str = "broadband") -> BroadbandTool:
    """Factory function to create a BroadbandTool instance."""
    return BroadbandTool(rtvi_processor, task, initial_current_page)

