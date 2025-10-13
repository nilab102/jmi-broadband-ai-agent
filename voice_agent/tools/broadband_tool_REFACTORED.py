#!/usr/bin/env python3
"""
Broadband Tool for voice-agent backend - REFACTORED VERSION.
Slim orchestrator that delegates to modular functions.

Handles natural language queries about broadband requirements, generates comparison URLs,
scrapes data, and provides AI-powered recommendations with fuzzy postal code validation.

ARCHITECTURE:
- This file is now a slim orchestrator (~400 lines vs original 2,330 lines)
- All business logic moved to /voice_agent/functions/broadband/ modules
- Uses dependency injection for testability
- Delegates to handler functions instead of internal methods
"""

from typing import Dict, Any, Optional
from loguru import logger
from pipecat.processors.frameworks.rtvi import RTVIProcessor
from pipecat.adapters.schemas.function_schema import FunctionSchema

# Import URL generator and constants (for tool definition)
from voice_agent.broadband_url_generator import BroadbandConstants

# Import services
from voice_agent.services import (
    get_postal_code_service,
    get_scraper_service,
    get_url_generator_service,
    get_recommendation_service
)

# Import modular broadband functions
from voice_agent.functions.broadband import (
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
    normalize_contract_length
)

# Import AI parameter extraction service
try:
    from voice_agent.tools.parameter_extraction_service import get_parameter_extractor
    AI_EXTRACTION_AVAILABLE = True
except ImportError as e:
    AI_EXTRACTION_AVAILABLE = False
    logger.warning(f"⚠️ AI parameter extraction not available: {e}")

from voice_agent.tools.base_tool import BaseTool


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
        
        # Initialize AI parameter extractor if available
        self.ai_extractor = None
        if AI_EXTRACTION_AVAILABLE:
            try:
                self.ai_extractor = get_parameter_extractor()
                logger.info("✅ AI parameter extraction enabled")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize AI parameter extractor: {e}")
        
        # Initialize modular components
        self.provider_matcher = ProviderMatcher(
            valid_providers=BroadbandConstants.VALID_PROVIDERS,
            fuzzy_searcher=self.postal_code_service.searcher if self.postal_code_service else None
        )
        
        self.parameter_extractor = ParameterExtractor(
            ai_extractor=self.ai_extractor,
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
                return await handle_natural_language_query(
                    user_id=user_id,
                    query=kwargs.get('query'),
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

