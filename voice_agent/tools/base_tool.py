#!/usr/bin/env python3
"""
Base tool class for all tools to follow the same WebSocket communication pattern.
Enhanced with better error handling and configuration support.
"""

import json
import re
from typing import Dict, Any, Optional
from datetime import datetime
from pipecat.processors.frameworks.rtvi import RTVIProcessor, RTVIServerMessageFrame
from pipecat.frames.frames import Frame, LLMMessagesAppendFrame
from pipecat.adapters.schemas.function_schema import FunctionSchema
from loguru import logger


class BaseTool:
    """Base tool class with standard WebSocket communication and enhanced functionality."""
    
    def __init__(self, rtvi_processor: RTVIProcessor, task=None, initial_current_page: str = "broadband"):
        self.rtvi = rtvi_processor
        self.task = task
        self.initial_current_page = initial_current_page
        self.user_sessions: Dict[str, Dict[str, Any]] = {}

    def _clean_string_for_fuzzy_matching(self, text: str) -> str:
        """
        Clean string for fuzzy matching by:
        - Converting to lowercase (case insensitive)
        - Removing all non-alphabetic characters (special chars, numbers, etc.)
        - Keeping only letters a-z

        Examples:
        "John_Doe@123" -> "johndoe"
        "Test.User-Name" -> "testusername"
        "admin_user@test.com" -> "adminusertestcom"
        """
        if not text:
            return ""

        # Convert to lowercase
        cleaned = text.lower()

        # Remove all non-alphabetic characters (keep only a-z)
        cleaned = re.sub(r'[^a-z]', '', cleaned)

        return cleaned
        
    def get_tool_definition(self) -> FunctionSchema:
        """Get the tool definition for the LLM using Pipecat's FunctionSchema."""
        raise NotImplementedError("Subclasses must implement get_tool_definition")
    
    async def execute(self, **kwargs) -> str:
        """Execute the tool action."""
        raise NotImplementedError("Subclasses must implement execute")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
    
    def _initialize_user_session(self, user_id: str) -> Dict[str, Any]:
        """Initialize user session if not exists."""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "current_page": self.initial_current_page,
                "previous_page": None,
                "interaction_history": [],
                "last_activity": self._get_timestamp()
            }
        return self.user_sessions[user_id]
    
    def _update_user_session(self, user_id: str, action: str, details: Dict[str, Any]) -> None:
        """Update user session with new interaction."""
        session = self._initialize_user_session(user_id)
        session["interaction_history"].append({
            "action": action,
            "details": details,
            "timestamp": self._get_timestamp()
        })
        session["last_activity"] = self._get_timestamp()
    
    def get_user_current_page(self, user_id: str) -> str:
        """Get current page for a user."""
        session = self._initialize_user_session(user_id)
        return session.get("current_page", self.initial_current_page)
    
    def set_user_current_page(self, user_id: str, page: str) -> None:
        """Set current page for a user."""
        session = self._initialize_user_session(user_id)
        session["previous_page"] = session.get("current_page")
        session["current_page"] = page
    
    def _create_structured_output(self, user_id: str, action_type: str, param: str, value: str,
                                 interaction_type: str, **additional_fields) -> Dict[str, Any]:
        """Create standardized structured output for WebSocket communication."""
        session = self._initialize_user_session(user_id)

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

        # Add default fields for compatibility
        default_fields = {
            "clicked": False,
            "element_name": None,
            "search_query": None,
            "report_request": None,
            "report_query": None,
            "upload_request": None,
            "db_id": None,
            "table_specific": False,
            "tables": [],
            "file_descriptions": [],
            "table_names": [],
            "context": None
        }

        # Merge with additional fields (additional fields override defaults)
        merged_output = {**base_output, **default_fields, **additional_fields}

        # Convert list/dict values to JSON strings, but keep specific fields as proper JSON objects
        json_object_fields = {
            "form_data", "edit_form_data", "selected_columns", "edited_fields",
            "search_results", "similar_roles", "options", "dropdown_options",
            "table_data", "validation", "form_validation", "action_data",
            "ui_state", "user_data", "role_assignment_data", "selected_role",
            "selected_item", "dropdown_data", "deleted_users", "not_found_users",
            "suggested_corrections", "usernames", "employee_data", "salary_generation_data",
            "shift_assignment_data", "selected_shift_type", "shift_types_data",
            "employee", "shift_data", "shift_type_data", "filter_state", "item_table",
            "item_data", "removed_item", "updated_item", "transfer_data", "pending_deletion",
            "supplier_form_data", "item_form_data",
            # Broadband tool fields
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
    
    async def send_websocket_message(self, message_type: str, action: str, data: Dict[str, Any]) -> bool:
        """Send a message to all connected WebSocket clients."""
        try:
            # Create command data for the frontend
            command_data = {
                "type": message_type,
                "action": action,
                "data": data
            }

            # Log the command for debugging
            logger.info(f"🔧 Sending {message_type} message: {json.dumps(command_data)}")

            # Log WebSocket message to trace for better observability
            try:
                from ..core.conversation_manager import get_conversation_manager

                # Get conversation manager to log WebSocket response
                conversation_manager = get_conversation_manager()

                # Extract user_id from the data being sent (most WebSocket messages include user_id)
                user_id = data.get("user_id") if isinstance(data, dict) else None

                # If no user_id in data, try to get from active sessions
                if not user_id:
                    active_sessions = conversation_manager.get_active_sessions()
                    if active_sessions:
                        user_id = active_sessions[0].user_id

                if user_id:
                    # Log the WebSocket message as a trace activity
                    conversation_manager.log_activity_to_trace(
                        user_id=user_id,
                        activity_type="websocket_response",
                        data={
                            "message_type": message_type,
                            "action": action,
                            "websocket_data": data,
                            "full_command": command_data,
                            "timestamp": self._get_timestamp(),
                            "source": "tool_websocket"
                        }
                    )
                    logger.debug(f"📊 Logged WebSocket response to trace for user {user_id}")
            except Exception as trace_error:
                logger.warning(f"⚠️ Failed to log WebSocket message to trace: {trace_error}")
            
            # Method 1: Send via tool WebSocket connections using the registry
            from ..core.websocket_registry import get_registry
            
            # Get the active registry instance
            registry = get_registry()
            
            # Get all tool websocket users from the active registry
            tool_users = list(registry.user_tool_websockets.keys())
            sent_count = 0
            
            logger.info(f"🔧 Available tool WebSocket users: {tool_users}")
            logger.info(f"🔧 Total tool WebSocket connections: {len(registry.user_tool_websockets)}")
            
            for user_id in tool_users:
                try:
                    websocket_data = registry.user_tool_websockets.get(user_id)
                    if websocket_data and websocket_data.get("websocket"):
                        websocket = websocket_data["websocket"]
                        await websocket.send_json(command_data)
                        sent_count += 1
                        logger.info(f"✅ {message_type} message sent to user {user_id}")
                    else:
                        logger.warning(f"⚠️ No WebSocket found for user {user_id}")
                except Exception as ws_error:
                    logger.error(f"❌ Failed to send {message_type} to user {user_id}: {ws_error}")
            
            if sent_count > 0:
                logger.info(f"✅ {message_type} message sent to {sent_count} users via WebSocket")
                return True
            else:
                logger.info(f"ℹ️ No tool WebSocket clients available for {message_type}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error sending {message_type} message: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def send_websocket_message_with_fallback(self, message_type: str, action: str, data: Dict[str, Any]) -> bool:
        """Send a message to WebSocket clients with RTVI fallback."""
        try:
            # Try WebSocket first
            success = await self.send_websocket_message(message_type, action, data)
            if success:
                return True
            
            # Fallback to RTVI
            command_data = {
                "type": message_type,
                "action": action,
                "data": data
            }
            
            rtvi_frame = RTVIServerMessageFrame(data=command_data)
            
            if self.task:
                await self.task.queue_frames([rtvi_frame])
                logger.info(f"✅ {message_type} message sent via task queue (fallback)")
                return True
            elif self.rtvi:
                await self.rtvi.push_frame(rtvi_frame)
                logger.info(f"✅ {message_type} message sent via RTVI processor (fallback)")
                return True
            else:
                logger.info(f"ℹ️ No task or RTVI processor available for {message_type}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending {message_type} message with fallback: {e}")
            return False
    
    def _validate_required_params(self, required_params: list, kwargs: dict) -> tuple[bool, str]:
        """Validate that all required parameters are present."""
        missing_params = [param for param in required_params if param not in kwargs or kwargs[param] is None]
        
        if missing_params:
            return False, f"Missing required parameters: {', '.join(missing_params)}"
        
        return True, "All required parameters present"
    
    async def _handle_error(self, user_id: str, error_message: str, action_type: str = "error") -> str:
        """Handle errors consistently across all tools."""
        error_output = self._create_structured_output(
            user_id=user_id,
            action_type="error",
            param="error",
            value=error_message,
            interaction_type="error",
            success=False,
            error_message=error_message
        )
        
        # Send error via WebSocket
        await self.send_websocket_message(
            message_type="tool_error",
            action="error",
            data=error_output
        )
        
        logger.error(f"❌ Tool error for user {user_id}: {error_message}")
        return error_message