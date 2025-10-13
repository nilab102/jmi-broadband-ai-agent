#!/usr/bin/env python3
"""
Enhanced LangChain-based conversational AI agent with modular tool support.
Updated to work with the new tool structure and improved configuration.

OPTIMIZED VERSION WITH BROADBAND TOOL INTEGRATION:
- Intelligent query pre-processing for broadband queries
- Smart caching layer for broadband results and parameters
- Broadband-specific context management per user
- Enhanced system prompts with broadband guidance
- Progress tracking for long-running operations
- Optimized parameter extraction and validation
- Better error handling and recovery
"""

import os
import json
import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timedelta
from functools import partial
from collections import OrderedDict

from loguru import logger
from dotenv import load_dotenv

# LangChain imports
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.agents import create_tool_calling_agent, AgentExecutor
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.memory import ConversationBufferWindowMemory
    from langchain.schema import BaseMessage, HumanMessage, AIMessage
    from langchain.tools import BaseTool, tool, StructuredTool
    from langchain_core.messages import SystemMessage
    from langchain_core.runnables import RunnableConfig
    from pydantic import BaseModel, Field, create_model, field_validator
    from typing import Literal
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("⚠️ LangChain libraries not available, using mock implementation")

# Import new modular components
try:
    from ..config.settings import get_settings, MSSQL_SEARCH_AI_SYSTEM_INSTRUCTION
    from .websocket_registry import get_registry
    from .agent_manager import create_agent_manager
    from .conversation_manager import get_conversation_manager
    from ..utils.langfuse_tracing import (
        get_langfuse_tracer, trace_conversation, log_api_call,
        calculate_response_quality_score, extract_conversation_insights, score_conversation_quality
    )
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ..config.settings import get_settings, MSSQL_SEARCH_AI_SYSTEM_INSTRUCTION
    from .websocket_registry import get_registry
    from .agent_manager import create_agent_manager
    from ..utils.langfuse_tracing import get_langfuse_tracer, trace_conversation, log_api_call

load_dotenv(override=True)


# ============================================================================
# BROADBAND-SPECIFIC OPTIMIZATION CLASSES
# ============================================================================

class BroadbandContextManager:
    """
    Manages broadband search context and state per user.
    Tracks parameters, results, and conversation flow for optimized interactions.
    """
    
    def __init__(self):
        self.user_contexts: Dict[str, Dict[str, Any]] = {}
        self.context_timeout = timedelta(hours=24)  # Context expires after 24 hours
    
    def get_or_create_context(self, user_id: str) -> Dict[str, Any]:
        """Get or create broadband context for user."""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                "last_parameters": {},
                "confirmed_postcode": None,
                "scraped_data": None,
                "recommendations": None,
                "search_history": [],
                "preferences": {},
                "last_updated": datetime.now(),
                "query_count": 0
            }
        else:
            # Check if context has expired
            context = self.user_contexts[user_id]
            if datetime.now() - context["last_updated"] > self.context_timeout:
                logger.info(f"🔄 Broadband context expired for user {user_id}, resetting")
                self.user_contexts[user_id] = {
                    "last_parameters": {},
                    "confirmed_postcode": context.get("confirmed_postcode"),  # Keep postcode
                    "scraped_data": None,
                    "recommendations": None,
                    "search_history": [],
                    "preferences": context.get("preferences", {}),  # Keep preferences
                    "last_updated": datetime.now(),
                    "query_count": 0
                }
        
        return self.user_contexts[user_id]
    
    def update_parameters(self, user_id: str, parameters: Dict[str, Any]):
        """Update last known parameters for user."""
        context = self.get_or_create_context(user_id)
        context["last_parameters"] = parameters
        context["last_updated"] = datetime.now()
        logger.info(f"📝 Updated broadband parameters for user {user_id}")
    
    def update_postcode(self, user_id: str, postcode: str):
        """Update confirmed postcode for user."""
        context = self.get_or_create_context(user_id)
        context["confirmed_postcode"] = postcode
        context["last_updated"] = datetime.now()
        logger.info(f"📍 Updated confirmed postcode for user {user_id}: {postcode}")
    
    def get_last_parameters(self, user_id: str) -> Dict[str, Any]:
        """Get last known parameters for user."""
        context = self.get_or_create_context(user_id)
        return context.get("last_parameters", {})
    
    def get_confirmed_postcode(self, user_id: str) -> Optional[str]:
        """Get confirmed postcode for user."""
        context = self.get_or_create_context(user_id)
        return context.get("confirmed_postcode")
    
    def add_search_to_history(self, user_id: str, query: str, parameters: Dict[str, Any]):
        """Add search to history."""
        context = self.get_or_create_context(user_id)
        context["search_history"].append({
            "query": query,
            "parameters": parameters,
            "timestamp": datetime.now().isoformat()
        })
        context["query_count"] += 1
        # Keep only last 10 searches
        if len(context["search_history"]) > 10:
            context["search_history"] = context["search_history"][-10:]
    
    def clear_context(self, user_id: str):
        """Clear broadband context for user."""
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]
            logger.info(f"🗑️ Cleared broadband context for user {user_id}")


class BroadbandCacheManager:
    """
    Smart caching layer for broadband results, parameters, and scraped data.
    Reduces redundant API calls and improves response times.
    """
    
    def __init__(self, max_size: int = 100, ttl_minutes: int = 30):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _generate_cache_key(self, key_type: str, *args) -> str:
        """Generate cache key from arguments."""
        return f"{key_type}::{':'.join(str(arg) for arg in args)}"
    
    def _is_expired(self, timestamp: datetime) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() - timestamp > self.ttl
    
    def get(self, key_type: str, *args) -> Optional[Any]:
        """Get value from cache."""
        key = self._generate_cache_key(key_type, *args)
        if key in self.cache:
            value, timestamp = self.cache[key]
            if not self._is_expired(timestamp):
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                logger.info(f"🎯 Cache hit for {key_type}")
                return value
            else:
                # Expired, remove it
                del self.cache[key]
                logger.info(f"⏰ Cache expired for {key_type}")
        return None
    
    def set(self, key_type: str, value: Any, *args):
        """Set value in cache."""
        key = self._generate_cache_key(key_type, *args)
        self.cache[key] = (value, datetime.now())
        
        # Enforce max size (LRU eviction)
        if len(self.cache) > self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.info(f"🗑️ Evicted oldest cache entry: {oldest_key}")
        
        logger.info(f"💾 Cached {key_type} (cache size: {len(self.cache)})")
    
    def invalidate(self, key_type: str, *args):
        """Invalidate specific cache entry."""
        key = self._generate_cache_key(key_type, *args)
        if key in self.cache:
            del self.cache[key]
            logger.info(f"🗑️ Invalidated cache for {key_type}")
    
    def clear(self):
        """Clear all cache."""
        self.cache.clear()
        logger.info("🗑️ Cleared all cache")


class BroadbandQueryOptimizer:
    """
    Intelligent query pre-processor for broadband queries.
    Detects broadband intent, extracts parameters, and optimizes tool calls.
    """
    
    def __init__(self, context_manager: BroadbandContextManager):
        self.context_manager = context_manager
        
        # Broadband query detection patterns
        self.broadband_keywords = [
            'broadband', 'internet', 'fibre', 'fiber', 'wifi', 'connection',
            'speed', 'mbps', 'mb', 'provider', 'isp', 'deal', 'package',
            'bt', 'sky', 'virgin', 'talktalk', 'plusnet', 'vodafone',
            'postcode', 'contract', 'monthly cost'
        ]
    
    def is_broadband_query(self, query: str) -> bool:
        """Detect if query is related to broadband."""
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.broadband_keywords)
    
    def detect_intent(self, query: str) -> str:
        """Detect primary intent of broadband query."""
        query_lower = query.lower()
        
        # Intent detection patterns
        if any(word in query_lower for word in ['cheapest', 'lowest cost', 'affordable']):
            return "get_cheapest"
        elif any(word in query_lower for word in ['fastest', 'highest speed', 'quickest']):
            return "get_fastest"
        elif any(word in query_lower for word in ['compare', 'comparison', 'versus', 'vs']):
            return "compare_providers"
        elif any(word in query_lower for word in ['recommend', 'suggest', 'best', 'top']):
            return "get_recommendations"
        elif any(word in query_lower for word in ['filter', 'refine', 'change', 'modify']):
            return "refine_search"
        elif any(word in query_lower for word in ['list', 'show all', 'available providers']):
            return "list_providers"
        else:
            return "query"
    
    def optimize_parameters(self, user_id: str, new_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize parameters by merging with previous context.
        Auto-fills missing parameters from user's history.
        """
        # Get last known parameters
        last_params = self.context_manager.get_last_parameters(user_id)
        confirmed_postcode = self.context_manager.get_confirmed_postcode(user_id)
        
        # Merge parameters (new params override old)
        optimized = {**last_params, **new_params}
        
        # Auto-fill postcode if confirmed
        if not optimized.get('postcode') and confirmed_postcode:
            optimized['postcode'] = confirmed_postcode
            logger.info(f"✨ Auto-filled postcode from context: {confirmed_postcode}")
        
        return optimized
    
    def suggest_next_action(self, user_id: str, current_intent: str) -> Optional[str]:
        """Suggest next logical action based on context."""
        context = self.context_manager.get_or_create_context(user_id)
        
        # If no postcode confirmed yet, suggest postcode input
        if not context.get("confirmed_postcode"):
            return "Please provide your postcode to find broadband deals in your area."
        
        # If parameters set but no results yet, suggest search
        if context.get("last_parameters") and not context.get("scraped_data"):
            return "Would you like me to search for broadband deals with these parameters?"
        
        # If results available but no recommendations, suggest recommendations
        if context.get("scraped_data") and not context.get("recommendations"):
            return "Would you like me to analyze these deals and provide personalized recommendations?"
        
        return None


# ============================================================================
# WEBSOCKET CALLBACK HANDLER
# ============================================================================

class WebSocketCallbackHandler:
    """Callback handler to send tool execution results to WebSocket."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    async def send_tool_result(self, result: str):
        """Send tool execution result to WebSocket."""
        registry = get_registry()
        await registry.send_to_user_tool_websocket(
            self.user_id,
            {
                "type": "tool_execution_result",
                "action": "completed",
                "data": {
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )


if LANGCHAIN_AVAILABLE:
    def create_page_tool_function(
        function_name: str,
        page_name: str,
        user_id: str,
        agent_manager: Any,
        callback_handler: Any
    ):
        """
        Create an async function for a page-specific tool that routes through AgentManager.
        
        Args:
            function_name: Name of the function (e.g., "tables_action")
            page_name: Page name (e.g., "tables")
            user_id: User ID for session management
            agent_manager: AgentManager instance
            callback_handler: WebSocket callback handler
            
        Returns:
            Async function that executes the tool
        """
        async def tool_function(**kwargs) -> str:
            """Execute page-specific tool action via AgentManager."""
            try:
                logger.info(f"🔧 LangChain Tool - Tool: {function_name}, Page: {page_name}, User: {user_id}")
                logger.info(f"🔧 Tool call arguments: {kwargs}")
                
                # Create mock function call for agent manager
                class MockFunctionCall:
                    def __init__(self, name, arguments):
                        self.name = name
                        self.arguments = arguments
                
                # Ensure user_id is in arguments
                arguments = {"user_id": user_id, **kwargs}
                
                # Create mock function call
                mock_call = MockFunctionCall(function_name, arguments)
                
                # Execute through agent manager
                result = await agent_manager.handle_function_call(mock_call)
                
                # NOTE: Tools send their own detailed WebSocket messages via send_websocket_message()
                # in base_tool.py. We don't send a duplicate wrapped version here.
                
                logger.info(f"✅ LangChain tool executed successfully: {function_name}")
                return result

            except Exception as e:
                logger.error(f"❌ Tool error for {function_name}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                error_msg = f"Error executing {function_name}: {str(e)}"
                
                # NOTE: Tools handle their own error WebSocket messages via _handle_error()
                # in base_tool.py. We don't send a duplicate here.
                
                return error_msg
        
        return tool_function

else:
    # Mock tool when LangChain is not available
    class PageSpecificToolAdapter:
        """Mock tool adapter when LangChain is not available."""
        
        def __init__(self, page_name: str, tool_schema: Any, user_id: str, callback_handler=None, agent_manager=None):
            self.name = f"{page_name}_action"
            self.description = f"Mock tool for {page_name} page"
            self.page_name = page_name
            self.user_id = user_id
            self.callback_handler = callback_handler
            self.agent_manager = agent_manager

        async def _arun(self, **kwargs) -> str:
            """Mock async implementation."""
            logger.info(f"🤖 Mock {self.page_name} action: {kwargs}")
            return f"Mock {self.page_name} action completed"

        def _run(self, **kwargs) -> str:
            """Mock sync implementation."""
            return f"Mock {self.page_name} action completed"


def create_langchain_tools_from_agent_manager(user_id: str, callback_handler=None, current_page: str = "broadband"):
    """
    Factory function to create LangChain tools from the modular tool structure.
    Creates page-specific StructuredTools that expose all action types and parameters.
    
    Args:
        user_id: User ID for session management
        callback_handler: Optional WebSocket callback handler
        current_page: Current page context for the agent
        
    Returns:
        List of LangChain StructuredTools that wrap each page-specific tool
    """
    if not LANGCHAIN_AVAILABLE:
        logger.warning("⚠️ LangChain not available, returning empty tool list")
        return []
    
    try:
        # Create agent manager with current page context
        agent_manager = create_agent_manager(current_page=current_page)
        
        # Get all tool definitions from agent manager
        tool_definitions = agent_manager.get_tool_definitions()
        
        if not tool_definitions:
            logger.error("❌ No tool definitions found in agent manager")
            return []
        
        # Create page-specific StructuredTools for each tool
        langchain_tools = []
        seen_tool_names = set()  # Track tool names to avoid duplicates
        
        for tool_def in tool_definitions:
            try:
                # Skip duplicate tool names (e.g., database_query_action from both database-query and database-query-results)
                if tool_def.name in seen_tool_names:
                    logger.info(f"⚠️ Skipping duplicate tool: {tool_def.name}")
                    continue
                seen_tool_names.add(tool_def.name)
                
                # Extract page name from tool definition name (e.g., "users_action" -> "users")
                page_name = tool_def.name.replace("_action", "")
                
                # Create tool function
                tool_func = create_page_tool_function(
                    function_name=tool_def.name,
                    page_name=page_name,
                    user_id=user_id,
                    agent_manager=agent_manager,
                    callback_handler=callback_handler
                )
                
                # Convert Pipecat schema properties to LangChain args_schema
                # Create a dynamic Pydantic model for the tool arguments
                fields = {}
                for prop_name, prop_info in tool_def.properties.items():
                    # Skip user_id as we inject it automatically
                    if prop_name == "user_id":
                        continue
                    
                    # Check for enum constraint first
                    enum_values = prop_info.get("enum")
                    
                    if enum_values and len(enum_values) > 0:
                        # Create Literal type for enum (unpack the list into Literal args)
                        # Literal expects literal arguments, not a tuple
                        try:
                            # Create Literal dynamically using __class_getitem__
                            field_type = Literal.__class_getitem__(tuple(enum_values))
                        except:
                            # Fallback to str if Literal creation fails
                            field_type = str
                        field_description = prop_info.get("description", "")
                        # Add enum values to description for clarity
                        field_description += f" Valid values: {', '.join(map(str, enum_values))}"
                    else:
                        # Determine field type normally
                        prop_type = prop_info.get("type", "string")
                        field_type = str  # Default to string
                        field_description = prop_info.get("description", "")
                        
                        if prop_type == "integer":
                            field_type = int
                        elif prop_type == "number":
                            field_type = float
                        elif prop_type == "boolean":
                            field_type = bool
                        elif prop_type == "object":
                            field_type = dict
                        elif prop_type == "array":
                            # Handle array types properly with items specification
                            items_info = prop_info.get("items", {})
                            items_type = items_info.get("type", "string")
                            
                            if items_type == "string":
                                field_type = List[str]
                            elif items_type == "integer":
                                field_type = List[int]
                            elif items_type == "number":
                                field_type = List[float]
                            elif items_type == "boolean":
                                field_type = List[bool]
                            elif items_type == "object":
                                field_type = List[dict]
                            else:
                                field_type = list  # Fallback to untyped list
                    
                    # Create field with optional annotation
                    is_required = prop_name in tool_def.required if hasattr(tool_def, 'required') and tool_def.required else False
                    
                    if is_required:
                        fields[prop_name] = (field_type, Field(..., description=field_description))
                    else:
                        fields[prop_name] = (Optional[field_type], Field(None, description=field_description))
                
                # Create dynamic Pydantic model for args with JSON parsing for dict fields
                class BaseArgsModel(BaseModel):
                    """Base model with JSON parsing for dict fields."""

                    @field_validator('*', mode='before')
                    @classmethod
                    def parse_json_fields(cls, v, info):
                        """Parse JSON strings for dict fields."""
                        if info.field_name in cls.__annotations__ and cls.__annotations__[info.field_name] == dict:
                            if isinstance(v, str):
                                try:
                                    import json
                                    return json.loads(v)
                                except (json.JSONDecodeError, ValueError):
                                    raise ValueError(f"Invalid JSON string for {info.field_name}: {v}")
                        return v

                # Create the dynamic model class inheriting from BaseArgsModel
                ArgsSchema = create_model(
                    f"{tool_def.name}_args",
                    **fields,
                    __base__=BaseArgsModel
                )
                
                # Create StructuredTool
                # Use a closure to capture tool_func correctly
                def create_sync_wrapper(async_func):
                    def sync_func(**kwargs):
                        return asyncio.run(async_func(**kwargs))
                    return sync_func
                
                structured_tool = StructuredTool(
                    name=tool_def.name,
                    description=tool_def.description,
                    func=create_sync_wrapper(tool_func),  # Sync wrapper with proper closure
                    coroutine=tool_func,  # Async function
                    args_schema=ArgsSchema
                )
                
                langchain_tools.append(structured_tool)
                logger.info(f"✅ Created StructuredTool for {tool_def.name} ({page_name} page) with {len(fields)} parameters")
                
            except Exception as e:
                logger.error(f"❌ Error creating adapter for {tool_def.name}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                continue
        
        logger.info(f"✅ Created {len(langchain_tools)} LangChain tool adapters for user {user_id}")
        logger.info(f"🔧 Available tools: {[t.name for t in langchain_tools]}")
        
        return langchain_tools
        
    except Exception as e:
        logger.error(f"❌ Error creating LangChain tools: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


class LangChainTextAgent:
    """
    Enhanced LangChain-based conversational AI agent with broadband optimization.
    
    OPTIMIZATIONS:
    - Intelligent query pre-processing for broadband queries
    - Smart caching for parameters and results  
    - Context-aware parameter auto-filling
    - Progress tracking for long operations
    - Enhanced error recovery
    """

    def __init__(self, user_id: str, current_page: str = "broadband"):
        self.user_id = user_id
        self.current_page = current_page
        self.llm = None
        self.agent_executor = None
        self.memory = None
        self.callback_handler = WebSocketCallbackHandler(user_id)
        self.initialized = False
        self.settings = get_settings()
        self.agent_manager = None  # Will be created during initialization
        self.langfuse_tracer = get_langfuse_tracer()
        self.langchain_callback_handler = None
        self.current_trace = None
        
        # Broadband optimization components
        self.broadband_context = BroadbandContextManager()
        self.broadband_cache = BroadbandCacheManager(max_size=100, ttl_minutes=30)
        self.broadband_optimizer = BroadbandQueryOptimizer(self.broadband_context)

    async def initialize(self):
        """Initialize the LangChain agent with tools and memory."""
        try:
            if not LANGCHAIN_AVAILABLE:
                raise ImportError("LangChain libraries are not available")

            # Initialize Google Gemini LLM
            if not self.settings.google_api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment variables")

            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=self.settings.google_api_key,
                temperature=self.settings.temperature,
                max_output_tokens=self.settings.max_output_tokens,
            )

            # Initialize memory
            self.memory = ConversationBufferWindowMemory(
                memory_key="chat_history",
                return_messages=True,
                k=self.settings.conversation_memory_size
            )

            # Create agent manager for tool routing
            self.agent_manager = create_agent_manager(current_page=self.current_page)

            # Note: Disabled LangChain callback handler to prevent duplicate traces
            # We use manual trace logging instead for better control and unified tracing
            self.langchain_callback_handler = None
            logger.info("🔧 Using manual trace logging for unified conversation tracing")

            # Create tools using the modular tool adapter
            tools = create_langchain_tools_from_agent_manager(
                user_id=self.user_id,
                callback_handler=self.callback_handler,
                current_page=self.current_page
            )
            
            if not tools:
                logger.warning("⚠️ No tools created, using fallback")
                raise ValueError("Failed to create tools from agent manager")
            
            logger.info(f"✅ Created {len(tools)} LangChain tools from modular structure")

            # Get system instruction with page context
            system_instruction = self.agent_manager.get_system_instruction_with_page_context(self.user_id)
            
            # Add tool-specific guidance
            tool_guidance = self._generate_tool_guidance(tools, self.current_page)
            system_instruction += f"\n\n{tool_guidance}"

            # Create prompt template with page-aware system instruction
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=system_instruction),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])

            # Create the agent
            agent = create_tool_calling_agent(
                llm=self.llm,
                tools=tools,
                prompt=prompt
            )

            # Create agent executor (using manual trace logging instead of LangChain callbacks)
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                memory=self.memory,
                verbose=True,
                return_intermediate_steps=True,
                handle_parsing_errors=True,
                max_iterations=5  # Increased for more complex tool interactions
            )

            self.initialized = True
            logger.info(f"✅ LangChain TextAgent initialized for user {self.user_id} on page {self.current_page}")
            logger.info(f"🔧 Available pages via AgentManager: {self.agent_manager.get_available_pages()}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize LangChain TextAgent for user {self.user_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def process_message(self, message: str) -> str:
        """
        Process a text message using the LangChain agent.
        ENHANCED with broadband-specific optimizations and intelligent pre-processing.
        """
        start_time = time.time()

        # Get unified conversation session
        conversation_manager = get_conversation_manager()
        conversation_session = conversation_manager.get_or_create_session(
            user_id=self.user_id,
            conversation_type="text",
            current_page=self.current_page
        )

        # Update activity and message count
        conversation_manager.update_session_activity(self.user_id, conversation_type="text")
        conversation_manager.increment_message_count(self.user_id)

        conversation_session_id = conversation_session.session_id
        trace = conversation_session.trace  # Use the actual trace object
        
        # Extract trace_id string from trace object for scoring
        # The trace is a LangfuseSpan object, we need its id as string
        trace_id = trace.id if trace and hasattr(trace, 'id') else None

        logger.info(f"📝 Using unified conversation session {conversation_session_id} for text (user: {self.user_id})")

        try:
            if not self.initialized:
                await self.initialize()

            logger.info(f"📝 Processing message for user {self.user_id}: {message[:100]}...")
            
            # ============================================================
            # BROADBAND QUERY OPTIMIZATION - Pre-Processing
            # ============================================================
            
            is_broadband_query = False
            broadband_intent = None
            optimized_message = message
            
            # Detect if this is a broadband query
            if self.current_page == "broadband" or self.broadband_optimizer.is_broadband_query(message):
                is_broadband_query = True
                broadband_intent = self.broadband_optimizer.detect_intent(message)
                
                logger.info(f"🌐 Detected broadband query - Intent: {broadband_intent}")
                
                # Check cache for similar queries
                cached_response = self.broadband_cache.get("response", self.user_id, message.lower().strip())
                if cached_response and broadband_intent == "query":
                    logger.info(f"🎯 Found cached response for broadband query")
                    return cached_response
                
                # Get broadband context
                bb_context = self.broadband_context.get_or_create_context(self.user_id)
                
                # Add context hint to message for better LLM understanding
                if bb_context.get("confirmed_postcode"):
                    postcode = bb_context["confirmed_postcode"]
                    logger.info(f"📍 Auto-filling context: postcode={postcode}")
                    
                    # Don't modify the message, let the tool handle context internally
                    # The tool will auto-fill from its own conversation state
                
                # Log broadband query activity
                conversation_manager.log_activity_to_trace(
                    user_id=self.user_id,
                    activity_type="broadband_query_detected",
                    data={
                        "query": message,
                        "intent": broadband_intent,
                        "has_cached_postcode": bb_context.get("confirmed_postcode") is not None,
                        "query_count": bb_context.get("query_count", 0) + 1,
                        "session_id": conversation_session_id
                    }
                )

            # Log message activity to unified trace
            conversation_manager.log_activity_to_trace(
                user_id=self.user_id,
                activity_type="text_message",
                data={
                    "message": message,
                    "message_length": len(message),
                    "is_broadband_query": is_broadband_query,
                    "broadband_intent": broadband_intent,
                    "session_id": conversation_session_id
                }
            )

            # Process the message through the agent (using manual trace logging)
            result = await self.agent_executor.ainvoke(
                {"input": message},
                config=RunnableConfig(
                    tags=[f"user_{self.user_id}"],
                    metadata={"langfuse_user_id": self.user_id}
                )
            )

            response_text = result["output"]
            intermediate_steps = result.get("intermediate_steps", [])
            
            # ============================================================
            # BROADBAND RESULT POST-PROCESSING
            # ============================================================
            
            # Track if broadband tool was used
            used_broadband_tool = False
            broadband_tool_action = None
            
            # Check if broadband tool was called in intermediate steps
            for step in intermediate_steps:
                tool_action = step[0] if len(step) > 0 else None
                if tool_action and hasattr(tool_action, 'tool'):
                    tool_name = tool_action.tool
                    if 'broadband' in tool_name.lower():
                        used_broadband_tool = True
                        if hasattr(tool_action, 'tool_input'):
                            broadband_tool_action = tool_action.tool_input.get('action_type')
                        break
            
            # If broadband query was processed, update context and cache
            if is_broadband_query and used_broadband_tool:
                logger.info(f"🌐 Broadband tool was used - updating context and cache")
                
                # Cache the response for similar future queries
                if broadband_intent == "query" and response_text:
                    self.broadband_cache.set("response", response_text, self.user_id, message.lower().strip())
                    logger.info(f"💾 Cached broadband response")
                
                # Update broadband context based on tool action
                bb_context = self.broadband_context.get_or_create_context(self.user_id)
                
                # Extract postcode from response if present (for context tracking)
                # Look for patterns like "postcode: E14 9WB" or "E14 9WB" in response
                import re
                postcode_pattern = r'\b([A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2})\b'
                postcode_matches = re.findall(postcode_pattern, response_text, re.IGNORECASE)
                if postcode_matches:
                    # Update confirmed postcode in context
                    confirmed_postcode = postcode_matches[0].strip().upper()
                    self.broadband_context.update_postcode(self.user_id, confirmed_postcode)
                
                # Log broadband result
                conversation_manager.log_activity_to_trace(
                    user_id=self.user_id,
                    activity_type="broadband_result",
                    data={
                        "intent": broadband_intent,
                        "tool_action": broadband_tool_action,
                        "response_length": len(response_text),
                        "used_cache": False,  # This was a fresh result
                        "session_id": conversation_session_id
                    }
                )

            # Log tool usage and API calls with detailed information
            if intermediate_steps:
                logger.info(f"🔧 Agent used {len(intermediate_steps)} tools")
                for i, step in enumerate(intermediate_steps):
                    # Log each tool call with comprehensive details
                    tool_action = step[0] if len(step) > 0 else None
                    tool_result = step[1] if len(step) > 1 else ""

                    tool_name = "unknown_tool"
                    tool_input = {}

                    if tool_action and hasattr(tool_action, 'tool'):
                        tool_name = tool_action.tool
                    if tool_action and hasattr(tool_action, 'tool_input'):
                        tool_input = tool_action.tool_input

                    # Log detailed tool call activity
                    conversation_manager.log_activity_to_trace(
                        user_id=self.user_id,
                        activity_type="text_tool_call",
                        data={
                            "step_number": i + 1,
                            "total_steps": len(intermediate_steps),
                            "tool_name": tool_name,
                            "tool_input": tool_input,
                            "tool_output": str(tool_result)[:1000],  # Truncate long results
                            "tool_output_type": type(tool_result).__name__,
                            "session_id": conversation_session_id,
                            "success": True
                        }
                    )

                    # Also log to the legacy API call system for compatibility
                    log_api_call(
                        tool_name=tool_name,
                        action="execute",
                        parameters=tool_input,
                        result=tool_result,
                        duration=0.0,
                        success=True,
                        trace_id=trace_id,  # Use string trace_id, not span object
                        user_id=self.user_id,
                        session_id=conversation_session_id
                    )

            # Log final response metrics
            end_time = time.time()
            duration = end_time - start_time

            # Log response activity to unified trace
            conversation_manager.log_activity_to_trace(
                user_id=self.user_id,
                activity_type="text_response",
                data={
                    "response": response_text,
                    "response_length": len(response_text),
                    "duration_seconds": duration,
                    "tool_calls_count": len(intermediate_steps),
                    "session_id": conversation_session_id
                }
            )

            # Calculate comprehensive quality score
            quality_score = calculate_response_quality_score(
                response_text=response_text,
                duration_seconds=duration,
                tool_calls_count=len(intermediate_steps),
                success=True
            )

            # Score the trace with quality metrics using unified trace ID
            if trace_id:
                self.langfuse_tracer.score_trace(
                    trace_id=trace_id,  # Use string trace_id, not span object
                    name="response_quality",
                    value=quality_score,
                    data_type="NUMERIC",
                    comment=f"Response length: {len(response_text)}, Tools used: {len(intermediate_steps)}, Duration: {duration:.2f}s, Quality score: {quality_score:.3f}"
                )

                # Add conversation-level insights and scoring
                memory_messages = await self.get_memory()
                if memory_messages:
                    conversation_insights = extract_conversation_insights(memory_messages, trace_id)  # Use string trace_id
                    if conversation_insights.get("conversation_score"):
                        score_conversation_quality(
                            trace_id=trace_id,  # Use string trace_id, not span object
                            quality_score=conversation_insights["conversation_score"],
                            feedback=f"Conversation insights: {conversation_insights['insights']}",
                            metadata=conversation_insights["insights"]
                        )

            # NOTE: Only tool responses are sent via WebSocket, NOT the final LLM response
            # Tools send their own detailed structured messages directly via send_websocket_message()
            # in base_tool.py. The final LLM response is only returned, not sent to WebSocket.

            logger.info(f"✅ Message processed for user {self.user_id}, returning response (not sent to WebSocket)")
            return response_text

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time

            logger.error(f"❌ Error processing message for user {self.user_id}: {e}")

            # Log error activity to unified trace
            conversation_manager.log_activity_to_trace(
                user_id=self.user_id,
                activity_type="text_error",
                data={
                    "error": str(e),
                    "duration_seconds": duration,
                    "message": message[:200],
                    "session_id": conversation_session_id
                }
            )

            if trace_id:
                self.langfuse_tracer.score_trace(
                    trace_id=trace_id,  # Use string trace_id, not span object
                    name="error_score",
                    value=1,
                    data_type="BINARY",
                    comment=f"Error: {str(e)}"
                )

            error_msg = f"I apologize, but I encountered an error processing your message: {str(e)}"

            # Send error to WebSocket
            registry = get_registry()
            await registry.send_to_user_tool_websocket(
                self.user_id,
                {
                    "type": "langchain_agent_error",
                    "action": "error_occurred",
                    "data": {
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                }
            )

            return error_msg

    async def get_memory(self) -> List[Dict[str, Any]]:
        """Get the current conversation memory."""
        try:
            if not self.memory:
                return []

            messages = self.memory.chat_memory.messages
            memory_list = []
            
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    memory_list.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    memory_list.append({"role": "assistant", "content": msg.content})

            return memory_list

        except Exception as e:
            logger.error(f"❌ Error getting memory for user {self.user_id}: {e}")
            return []

    async def clear_memory(self, clear_broadband_context: bool = False) -> bool:
        """
        Clear the conversation memory.
        ENHANCED to optionally clear broadband-specific context.
        
        Args:
            clear_broadband_context: If True, also clear broadband context and cache
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.memory:
                self.memory.clear()
            
            # Optionally clear broadband-specific data
            if clear_broadband_context:
                self.broadband_context.clear_context(self.user_id)
                self.broadband_cache.clear()
                logger.info(f"🧹 Cleared conversation memory AND broadband context for user {self.user_id}")
            else:
                logger.info(f"🧹 Cleared conversation memory for user {self.user_id}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Error clearing memory for user {self.user_id}: {e}")
            return False
    
    def get_broadband_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get broadband context for a specific user.
        Useful for debugging and monitoring user's broadband search journey.
        
        Args:
            user_id: User ID to get context for
            
        Returns:
            Dictionary containing broadband context
        """
        return self.broadband_context.get_or_create_context(user_id)
    
    def get_broadband_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get broadband interaction statistics for a user.
        
        Args:
            user_id: User ID to get statistics for
            
        Returns:
            Dictionary containing statistics
        """
        context = self.broadband_context.get_or_create_context(user_id)
        return {
            "query_count": context.get("query_count", 0),
            "has_confirmed_postcode": context.get("confirmed_postcode") is not None,
            "confirmed_postcode": context.get("confirmed_postcode"),
            "search_history_count": len(context.get("search_history", [])),
            "has_parameters": bool(context.get("last_parameters")),
            "last_updated": context.get("last_updated"),
            "cache_size": len(self.broadband_cache.cache)
        }
    
    def _generate_tool_guidance(self, tools: List[Any], current_page: str) -> str:
        """
        Generate guidance for the LLM on which tools to use based on current page.
        ENHANCED with broadband-specific guidance and examples.
        
        Args:
            tools: List of available LangChain tools
            current_page: Current page name
            
        Returns:
            Formatted guidance string
        """
        guidance = f"""
## 🔧 AVAILABLE TOOLS FOR CURRENT PAGE ({current_page}):

You have access to {len(tools)} specialized tools for broadband comparison.

### Tool Selection Rules:
1. **For broadband operations**: Use `broadband_action` tool with appropriate action_type
2. **Check the tool description** to see what actions are available

### Available Tools:
"""
        for tool in tools:
            tool_name = tool.name
            tool_desc = tool.description
            guidance += f"\n- **{tool_name}**: {tool_desc[:200]}..."
        
        guidance += f"""

### Current Page Guidance:
- You are currently on the **{current_page}** page
- Use the **broadband_action** tool for all broadband comparison operations
- Available actions include: query, generate_url, get_recommendations, compare_providers, get_cheapest, get_fastest, list_providers, open_url

### Important:
- Each tool has specific action_type enums - only use valid action types
- Read the tool descriptions carefully to understand what actions are supported
- If unsure, check the tool's description for the list of valid action types
"""
        
        # Add broadband-specific guidance if on broadband page
        if current_page == "broadband":
            guidance += """

## 🌐 BROADBAND TOOL - SPECIAL GUIDANCE:

### CONVERSATIONAL MODE - Build Requirements Piece by Piece:
- **NEW**: Support for building broadband requirements incrementally
- User can provide postcode first, then speed, then contract, etc.
- **URLs auto-generate** when minimum parameters (postcode + speed) are available
- **No scraping or recommendations until explicitly requested**
- System remembers parameters across conversation turns

### Automatic Postcode Validation:
- Postcodes are AUTOMATICALLY validated with regex and matched against database using fuzzy search
- The system AUTO-SELECTS the best match (100% match or highest score)
- **NO USER CONFIRMATION NEEDED** - postcode selection happens in the background
- Simply pass the postcode in your query - the tool handles validation and matching

### Natural Language Processing:
- The broadband tool has advanced AI parameter extraction
- It understands queries like:
  - "Find broadband in E14 9WB with 100Mb speed and 12 month contract"
  - "Show me cheapest deals from BT and Sky"
  - "I want superfast fibre with unlimited calls"
  - "Compare Virgin Media and TalkTalk in Manchester"

### CONVERSATIONAL PARAMETER HANDLING:
- **action_type="query"** now supports BOTH natural language AND individual parameters
- If you get individual parameters (postcode, speed_in_mb, etc.), treat as parameter updates
- URLs will auto-generate when postcode + speed are available
- Example conversational flow:
  - User: "I need broadband in E14 9WB" → Tool updates postcode, no URL yet
  - User: "100Mb speed please" → Tool updates speed, auto-generates URL
  - User: "Change to 24 months" → Tool updates contract, regenerates URL

### Action Types Available:
1. **query** - Process natural language OR handle parameter updates
   - Natural language: user_id="123", action_type="query", query="Find 100Mb broadband in SW1A 1AA"
   - Parameter updates: user_id="123", action_type="query", postcode="E14 9WB", speed_in_mb="55Mb"
   - Automatically extracts and updates parameters incrementally
   - URLs auto-generate when sufficient parameters available

2. **generate_url** - Generate comparison URL with explicit parameters
   - Use when parameters are already known
   - Example: user_id="123", action_type="generate_url", postcode="E149WB", speed_in_mb="100Mb"

3. **get_recommendations** - Get AI-powered deal recommendations (only when requested)
   - Analyzes scraped data and provides personalized suggestions
   - Example: user_id="123", action_type="get_recommendations"

4. **compare_providers** - Compare specific providers
   - Example: user_id="123", action_type="compare_providers", providers="BT,Sky,Virgin Media"

5. **get_cheapest** - Find cheapest available deal
6. **get_fastest** - Find fastest available deal
7. **list_providers** - Show all available providers
8. **filter_data** - Apply filters to existing results
9. **refine_search** - Refine search parameters

### CONVERSATIONAL MEMORY:
- System maintains broadband parameters across conversation turns
- **Auto-fills** previously mentioned parameters
- **Auto-generates URLs** when minimum requirements met
- **Only scrapes/recommends** when explicitly asked

### Example Usage Patterns:

**CONVERSATIONAL FLOW (RECOMMENDED):**
```
User: "I need broadband in E14 9WB"
Tool Call: broadband_action(
  user_id="123",
  action_type="query",
  postcode="E14 9WB"
)
# Response: Parameters updated, waiting for more info

User: "100Mb speed with Hyperoptic"
Tool Call: broadband_action(
  user_id="123",
  action_type="query",
  speed_in_mb="100Mb",
  providers="Hyperoptic"
)
# Response: URL auto-generated with all parameters

User: "Actually, change that to 24 months"
Tool Call: broadband_action(
  user_id="123",
  action_type="query",
  contract_length="24 months"
)
# Response: URL updated with new contract length
```

**Natural Language Query (still supported):**
```
User: "Find broadband deals in E14 9WB with 100Mb speed"
Tool Call: broadband_action(
  user_id="123",
  action_type="query",
  query="Find broadband deals in E14 9WB with 100Mb speed"
)
```

**Explicit Actions (when intent is clear):**
```
User: "Show me recommendations"
Tool Call: broadband_action(
  user_id="123",
  action_type="get_recommendations"
)
# Uses current parameters from conversation state

User: "Compare BT and Virgin Media"
Tool Call: broadband_action(
  user_id="123",
  action_type="compare_providers",
  providers="BT,Virgin Media"
)
```

### Best Practices:
1. **CONVERSATIONAL FIRST**: Use individual parameters with action_type="query" to build requirements incrementally
2. **AUTO-GENERATION**: URLs generate automatically when postcode + speed are available - no need to explicitly request
3. **NATURAL FLOW**: Users can say "postcode first", then "speed", then "contract" - parameters accumulate naturally
4. **Don't ask for postcode confirmation** - System auto-selects best match
5. **Only scrape/recommend when asked** - URLs generate immediately, but data analysis only on request
6. **Use specific action types** (get_recommendations, compare_providers, etc.) when user explicitly asks for analysis
7. **Trust parameter accumulation** - System remembers and auto-fills previous parameters
"""
        
        return guidance


# Mock implementations for when LangChain is not available
class MockLangChainAgent:
    """Mock implementation when LangChain is not available."""

    def __init__(self, user_id: str, current_page: str = "broadband"):
        self.user_id = user_id
        self.current_page = current_page
        self.memory = []
        self.initialized = False

    async def initialize(self):
        """Mock initialization."""
        self.initialized = True
        logger.info(f"🔧 Mock LangChain agent initialized for user {self.user_id} on page {self.current_page}")

    async def process_message(self, message: str) -> str:
        """Mock message processing."""
        self.memory.append({"role": "user", "content": message})
        response = f"Mock LangChain response to: '{message}' (on {self.current_page} page)"
        self.memory.append({"role": "assistant", "content": response})
        return response

    async def get_memory(self) -> List[Dict[str, Any]]:
        return self.memory.copy()

    async def clear_memory(self) -> bool:
        self.memory = []
        return True


def create_text_agent(user_id: str, current_page: str = "broadband"):
    """
    Factory function to create the appropriate text agent.
    
    Args:
        user_id: User ID for session management
        current_page: Current page context (default: "broadband")
        
    Returns:
        LangChainTextAgent or MockLangChainAgent instance
    """
    if LANGCHAIN_AVAILABLE:
        return LangChainTextAgent(user_id, current_page)
    else:
        logger.warning("🔧 Using mock LangChain agent")
        return MockLangChainAgent(user_id, current_page)


# Example usage
async def main():
    """Example usage of the enhanced text agent."""
    try:
        agent = create_text_agent("test_user_123")
        await agent.initialize()

        # Test conversation
        response1 = await agent.process_message("Hello, how can you help me?")
        print(f"Response 1: {response1}")

        response2 = await agent.process_message("Find broadband deals in London")
        print(f"Response 2: {response2}")

        response3 = await agent.process_message("Search for all users created in the last month")
        print(f"Response 3: {response3}")

        # Get memory
        memory = await agent.get_memory()
        print(f"Memory contains {len(memory)} messages")

    except Exception as e:
        logger.error(f"❌ Example usage failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())