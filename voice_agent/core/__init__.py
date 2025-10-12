#!/usr/bin/env python3
"""
Core package for agent voice backend.
Contains main system components including agent management, routing, and WebSocket handling.
"""

__version__ = "1.0.0"
__author__ = "Agent Team"

# Core module imports
from .agent_manager import AgentManager, create_agent_manager
from .text_agent import LangChainTextAgent, create_text_agent
from .websocket_registry import (
    register_tool_websocket,
    unregister_tool_websocket,
    get_tool_websocket,
    send_to_user_tool_websocket,
    register_session_user,
    unregister_session_user
)

__all__ = [
    "AgentManager",
    "create_agent_manager",
    "LangChainTextAgent",
    "create_text_agent",
    "register_tool_websocket",
    "unregister_tool_websocket",
    "get_tool_websocket",
    "send_to_user_tool_websocket",
    "register_session_user",
    "unregister_session_user"
]