#!/usr/bin/env python3
"""
Voice Agent - Gemini-based conversational AI agent for voice interactions.
Handles voice pipeline setup, conversation management, and tool integration.
Extracted from router.py for better code organization.
"""

import os
import sys
import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

# Import Pipecat components
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.gemini_multimodal_live.gemini import GeminiMultimodalLiveLLMService
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

# Import websockets for error handling
import websockets

# Import internal modules
from ..config.settings import get_settings
from ..utils.validators import validate_page_name, validate_api_key
from ..utils.langfuse_tracing import get_langfuse_tracer, log_api_call, setup_tracing
from .agent_manager import create_agent_manager
from .conversation_manager import get_conversation_manager


class VoiceAgent:
    """
    Voice-based conversational AI agent using Gemini Multimodal Live.
    Manages voice pipeline, LLM service, and tool integration.
    """
    
    def __init__(self, user_id: str, session_id: str, current_page: str = "broadband"):
        """
        Initialize the voice agent.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            current_page: Current page context for the agent
        """
        self.user_id = user_id
        self.session_id = session_id
        self.current_page = current_page
        self.settings = get_settings()
        
        # Components (initialized later)
        self.llm_service = None
        self.agent_manager = None
        self.transport = None
        self.task = None
        self.pipeline = None
        self.runner = None
        
        # Conversation management
        self.conversation_manager = get_conversation_manager()
        self.conversation_session = None
        self.conversation_trace = None
        
        # Timing
        self.start_time = time.time()
        
        logger.info(f"🎤 Voice agent initialized - User: {user_id}, Session: {session_id}, Page: {current_page}")
    
    async def initialize(self, websocket):
        """
        Initialize the voice agent with all necessary components.
        
        Args:
            websocket: FastAPI WebSocket connection
        """
        # Normalize page name
        is_valid, normalized_page = validate_page_name(self.current_page)
        if is_valid:
            self.current_page = normalized_page
        else:
            logger.warning(f"⚠️ Invalid page name, using: {self.current_page}")
            self.current_page = self.current_page.lower().strip().replace(" ", "-").replace("_", "-")
        
        # Setup tracing
        if self.settings.langfuse_enabled:
            if self.settings.otel_exporter_otlp_endpoint:
                os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = self.settings.otel_exporter_otlp_endpoint
                logger.info(f"✅ Set OTLP environment variables for Pipecat")
            if self.settings.otel_exporter_otlp_headers:
                os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = self.settings.otel_exporter_otlp_headers
        
        try:
            setup_tracing(
                service_name=self.settings.otel_service_name,
                settings=self.settings
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize OpenTelemetry tracing: {e}")
        
        # Get unified conversation session
        self.conversation_session = self.conversation_manager.get_or_create_session(
            user_id=self.user_id,
            conversation_type="voice",
            current_page=self.current_page
        )
        
        self.conversation_trace = self.conversation_session.trace
        logger.info(f"🎤 Using unified conversation session {self.conversation_session.session_id}")
        
        # Create transport
        self.transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=self.settings.vad_stop_seconds)),
                serializer=ProtobufFrameSerializer(),
            ),
        )
        
        # Create LLM service and agent manager
        self.llm_service, self.agent_manager = await self._create_gemini_llm()
        
        # Create context for function calling
        system_prompt = self.agent_manager.get_system_instruction_with_page_context(self.user_id)
        context = OpenAILLMContext([{
            "role": "user",
            "content": system_prompt
        }])
        context_aggregator = self.llm_service.create_context_aggregator(context)
        
        # Log system initialization
        self.conversation_manager.log_activity_to_trace(
            user_id=self.user_id,
            activity_type="system_initialization",
            data={
                "system_prompt": system_prompt,
                "current_page": self.current_page,
                "session_id": self.conversation_session.session_id
            }
        )
        
        # Setup LLM event handlers
        self._setup_llm_event_handlers()
        
        # Create processors
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
        transcript = TranscriptProcessor()
        
        # Setup transcript event handlers
        self._setup_transcript_event_handlers(transcript)
        
        # Store agent manager reference for transcript updates
        self.agent_manager.conversation_trace = self.conversation_trace
        self.agent_manager.conversation_session_id = self.conversation_session.session_id
        
        # Build pipeline
        self.pipeline = Pipeline([
            self.transport.input(),
            context_aggregator.user(),
            rtvi,
            self.llm_service,
            transcript.user(),
            self.transport.output(),
            transcript.assistant(),
            context_aggregator.assistant(),
        ])
        
        logger.info(f"🔧 Pipeline created successfully")
        
        # Create task with tracing
        self.task = PipelineTask(
            self.pipeline,
            params=PipelineParams(
                enable_metrics=self.settings.enable_metrics,
                enable_usage_metrics=self.settings.enable_usage_metrics,
            ),
            enable_tracing=True,
            observers=[RTVIObserver(rtvi)],
        )
        
        self.agent_manager.task = self.task
        
        # Register function handlers
        self._register_function_handlers()
        
        # Setup transport event handlers
        self._setup_transport_event_handlers(rtvi)
        
        # Create pipeline runner
        self.runner = PipelineRunner(handle_sigint=False)
        
        logger.info(f"✅ Voice agent fully initialized")
    
    async def _create_gemini_llm(self):
        """Create Gemini Live LLM service with function calling."""
        if not validate_api_key(self.settings.google_api_key)[0]:
            raise ValueError("Invalid or missing GOOGLE_API_KEY")
        
        logger.info("🚀 Creating Gemini Multimodal Live service")
        
        # Create agent manager and get tools
        agent_manager = create_agent_manager(current_page=self.current_page)
        tool_definitions = agent_manager.get_tool_definitions()
        
        for tool_def in tool_definitions:
            logger.info(f"🔧 Tool registered: {tool_def.name}")
        
        tools_schema = ToolsSchema(standard_tools=tool_definitions)
        logger.info(f"🔧 Function calling enabled with {len(tool_definitions)} tools")
        
        # Get system instruction
        system_instruction = agent_manager.get_system_instruction_with_page_context()
        
        # Create Gemini service with retry logic
        async def _create_service():
            try:
                llm_service = GeminiMultimodalLiveLLMService(
                    api_key=self.settings.google_api_key,
                    system_instruction=system_instruction,
                    voice_id=self.settings.gemini_voice_id,
                    model=self.settings.gemini_model,
                    transcribe_model_audio=True,
                    temperature=self.settings.temperature,
                    tools=tools_schema,
                )
                return llm_service
            except Exception as e:
                logger.error(f"❌ Failed to create Gemini service: {e}")
                if isinstance(e, (websockets.exceptions.ConnectionClosedError, websockets.exceptions.WebSocketException)):
                    logger.info("🔄 WebSocket connection error detected, will retry...")
                elif "deadline expired" in str(e).lower():
                    logger.warning("⏰ Gemini service deadline expired, will retry with backoff...")
                raise e
        
        # Retry logic
        max_retries = self.settings.max_gemini_retries
        for attempt in range(max_retries + 1):
            try:
                llm_service = await _create_service()
                return llm_service, agent_manager
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"❌ All {max_retries + 1} attempts failed")
                    raise
                
                delay = min(2.0 * (2 ** attempt), 10.0)
                logger.warning(f"⚠️ Attempt {attempt + 1}/{max_retries + 1} failed, retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
        
        raise Exception("Failed to create Gemini service after retries")
    
    def _setup_llm_event_handlers(self):
        """Setup event handlers for LLM responses and function calls."""
        
        @self.llm_service.event_handler("on_llm_response")
        async def on_llm_response(response):
            """Capture LLM responses for transcript logging."""
            llm_start_time = time.time()
            
            try:
                logger.info(f"🤖 LLM Response received")
                
                transcript_text = None
                response_text = None
                
                # Check for transcript in response metadata
                if hasattr(response, 'metadata') and response.metadata:
                    if 'transcript' in response.metadata:
                        transcript_text = response.metadata['transcript']
                
                # Check for content
                if hasattr(response, 'content'):
                    response_text = response.content[:200] + "..." if len(response.content) > 200 else response.content
                    logger.info(f"📝 LLM Response content: {response_text}")
                
                llm_end_time = time.time()
                llm_duration = llm_end_time - llm_start_time
                
                # Log to Langfuse
                if self.conversation_trace:
                    try:
                        update_data = {"user_id": self.user_id}
                        update_metadata = {"response_source": "llm", "user_id": self.user_id}
                        
                        if transcript_text:
                            update_data["transcript"] = transcript_text
                            update_metadata["transcript_source"] = "llm_response_metadata"
                        
                        if response_text:
                            update_data["ai_response"] = response_text
                            update_metadata["response_length"] = len(response_text)
                        
                        update_metadata.update({
                            "llm_duration_seconds": llm_duration,
                            "llm_processing_time": llm_end_time,
                            "llm_start_time": llm_start_time
                        })
                        
                        self.conversation_manager.log_activity_to_trace(
                            user_id=self.user_id,
                            activity_type="llm_response",
                            data={
                                **update_data,
                                **update_metadata,
                                "session_id": self.conversation_session.session_id
                            }
                        )
                        
                        if transcript_text:
                            logger.info(f"🔍 Logged transcript to Langfuse (duration: {llm_duration:.3f}s)")
                        if response_text:
                            logger.info(f"🔍 Logged AI response to Langfuse (duration: {llm_duration:.3f}s)")
                    
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to log LLM response to Langfuse: {e}")
            
            except Exception as e:
                logger.warning(f"⚠️ Failed to handle LLM response: {e}")
        
        @self.llm_service.event_handler("on_function_call")
        async def on_function_call(function_call):
            """Capture function calls for transcript logging."""
            llm_tool_call_start_time = time.time()
            
            try:
                logger.info(f"🔧 Function call received: {type(function_call)}")
                
                if hasattr(function_call, 'name'):
                    logger.info(f"📝 Function name: {function_call.name}")
                    if hasattr(function_call, 'arguments'):
                        logger.info(f"📝 Function arguments: {function_call.arguments}")
                    
                    llm_tool_call_end_time = time.time()
                    llm_tool_call_duration = llm_tool_call_end_time - llm_tool_call_start_time
                    
                    self.conversation_manager.log_activity_to_trace(
                        user_id=self.user_id,
                        activity_type="llm_function_call",
                        data={
                            "function_name": function_call.name,
                            "arguments": function_call.arguments if hasattr(function_call, 'arguments') else {},
                            "llm_tool_call_duration_seconds": llm_tool_call_duration,
                            "source": "voice_llm"
                        }
                    )
                    logger.info(f"🔍 Logged function call to unified trace (duration: {llm_tool_call_duration:.3f}s)")
            
            except Exception as e:
                logger.warning(f"⚠️ Failed to handle function call: {e}")
    
    def _setup_transcript_event_handlers(self, transcript):
        """Setup event handlers for transcript updates."""
        
        @transcript.event_handler("on_transcript_update")
        async def on_transcript_update(processor, frame):
            """Handle STT transcript data."""
            stt_start_time = time.time()
            
            try:
                logger.info(f"🎤 Received transcript update")
                
                if hasattr(self.agent_manager, 'conversation_trace') and self.agent_manager.conversation_trace:
                    if hasattr(frame, 'messages') and frame.messages:
                        logger.info(f"📝 Found {len(frame.messages)} messages in frame")
                        for i, message in enumerate(frame.messages):
                            if message.role == "user" and message.content.strip():
                                transcript_text = message.content.strip()
                                stt_end_time = time.time()
                                stt_duration = stt_end_time - stt_start_time
                                
                                try:
                                    self.conversation_manager.log_activity_to_trace(
                                        user_id=self.user_id,
                                        activity_type="input",
                                        data={
                                            "transcript": transcript_text,
                                            "source": "stt",
                                            "processor": type(processor).__name__,
                                            "message_role": message.role,
                                            "content_length": len(transcript_text),
                                            "session_id": self.conversation_session.session_id,
                                            "is_final": True,
                                            "language": "en-US",
                                            "stt_duration_seconds": stt_duration
                                        }
                                    )
                                    logger.info(f"🔍 Updated unified trace with STT input (duration: {stt_duration:.3f}s)")
                                
                                except Exception as e:
                                    logger.warning(f"⚠️ Failed to update STT input in unified trace: {e}")
                    else:
                        logger.warning(f"⚠️ Frame has no messages")
                else:
                    logger.warning("⚠️ No conversation trace available")
            
            except Exception as e:
                logger.warning(f"⚠️ Failed to handle transcript event: {e}")
    
    def _register_function_handlers(self):
        """Register all function handlers for tools."""
        
        async def handle_function_call_gemini(params: FunctionCallParams):
            """Handle function calls from Gemini Live."""
            function_start_time = time.time()
            
            try:
                logger.info(f"🔧 Function call: {params.function_name}")
                params.arguments["user_id"] = self.user_id
                
                class MockFunctionCall:
                    def __init__(self, name, arguments):
                        self.name = name
                        self.arguments = arguments
                
                mock_call = MockFunctionCall(params.function_name, params.arguments)
                tool_execution_start_time = time.time()
                result = await self.agent_manager.handle_function_call(mock_call)
                tool_execution_end_time = time.time()
                tool_execution_duration = tool_execution_end_time - tool_execution_start_time
                
                end_time = time.time()
                duration = end_time - function_start_time
                
                # Parse tool response
                tool_response_data = None
                try:
                    import json
                    if isinstance(result, str):
                        tool_response_data = json.loads(result)
                    elif isinstance(result, dict):
                        tool_response_data = result
                except:
                    tool_response_data = {"raw_result": str(result)}
                
                # Log function call activity
                self.conversation_manager.log_activity_to_trace(
                    user_id=self.user_id,
                    activity_type="tool_function_call",
                    data={
                        "function_name": params.function_name,
                        "arguments": params.arguments,
                        "result": str(result)[:1000],
                        "duration_seconds": duration,
                        "success": True,
                        "source": "voice"
                    }
                )
                
                # Log tool response
                self.conversation_manager.log_activity_to_trace(
                    user_id=self.user_id,
                    activity_type="tool_response",
                    data={
                        "function_name": params.function_name,
                        "tool_response": tool_response_data,
                        "response_type": type(result).__name__,
                        "response_length": len(str(result)),
                        "total_duration_seconds": duration,
                        "tool_execution_duration_seconds": tool_execution_duration,
                        "success": True,
                        "source": "voice",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                log_api_call(
                    tool_name=params.function_name,
                    action="execute",
                    parameters=params.arguments,
                    result=result,
                    duration=duration,
                    success=True,
                    trace_id=self.conversation_trace,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                
                await params.result_callback({"result": result})
            
            except Exception as e:
                end_time = time.time()
                duration = end_time - function_start_time
                
                logger.error(f"❌ Function call error: {e}")
                
                # Log error
                self.conversation_manager.log_activity_to_trace(
                    user_id=self.user_id,
                    activity_type="tool_function_call_error",
                    data={
                        "function_name": params.function_name,
                        "arguments": params.arguments,
                        "error": str(e),
                        "total_duration_seconds": duration,
                        "success": False,
                        "source": "voice"
                    }
                )
                
                log_api_call(
                    tool_name=params.function_name,
                    action="execute",
                    parameters=params.arguments,
                    result=str(e),
                    duration=duration,
                    success=False,
                    error_message=str(e),
                    trace_id=self.conversation_trace,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                
                await params.result_callback({"error": str(e)})
        
        # Register all tools
        tool_definitions = self.agent_manager.get_tool_definitions()
        for tool_def in tool_definitions:
            self.llm_service.register_function(tool_def.name, handle_function_call_gemini)
    
    def _setup_transport_event_handlers(self, rtvi):
        """Setup event handlers for transport events."""
        
        @rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi_processor):
            logger.info("✅ Client ready")
            await rtvi_processor.set_bot_ready()
            context_aggregator = self.llm_service.create_context_aggregator(OpenAILLMContext([]))
            await self.task.queue_frames([context_aggregator.user().get_context_frame()])
        
        @self.transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            logger.info("🔗 Client connected")
        
        @self.transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            logger.info("👋 Client disconnected")
            await self.task.cancel()
    
    async def run(self):
        """Run the voice pipeline."""
        try:
            await self.runner.run(self.task)
            
            # Update conversation session
            self.conversation_manager.update_session_activity(self.user_id, conversation_type="voice")
            logger.info(f"✅ Voice conversation completed for user {self.user_id}")
        
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"⚠️ WebSocket connection closed: {e}")
            
            # Log connection closure
            self.conversation_manager.log_activity_to_trace(
                user_id=self.user_id,
                activity_type="conversation_disconnected",
                data={
                    "reason": "websocket_closed",
                    "duration_seconds": time.time() - self.start_time,
                    "status": "disconnected",
                    "source": "voice_pipeline"
                }
            )
        
        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}")
            
            # Log error
            self.conversation_manager.log_activity_to_trace(
                user_id=self.user_id,
                activity_type="conversation_error",
                data={
                    "error": str(e),
                    "duration_seconds": time.time() - self.start_time,
                    "status": "error",
                    "source": "voice_pipeline"
                }
            )
        
        finally:
            # Clean up
            if self.conversation_trace and hasattr(self.conversation_trace, 'end'):
                self.conversation_trace.end()


async def create_voice_agent(
    user_id: str,
    session_id: str,
    websocket,
    current_page: str = "broadband"
) -> VoiceAgent:
    """
    Factory function to create and initialize a voice agent.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        websocket: FastAPI WebSocket connection
        current_page: Current page context
        
    Returns:
        Initialized VoiceAgent instance
    """
    agent = VoiceAgent(user_id, session_id, current_page)
    await agent.initialize(websocket)
    return agent

