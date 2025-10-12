#!/usr/bin/env python3
"""
Unified Conversation Manager for Langfuse session and user ID management.
Ensures each user has one conversation session with proper trace consolidation.
"""

import uuid
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger

from ..utils.langfuse_tracing import get_langfuse_tracer


@dataclass
class ConversationSession:
    """Represents a unified conversation session for a user."""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    trace_id: Optional[str] = None
    trace: Optional[Any] = None  # The actual trace object for ending
    conversation_type: str = "unified"  # unified, voice, text
    current_page: str = "broadband"
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0
    is_active: bool = True

    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()

    def increment_message_count(self):
        """Increment the message count."""
        self.message_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "trace_id": self.trace_id,
            "conversation_type": self.conversation_type,
            "current_page": self.current_page,
            "metadata": self.metadata,
            "message_count": self.message_count,
            "is_active": self.is_active
        }


class ConversationManager:
    """Unified conversation manager for session and trace management."""

    _instance: Optional['ConversationManager'] = None
    _sessions: Dict[str, ConversationSession] = {}  # user_id -> session
    _user_sessions: Dict[str, str] = {}  # user_id -> session_id

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.langfuse_tracer = get_langfuse_tracer()
        logger.info("✅ ConversationManager initialized")

    def get_or_create_session(self, user_id: str, conversation_type: str = "unified", current_page: str = "broadband") -> ConversationSession:
        """
        Get existing session for user or create a new one.
        Ensures only one active session per user.
        """
        # Check if user already has an active session
        if user_id in self._user_sessions:
            session_id = self._user_sessions[user_id]
            if session_id in self._sessions:
                session = self._sessions[session_id]
                if session.is_active:
                    # Update session activity and page
                    session.update_activity()
                    session.current_page = current_page
                    session.conversation_type = conversation_type
                    logger.info(f"🔄 Reusing existing session {session_id} for user {user_id}")
                    return session

        # Create new session
        session_id = str(uuid.uuid4())
        now = datetime.now()

        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_activity=now,
            conversation_type=conversation_type,
            current_page=current_page,
            metadata={"created_by": conversation_type}
        )

        # Create Langfuse trace for this session
        trace = self._create_conversation_trace(session)
        if trace:
            session.trace_id = getattr(trace, 'id', None) or session_id
            session.trace = trace  # Store the actual trace object

        # Store session
        self._sessions[session_id] = session
        self._user_sessions[user_id] = session_id

        logger.info(f"🆕 Created new conversation session {session_id} for user {user_id} (type: {conversation_type})")
        return session

    def _create_conversation_trace(self, session: ConversationSession) -> Optional[Any]:
        """Create a unified conversation trace for the session."""
        if not self.langfuse_tracer.is_enabled():
            return None

        try:
            trace = self.langfuse_tracer.create_trace(
                name=f"User Conversation - {session.user_id}",
                session_id=session.session_id,
                user_id=session.user_id,
                input_data={
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "conversation_type": session.conversation_type,
                    "current_page": session.current_page,
                    "created_at": session.created_at.isoformat()
                },
                metadata={
                    "conversation_type": session.conversation_type,
                    "current_page": session.current_page,
                    "created_by": "conversation_manager",
                    "is_unified_session": True
                }
            )

            if trace:
                logger.info(f"✅ Created unified conversation trace for session {session.session_id}")
            return trace

        except Exception as e:
            logger.warning(f"⚠️ Failed to create conversation trace: {e}")
            return None

    def get_session(self, user_id: str) -> Optional[ConversationSession]:
        """Get the active session for a user."""
        if user_id in self._user_sessions:
            session_id = self._user_sessions[user_id]
            session = self._sessions.get(session_id)
            if session and session.is_active:
                return session
        return None

    def get_session_by_id(self, session_id: str) -> Optional[ConversationSession]:
        """Get session by session ID."""
        return self._sessions.get(session_id)

    def update_session_activity(self, user_id: str, conversation_type: Optional[str] = None, current_page: Optional[str] = None):
        """Update session activity and metadata."""
        session = self.get_session(user_id)
        if session:
            session.update_activity()
            if conversation_type:
                session.conversation_type = conversation_type
            if current_page:
                session.current_page = current_page

    def increment_message_count(self, user_id: str):
        """Increment message count for user's session."""
        session = self.get_session(user_id)
        if session:
            session.increment_message_count()

    def end_session(self, user_id: str):
        """End the session for a user."""
        session = self.get_session(user_id)
        if session:
            session.is_active = False
            session.metadata["ended_at"] = datetime.now().isoformat()

            # End the Langfuse trace properly
            if session.trace and hasattr(session.trace, 'end'):
                try:
                    session.trace.end()
                    logger.info(f"🏁 Ended Langfuse trace for session {session.session_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to end Langfuse trace: {e}")

            # Update Langfuse trace with session end metadata
            if session.trace_id and self.langfuse_tracer.is_enabled():
                try:
                    self.langfuse_tracer._langfuse_client.update_current_span(
                        output={"session_ended": True, "total_messages": session.message_count},
                        metadata={"end_time": datetime.now().isoformat()}
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update Langfuse trace on session end: {e}")

            logger.info(f"🏁 Ended conversation session {session.session_id} for user {user_id}")

    def get_active_sessions(self) -> List[ConversationSession]:
        """Get all active sessions."""
        return [s for s in self._sessions.values() if s.is_active]

    def cleanup_inactive_sessions(self, max_age_minutes: int = 60):
        """Clean up sessions that haven't had activity for max_age_minutes."""
        now = datetime.now()
        to_remove = []

        for session_id, session in self._sessions.items():
            if not session.is_active:
                # Remove inactive sessions immediately
                to_remove.append(session_id)
            elif (now - session.last_activity).total_seconds() > (max_age_minutes * 60):
                # Mark old sessions as inactive
                session.is_active = False
                session.metadata["auto_ended_at"] = now.isoformat()
                logger.info(f"⏰ Auto-ended inactive session {session_id} for user {session.user_id}")

        for session_id in to_remove:
            user_id = self._sessions[session_id].user_id
            del self._sessions[session_id]
            if user_id in self._user_sessions and self._user_sessions[user_id] == session_id:
                del self._user_sessions[user_id]

        if to_remove:
            logger.info(f"🧹 Cleaned up {len(to_remove)} inactive sessions")

    def log_activity_to_trace(self, user_id: str, activity_type: str, data: Dict[str, Any]):
        """Log activity to the user's conversation trace."""
        session = self.get_session(user_id)
        if not session:
            return

        if not self.langfuse_tracer.is_enabled():
            return

        try:
            # Create a child span for this activity using TraceContext
            from langfuse.types import TraceContext

            trace_context = TraceContext(
                session_id=session.session_id,
                user_id=user_id
            )

            # Create a span as part of this trace
            activity_span = self.langfuse_tracer._langfuse_client.start_span(
                name=f"activity_{activity_type}",
                trace_context=trace_context,
                input=data,
                metadata={
                    "activity_type": activity_type,
                    "user_id": user_id,
                    "session_id": session.session_id,
                    "timestamp": datetime.now().isoformat()
                }
            )

            if activity_span:
                activity_span.end()
                logger.debug(f"📊 Logged {activity_type} activity to trace for session {session.session_id}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to log activity to trace: {e}")

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions."""
        active_sessions = self.get_active_sessions()
        return {
            "total_active_sessions": len(active_sessions),
            "total_users": len(set(s.user_id for s in active_sessions)),
            "sessions_by_type": {
                "unified": sum(1 for s in active_sessions if s.conversation_type == "unified"),
                "voice": sum(1 for s in active_sessions if s.conversation_type == "voice"),
                "text": sum(1 for s in active_sessions if s.conversation_type == "text")
            },
            "total_messages": sum(s.message_count for s in active_sessions)
        }


# Global instance
_conversation_manager = None

def get_conversation_manager() -> ConversationManager:
    """Get the global conversation manager instance."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
