# LangChain Tool Adapter Implementation

## Overview

This document describes the implementation of a unified tool adapter that allows the LangChain text agent to use the same modular page-specific tools as the Pipecat voice agent.

## Problem Statement

Previously:
- **Voice Agent (Pipecat)**: Used `AgentManager` to route function calls to page-specific tools (`DashboardTool`, `UsersTool`, `RolesTool`, etc.)
- **Text Agent (LangChain)**: Had its own mock tools that didn't integrate with the actual tool structure

This created code duplication and inconsistent behavior between voice and text agents.

## Solution Architecture

### 1. **ModularToolAdapter** (LangChain BaseTool)

A unified LangChain tool that wraps the entire modular tool structure and routes calls through `AgentManager`.

**Location:** `voice_agent/core/text_agent.py`

**Key Features:**
- Implements LangChain's `BaseTool` interface
- Maintains reference to `AgentManager` for tool routing
- Supports page-aware context
- Routes all actions to appropriate page-specific tools
- Returns the same structured output as voice agent tools

**Signature:**
```python
class ModularToolAdapter(BaseTool):
    name: str = "page_action"
    description: str = "Execute actions on different pages..."
    user_id: str
    callback_handler: Optional[Any]
    agent_manager: Optional[Any]
    current_page: str
    
    async def _arun(
        self, 
        action_type: str,
        target: str = None,
        context: str = None,
        **kwargs
    ) -> str:
        # Routes to agent_manager.handle_function_call()
```

### 2. **Tool Routing Logic**

The adapter uses `_determine_function_name()` to map actions to the correct page-specific function:

```python
page_function_map = {
    "dashboard": "dashboard_action",
    "users": "users_action",
    "roles": "roles_action",
    "database-query": "database_query_action",
    "database-query-results": "database_query_action",
    "company-structure": "company_structure_action",
    "tables": "tables_action",
    "file-query": "file_query_action",
    "history": "history_action",
    "profile": "profile_action",
}
```

**Navigation actions** always route through `dashboard_action`, while other actions route based on the current page context.

### 3. **Factory Function**

`create_langchain_tools_from_agent_manager()` creates LangChain-compatible tools from the modular structure:

**Location:** `voice_agent/core/text_agent.py`

```python
def create_langchain_tools_from_agent_manager(
    user_id: str, 
    callback_handler=None, 
    current_page: str = "dashboard"
):
    # Creates AgentManager instance
    # Returns list of LangChain tools (currently just ModularToolAdapter)
```

### 4. **Updated LangChainTextAgent**

**Location:** `voice_agent/core/text_agent.py`

**Changes:**
- Added `current_page` parameter to `__init__`
- Added `agent_manager` instance variable
- Updated `initialize()` to:
  - Create `AgentManager` for tool routing
  - Use `create_langchain_tools_from_agent_manager()` instead of mock tools
  - Get page-aware system instruction from agent_manager
  - Increase max_iterations to 5 for complex interactions

**Example:**
```python
class LangChainTextAgent:
    def __init__(self, user_id: str, current_page: str = "dashboard"):
        self.user_id = user_id
        self.current_page = current_page
        self.agent_manager = None  # Created during initialization
        # ...
    
    async def initialize(self):
        # Create agent manager
        self.agent_manager = create_agent_manager(current_page=self.current_page)
        
        # Create tools from modular structure
        tools = create_langchain_tools_from_agent_manager(
            user_id=self.user_id,
            callback_handler=self.callback_handler,
            current_page=self.current_page
        )
        
        # Get page-aware system instruction
        system_instruction = self.agent_manager.get_system_instruction_with_page_context(self.user_id)
        # ...
```

### 5. **Router Updates**

**Location:** `voice_agent/core/router.py`

**Changes:**
- Text agents are now keyed by `f"{user_id}_{current_page}"` to support page-specific contexts
- All endpoints updated to accept `current_page` parameter
- Agent creation uses `create_text_agent(user_id, current_page)`
- Memory management endpoints updated to support page-specific agents

**Updated Endpoints:**
```python
# Text conversation WebSocket
@router.websocket("/ws/text-conversation")
async def text_conversation_websocket_endpoint(websocket: WebSocket):
    # Creates agent with current_page context
    agent = create_text_agent(user_id, current_page)

# Memory management
@router.get("/memory/{user_id}")
async def get_user_memory(user_id: str, current_page: str = "dashboard"):
    # Uses page-specific agent key

@router.delete("/memory/{user_id}")
async def clear_user_memory(user_id: str, current_page: str = "dashboard"):
    # Uses page-specific agent key

@router.post("/memory/{user_id}/save")
async def save_user_memory(user_id: str, current_page: str = "dashboard"):
    # Uses page-specific agent key

@router.post("/memory/{user_id}/load")
async def load_user_memory(user_id: str, memory_data: dict, current_page: str = "dashboard"):
    # Uses page-specific agent key

@router.delete("/text-agent/{user_id}")
async def cleanup_text_agent(user_id: str, current_page: str = None):
    # Can clean up specific page agent or all agents for user
```

## Data Flow

### Voice Agent (Pipecat) Flow:
```
User speaks → Pipecat → Gemini Live → Function Call 
→ AgentManager.handle_function_call() 
→ Page-specific Tool.execute() 
→ WebSocket message sent 
→ Returns result string
```

### Text Agent (LangChain) Flow:
```
User types → LangChain Agent → Gemini 2.5 Flash → Tool Call
→ ModularToolAdapter._arun()
→ AgentManager.handle_function_call()
→ Page-specific Tool.execute()
→ WebSocket message sent
→ Returns result string
→ LangChain formats response
```

**Key Point:** Both flows converge at `AgentManager.handle_function_call()` and use the **same page-specific tools**.

## Benefits

1. **No Code Duplication**: Both voice and text agents use the same tools
2. **Consistent Behavior**: Same logic, same output format, same WebSocket messages
3. **Single Source of Truth**: Tool implementations only exist in `/tools/` directory
4. **Easy Maintenance**: Update tools once, affects both agents
5. **Page Awareness**: Both agents understand page context
6. **Unified WebSocket Communication**: Both send structured output via WebSocket

## Tool Capabilities

All page-specific tools are now available to the text agent:

- **DashboardTool**: Navigation, overview, status checks
- **UsersTool**: User access management, MSSQL/Vector DB access
- **RolesTool**: Role management, assignment, permissions
- **DatabaseQueryTool**: Natural language database queries
- **CompanyStructureTool**: Organization hierarchy management
- **TablesTool**: Database table operations
- **FileQueryTool**: File search and upload
- **HistoryTool**: Query history viewing
- **ProfileTool**: User profile and configuration

## Testing

### Test Text Agent Connection:
```bash
# Connect to text conversation WebSocket
wscat -c "wss://your-backend/voice/ws/text-conversation?user_id=test_user&current_page=dashboard"

# Send a message
{"message": "Navigate to users page"}
```

### Test Tool Execution:
```bash
# The text agent should now:
# 1. Parse your message with LangChain
# 2. Call ModularToolAdapter
# 3. Route through AgentManager
# 4. Execute UsersTool or appropriate tool
# 5. Send WebSocket message with structured output
# 6. Return natural language response
```

### Verify Memory Management:
```bash
# Get memory
curl https://your-backend/voice/memory/test_user?current_page=dashboard

# Clear memory
curl -X DELETE https://your-backend/voice/memory/test_user?current_page=dashboard
```

## Migration Notes

### For Existing Code:
- No changes needed to existing tools
- No changes needed to voice agent flow
- Text agent now uses real tools instead of mocks

### For New Tools:
1. Create tool in `/tools/` directory
2. Inherit from `BaseTool`
3. Implement `get_tool_definition()` and `execute()`
4. Add factory function
5. Register in `tools/__init__.py`
6. Add to `agent_manager.py` page_tools mapping
7. **Both voice and text agents will automatically have access**

## Troubleshooting

### Issue: LangChain tool not calling the right page tool
- **Solution**: Check `_determine_function_name()` mapping in `ModularToolAdapter`
- **Check**: Current page is being passed correctly to agent
- **Verify**: `agent_manager.update_current_page()` is called when page changes

### Issue: WebSocket messages not being sent
- **Solution**: Ensure tool WebSocket is connected via `/ws/tools`
- **Check**: `callback_handler` is passed to `ModularToolAdapter`
- **Verify**: `send_websocket_message()` in `BaseTool` is working

### Issue: Different output format between voice and text
- **Solution**: This shouldn't happen - both use the same tools
- **Check**: Both are routing through `AgentManager.handle_function_call()`
- **Verify**: Same tool instance is being called

## Future Enhancements

1. **Add more specialized tools** as separate LangChain tools alongside `ModularToolAdapter`
2. **Implement tool result caching** for repeated queries
3. **Add tool usage analytics** to track which tools are most used
4. **Implement tool chaining** for complex multi-step operations
5. **Add tool execution history** per user session

## Conclusion

The LangChain Tool Adapter successfully unifies the tool architecture between voice and text agents, eliminating code duplication and ensuring consistent behavior across both interaction modes.

**No more separate tool implementations needed!** 🎉
