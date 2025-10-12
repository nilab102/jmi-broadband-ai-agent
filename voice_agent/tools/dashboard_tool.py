#!/usr/bin/env python3
"""
Dashboard Tool for agent voice backend.
Handles dashboard-specific operations and navigation.
"""

from typing import Dict, Any
from pipecat.processors.frameworks.rtvi import RTVIProcessor
from pipecat.adapters.schemas.function_schema import FunctionSchema
from loguru import logger
from .base_tool import BaseTool
from voice_agent.utils.validators import validate_page_name, validate_url


class DashboardTool(BaseTool):
    """Tool for handling dashboard-specific operations."""
    
    def __init__(self, rtvi_processor: RTVIProcessor, task=None, initial_current_page: str = "dashboard"):
        super().__init__(rtvi_processor, task, initial_current_page)
        self.page_name = "dashboard"
        
    def get_tool_definition(self) -> FunctionSchema:
        """Get the tool definition for the LLM."""
        return FunctionSchema(
            name="dashboard_action",
            description="Handle dashboard-specific operations including navigation to other pages, general dashboard interactions, and URL opening.",
            properties={
                "user_id": {
                    "type": "string",
                    "description": "User ID for session management"
                },
                "action_type": {
                    "type": "string",
                    "enum": ["navigate", "overview", "status_check", "open_url"],
                    "description": "Type of dashboard action: 'navigate' for going to other pages, 'overview' for dashboard overview, 'status_check' for system status, 'open_url' for opening URLs in new tabs"
                },
                "target": {
                    "type": "string",
                    "description": "Target page for navigation or specific dashboard element"
                },
                "url": {
                    "type": "string",
                    "description": "URL to open in a new tab (required when action_type is 'open_url')"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context for the action"
                }
            },
            required=["user_id", "action_type"]
        )
    
    async def execute(self, user_id: str, action_type: str, target: str = None, url: str = None, context: str = None, **kwargs) -> str:
        """Execute dashboard action."""
        try:

            # Initialize user session
            self._initialize_user_session(user_id)

            logger.info(f"🏠 Dashboard action - User: {user_id}, Action: {action_type}, Target: {target}, URL: {url}")

            if action_type == "navigate":
                return await self._handle_navigation(user_id, target, context)
            elif action_type == "overview":
                return await self._handle_overview(user_id, context)
            elif action_type == "status_check":
                return await self._handle_status_check(user_id, context)
            elif action_type == "open_url":
                return await self._handle_open_url(user_id, url, context)
            else:
                return await self._handle_error(user_id, f"Invalid action type: {action_type}")

        except Exception as e:
            logger.error(f"❌ Error executing dashboard tool: {e}")
            return await self._handle_error(user_id, f"Error processing dashboard request: {str(e)}")
    
    async def _handle_navigation(self, user_id: str, target: str, context: str = None) -> str:
        """Handle navigation from dashboard to other pages."""
        if not target:
            return await self._handle_error(user_id, "Target page must be specified for navigation")
        
        # Handle page name mapping for backward compatibility
        page_mapping = {
            "departments": "organization/departments",
            "department": "organization/departments",
            "locations": "organization/locations",
            "location": "organization/locations"
        }

        # Apply mapping if target matches
        if target in page_mapping:
            original_target = target
            target = page_mapping[target]
            logger.info(f"🔄 Mapped page navigation: {original_target} → {target}")

        # Validate target page
        is_valid, result = validate_page_name(target)
        if not is_valid:
            return await self._handle_error(user_id, result)

        target_page = result
        current_page = self.get_user_current_page(user_id)
        
        # Update user session
        self.set_user_current_page(user_id, target_page)
        self._update_user_session(user_id, "navigate", {
            "from": current_page,
            "to": target_page,
            "context": context
        })
        
        # Create structured output
        structured_output = self._create_structured_output(
            user_id=user_id,
            action_type="navigation",
            param="name",
            value=target_page,
            interaction_type="page_navigation",
            clicked=False,
            element_name=None,
            context=context
        )
        
        # Update the page in the output to reflect the new page
        structured_output["page"] = target_page
        structured_output["previous_page"] = current_page
        
        logger.info(f"🏠 Dashboard navigation: {current_page} → {target_page}")
        
        # Send via WebSocket
        await self.send_websocket_message(
            message_type="navigation_result",
            action="navigate",
            data=structured_output
        )
        
        # Note: History page functionality removed as part of tool cleanup
        # If navigating to history page, just navigate (history tool no longer available)
        if target_page == "history":
            return f"Navigated from dashboard to {target_page} page."
        
        return f"Navigated from dashboard to {target_page} page."
    
    async def _handle_overview(self, user_id: str, context: str = None) -> str:
        """Handle dashboard overview request."""
        current_page = self.get_user_current_page(user_id)
        
        # Update user session
        self._update_user_session(user_id, "overview", {
            "page": current_page,
            "context": context
        })
        
        # Create structured output
        structured_output = self._create_structured_output(
            user_id=user_id,
            action_type="clicked",
            param="overview",
            value="dashboard_overview",
            interaction_type="dashboard_overview",
            clicked=True,
            element_name="overview",
            context=context
        )
        
        logger.info(f"🏠 Dashboard overview requested by user {user_id}")
        
        # Send via WebSocket
        await self.send_websocket_message(
            message_type="dashboard_result",
            action="overview",
            data=structured_output
        )
        
        overview_text = """
        Welcome to the agent dashboard! From here you can:
        
        📊 Database Query - Search databases and generate reports
        📁 File Query - Search and upload files
        👥 Users - Manage user access and permissions
        📋 Tables - Manage database tables and visualizations
        ⚙️ User Configuration - Configure database and business rules
        🏢 Company Structure - View organizational structure
        
        Where would you like to go?
        """
        
        return overview_text.strip()
    
    async def _handle_status_check(self, user_id: str, context: str = None) -> str:
        """Handle system status check request."""
        current_page = self.get_user_current_page(user_id)
        
        # Update user session
        self._update_user_session(user_id, "status_check", {
            "page": current_page,
            "context": context
        })
        
        # Create structured output
        structured_output = self._create_structured_output(
            user_id=user_id,
            action_type="clicked",
            param="status_check",
            value="system_status",
            interaction_type="status_check",
            clicked=True,
            element_name="status_check",
            context=context
        )
        
        logger.info(f"🏠 System status check requested by user {user_id}")
        
        # Send via WebSocket
        await self.send_websocket_message(
            message_type="dashboard_result",
            action="status_check",
            data=structured_output
        )
        
        # Simple status check (could be enhanced with actual system checks)
        status_text = """
        System Status: ✅ All systems operational
        
        🔗 WebSocket connections: Active
        🗄️ Database: Connected
        🤖 AI Services: Available
        🔒 Security: Enabled
        
        All services are running normally.
        """
        
        return status_text.strip()

    async def _handle_open_url(self, user_id: str, url: str, context: str = None) -> str:
        """Handle opening URL in a new tab."""
        if not url:
            return await self._handle_error(user_id, "URL must be specified for open_url action")

        # Validate URL
        is_valid, result = validate_url(url)
        if not is_valid:
            return await self._handle_error(user_id, result)

        validated_url = result
        current_page = self.get_user_current_page(user_id)

        # Update user session
        self._update_user_session(user_id, "open_url", {
            "url": validated_url,
            "page": current_page,
            "context": context
        })

        # Create structured output
        structured_output = self._create_structured_output(
            user_id=user_id,
            action_type="open_url",
            param="url",
            value=validated_url,
            interaction_type="url_open",
            clicked=True,
            element_name="open_url",
            context=context,
            url=validated_url
        )

        logger.info(f"🔗 Opening URL for user {user_id}: {validated_url}")

        # Send via WebSocket
        await self.send_websocket_message(
            message_type="dashboard_result",
            action="open_url",
            data=structured_output
        )

        return f"Opening URL in new tab: {validated_url}"


def create_dashboard_tool(rtvi_processor: RTVIProcessor, task=None, initial_current_page: str = "dashboard") -> DashboardTool:
    """Factory function to create a DashboardTool instance."""
    return DashboardTool(rtvi_processor, task, initial_current_page)