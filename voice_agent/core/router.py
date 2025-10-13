#!/usr/bin/env python3
"""
Enhanced Voice Agent Router for agent voice backend.
Updated to work with the new modular tool structure and improved configuration.
"""

import os
import sys
import time
import uuid
import random

# Add the project root to Python path FIRST, before any other imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
import json
from typing import Any, Dict, Optional
from datetime import datetime

import uvicorn
from dotenv import load_dotenv
from fastapi import WebSocket, Request, APIRouter, HTTPException
from loguru import logger
import websockets

# Import OpenTelemetry with fallback
try:
    from opentelemetry import trace
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    logger.warning("⚠️ OpenTelemetry not available, tracing disabled")
    # Create a mock trace object to avoid errors
    class MockTracer:
        def get_tracer(self, name):
            return MockTracer()
        def start_span(self, name, **kwargs):
            return MockSpan()
    class MockSpan:
        def set_attribute(self, key, value):
            pass
        def end(self):
            pass
        def get_span_context(self):
            return MockSpanContext()
    class MockSpanContext:
        def __init__(self):
            self.trace_id = None
    trace = MockTracer()

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.frames.frames import LLMMessagesAppendFrame, TranscriptionMessage
from pipecat.services.gemini_multimodal_live.gemini import GeminiMultimodalLiveLLMService
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

# Import new modular components
from voice_agent.config.environment import get_backend_url, get_frontend_url, validate_environment
from voice_agent.config.settings import get_settings, validate_settings
from voice_agent.core.agent_manager import AgentManager, create_agent_manager
from voice_agent.core.websocket_registry import (
    register_session_user, unregister_session_user,
    register_tool_websocket, unregister_tool_websocket,
    get_all_users, send_to_user_tool_websocket
)
from voice_agent.core.text_agent import create_text_agent
from voice_agent.core.voice_agent import create_voice_agent
from voice_agent.core.conversation_manager import get_conversation_manager
from voice_agent.utils.validators import validate_page_name, validate_api_key
from voice_agent.utils.langfuse_tracing import get_langfuse_tracer, log_api_call, setup_tracing
from voice_agent.functions.auth_store import auth_store_router

load_dotenv(override=True)

# Ensure we're in the correct directory for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Session storage
session_agents = {}
session_websockets = {}
session_user_mapping = {}
user_text_agents = {}

# Configure logger
try:
    logger.remove(0)
except ValueError:
    # Handle case where default handler doesn't exist
    pass
logger.add(sys.stderr, level="DEBUG")


async def retry_with_exponential_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,)
):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retryable_exceptions as e:
            if attempt == max_retries:
                logger.error(f"❌ All {max_retries + 1} attempts failed. Final error: {e}")
                raise

            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)  # Add jitter

            logger.warning(f"⚠️ Attempt {attempt + 1}/{max_retries + 1} failed: {e}. Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)

    return None


async def fallback_to_text_mode(websocket: WebSocket, session_id: str, user_id: str, current_page: str = "broadband"):
    """Fallback to text-only conversation when voice service fails."""
    logger.info(f"📝 Falling back to text mode for user {user_id} on page {current_page}")

    try:
        # Send message to user about fallback
        fallback_message = "I'm switching to text-only mode due to voice service issues. Please type your messages and I'll respond."
        await websocket.send_text(fallback_message)

        # Run text conversation bot as fallback
        await run_text_conversation_bot(websocket, session_id, user_id, current_page)

    except Exception as e:
        logger.error(f"❌ Text fallback failed: {e}")
        try:
            await websocket.send_text("I'm experiencing technical difficulties. Please try reconnecting.")
        except:
            pass


async def create_gemini_live_llm(enable_function_calling: bool = True, current_page: str = "broadband"):
    """Create Gemini Live LLM service with function calling and page context."""
    settings = get_settings()

    if not validate_api_key(settings.google_api_key)[0]:
        raise ValueError("Invalid or missing GOOGLE_API_KEY.")

    logger.info("🚀 Using Gemini Multimodal Live")
    logger.info(f"🔧 Current page context: {current_page}")

    # Create tools if function calling is enabled
    tools = None
    if enable_function_calling:
        agent_manager = create_agent_manager(current_page=current_page)
        tool_definitions = agent_manager.get_tool_definitions()

        for tool_def in tool_definitions:
            logger.info(f"🔧 Tool registered: {tool_def.name}")

        tools_schema = ToolsSchema(standard_tools=tool_definitions)
        logger.info(f"🔧 Function calling enabled with {len(tool_definitions)} tools")
    else:
        tools_schema = None
        logger.info("⚡ Function calling disabled")

    # Create agent manager and get system instruction
    agent_manager = create_agent_manager(current_page=current_page)
    system_instruction = agent_manager.get_system_instruction_with_page_context()

    # Create Gemini Live service with retry logic
    async def _create_service():
        try:
            llm_service = GeminiMultimodalLiveLLMService(
                api_key=settings.google_api_key,
                system_instruction=system_instruction,
                voice_id=settings.gemini_voice_id,
                model=settings.gemini_model,
                transcribe_model_audio=True,
                temperature=settings.temperature,
                tools=tools_schema,
            )
            return llm_service
        except Exception as e:
            logger.error(f"❌ Failed to create Gemini service: {e}")
            # Check if it's a WebSocket-related error that we should retry
            if isinstance(e, (websockets.exceptions.ConnectionClosedError, websockets.exceptions.WebSocketException)):
                logger.info("🔄 WebSocket connection error detected, will retry...")
            elif "deadline expired" in str(e).lower():
                logger.warning("⏰ Gemini service deadline expired, will retry with backoff...")
            raise e

    # Use retry logic for service creation
    llm_service = await retry_with_exponential_backoff(
        _create_service,
        max_retries=settings.max_gemini_retries,
        base_delay=2.0,
        max_delay=10.0,
        retryable_exceptions=(websockets.exceptions.ConnectionClosedError, websockets.exceptions.WebSocketException, Exception)
    )

    if llm_service is None:
        raise Exception("Failed to create Gemini service after retries")

    return llm_service, agent_manager


async def run_simplified_conversation_bot(websocket: WebSocket, session_id: str, user_id: str, current_page: str = "broadband"):
    """
    Run the conversational AI bot with Gemini Live.
    Now uses the refactored VoiceAgent class for better code organization.
    """
    logger.info(f"🎤 Starting conversation bot - Session: {session_id}, User: {user_id}, Page: {current_page}")
    
    try:
        # Create and initialize voice agent
        voice_agent = await create_voice_agent(
            user_id=user_id,
            session_id=session_id,
            websocket=websocket,
            current_page=current_page
        )
        
        # Run the voice pipeline
        await voice_agent.run()
    
    except Exception as e:
        logger.error(f"❌ Voice agent error: {e}")
        raise


async def run_simplified_conversation_bot_legacy(websocket: WebSocket, session_id: str, user_id: str, current_page: str = "broadband"):
    """
    LEGACY: Original implementation kept for reference.
    This function is no longer used - see run_simplified_conversation_bot above.
    """
    logger.info(f"🎤 Starting conversation bot - Session: {session_id}, User: {user_id}, Page: {current_page}")
    start_time = time.time()  # Define start_time at function level

    # Normalize page name - no longer strict validation
    is_valid, normalized_page = validate_page_name(current_page)
    if is_valid:
        current_page = normalized_page
    else:
        logger.warning(f"⚠️ Invalid page name, using: {current_page}")
        current_page = current_page.lower().strip().replace(" ", "-").replace("_", "-")

    settings = get_settings()

    # Set OTLP environment variables before Pipecat initializes
    if settings.langfuse_enabled:
        if settings.otel_exporter_otlp_endpoint:
            os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = settings.otel_exporter_otlp_endpoint
            logger.info(f"✅ Set OTLP environment variables for Pipecat: {settings.otel_exporter_otlp_endpoint}")
        if settings.otel_exporter_otlp_headers:
            os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = settings.otel_exporter_otlp_headers

    # Initialize OpenTelemetry tracing for Pipecat following official docs
    try:
        setup_tracing(
            service_name=settings.otel_service_name,
            settings=settings
        )
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize OpenTelemetry tracing: {e}")

    # Get unified conversation session and trace
    conversation_manager = get_conversation_manager()
    conversation_session = conversation_manager.get_or_create_session(
        user_id=user_id,
        conversation_type="voice",
        current_page=current_page
    )

    # Use the unified session ID and trace
    conversation_session_id = conversation_session.session_id
    voice_session_id = f"voice_session_{user_id}_{conversation_session_id}"
    conversation_trace = conversation_session.trace  # Use the actual trace object

    logger.info(f"🎤 Using unified conversation session {conversation_session_id} for voice (user: {user_id})")

    # Note: Using unified Langfuse tracing via conversation_manager
    # Removed duplicate OpenTelemetry span creation to prevent multiple traces
    
    # Create transport
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=settings.vad_stop_seconds)),
            serializer=ProtobufFrameSerializer(),
        ),
    )
    
    # Create LLM service and agent
    llm_service, agent_manager = await create_gemini_live_llm(enable_function_calling=True, current_page=current_page)
    
    # Create context for function calling
    system_prompt = "You are a helpful AI assistant. Use function calling when needed."
    context = OpenAILLMContext([{
        "role": "user",
        "content": system_prompt
    }])
    context_aggregator = llm_service.create_context_aggregator(context)

    # Log system prompt to unified trace
    conversation_manager.log_activity_to_trace(
        user_id=user_id,
        activity_type="system_initialization",
        data={
            "system_prompt": system_prompt,
            "current_page": current_page,
            "session_id": conversation_session_id
        }
    )

    # Add event handler to capture LLM responses and function calls for transcript logging
    @llm_service.event_handler("on_llm_response")
    async def on_llm_response(response):
        """Capture LLM responses for transcript logging."""
        llm_start_time = time.time()  # Track LLM response processing duration
        
        try:
            logger.info(f"🤖 LLM Response received: {type(response)}")
            logger.info(f"📝 Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")

            # Check if response has transcript data (for multimodal Gemini)
            transcript_text = None
            response_text = None

            # Check for transcript in response metadata or content
            if hasattr(response, 'metadata') and response.metadata:
                logger.info(f"📝 Response metadata: {response.metadata}")
                if 'transcript' in response.metadata:
                    transcript_text = response.metadata['transcript']

            # Check for transcript in response content
            if hasattr(response, 'content'):
                response_text = response.content[:200] + "..." if len(response.content) > 200 else response.content
                logger.info(f"📝 LLM Response content: {response_text}")

                # For multimodal responses, transcript might be in content
                if not transcript_text and 'transcript' in response_text.lower():
                    # Try to extract transcript from content (this is a fallback)
                    pass

            # Calculate LLM response duration
            llm_end_time = time.time()
            llm_duration = llm_end_time - llm_start_time

            # Log both transcript and response to Langfuse with duration
            if conversation_trace:
                try:
                    update_data = {"user_id": user_id}
                    update_metadata = {"response_source": "llm", "user_id": user_id}

                    if transcript_text:
                        update_data["transcript"] = transcript_text
                        update_metadata["transcript_source"] = "llm_response_metadata"

                    if response_text:
                        update_data["ai_response"] = response_text
                        update_metadata["response_length"] = len(response_text)

                    # Add LLM duration timing
                    update_metadata.update({
                        "llm_duration_seconds": llm_duration,
                        "llm_processing_time": llm_end_time,
                        "llm_start_time": llm_start_time
                    })

                    conversation_manager.log_activity_to_trace(
                        user_id=user_id,
                        activity_type="llm_response",
                        data={
                            **update_data,
                            **update_metadata,
                            "session_id": conversation_session_id
                        }
                    )

                    if transcript_text:
                        logger.info(f"🔍 Logged transcript to Langfuse: '{transcript_text[:50]}...' (duration: {llm_duration:.3f}s)")
                    if response_text:
                        logger.info(f"🔍 Logged AI response to Langfuse: {response_text[:50]}... (duration: {llm_duration:.3f}s)")

                except Exception as e:
                    logger.warning(f"⚠️ Failed to log LLM response to Langfuse: {e}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to handle LLM response: {e}")
            import traceback
            logger.warning(f"Response object: {response}")
            logger.warning(f"Traceback: {traceback.format_exc()}")

    @llm_service.event_handler("on_function_call")
    async def on_function_call(function_call):
        """Capture function calls for transcript logging."""
        llm_tool_call_start_time = time.time()

        try:
            logger.info(f"🔧 Function call received: {type(function_call)}")
            if hasattr(function_call, 'name'):
                logger.info(f"📝 Function name: {function_call.name}")
                if hasattr(function_call, 'arguments'):
                    logger.info(f"📝 Function arguments: {function_call.arguments}")

                # Log function call activity to unified trace with duration tracking
                llm_tool_call_end_time = time.time()
                llm_tool_call_duration = llm_tool_call_end_time - llm_tool_call_start_time

                conversation_manager.log_activity_to_trace(
                    user_id=user_id,
                    activity_type="llm_function_call",
                    data={
                        "function_name": function_call.name,
                        "arguments": function_call.arguments if hasattr(function_call, 'arguments') else {},
                        "llm_tool_call_duration_seconds": llm_tool_call_duration,
                        "llm_tool_call_start_time": llm_tool_call_start_time,
                        "llm_tool_call_end_time": llm_tool_call_end_time,
                        "source": "voice_llm"
                    }
                )
                logger.info(f"🔍 Logged function call to unified trace: {function_call.name} (duration: {llm_tool_call_duration:.3f}s)")
        except Exception as e:
            llm_tool_call_end_time = time.time()
            llm_tool_call_duration = llm_tool_call_end_time - llm_tool_call_start_time
            logger.warning(f"⚠️ Failed to handle function call: {e}")

            # Log error with duration info
            conversation_manager.log_activity_to_trace(
                user_id=user_id,
                activity_type="llm_function_call_error",
                data={
                    "function_name": getattr(function_call, 'name', 'unknown') if hasattr(function_call, 'name') else 'unknown',
                    "error": str(e),
                    "llm_tool_call_duration_seconds": llm_tool_call_duration,
                    "source": "voice_llm"
                }
            )

    # Note: Transcript handling is done via TranscriptProcessor event handlers below
    # LLM service transcript events are not used - transcripts come through the processor

    # Create processors
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
    transcript = TranscriptProcessor()

    # Debug logging for transcript processor setup
    logger.info(f"🔧 Created TranscriptProcessor: {transcript}")
    logger.info(f"🔧 Transcript user processor: {transcript.user()}")
    logger.info(f"🔧 Transcript assistant processor: {transcript.assistant()}")

    # Store agent in session and conversation trace for transcript updates
    session_agents[session_id] = agent_manager
    agent_manager.conversation_trace = conversation_trace
    agent_manager.conversation_session_id = conversation_session_id
    
    # Build pipeline - place transcript processors where they can capture data
    # For multimodal Gemini, the transcript might come from the LLM service itself
    pipeline = Pipeline([
        transport.input(),
        context_aggregator.user(),
        rtvi,
        llm_service,
        transcript.user(),  # Try to capture user input from LLM service
        transport.output(),
        transcript.assistant(),  # Assistant transcript after TTS
        context_aggregator.assistant(),
    ])

    logger.info(f"🔧 Pipeline created successfully")
    
    # Create task with tracing enabled following official Langfuse docs
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=settings.enable_metrics,
            enable_usage_metrics=settings.enable_usage_metrics,
        ),
        enable_tracing=True,  # Enable Pipecat tracing for Langfuse
        observers=[RTVIObserver(rtvi)],
    )
    
    agent_manager.task = task

    # Add transcript event handler to update Langfuse trace with STT input
    @transcript.event_handler("on_transcript_update")
    async def on_transcript_update(processor, frame):
        """Handle STT transcript data to update Langfuse trace with user input."""
        stt_start_time = time.time()  # Track STT processing duration
        
        try:
            logger.info(f"🎤 Received transcript update from processor: {type(processor).__name__}")
            logger.info(f"📝 Frame type: {type(frame).__name__}")
            logger.info(f"📝 Frame attributes: {dir(frame)}")

            if hasattr(agent_manager, 'conversation_trace') and agent_manager.conversation_trace:
                # Extract transcript messages from the frame
                if hasattr(frame, 'messages') and frame.messages:
                    logger.info(f"📝 Found {len(frame.messages)} messages in frame")
                    for i, message in enumerate(frame.messages):
                        logger.info(f"📝 Message {i}: role={message.role}, content='{message.content[:100]}...', timestamp={getattr(message, 'timestamp', None)}")

                        if message.role == "user" and message.content.strip():
                            transcript_text = message.content.strip()
                            stt_end_time = time.time()
                            stt_duration = stt_end_time - stt_start_time

                            # Log STT input to unified trace with duration
                            try:
                                conversation_manager.log_activity_to_trace(
                                    user_id=user_id,
                                    activity_type="input",
                                    data={
                                        "transcript": transcript_text,
                                        "source": "stt",
                                        "processor": type(processor).__name__,
                                        "message_role": message.role,
                                        "content_length": len(transcript_text),
                                        "timestamp": getattr(message, 'timestamp', None),
                                        "session_id": conversation_session_id,
                                        "is_final": True,
                                        "language": "en-US",  # Default, could be extracted from frame metadata
                                        "stt_duration_seconds": stt_duration,
                                        "stt_processing_time": stt_end_time,
                                        "stt_start_time": stt_start_time
                                    }
                                )
                                logger.info(f"🔍 Updated unified trace with STT input: '{transcript_text[:50]}...' (duration: {stt_duration:.3f}s)")
                                logger.info(f"✅ STT input logged to unified trace successfully")
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to update STT input in unified trace: {e}")
                else:
                    logger.warning(f"⚠️ Frame has no messages attribute or messages is empty")
                    logger.info(f"📝 Frame content: {frame}")
            else:
                logger.warning("⚠️ No conversation trace available for transcript update")

        except Exception as e:
            logger.warning(f"⚠️ Failed to handle transcript event: {e}")
            import traceback
            logger.warning(f"Traceback: {traceback.format_exc()}")

    # Note: The TranscriptProcessor only has 'on_transcript_update' event, not 'on_transcript'
    # The 'on_transcript_update' handler above should handle all transcript events

    # Register function handlers
    async def handle_function_call_gemini(params: FunctionCallParams):
        """Handle function calls from Gemini Live."""
        function_start_time = time.time()  # Use different variable name for function-level timing
        function_span = None

        # Note: Using unified Langfuse tracing via conversation_manager
        # Removed OpenTelemetry span creation to prevent duplicate traces

        try:
            logger.info(f"🔧 Function call: {params.function_name}")
            params.arguments["user_id"] = user_id

            class MockFunctionCall:
                def __init__(self, name, arguments):
                    self.name = name
                    self.arguments = arguments

            mock_call = MockFunctionCall(params.function_name, params.arguments)
            tool_execution_start_time = time.time()
            result = await agent_manager.handle_function_call(mock_call)
            tool_execution_end_time = time.time()
            tool_execution_duration = tool_execution_end_time - tool_execution_start_time

            # Log API call metrics
            end_time = time.time()
            duration = end_time - function_start_time

            # Parse tool response to extract structured data
            tool_response_data = None
            try:
                # Try to parse result as JSON if it's a string
                if isinstance(result, str):
                    tool_response_data = json.loads(result)
                elif isinstance(result, dict):
                    tool_response_data = result
            except:
                tool_response_data = {"raw_result": str(result)}

            # Log function call activity to unified trace
            conversation_manager.log_activity_to_trace(
                user_id=user_id,
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

            # Log detailed tool response separately for better trace visibility
            conversation_manager.log_activity_to_trace(
                user_id=user_id,
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

            # Log tool result processing duration (when LLM processes the tool result)
            tool_result_processing_start_time = time.time()
            # Simulate tool result processing time (this is when LLM processes the result)
            tool_result_processing_end_time = time.time()
            tool_result_processing_duration = tool_result_processing_end_time - tool_result_processing_start_time

            conversation_manager.log_activity_to_trace(
                user_id=user_id,
                activity_type="tool_result_processing",
                data={
                    "function_name": params.function_name,
                    "tool_result_processing_duration_seconds": tool_result_processing_duration,
                    "tool_result_processing_start_time": tool_result_processing_start_time,
                    "tool_result_processing_end_time": tool_result_processing_end_time,
                    "source": "voice_llm"
                }
            )

            log_api_call(
                tool_name=params.function_name,
                action="execute",
                parameters=params.arguments,
                result=result,
                duration=duration,
                success=True,
                trace_id=conversation_trace,
                user_id=user_id,
                session_id=voice_session_id
            )

            await params.result_callback({"result": result})

        except Exception as e:
            # Calculate durations even for errors
            end_time = time.time()
            duration = end_time - function_start_time

            # Tool execution duration (from start to error)
            tool_execution_end_time = time.time()
            tool_execution_duration = tool_execution_end_time - tool_execution_start_time

            logger.error(f"❌ Function call error: {e}")

            # Log API call error metrics
            # Log function call error to unified trace
            conversation_manager.log_activity_to_trace(
                user_id=user_id,
                activity_type="tool_function_call_error",
                data={
                    "function_name": params.function_name,
                    "arguments": params.arguments,
                    "error": str(e),
                    "total_duration_seconds": duration,
                    "tool_execution_duration_seconds": tool_execution_duration,
                    "success": False,
                    "source": "voice"
                }
            )

            # Log tool error response separately
            conversation_manager.log_activity_to_trace(
                user_id=user_id,
                activity_type="tool_error_response",
                data={
                    "function_name": params.function_name,
                    "error_response": str(e),
                    "error_type": type(e).__name__,
                    "total_duration_seconds": duration,
                    "tool_execution_duration_seconds": tool_execution_duration,
                    "success": False,
                    "source": "voice",
                    "timestamp": datetime.now().isoformat()
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
                trace_id=conversation_trace,
                user_id=user_id,
                session_id=voice_session_id
            )

            await params.result_callback({"error": str(e)})
    
    # Register all tool functions
    tool_definitions = agent_manager.get_tool_definitions()
    for tool_def in tool_definitions:
        llm_service.register_function(tool_def.name, handle_function_call_gemini)
    
    # Event handlers
    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info("✅ Client ready")
        await rtvi.set_bot_ready()
        await task.queue_frames([context_aggregator.user().get_context_frame()])
    
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("🔗 Client connected")
    
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("👋 Client disconnected")
        await task.cancel()
    
    # Run pipeline with enhanced error handling
    runner = PipelineRunner(handle_sigint=False)
    try:
        await runner.run(task)

        # Update conversation session with completion
        conversation_manager.update_session_activity(user_id, conversation_type="voice")
        logger.info(f"✅ Voice conversation completed for user {user_id}")

    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"⚠️ WebSocket connection closed during pipeline execution: {e}")
        # This is expected when the user disconnects, don't treat as error

        # Log connection closure to unified trace
        conversation_manager.log_activity_to_trace(
            user_id=user_id,
            activity_type="conversation_disconnected",
            data={
                "reason": "websocket_closed",
                "duration_seconds": time.time() - start_time,
                "status": "disconnected",
                "source": "voice_pipeline"
            }
        )

    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}")

        # Check if it's a Gemini service error that we should handle gracefully
        if ("1011" in str(e) or
            "internal error" in str(e).lower() or
            "service is currently unavailable" in str(e).lower() or
            "deadline expired" in str(e).lower()):
            logger.warning("⚠️ Gemini service timeout or temporarily unavailable, attempting graceful degradation")

            # Send error message to user
            try:
                error_message = "I'm experiencing a temporary connection timeout with the voice service. This usually resolves itself quickly - please try again in a few seconds."
                await websocket.send_text(error_message)
                await asyncio.sleep(2)  # Give user time to hear the message
            except:
                pass  # WebSocket might already be closed

            # Log service error to unified trace
            conversation_manager.log_activity_to_trace(
                user_id=user_id,
                activity_type="service_unavailable",
                data={
                    "error": str(e),
                    "duration_seconds": time.time() - start_time,
                    "status": "service_error",
                    "source": "gemini_service"
                }
            )

        else:
            # Log other errors to unified trace
            conversation_manager.log_activity_to_trace(
                user_id=user_id,
                activity_type="conversation_error",
                data={
                    "error": str(e),
                    "duration_seconds": time.time() - start_time,
                    "status": "error",
                    "source": "voice_pipeline"
                }
            )

        try:
            await websocket.close(code=1000, reason="Pipeline error")
        except:
            pass  # WebSocket might already be closed

    finally:
        # Clean up Langfuse trace
        if conversation_trace and hasattr(conversation_trace, 'end'):
            conversation_trace.end()


async def run_text_conversation_bot(websocket: WebSocket, session_id: str, user_id: str, current_page: str = "broadband"):
    """Run text-only conversation bot."""
    logger.info(f"📝 Starting text bot - Session: {session_id}, User: {user_id}, Page: {current_page}")

    
    # Normalize page name - no longer strict validation
    is_valid, normalized_page = validate_page_name(current_page)
    if is_valid:
        current_page = normalized_page
    else:
        logger.warning(f"⚠️ Invalid page name, using: {current_page}")
        current_page = current_page.lower().strip().replace(" ", "-").replace("_", "-")

    # Create or get text agent with current page context
    agent_key = f"{user_id}_{current_page}"  # Use page-specific agent key
    if agent_key not in user_text_agents:
        user_text_agents[agent_key] = create_text_agent(user_id, current_page)
        await user_text_agents[agent_key].initialize()
    
    agent = user_text_agents[agent_key]
    
    # Update agent's current page if it changed
    if hasattr(agent, 'current_page'):
        agent.current_page = current_page
    if hasattr(agent, 'agent_manager') and agent.agent_manager:
        agent.agent_manager.update_current_page(current_page, user_id)

    # Handle messages
    try:
        while True:
            text_message = await websocket.receive_text()
            logger.info(f"📝 Received: '{text_message[:50]}...'")
            
            # Parse JSON if needed
            if text_message.strip().startswith('{'):
                try:
                    parsed = json.loads(text_message)
                    if 'message' in parsed:
                        text_message = parsed['message']
                except:
                    pass

            try:
                # Process with timeout
                response_text = await asyncio.wait_for(
                    agent.process_message(text_message),
                    timeout=30.0
                )
                
                if response_text and response_text.strip():
                    await websocket.send_text(response_text)
                    logger.info(f"📤 Response sent")
                else:
                    fallback = f"On the {current_page} page. What would you like to do?"
                    await websocket.send_text(fallback)

            except asyncio.TimeoutError:
                await websocket.send_text("Request timed out. Please try again.")
            except Exception as e:
                logger.error(f"❌ Error processing message: {e}")
                await websocket.send_text("I encountered an error processing your message.")

    except Exception as e:
        logger.info(f"📝 WebSocket closed: {e}")


# Create router for voice agent endpoints
router = APIRouter(tags=["Voice Agent"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main voice WebSocket endpoint."""
    # Extract parameters
    user_id = websocket.query_params.get("user_id")
    current_page = websocket.query_params.get("current_page")
    
    # STRICT: user_id is now mandatory - NO auto-generation
    if not user_id or not user_id.strip():
        logger.error("❌ Voice WebSocket connection rejected: user_id parameter is required")
        await websocket.close(code=1008, reason="user_id parameter is required")
        return
    
    user_id = user_id.strip()
    
    # Be more permissive with current_page validation
    if not current_page:
        current_page = "broadband"  # Default page
    else:
        # Just normalize, don't reject
        current_page = current_page.strip().lower().replace(" ", "-").replace("_", "-")
    
    await websocket.accept()
    
    # Create session
    session_id = str(uuid.uuid4())
    session_websockets[session_id] = websocket
    session_user_mapping[session_id] = user_id
    register_session_user(session_id, user_id)
    
    logger.info(f"🔗 Voice WebSocket connected - User: {user_id}, Page: {current_page}")

    try:
        await run_simplified_conversation_bot(websocket, session_id, user_id, current_page)
    except Exception as e:
        logger.error(f"❌ Voice bot error: {e}")

        # Check if it's a Gemini service error that should trigger fallback
        is_gemini_error = ("1011" in str(e) or
                          "internal error" in str(e).lower() or
                          "service is currently unavailable" in str(e).lower() or
                          "gemini" in str(e).lower())

        if is_gemini_error and settings.enable_voice_fallback:
            logger.warning("⚠️ Gemini service error detected, attempting fallback to text mode...")
            try:
                await fallback_to_text_mode(websocket, session_id, user_id, current_page)
            except Exception as fallback_error:
                logger.error(f"❌ Fallback to text mode failed: {fallback_error}")
        else:
            # For other types of errors, don't attempt fallback
            if is_gemini_error:
                logger.error(f"❌ Gemini service error but fallback disabled: {e}")
            else:
                logger.error(f"❌ Non-Gemini error, not attempting fallback: {e}")

    finally:
        # Cleanup
        session_agents.pop(session_id, None)
        session_websockets.pop(session_id, None)
        session_user_mapping.pop(session_id, None)
        unregister_session_user(session_id)

        # End conversation session
        conversation_manager = get_conversation_manager()
        conversation_manager.end_session(user_id)


@router.websocket("/ws/tools")
async def tools_websocket_endpoint(websocket: WebSocket):
    """Tool commands WebSocket endpoint."""
    user_id = websocket.query_params.get("user_id")
    
    # STRICT: user_id is now mandatory - NO auto-generation
    if not user_id or not user_id.strip():
        logger.error("❌ Tool WebSocket connection rejected: user_id parameter is required")
        await websocket.close(code=1008, reason="user_id parameter is required")
        return
    
    user_id = user_id.strip()
    
    current_page = websocket.query_params.get("current_page", "broadband")
    current_page = current_page.strip().lower().replace(" ", "-").replace("_", "-")
    
    await websocket.accept()
    register_tool_websocket(user_id, websocket)
    
    logger.info(f"🔧 Tool WebSocket connected - User: {user_id}, Page: {current_page}")
    
    # Send confirmation
    confirmation = {
        "type": "connection_confirmation",
        "user_id": user_id,
        "current_page": current_page,
        "timestamp": datetime.now().isoformat()
    }
    await websocket.send_json(confirmation)
    
    try:
        while True:
            message = await websocket.receive_text()
            echo = {
                "type": "echo_response",
                "user_id": user_id,
                "original_message": message,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_json(echo)
    except:
        pass
    finally:
        unregister_tool_websocket(user_id)


@router.websocket("/ws/text-conversation")
async def text_conversation_websocket_endpoint(websocket: WebSocket):
    """Text conversation WebSocket endpoint."""
    user_id = websocket.query_params.get("user_id")
    current_page = websocket.query_params.get("current_page")
    
    # STRICT: user_id is now mandatory - NO auto-generation
    if not user_id or not user_id.strip():
        logger.error("❌ Text WebSocket connection rejected: user_id parameter is required")
        await websocket.close(code=1008, reason="user_id parameter is required")
        return
    
    user_id = user_id.strip()
    
    if not current_page:
        current_page = "broadband"  # Default page instead of closing
    else:
        # Just normalize, don't reject
        current_page = current_page.strip().lower().replace(" ", "-").replace("_", "-")
    
    await websocket.accept()
    session_id = str(uuid.uuid4())
    
    logger.info(f"📝 Text WebSocket connected - User: {user_id}, Page: {current_page}")
    
    try:
        await run_text_conversation_bot(websocket, session_id, user_id, current_page)
    except Exception as e:
        logger.error(f"❌ Text bot error: {e}")
    finally:
        # End conversation session
        conversation_manager = get_conversation_manager()
        conversation_manager.end_session(user_id)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    google_key = os.getenv("GOOGLE_API_KEY")
    gemini_available = bool(google_key and google_key.startswith("AI"))

    # Get conversation statistics
    conversation_manager = get_conversation_manager()
    session_stats = conversation_manager.get_session_stats()

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "backend_url": get_backend_url(),
        "frontend_url": get_frontend_url(),
        "environment": {
            "mode": os.getenv("ENVIRONMENT", "development"),
            "ssl_enabled": True
        },
        "llm_service": {
            "provider": "Google Gemini",
            "available": gemini_available,
            "model": "gemini-2.5-flash"
        },
        "conversation_sessions": session_stats,
        "websockets": {
            "voice_conversation": f"{get_backend_url().replace('https://', 'wss://')}/voice/ws?user_id=your_user_id&current_page=broadband",
            "tools": f"{get_backend_url().replace('https://', 'wss://')}/voice/ws/tools?user_id=your_user_id",
            "text_conversation": f"{get_backend_url().replace('https://', 'wss://')}/voice/ws/text-conversation?user_id=your_user_id&current_page=broadband"
        },
        "endpoints": {
            "health": "/voice/health",
            "connect": "/voice/connect",
            "test_function_call": "/voice/test-function-call"
        }
    }


@router.post("/connect")
async def bot_connect(request: Request):
    """Connect endpoint for frontend."""
    user_id = None
    current_page = None
    
    # Try to get parameters from query first
    query_params = request.query_params
    user_id = query_params.get("user_id")
    current_page = query_params.get("current_page", "broadband")
    
    # Try to get from body if not in query
    if not user_id:
        try:
            body = await request.json()
            user_id = body.get("user_id")
            current_page = body.get("current_page", current_page)
        except:
            pass
    
    # STRICT: user_id is now mandatory - NO auto-generation
    if not user_id or not user_id.strip():
        return {
            "error": "user_id parameter is required",
            "message": "Please provide a valid user_id parameter",
            "status": "error"
        }
    
    user_id = user_id.strip()
    
    # Normalize current_page
    current_page = current_page.lower().replace(" ", "-").replace("_", "-")
    
    backend_url = get_backend_url()
    ws_base_url = backend_url.replace("https://", "wss://").replace("http://", "ws://")
    
    return {
        "ws_url": f"{ws_base_url}/voice/ws?user_id={user_id}&current_page={current_page}",
        "user_id": user_id,
        "current_page": current_page,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "backend_url": backend_url,
        "status": "success"
    }


@router.get("/test-function-call")
async def test_function_call():
    """Test function calling capabilities."""
    try:
        # Test if we can create agent manager with tools
        agent_manager = create_agent_manager()
        tool_definitions = agent_manager.get_tool_definitions()
        
        return {
            "message": "Function calling is available",
            "tool_available": True,
            "tools_count": len(tool_definitions),
            "tools": [tool.name for tool in tool_definitions],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Function call test failed: {e}")
        return {
            "message": f"Function call test failed: {str(e)}",
            "tool_available": False,
            "timestamp": datetime.now().isoformat()
        }


# Memory management endpoints
@router.get("/memory/{user_id}")
async def get_user_memory(user_id: str, current_page: str = "broadband"):
    """Get memory for a specific user."""
    agent_key = f"{user_id}_{current_page}"
    if agent_key not in user_text_agents:
        return {"memory": [], "message": "No memory found for user"}
    
    text_agent = user_text_agents[agent_key]
    memory_data = await text_agent.get_memory()
    return {"memory": memory_data, "user_id": user_id, "current_page": current_page}


@router.delete("/memory/{user_id}")
async def clear_user_memory(user_id: str, current_page: str = "broadband"):
    """Clear memory for a specific user."""
    agent_key = f"{user_id}_{current_page}"
    if agent_key not in user_text_agents:
        return {"message": f"No memory found for user {user_id} on page {current_page}"}
    
    text_agent = user_text_agents[agent_key]
    success = await text_agent.clear_memory()
    
    if success:
        return {"message": f"Memory cleared for user {user_id} on page {current_page}"}
    else:
        return {"error": f"Failed to clear memory for user {user_id}"}


@router.post("/memory/{user_id}/save")
async def save_user_memory(user_id: str, current_page: str = "broadband"):
    """Save memory for a specific user."""
    agent_key = f"{user_id}_{current_page}"
    if agent_key not in user_text_agents:
        user_text_agents[agent_key] = create_text_agent(user_id, current_page)
        await user_text_agents[agent_key].initialize()
    
    text_agent = user_text_agents[agent_key]
    if hasattr(text_agent, 'save_memory'):
        memory_data = await text_agent.save_memory()
        return memory_data
    else:
        # For agents without save_memory, return memory directly
        memory = await text_agent.get_memory()
        return {"memory": memory, "user_id": user_id, "current_page": current_page}


@router.post("/memory/{user_id}/load")
async def load_user_memory(user_id: str, memory_data: dict, current_page: str = "broadband"):
    """Load memory for a specific user."""
    agent_key = f"{user_id}_{current_page}"
    if agent_key not in user_text_agents:
        user_text_agents[agent_key] = create_text_agent(user_id, current_page)
        await user_text_agents[agent_key].initialize()
    
    text_agent = user_text_agents[agent_key]
    if hasattr(text_agent, 'load_memory'):
        success = await text_agent.load_memory(memory_data.get("memory", []))
        
        if success:
            return {"message": f"Memory loaded for user {user_id} on page {current_page}"}
        else:
            return {"error": f"Failed to load memory for user {user_id}"}
    else:
        return {"error": "Agent does not support memory loading"}


@router.delete("/text-agent/{user_id}")
async def cleanup_text_agent(user_id: str, current_page: str = None):
    """Clean up text agent for a specific user."""
    if current_page:
        # Clean up specific page agent
        agent_key = f"{user_id}_{current_page}"
        if agent_key in user_text_agents:
            text_agent = user_text_agents[agent_key]
            if hasattr(text_agent, 'save_memory'):
                await text_agent.save_memory()
            del user_text_agents[agent_key]
            return {"message": f"Text agent cleaned up for user {user_id} on page {current_page}"}
        else:
            return {"error": f"No text agent found for user {user_id} on page {current_page}"}
    else:
        # Clean up all agents for this user
        cleaned_count = 0
        keys_to_delete = [key for key in user_text_agents.keys() if key.startswith(f"{user_id}_")]
        for key in keys_to_delete:
            text_agent = user_text_agents[key]
            if hasattr(text_agent, 'save_memory'):
                await text_agent.save_memory()
            del user_text_agents[key]
            cleaned_count += 1
        
        if cleaned_count > 0:
            return {"message": f"Cleaned up {cleaned_count} text agents for user {user_id}"}
        else:
            return {"error": f"No text agents found for user {user_id}"}


# Create and configure FastAPI app
def create_app():
    """Create and configure the FastAPI application."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(
        title="Agent Voice Backend",
        description="Voice agent backend with /voice prefix endpoints",
        version="1.0.0"
    )
    
    # Configure CORS - allow both HTTP and HTTPS for development
    frontend_url = get_frontend_url()
    allowed_origins = [
        frontend_url,
        "http://localhost:3000",
        "https://localhost:3000",
        "http://localhost:3001",
        "https://localhost:3001"
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include voice router with /voice prefix
    app.include_router(router, prefix="/voice")
    
    # Include auth store router
    app.include_router(auth_store_router, prefix="/voice/auth")

    # Initialize services on startup
    @app.on_event("startup")
    async def startup_event():
        """Initialize all services on startup."""
        # Initialize conversation manager
        conversation_manager = get_conversation_manager()

        # Initialize fuzzy postal code search (global instance)
        try:
            from fuzzy_postal_code import FastPostalCodeSearch
            CONNECTION_STRING = "postgresql://postgres.jluuralqpnexhxlcuewz:HIiamjami1234@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
            global fuzzy_searcher
            fuzzy_searcher = FastPostalCodeSearch(CONNECTION_STRING)
            logger.info("✅ Fuzzy postal code search initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize fuzzy postal code search: {e}")
            fuzzy_searcher = None

        logger.info("🚀 Starting conversation cleanup task")

        async def cleanup_task():
            """Periodic cleanup of inactive conversations."""
            while True:
                try:
                    conversation_manager.cleanup_inactive_sessions()
                    stats = conversation_manager.get_session_stats()
                    logger.debug(f"🧹 Conversation cleanup completed. Active sessions: {stats['total_active_sessions']}")
                    await asyncio.sleep(300)  # Clean up every 5 minutes
                except Exception as e:
                    logger.warning(f"⚠️ Conversation cleanup failed: {e}")
                    await asyncio.sleep(60)  # Retry in 1 minute on error

        # Start cleanup task
        asyncio.create_task(cleanup_task())

    # Shutdown event handler
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        if 'fuzzy_searcher' in globals() and fuzzy_searcher:
            try:
                fuzzy_searcher.shutdown()
                logger.info("✅ Fuzzy postal code search shutdown")
            except Exception as e:
                logger.error(f"⚠️ Error shutting down fuzzy search: {e}")

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    # Run the server
    logger.info("🚀 Starting FastAPI server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8200,
        ssl_keyfile="./frontend/certificates/localhost-key.pem",
        ssl_certfile="./frontend/certificates/localhost.pem",
        log_level="info"
    )