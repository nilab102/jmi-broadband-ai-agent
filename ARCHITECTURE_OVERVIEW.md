# Architecture Overview - Refactored System

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │   Voice    │  │    Text    │  │    UI      │                │
│  │ Interface  │  │Conversation│  │ Components │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└─────────────────────────────────────────────────────────────────┘
                           │ WebSocket / HTTP
┌─────────────────────────────────────────────────────────────────┐
│                    Backend Router (FastAPI)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Voice & Text Endpoints                        │  │
│  │  /ws  |  /ws/text-conversation  |  /health  |  /connect   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
      ┌────────────────────┴────────────────────┐
      │                                         │
┌─────▼──────┐                          ┌──────▼──────┐
│Voice Agent │                          │ Text Agent  │
│  (Gemini   │                          │ (LangChain) │
│Multimodal) │                          │             │
└─────┬──────┘                          └──────┬──────┘
      │                                         │
      └────────────────────┬────────────────────┘
                           │
┌─────────────────────────▼─────────────────────────────────────┐
│                     Agent Manager                              │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │           Tool Registry & Function Routing               │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                           │
      ┌────────────────────┴────────────────────┐
      │                                         │
┌─────▼──────────┐                    ┌────────▼────────┐
│ Broadband Tool │                    │  Other Tools    │
│  (Enhanced)    │                    │   (Future)      │
└─────┬──────────┘                    └─────────────────┘
      │
      │ Uses
      │
┌─────▼──────────────────────────────────────────────────────────┐
│                   Services Layer (NEW) ⭐                       │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐     │
│  │ PostalCode    │  │   Scraper     │  │ URL Generator │     │
│  │   Service     │  │   Service     │  │    Service    │     │
│  └───────────────┘  └───────────────┘  └───────────────┘     │
│  ┌───────────────┐  ┌───────────────┐                         │
│  │Recommendation │  │   Database    │                         │
│  │   Service     │  │   Service     │                         │
│  └───────────────┘  └───────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
                           │
      ┌────────────────────┴────────────────────┐
      │                                         │
┌─────▼──────────┐                    ┌────────▼────────┐
│   External     │                    │   PostgreSQL    │
│   Websites     │                    │    Database     │
│ (JustMoveIn)   │                    │  (Supabase)     │
└────────────────┘                    └─────────────────┘
```

## Component Breakdown

### 1. Router Layer (`voice_agent/core/router.py`)

**Responsibilities**:
- Handle WebSocket connections
- Route requests to appropriate agents
- Manage sessions and user mappings
- Provide REST API endpoints

**Key Endpoints**:
- `/voice/ws` - Voice conversation WebSocket
- `/voice/ws/text-conversation` - Text conversation WebSocket  
- `/voice/ws/tools` - Tool execution WebSocket
- `/voice/health` - Health check
- `/voice/connect` - Connection info

**Changes**:
- ✨ Simplified by extracting voice agent logic
- ✅ Uses `create_voice_agent()` factory function
- ✅ Cleaner error handling

### 2. Voice Agent (`voice_agent/core/voice_agent.py`) ⭐ NEW

**Responsibilities**:
- Manage Gemini Multimodal Live LLM
- Handle voice pipeline (Pipecat)
- Process audio input/output
- Manage function calling
- Track conversation state

**Key Components**:
```python
class VoiceAgent:
    - __init__()           # Initialize agent
    - initialize()         # Setup pipeline & LLM
    - _create_gemini_llm() # Create LLM service
    - run()                # Run voice pipeline
```

**Event Handlers**:
- `on_llm_response` - Capture AI responses
- `on_function_call` - Handle tool calls
- `on_transcript_update` - Process STT input
- `on_client_connected/disconnected` - Connection events

### 3. Text Agent (`voice_agent/core/text_agent.py`)

**Responsibilities**:
- Manage LangChain-based text conversations
- Handle tool calling via LangChain
- Maintain conversation memory
- Process text messages

**Key Components**:
```python
class LangChainTextAgent:
    - initialize()          # Setup LangChain agent
    - process_message()     # Process text input
    - get_memory()          # Retrieve conversation history
    - clear_memory()        # Reset conversation
```

**Optimizations**:
- Broadband context management
- Smart caching
- Parameter auto-fill
- Query pre-processing

### 4. Agent Manager (`voice_agent/core/agent_manager.py`)

**Responsibilities**:
- Register and manage tools
- Route function calls to appropriate tools
- Provide system instructions
- Handle page context

**Key Methods**:
```python
class AgentManager:
    - register_tool()           # Add tool to registry
    - handle_function_call()    # Route and execute
    - get_tool_definitions()    # Get all tool schemas
    - update_current_page()     # Change page context
```

### 5. Services Layer ⭐ NEW

#### PostalCodeService (`services/postal_code_service.py`)

**Responsibilities**:
- Validate UK postcodes
- Fuzzy search for postcodes
- Auto-select best matches
- Normalize postcode format

**Key Methods**:
```python
class PostalCodeService:
    - validate_postcode()    # Check format
    - fuzzy_search()         # Find similar postcodes
    - get_best_match()       # Auto-select match
    - normalize_postcode()   # Format standardization
```

**Integration**:
- Wraps `fuzzy_postal_code.py`
- Singleton pattern
- Graceful fallbacks

#### ScraperService (`services/scraper_service.py`)

**Responsibilities**:
- Scrape broadband comparison websites
- Extract structured deal data
- Parse pricing and features
- Handle async operations

**Key Methods**:
```python
class ScraperService:
    - scrape_url_async()      # Async scraping
    - scrape_url_sync()       # Sync scraping
    - extract_deal_summary()  # Get metrics
    - get_cheapest_deal()     # Find best price
    - get_fastest_deal()      # Find best speed
```

**Integration**:
- Wraps `jmi_scrapper.py`
- Handles Playwright browser automation
- Mock responses on error

#### URLGeneratorService (`services/url_generator_service.py`)

**Responsibilities**:
- Generate comparison URLs
- Validate parameters
- Provide available options
- Parse URL parameters

**Key Methods**:
```python
class URLGeneratorService:
    - generate_url()           # Create URL
    - validate_parameters()    # Check params
    - get_available_speeds()   # List options
    - parse_url_parameters()   # Extract from URL
```

**Integration**:
- Wraps `broadband_url_generator.py`
- Parameter validation
- Fallback URL generation

#### RecommendationService (`services/recommendation_service.py`)

**Responsibilities**:
- Analyze deals
- Score based on criteria
- Generate recommendations
- Compare deals

**Key Methods**:
```python
class RecommendationService:
    - generate_recommendations() # Top N deals
    - compare_deals()            # Side-by-side
    - _calculate_deal_score()    # Scoring algorithm
```

**Scoring Algorithm**:
- Price (35%)
- Speed (30%)
- Contract (15%)
- Provider (10%)
- Features (10%)

#### DatabaseService (`services/database_service.py`)

**Responsibilities**:
- Database connections
- Query execution
- Postal code lookup
- Data insertion

**Key Methods**:
```python
class DatabaseService:
    - get_connection()        # DB connection
    - execute_query()         # Run SQL
    - get_postal_code()       # Lookup postcode
    - search_postal_codes()   # Search by pattern
    - insert_data()           # Insert records
```

**Integration**:
- Wraps `data_insert&search.py` functionality
- Connection pooling
- Error handling

### 6. Broadband Tool (`voice_agent/tools/broadband_tool.py`)

**Responsibilities**:
- Orchestrate broadband search workflow
- Extract parameters from natural language
- Manage conversation state
- Coordinate services

**Key Actions**:
- `query` - Process natural language queries
- `generate_url` - Create comparison URLs
- `get_recommendations` - AI recommendations
- `compare_providers` - Provider comparison
- `get_cheapest/fastest` - Find best deals
- `filter_data` - Apply filters
- `refine_search` - Modify parameters

**Uses Services**:
✅ `PostalCodeService` - Postcode validation
✅ `ScraperService` - Data scraping
✅ `URLGeneratorService` - URL generation
✅ `RecommendationService` - Deal analysis
✅ `DatabaseService` - Data storage

## Data Flow

### Voice Conversation Flow:

```
User Voice Input
    │
    ▼
WebSocket (/voice/ws)
    │
    ▼
Router.websocket_endpoint()
    │
    ▼
create_voice_agent()
    │
    ▼
VoiceAgent.initialize()
    │
    ├─► Create Gemini LLM
    ├─► Setup Pipeline
    └─► Register Tools
    │
    ▼
VoiceAgent.run()
    │
    ├─► Process Audio Input (STT)
    ├─► LLM Processing
    ├─► Function Call Detection
    │   │
    │   ▼
    │   AgentManager.handle_function_call()
    │   │
    │   ▼
    │   BroadbandTool.execute_action()
    │   │
    │   ├─► PostalCodeService.fuzzy_search()
    │   ├─► URLGeneratorService.generate_url()
    │   ├─► ScraperService.scrape_url_async()
    │   └─► RecommendationService.generate_recommendations()
    │   │
    │   ▼
    │   Return Results
    │
    ├─► Generate Response (TTS)
    └─► Send Audio Output
    │
    ▼
User Hears Response
```

### Text Conversation Flow:

```
User Text Input
    │
    ▼
WebSocket (/voice/ws/text-conversation)
    │
    ▼
Router.text_conversation_websocket_endpoint()
    │
    ▼
run_text_conversation_bot()
    │
    ▼
LangChainTextAgent.process_message()
    │
    ├─► LangChain Agent Processing
    ├─► Tool Call Detection
    │   │
    │   ▼
    │   AgentManager.handle_function_call()
    │   │
    │   ▼
    │   BroadbandTool.execute_action()
    │   │
    │   └─► [Same service flow as voice]
    │   │
    │   ▼
    │   Return Results
    │
    └─► Generate Text Response
    │
    ▼
User Receives Text Response
```

## Key Design Patterns

### 1. Singleton Pattern
Services use singleton pattern for efficient resource usage:
```python
_service = None

def get_service():
    global _service
    if _service is None:
        _service = Service()
    return _service
```

### 2. Factory Pattern
Agent creation uses factory functions:
```python
async def create_voice_agent(user_id, session_id, websocket, page):
    agent = VoiceAgent(user_id, session_id, page)
    await agent.initialize(websocket)
    return agent
```

### 3. Service Layer Pattern
Business logic separated into services:
- Clear interfaces
- Reusable components
- Easy to test
- Loose coupling

### 4. Observer Pattern
Event handlers for async communication:
- LLM response events
- Function call events
- Transcript update events
- Connection events

## Benefits of Architecture

### Separation of Concerns ✅
- Each component has clear responsibility
- Easy to understand and modify
- Reduced coupling

### Code Reusability ✅
- Services used by multiple tools
- No code duplication
- DRY principle applied

### Testability ✅
- Services can be unit tested
- Mock services for integration tests
- Clear interfaces

### Maintainability ✅
- Small, focused files
- Self-documenting code
- Clear dependencies

### Scalability ✅
- Easy to add new services
- Services can be optimized independently
- Clear extension points

## Performance Considerations

### Caching
- Postal code search results cached
- Provider fuzzy matching cached
- Conversation state cached

### Async Operations
- Scraping uses async/await
- Non-blocking I/O
- Parallel processing where possible

### Connection Pooling
- Database connections pooled
- WebSocket connections managed
- Resource cleanup

### Error Handling
- Graceful fallbacks
- Retry logic for external services
- User-friendly error messages

## Security Considerations

### API Key Management
- Environment variables
- No hardcoded secrets
- Validation before use

### Input Validation
- Postcode format validation
- Parameter validation
- SQL injection prevention

### WebSocket Security
- User ID validation
- Session management
- CORS configuration

## Future Improvements

### Testing
- [ ] Add unit tests for services
- [ ] Add integration tests
- [ ] Add end-to-end tests
- [ ] Achieve >80% coverage

### Documentation
- [ ] API documentation (Sphinx)
- [ ] Architecture diagrams
- [ ] Workflow examples

### Performance
- [ ] Profile service methods
- [ ] Optimize database queries
- [ ] Add more caching

### Monitoring
- [ ] Service-level metrics
- [ ] Performance tracking
- [ ] Error rate monitoring

---

**Last Updated**: October 12, 2025
**Version**: 2.0.0

