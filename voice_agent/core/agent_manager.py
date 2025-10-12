#!/usr/bin/env python3
"""
Enhanced Agent Manager for agent voice backend.
Handles tool registration, page awareness, and agent coordination with the new modular tool structure.
"""

import asyncio
from typing import Dict, Any, Optional, List
from loguru import logger
from pipecat.frames.frames import LLMMessagesAppendFrame
from pipecat.processors.frameworks.rtvi import RTVIProcessor

# Import configuration and utilities
from voice_agent.config.settings import get_settings, MSSQL_SEARCH_AI_SYSTEM_INSTRUCTION
from voice_agent.utils.validators import validate_page_name

# Import page-specific tools
from voice_agent.tools import (
    DashboardTool, BroadbandTool,
    create_dashboard_tool, create_broadband_tool
)


class AgentManager:
    """Enhanced agent manager with modular tool support and page awareness."""
    
    def __init__(self, rtvi_processor: RTVIProcessor = None, task=None, current_page: str = "dashboard"):
        self.rtvi_processor = rtvi_processor
        self.task = task
        self.settings = get_settings()
        
        # Tool registry and instances
        self.page_tools: Dict[str, Any] = {}
        self.tool_instances: Dict[str, Any] = {}
        self.tool_definitions: List[Any] = []
        
        # Page and session management
        self.current_page = current_page
        self.user_sessions: Dict[str, Dict[str, Any]] = {}

        # Langfuse tracing
        self.conversation_trace = None
        self.conversation_session_id = None

        # Initialize tools
        self._initialize_tools()
        
    def _initialize_tools(self):
        """Initialize all page-specific tools."""
        try:
            if not self.rtvi_processor:
                logger.warning("⚠️ No RTVI processor provided, creating mock processor")
                from pipecat.processors.frameworks.rtvi import RTVIProcessor, RTVIConfig
                self.rtvi_processor = RTVIProcessor(config=RTVIConfig(config=[]))
            
            # Create page-specific tools
            self.page_tools = {
                "dashboard": create_dashboard_tool(self.rtvi_processor, self.task, "dashboard"),
                "broadband": create_broadband_tool(self.rtvi_processor, self.task, "broadband"),
            }

            # Create tool instances mapping for backward compatibility
            self.tool_instances = {
                "dashboard_tool": self.page_tools["dashboard"],
                "broadband_tool": self.page_tools["broadband"],
            }
            
            # Get tool definitions for LLM
            self.tool_definitions = []
            for tool in self.page_tools.values():
                try:
                    definition = tool.get_tool_definition()
                    self.tool_definitions.append(definition)
                except Exception as e:
                    logger.error(f"❌ Error getting tool definition: {e}")
            
            logger.info(f"✅ Initialized {len(self.page_tools)} page-specific tools")
            logger.info(f"🔧 Available pages: {list(self.page_tools.keys())}")
            
        except Exception as e:
            logger.error(f"❌ Error initializing tools: {e}")
            raise
    
    def register_tools(self, tools: list, tool_instances: dict):
        """Register tools and their instances (for backward compatibility)."""
        # This method is kept for backward compatibility but the new structure
        # uses the _initialize_tools method instead
        logger.info(f"📝 Legacy tool registration called with {len(tools)} tools")
        
        # Update tool_instances if provided
        if tool_instances:
            self.tool_instances.update(tool_instances)
        
        logger.info(f"✅ Registered tools: {list(self.tool_instances.keys())}")
    
    def get_tools(self) -> dict:
        """Get tool instances."""
        return self.tool_instances
    
    def get_tool_definitions(self) -> list:
        """Get all tool definitions for LLM registration."""
        return self.tool_definitions
    
    def get_page_tool(self, page_name: str) -> Optional[Any]:
        """Get tool for specific page."""
        return self.page_tools.get(page_name)
    
    def get_available_pages(self) -> List[str]:
        """Get list of available pages."""
        return list(self.page_tools.keys())
    
    def update_current_page(self, page: str, user_id: str = None):
        """Update the current page for the agent."""
        # Validate page name
        is_valid, result = validate_page_name(page)
        if not is_valid:
            logger.error(f"❌ Invalid page name: {result}")
            return False
        
        self.current_page = result
        
        # Update user session if user_id provided
        if user_id:
            self._update_user_session(user_id, "page_change", {"new_page": result})
        
        logger.info(f"🔄 Updated agent current page to: {result}")
        return True
    
    def get_current_page(self, user_id: str = None) -> str:
        """Get the current page for the agent or specific user."""
        if user_id and user_id in self.user_sessions:
            return self.user_sessions[user_id].get("current_page", self.current_page)
        return self.current_page
    
    def _update_user_session(self, user_id: str, action: str, details: Dict[str, Any]):
        """Update user session with new interaction."""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "current_page": self.current_page,
                "interaction_history": [],
                "last_activity": None
            }
        
        session = self.user_sessions[user_id]
        session["interaction_history"].append({
            "action": action,
            "details": details,
            "timestamp": self._get_timestamp()
        })
        session["last_activity"] = self._get_timestamp()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_system_instruction_with_page_context(self, user_id: str = None) -> str:
        """Get system instruction with current page context."""
        current_page = self.get_current_page(user_id)
        base_instruction = MSSQL_SEARCH_AI_SYSTEM_INSTRUCTION
        
        # Add current page context to the system instruction
        page_context = f"""

## CURRENT PAGE CONTEXT:
You are currently on the **{current_page}** page.

### Current Page Details:
"""
        
        # Get page configuration from settings
        page_config = self.settings.page_configs.get(current_page, {})
        
        # Add specific page information
        page_context += f"""
- **Page**: {current_page}
- **Available Buttons**: {page_config.get('buttons', [])}
- **Features**: {self._get_page_features(current_page, page_config)}
- **Recommended Actions**: {self._get_page_recommendations(current_page, page_config)}
"""


        page_context += f"""

### IMPORTANT - PAGE AWARENESS:
- You are currently on the **{current_page}** page
- Consider this context when interpreting user requests
- Suggest appropriate actions based on the current page capabilities
- If user wants to perform actions not available on current page, suggest navigation first
- Always be aware of what page the user is currently on when providing assistance

### AVAILABLE TOOLS FOR CURRENT PAGE:
{self._get_page_tool_info(current_page)}

"""
        
        # Combine base instruction with page context
        updated_instruction = base_instruction + page_context
        
        logger.info(f"🔧 Updated system instruction with current page context: {current_page}")
        return updated_instruction
    
    def _get_page_features(self, page_name: str, page_config: Dict[str, Any]) -> str:
        """Get formatted features string for a page."""
        features = []
        
        if page_config.get("search_enabled"):
            features.append("Database search enabled")
        if page_config.get("file_search_enabled"):
            features.append("File search enabled")
        if page_config.get("file_upload_enabled"):
            features.append("File upload enabled")
        if page_config.get("navigation_enabled"):
            features.append("Navigation enabled")
        
        return ", ".join(features) if features else "Basic navigation"
    
    def _get_page_recommendations(self, page_name: str, page_config: Dict[str, Any]) -> str:
        """Get formatted recommendations string for a page."""
        recommendations = []
        
        if page_name == "dashboard":
            recommendations.append("Use 'navigate' to go to other pages")
        elif page_name == "users":
            recommendations.extend([
                "Use 'switch_tab' to switch between 'mssql' and 'vector' tabs",
                "Use 'click' for button interactions: add mssql access, add vector db access",
                "For MSSQL Access: 'update_mssql_form', 'confirm_mssql_form', 'create_mssql_access'",
                "For Vector DB Access: 'update_vector_form', 'confirm_vector_form', 'create_vector_access'",
                "Use dropdown functions: 'show_all_parent_companies', 'select_parent_company', 'show_all_databases', 'select_database'"
            ])
        elif page_name == "database-query":
            recommendations.extend([
                "Use 'click' for button interactions: report query, quick query",
                "Use 'update_query' to enter your natural language query",
                "Use 'execute_report_query' to run comprehensive report queries",
                "Use 'execute_quick_query' to run quick result queries"
            ])
        elif page_name == "database-query-results":
            recommendations.extend([
                "Use 'click' for button interactions: view result, table view, chart visualization",
                "Use 'view_results' to navigate to results page",
                "Use 'switch_to_table_view' to display results in table format",
                "Use 'switch_to_chart_view' to display results in chart format",
                "Use 'select_graph_type' to choose chart type (Bar, Line, Pie, Area)",
                "Use 'select_aggregation' to choose aggregation method (Sum, Count, Average)",
                "Use 'update_visualization' to change both graph type and aggregation"
            ])
        elif page_name == "profile":
            recommendations.extend([
                "Use 'switch_tab' to switch between 'overview', 'database', 'business_rules', 'report_structure' tabs",
                "For Overview tab: 'update_profile_form', 'confirm_profile_form', 'save_profile'",
                "For Database Selection: 'show_all_databases', 'search_databases', 'select_database', 'select_first_database'",
                "For Business Rules: 'show_business_rules', 'update_business_rules', 'save_business_rules'",
                "For Report Structure: 'show_report_structure', 'update_report_structure', 'save_report_structure'"
            ])

        else:
            buttons = page_config.get("buttons", [])
            if buttons:
                recommendations.append(f"Use 'click' for button interactions: {', '.join(buttons)}")
            else:
                recommendations.append("Use 'navigate' to go to other pages")
        
        return "\n  - ".join([""] + recommendations)
    
    def _get_page_tool_info(self, page_name: str) -> str:
        """Get tool information for the current page."""
        tool = self.page_tools.get(page_name)
        if tool:
            try:
                definition = tool.get_tool_definition()
                return f"- **{definition.name}**: {definition.description}"
            except Exception as e:
                logger.error(f"❌ Error getting tool definition for {page_name}: {e}")
                return f"- Tool available for {page_name} page operations"
        return "- No specific tool available for this page"
    
    async def handle_function_call(self, function_call):
        """Handle function calls by routing to appropriate page-specific tools."""
        function_name = function_call.name
        args = function_call.arguments
        
        logger.info(f"🔧 Agent Manager handling function: {function_name} with args: {args}")
        
        # Extract user_id for session management
        user_id = args.get("user_id", "unknown")
        
        
        # Route function calls to appropriate tools based on function name
        try:
            result = await self._route_function_call(function_name, args, user_id)
            
            logger.info(f"🔧 Function call result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error handling function call {function_name}: {e}")
            return f"Error processing {function_name}: {str(e)}"
    
    async def _route_function_call(self, function_name: str, args: Dict[str, Any], user_id: str) -> str:
        """Route function calls to appropriate page-specific tools."""
        
        # Function name to tool mapping
        function_tool_mapping = {
            "dashboard_action": "dashboard",
            "broadband_action": "broadband",

            # Legacy mapping for backward compatibility
            "navigate_page": self._handle_legacy_navigate_page
        }
        
        # Check if it's a direct tool function
        if function_name in function_tool_mapping:
            target = function_tool_mapping[function_name]
            
            # If it's a callable (legacy handler), call it
            if callable(target):
                return await target(args, user_id)
            
            # Otherwise, it's a page name - get the tool and execute
            tool = self.page_tools.get(target)
            if tool:
                return await tool.execute(**args)
            else:
                return f"Tool for page {target} not found"
        
        # If no direct mapping found, try to determine from current page or action type
        current_page = self.get_current_page(user_id)
        action_type = args.get("action_type", "")
        
        # Try to route based on action type and current page
        if action_type == "navigate":
            # Navigation can be handled by any page tool, use current page tool
            tool = self.page_tools.get(current_page)
            if tool and hasattr(tool, 'execute'):
                return await tool.execute(**args)
        
        # Fallback: try current page tool
        tool = self.page_tools.get(current_page)
        if tool:
            try:
                return await tool.execute(**args)
            except Exception as e:
                logger.error(f"❌ Error executing {current_page} tool: {e}")
        
        return f"Unknown function: {function_name}"
    
    async def _handle_legacy_navigate_page(self, args: Dict[str, Any], user_id: str) -> str:
        """Handle legacy navigate_page function calls by routing to appropriate tools."""
        action_type = args.get("action_type", "navigate")
        target = args.get("target", "")
        current_page = self.get_current_page(user_id)
        
        logger.info(f"🔧 Legacy navigate_page call: {action_type} -> {target} from {current_page}")
        
        # Route based on action type
        if action_type == "navigate":
            # Use dashboard tool for navigation (or current page tool)
            tool = self.page_tools.get("dashboard") or self.page_tools.get(current_page)
            if tool:
                # Convert to new format
                new_args = {
                    "user_id": user_id,
                    "action_type": "navigate",
                    "target": target,
                    "context": args.get("context")
                }
                return await tool.execute(**new_args)
        
        # Fallback to current page tool
        tool = self.page_tools.get(current_page)
        if tool:
            return await tool.execute(**args)
        
        return f"Could not route legacy function call: {action_type} -> {target}"


def create_agent_manager(rtvi_processor: RTVIProcessor = None, task=None, current_page: str = "dashboard") -> AgentManager:
    """Factory function to create an AgentManager instance."""
    return AgentManager(rtvi_processor, task, current_page)