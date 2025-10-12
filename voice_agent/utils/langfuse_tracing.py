#!/usr/bin/env python3
"""
Centralized Langfuse tracing utility for the voice agent system.
Provides unified tracing, metrics, and evaluation capabilities for both
LangChain text agents and Pipecat voice agents.
"""

import os
import time
import asyncio
from typing import Dict, Any, Optional, Union, List
from contextlib import contextmanager
from datetime import datetime

from loguru import logger

try:
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler
    from langfuse.types import TraceContext
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    logger.warning("⚠️ Langfuse not available, tracing disabled")

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    logger.warning("⚠️ OpenTelemetry not available, voice agent tracing disabled")


def setup_tracing(service_name: str, exporter=None, settings=None):
    """
    Set up OpenTelemetry tracing for Pipecat following official Langfuse documentation.

    Args:
        service_name: Name of the service for tracing
        exporter: Optional OTLP exporter (will create one if not provided)
        settings: Application settings containing Langfuse configuration
    """
    if not OPENTELEMETRY_AVAILABLE:
        logger.warning("⚠️ OpenTelemetry not available, cannot setup tracing")
        return None

    try:
        # Use provided settings or get default
        if settings is None:
            from voice_agent.config.settings import get_settings
            settings = get_settings()

        # Create resource with service information
        resource = Resource(attributes={
            "service.name": service_name,
            "service.version": "1.0.0"
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Create OTLP exporter if not provided and OTLP is enabled
        if exporter is None and settings.langfuse_enabled and settings.otel_exporter_otlp_endpoint:
            if not (settings.langfuse_public_key and settings.langfuse_secret_key):
                logger.warning("⚠️ Langfuse credentials not configured, cannot create OTLP exporter")
                return None

            try:
                exporter = OTLPSpanExporter(
                    endpoint=settings.otel_exporter_otlp_endpoint,
                    headers={"Authorization": settings.otel_exporter_otlp_headers}
                )
                logger.info(f"✅ OTLP exporter created for {settings.otel_exporter_otlp_endpoint}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to create OTLP exporter: {e}, continuing without OTLP export")
                exporter = None

        # Add span processor with error handling
        if exporter:
            try:
                span_processor = BatchSpanProcessor(exporter)
                provider.add_span_processor(span_processor)
                logger.info("✅ OTLP span processor added successfully")
            except Exception as e:
                logger.warning(f"⚠️ Failed to add OTLP span processor: {e}, continuing without OTLP export")
                exporter = None

        # Set the tracer provider
        trace.set_tracer_provider(provider)

        # Set environment variables for Pipecat to use
        if settings.langfuse_enabled:
            if settings.otel_exporter_otlp_endpoint:
                os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = settings.otel_exporter_otlp_endpoint
            if settings.otel_exporter_otlp_headers:
                os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = settings.otel_exporter_otlp_headers
            if settings.otel_exporter_otlp_endpoint:
                logger.info(f"✅ Set OTLP environment variables for Pipecat")

        logger.info(f"✅ OpenTelemetry tracing setup complete for service: {service_name}")
        return provider

    except Exception as e:
        logger.error(f"❌ Failed to setup OpenTelemetry tracing: {e}")
        return None


class LangfuseTracer:
    """Centralized Langfuse tracing utility."""

    _instance: Optional['LangfuseTracer'] = None
    _langfuse_client: Optional[Any] = None
    _otel_provider: Optional[Any] = None
    _tracer: Optional[Any] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        from voice_agent.config.settings import get_settings
        self.settings = get_settings()

        if self.settings.langfuse_enabled and LANGFUSE_AVAILABLE:
            self._initialize_langfuse()
        else:
            logger.info("🔧 Langfuse tracing disabled or not available")

        if self.settings.langfuse_enabled and OPENTELEMETRY_AVAILABLE:
            self._initialize_opentelemetry()
        else:
            logger.info("🔧 OpenTelemetry tracing disabled or not available")

    def _initialize_langfuse(self):
        """Initialize Langfuse client."""
        try:
            self._langfuse_client = Langfuse(
                secret_key=self.settings.langfuse_secret_key,
                public_key=self.settings.langfuse_public_key,
                host=self.settings.langfuse_host
            )
            logger.info("✅ Langfuse client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Langfuse client: {e}")
            self._langfuse_client = None

    def _initialize_opentelemetry(self):
        """Initialize OpenTelemetry for Pipecat tracing following official docs."""
        try:
            # Use the centralized setup function
            self._otel_provider = setup_tracing(
                service_name=self.settings.otel_service_name,
                settings=self.settings
            )

            if self._otel_provider:
                self._tracer = trace.get_tracer(__name__)
                logger.info("✅ OpenTelemetry initialized for Pipecat with Langfuse")
            else:
                logger.warning("⚠️ Failed to initialize OpenTelemetry provider")
                self._tracer = None

        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenTelemetry: {e}")
            self._tracer = None

    def is_enabled(self) -> bool:
        """Check if Langfuse tracing is enabled and available."""
        return (
            self.settings.langfuse_enabled and
            LANGFUSE_AVAILABLE and
            self._langfuse_client is not None
        )

    def create_trace(
        self,
        name: str,
        session_id: str,
        user_id: str,
        input_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Create a new trace for a conversation session using Langfuse SDK."""
        if not self.is_enabled():
            logger.debug("🔧 Langfuse tracing disabled, skipping trace creation")
            return None

        # Validate inputs
        if not name or not session_id or not user_id:
            logger.error("❌ Invalid parameters for trace creation")
            return None

        try:
            # Create a trace using Langfuse SDK - use start_span with TraceContext
            # Langfuse doesn't have a direct trace() method, but we can create spans with trace context
            trace_id = self._langfuse_client.create_trace_id()

            # Create trace context with session and user information
            trace_context = TraceContext(
                session_id=session_id,
                user_id=user_id
            )

            # Start a span as the root of this trace
            span = self._langfuse_client.start_span(
                name=name,
                trace_context=trace_context,
                input=input_data,
                metadata=metadata or {}
            )

            logger.debug(f"🔍 Created trace: {name} for session {session_id}")
            return span
        except Exception as e:
            logger.error(f"❌ Failed to create trace: {e}")
            return None

    def create_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span: Optional[Any] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Create a span within a trace."""
        if not self.is_enabled() or not self._tracer:
            return None

        try:
            if parent_span:
                span = self._tracer.start_span(name, context=parent_span.get_span_context())
            else:
                span = self._tracer.start_span(name)

            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)

            logger.debug(f"🔍 Created span: {name}")
            return span
        except Exception as e:
            logger.error(f"❌ Failed to create span: {e}")
            return None

    def create_langchain_callback_handler(self) -> Optional[Any]:
        """Create LangChain callback handler for automatic tracing."""
        if not self.is_enabled():
            return None

        try:
            return CallbackHandler()
        except Exception as e:
            logger.error(f"❌ Failed to create LangChain callback handler: {e}")
            return None

    def score_trace(
        self,
        trace_id: str,
        name: str,
        value: Union[float, int],
        data_type: str = "NUMERIC",
        comment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a score to a trace for evaluation using Langfuse SDK."""
        if not self.is_enabled():
            logger.debug("🔧 Langfuse tracing disabled, skipping score addition")
            return False

        # Validate inputs
        if not trace_id or not name:
            logger.error("❌ Invalid parameters for trace scoring")
            return False

        try:
            # Use create_score method to add score to specific trace
            self._langfuse_client.create_score(
                trace_id=trace_id,
                name=name,
                value=value,
                data_type=data_type,
                comment=comment,
                metadata=metadata or {}
            )
            logger.debug(f"📊 Added score {name}={value} to trace {trace_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to score trace: {e}")
            return False

    def flush(self):
        """Flush any pending traces."""
        if self._langfuse_client:
            try:
                self._langfuse_client.flush()
                logger.debug("🔄 Flushed Langfuse traces")
            except Exception as e:
                logger.error(f"❌ Failed to flush traces: {e}")


# Global tracer instance
_langfuse_tracer = None

def get_langfuse_tracer() -> LangfuseTracer:
    """Get the global Langfuse tracer instance."""
    global _langfuse_tracer
    if _langfuse_tracer is None:
        _langfuse_tracer = LangfuseTracer()
    return _langfuse_tracer


@contextmanager
def trace_conversation(
    name: str,
    session_id: str,
    user_id: str,
    input_data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
):
    """Context manager for tracing a conversation using Langfuse SDK."""
    tracer = get_langfuse_tracer()
    span = None

    try:
        span = tracer.create_trace(name, session_id, user_id, input_data, metadata)
        start_time = time.time()

        if span:
            # Update span with start time metadata using update_current_span
            tracer._langfuse_client.update_current_span(metadata={"start_time": start_time})

        yield span

    except Exception as e:
        logger.error(f"❌ Error in conversation trace: {e}")
        if span:
            # Update span with error using update_current_span
            tracer._langfuse_client.update_current_span(output={"error": str(e)})
            tracer.score_current_span("error_score", 1, "BINARY", "Error occurred")
        raise

    finally:
        if span:
            end_time = time.time()
            duration = end_time - start_time
            # Update span with final metadata using update_current_span
            tracer._langfuse_client.update_current_span(
                output={"duration_seconds": duration},
                metadata={"end_time": end_time}
            )
            span.end()


@contextmanager
def trace_function_call(
    function_name: str,
    trace_id: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
):
    """Context manager for tracing a function call."""
    tracer = get_langfuse_tracer()
    span = None

    try:
        span = tracer.create_span(
            f"function_call_{function_name}",
            trace_id=trace_id,
            attributes=attributes
        )
        start_time = time.time()

        yield span

    except Exception as e:
        logger.error(f"❌ Error in function call trace: {e}")
        if span:
            span.set_attribute("error", str(e))
        raise

    finally:
        if span:
            end_time = time.time()
            duration = end_time - start_time
            span.set_attribute("duration_seconds", duration)
            span.end()


async def trace_async_function_call(
    function_name: str,
    trace_id: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
):
    """Async context manager for tracing an async function call."""
    tracer = get_langfuse_tracer()
    span = None

    try:
        span = tracer.create_span(
            f"async_function_call_{function_name}",
            trace_id=trace_id,
            attributes=attributes
        )
        start_time = time.time()

        # For async operations, we'll use a context variable approach
        if span:
            span.set_attribute("start_time", start_time)

        yield span

    except Exception as e:
        logger.error(f"❌ Error in async function call trace: {e}")
        if span:
            span.set_attribute("error", str(e))
        raise

    finally:
        if span:
            end_time = time.time()
            duration = end_time - start_time
            span.set_attribute("duration_seconds", duration)
            span.end()


def log_api_call(
    tool_name: str,
    action: str,
    parameters: Dict[str, Any],
    result: Any,
    duration: float,
    success: bool = True,
    error_message: Optional[str] = None,
    trace_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Log an API/tool call for tracing and metrics."""
    tracer = get_langfuse_tracer()

    if not tracer.is_enabled():
        logger.debug("🔧 Langfuse tracing disabled, skipping API call logging")
        return

    # Validate inputs
    if not tool_name or not action:
        logger.error("❌ Invalid parameters for API call logging")
        return

    try:
        # Create a span for the API call
        span = tracer.create_span(
            f"api_call_{tool_name}_{action}",
            trace_id=trace_id,
            attributes={
                "tool.name": tool_name,
                "tool.action": action,
                "duration_seconds": duration,
                "success": success,
                "user.id": user_id,
                "session.id": session_id,
                **parameters
            }
        )

        if span:
            if success:
                span.set_attribute("result", str(result)[:1000])  # Truncate long results
            else:
                span.set_attribute("error_message", error_message or "Unknown error")

            span.end()

        logger.debug(f"📊 Logged API call: {tool_name}.{action} in {duration:.3f}s")

    except Exception as e:
        logger.error(f"❌ Failed to log API call: {e}")


def score_conversation_quality(
    trace_id: str,
    quality_score: float,
    feedback: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Score conversation quality for evaluation."""
    tracer = get_langfuse_tracer()

    if not tracer.is_enabled():
        return False

    return tracer.score_trace(
        trace_id=trace_id,
        name="conversation_quality",
        value=quality_score,
        data_type="NUMERIC",
        comment=feedback,
        metadata=metadata
    )


def calculate_response_quality_score(
    response_text: str,
    duration_seconds: float,
    tool_calls_count: int,
    success: bool = True,
    error_message: Optional[str] = None
) -> float:
    """Calculate a quality score for a response based on various metrics."""
    if not success:
        return 0.0

    # Base score
    score = 0.5

    # Length bonus (prefer responses that are not too short or too long)
    response_length = len(response_text)
    if 100 <= response_length <= 1000:
        score += 0.2
    elif response_length > 1000:
        score += 0.1
    elif response_length < 50:
        score += 0.05

    # Tool usage bonus (responses that use tools are generally more helpful)
    if tool_calls_count > 0:
        score += min(0.2, tool_calls_count * 0.05)

    # Duration penalty (very slow responses are bad)
    if duration_seconds > 10:
        score -= 0.1
    elif duration_seconds < 1:
        score += 0.05

    # Response variety bonus (longer responses tend to be more comprehensive)
    if response_length > 500:
        score += 0.1

    return min(1.0, max(0.0, score))


def calculate_api_call_success_rate(
    total_calls: int,
    successful_calls: int,
    average_duration: float
) -> Dict[str, float]:
    """Calculate API call success metrics."""
    if total_calls == 0:
        return {"success_rate": 1.0, "avg_duration": 0.0}

    success_rate = successful_calls / total_calls
    return {
        "success_rate": success_rate,
        "avg_duration": average_duration,
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "failed_calls": total_calls - successful_calls
    }


def extract_conversation_insights(
    messages: List[Dict[str, Any]],
    trace_id: str
) -> Dict[str, Any]:
    """Extract insights from conversation messages for evaluation."""
    if not messages:
        return {}

    insights = {
        "message_count": len(messages),
        "user_message_count": sum(1 for msg in messages if msg.get("role") == "user"),
        "assistant_message_count": sum(1 for msg in messages if msg.get("role") == "assistant"),
        "avg_response_length": 0,
        "question_count": 0,
        "command_count": 0
    }

    response_lengths = []
    for msg in messages:
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            response_lengths.append(len(str(content)))

        elif msg.get("role") == "user":
            content = str(msg.get("content", ""))
            # Simple heuristics for question vs command detection
            if "?" in content:
                insights["question_count"] += 1
            else:
                insights["command_count"] += 1

    if response_lengths:
        insights["avg_response_length"] = sum(response_lengths) / len(response_lengths)

    # Score the conversation based on insights
    conversation_score = min(1.0, 0.3 + (insights["message_count"] * 0.1) + (insights["question_count"] * 0.05))

    return {
        "insights": insights,
        "conversation_score": conversation_score,
        "trace_id": trace_id
    }
