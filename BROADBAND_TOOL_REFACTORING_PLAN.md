# Broadband Tool Refactoring Plan

## 🎯 Objective
Refactor the massive 2,330-line `broadband_tool.py` into smaller, focused modules following best practices.

## 📊 Current State
**File**: `voice_agent/tools/broadband_tool.py`
- **Lines**: 2,330
- **Methods**: 30+
- **Issues**: Too many responsibilities, hard to maintain, difficult to test

## 🏗️ Target Architecture

```
voice_agent/
├── functions/
│   └── broadband/
│       ├── __init__.py                  ✅ Created
│       ├── helpers.py                   ✅ Created (utilities)
│       ├── parameter_extraction.py      # Extract & interpret parameters
│       ├── postcode_operations.py       # Postcode validation & fuzzy search
│       ├── provider_matching.py         # Provider fuzzy matching
│       ├── url_operations.py            # URL generation handlers
│       ├── data_operations.py           # Scraping & data handlers
│       ├── recommendation_engine.py     # Recommendation generation
│       ├── comparison_operations.py     # Compare, cheapest, fastest
│       └── filter_operations.py         # Data filtering
└── tools/
    └── broadband_tool.py                # Slim orchestrator (~300-400 lines)
```

## 📦 Module Breakdown

### 1. helpers.py ✅ (Already Created)
**Purpose**: Utility functions for data formatting and normalization

**Functions**:
- `create_structured_output()` - Format output for WebSocket
- `normalize_contract_length()` - Normalize contract format
- `normalize_contract_single()` - Single contract normalization
- `extract_contract_lengths()` - Extract multiple contracts
- `interpret_speed_adjective()` - Convert "fast" → "30Mb"
- `interpret_phone_calls()` - Interpret call preferences
- `interpret_product_type()` - Interpret product types
- `interpret_sort_preference()` - Interpret sort options
- `validate_uk_postcode_format()` - Validate postcode format
- `format_currency()` - Format currency strings
- `parse_currency()` - Parse currency to float
- `extract_numeric_speed()` - Extract speed from string

**Lines**: ~280

---

### 2. parameter_extraction.py
**Purpose**: Extract and interpret parameters from natural language

**Classes**:
```python
class ParameterExtractor:
    def __init__(self, ai_extractor=None, valid_providers=None):
        self.ai_extractor = ai_extractor
        self.valid_providers = valid_providers
        self.patterns = initialize_parameter_patterns(self)
    
    def extract_parameters(self, query: str, skip_validation: bool = False) -> Dict[str, str]:
        """Main extraction method - tries AI first, falls back to regex"""
        
    def _extract_parameters_regex(self, query: str) -> Dict[str, str]:
        """Regex-based extraction (fallback)"""
        
    def _extract_postcode_from_query(self, query: str) -> Optional[str]:
        """Extract postcode-like string from query"""
```

**Functions**:
- `initialize_parameter_patterns(extractor)` - Create regex patterns
- Helper methods for extraction logic

**Lines**: ~350-400

---

### 3. postcode_operations.py
**Purpose**: Postcode validation and fuzzy search operations

**Classes**:
```python
class PostcodeValidator:
    def __init__(self, postal_code_service, conversation_state):
        self.postal_code_service = postal_code_service
        self.conversation_state = conversation_state
    
    async def search_with_fuzzy(self, user_id: str, raw_postcode: str, 
                                 context: str = None) -> Tuple[bool, str, Optional[str]]:
        """Search with auto-selection"""
    
    async def handle_confirmation(self, user_id: str, confirmed_postcode: str = None,
                                   original_postcode: str = None) -> str:
        """Handle user confirmation (legacy)"""
```

**Functions**:
- `search_postcode_with_fuzzy()` - Standalone function
- `handle_postcode_confirmation()` - Standalone function

**Lines**: ~400-450

---

### 4. provider_matching.py
**Purpose**: Provider name fuzzy matching

**Classes**:
```python
class ProviderMatcher:
    def __init__(self, valid_providers, fuzzy_searcher=None):
        self.valid_providers = valid_providers
        self.fuzzy_searcher = fuzzy_searcher
        self.cache = {}
    
    def fuzzy_match(self, provider_input: str, threshold: float = 50.0) -> Optional[str]:
        """Fuzzy match provider name"""
    
    def extract_provider_with_fuzzy(self, match: str) -> str:
        """Extract single provider"""
    
    def extract_providers_with_fuzzy(self, match: str) -> str:
        """Extract multiple providers (comma-separated)"""
```

**Lines**: ~200-250

---

### 5. url_operations.py
**Purpose**: URL generation and natural language query handling

**Functions**:
```python
async def handle_generate_url(
    user_id: str, postcode: str, speed_in_mb: str, contract_length: str,
    phone_calls: str, product_type: str, providers: str, current_provider: str,
    sort_by: str, new_line: str, context: str, url_generator, send_websocket_fn,
    create_output_fn
) -> str:
    """Handle URL generation with explicit parameters"""

async def handle_natural_language_query(
    user_id: str, query: str, context: str, parameter_extractor,
    postcode_validator, url_generator, conversation_state,
    send_websocket_fn, create_output_fn
) -> str:
    """Handle natural language broadband queries"""

async def handle_open_url(
    user_id: str, url: str, context: str, send_websocket_fn, create_output_fn
) -> str:
    """Handle opening URL in new tab"""
```

**Lines**: ~300-350

---

### 6. data_operations.py
**Purpose**: Data scraping and listing operations

**Functions**:
```python
async def handle_scrape_data(
    user_id: str, postcode: str, speed_in_mb: str, contract_length: str,
    phone_calls: str, product_type: str, providers: str, current_provider: str,
    new_line: str, context: str, url_generator, scraper_service,
    scraped_data_cache, conversation_state, send_websocket_fn, create_output_fn
) -> str:
    """Handle data scraping for recommendations"""

async def handle_list_providers(
    user_id: str, context: str, valid_providers, send_websocket_fn, create_output_fn
) -> str:
    """Handle listing all available providers"""

async def handle_clarify_missing_params(
    user_id: str, context: str, send_websocket_fn, create_output_fn
) -> str:
    """Handle missing parameter clarification"""
```

**Lines**: ~300-350

---

### 7. recommendation_engine.py
**Purpose**: AI-powered recommendation generation

**Classes**:
```python
class RecommendationEngine:
    def __init__(self, recommendation_service):
        self.recommendation_service = recommendation_service
    
    async def handle_get_recommendations(
        self, user_id: str, postcode: str, speed_in_mb: str, contract_length: str,
        phone_calls: str, product_type: str, providers: str, current_provider: str,
        new_line: str, context: str, conversation_state, scrape_data_fn,
        send_websocket_fn, create_output_fn
    ) -> str:
        """Handle AI-powered recommendations"""
    
    def generate_recommendations(
        self, deals: List[Dict], preferences: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Generate AI-powered recommendations based on user preferences"""
```

**Lines**: ~250-300

---

### 8. comparison_operations.py
**Purpose**: Provider comparison and deal finding operations

**Functions**:
```python
async def handle_compare_providers(
    user_id: str, providers: str, postcode: str, speed_in_mb: str,
    current_provider: str, new_line: str, context: str, conversation_state,
    scrape_data_fn, send_websocket_fn, create_output_fn
) -> str:
    """Handle provider comparison"""

async def handle_get_cheapest(
    user_id: str, postcode: str, current_provider: str, new_line: str,
    context: str, conversation_state, scrape_data_fn, send_websocket_fn,
    create_output_fn
) -> str:
    """Handle cheapest deal requests"""

async def handle_get_fastest(
    user_id: str, postcode: str, current_provider: str, new_line: str,
    context: str, conversation_state, scrape_data_fn, send_websocket_fn,
    create_output_fn
) -> str:
    """Handle fastest deal requests"""
```

**Lines**: ~300-350

---

### 9. filter_operations.py
**Purpose**: Data filtering and search refinement

**Functions**:
```python
async def handle_filter_data(
    user_id: str, filter_speed: str, filter_providers: str, filter_contract: str,
    filter_phone_calls: str, filter_new_line: str, context: str,
    conversation_state, filter_state, send_websocket_fn, create_output_fn
) -> str:
    """Handle filtering of scraped data"""

def apply_filters(deals: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """Apply filters to deals list"""

async def handle_refine_search(
    user_id: str, contract_length: str, context: str, conversation_state,
    url_generator, send_websocket_fn, create_output_fn
) -> str:
    """Handle search refinement"""
```

**Lines**: ~250-300

---

### 10. broadband_tool.py (Refactored)
**Purpose**: Orchestrator - delegates to modular functions

**Structure**:
```python
from voice_agent.functions.broadband import (
    ParameterExtractor,
    PostcodeValidator,
    ProviderMatcher,
    RecommendationEngine,
    # ... all other imports
)

class BroadbandTool(BaseTool):
    """Slim orchestrator for broadband operations"""
    
    def __init__(self, rtvi_processor, task=None, initial_current_page="broadband"):
        super().__init__(rtvi_processor, task, initial_current_page)
        
        # Initialize services
        self._init_services()
        
        # Initialize modular components
        self.parameter_extractor = ParameterExtractor(self.ai_extractor, self.valid_providers)
        self.postcode_validator = PostcodeValidator(self.postal_code_service, self.conversation_state)
        self.provider_matcher = ProviderMatcher(self.valid_providers, self.fuzzy_searcher)
        self.recommendation_engine = RecommendationEngine(self.recommendation_service)
    
    def _init_services(self):
        """Initialize all services"""
        
    def get_tool_definition(self) -> FunctionSchema:
        """Get tool definition for LLM"""
    
    async def execute(self, user_id: str, action_type: str, **kwargs) -> str:
        """Execute broadband action - delegates to modular functions"""
        
        # Route to appropriate handler
        if action_type == "query":
            return await handle_natural_language_query(...)
        elif action_type == "generate_url":
            return await handle_generate_url(...)
        # ... etc
```

**Lines**: ~350-400 (down from 2,330!)

---

## 🎯 Benefits of Refactoring

### Code Quality
✅ **Single Responsibility Principle** - Each module has one clear purpose
✅ **DRY** - No code duplication
✅ **Small Functions** - Functions are 20-100 lines (not 200+)
✅ **Clear Naming** - Self-documenting code
✅ **Easy to Test** - Can unit test each module independently

### Maintainability
✅ **Easy to Find Code** - Logical organization
✅ **Easy to Modify** - Change one module without affecting others
✅ **Easy to Extend** - Add new operations easily
✅ **Easy to Debug** - Clear boundaries between components

### Performance
✅ **Better Imports** - Only import what you need
✅ **Lazy Loading** - Can lazy-load heavy modules
✅ **Parallel Testing** - Can test modules in parallel

---

## 📝 Implementation Steps

### Phase 1: Create Module Files ✅ STARTED
1. ✅ Create `voice_agent/functions/broadband/` directory
2. ✅ Create `__init__.py` with exports
3. ✅ Create `helpers.py` with utility functions
4. ⏳ Create `parameter_extraction.py`
5. ⏳ Create `postcode_operations.py`
6. ⏳ Create `provider_matching.py`
7. ⏳ Create `url_operations.py`
8. ⏳ Create `data_operations.py`
9. ⏳ Create `recommendation_engine.py`
10. ⏳ Create `comparison_operations.py`
11. ⏳ Create `filter_operations.py`

### Phase 2: Refactor broadband_tool.py
1. Remove extracted functions
2. Import from modules
3. Update method calls to use module functions
4. Pass dependencies as parameters

### Phase 3: Testing
1. Test each module independently
2. Test integration with broadband_tool.py
3. Test end-to-end workflows

### Phase 4: Documentation
1. Add docstrings to all functions
2. Create usage examples
3. Update README

---

## 🔍 Key Design Decisions

### 1. Function-Based vs Class-Based
- **Helper functions**: Function-based (pure functions)
- **Stateful operations**: Class-based (e.g., ParameterExtractor, PostcodeValidator)
- **Handler functions**: Function-based with dependency injection

### 2. Dependency Injection
All handler functions receive dependencies as parameters:
```python
async def handle_generate_url(
    user_id, postcode, ...,
    url_generator,  # Injected dependency
    send_websocket_fn,  # Injected function
    create_output_fn  # Injected function
) -> str:
```

This makes functions:
- **Testable** - Can mock dependencies
- **Flexible** - Can swap implementations
- **Clear** - Dependencies are explicit

### 3. Separation of Concerns
- **Business Logic** - In module functions
- **Orchestration** - In BroadbandTool class
- **Services** - In services layer
- **Utilities** - In helpers

---

## 📊 Size Comparison

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| broadband_tool.py | 2,330 lines | ~350 lines | **-85%** |
| Total codebase | 2,330 lines | ~3,200 lines | +37% (but organized!) |

**Note**: Total lines increase because we add:
- Clear separation
- Docstrings
- Type hints
- Better documentation

But each file is now **manageable** (200-400 lines vs 2,330!)

---

## 🚀 Next Steps

### To Complete This Refactoring:

1. **Create remaining module files** (7 files to go)
2. **Extract functions** from broadband_tool.py into modules
3. **Refactor broadband_tool.py** to use modules
4. **Test thoroughly** - Ensure nothing breaks
5. **Update documentation** - Document new structure

### Estimated Time:
- Module creation: 3-4 hours
- Refactoring broadband_tool.py: 2 hours
- Testing: 2 hours
- Documentation: 1 hour
- **Total**: ~8-9 hours

### Priority Order:
1. **parameter_extraction.py** (critical path)
2. **postcode_operations.py** (critical path)
3. **url_operations.py** (critical path)
4. **data_operations.py** (critical path)
5. **recommendation_engine.py**
6. **comparison_operations.py**
7. **filter_operations.py**
8. **provider_matching.py**

---

## 💡 Usage Example (After Refactoring)

### Before (Old broadband_tool.py):
```python
# Everything in one massive file
class BroadbandTool(BaseTool):
    # 2,330 lines of code...
    async def _handle_generate_url(self, ...):  # Line 1439
        # 50 lines of code
    
    async def _handle_scrape_data(self, ...):  # Line 1491
        # 111 lines of code
    
    # ... 28 more methods
```

### After (Refactored):
```python
# broadband_tool.py - Slim orchestrator
from voice_agent.functions.broadband import (
    handle_generate_url,
    handle_scrape_data
)

class BroadbandTool(BaseTool):
    async def execute(self, user_id, action_type, **kwargs):
        if action_type == "generate_url":
            return await handle_generate_url(
                user_id, kwargs.get('postcode'), ...,
                url_generator=self.url_generator_service,
                send_websocket_fn=self.send_websocket_message,
                create_output_fn=self._create_structured_output
            )
```

---

## ✅ Summary

This refactoring transforms a monolithic 2,330-line file into:
- **9 focused modules** (~200-400 lines each)
- **1 slim orchestrator** (~350 lines)
- **Clear separation of concerns**
- **Easy to maintain and extend**
- **Testable components**
- **Self-documenting code**

**Result**: A professional, maintainable, and scalable codebase! 🎉

---

**Created**: October 12, 2025
**Status**: In Progress (Helpers ✅, 8 modules remaining)
**Next**: Create parameter_extraction.py

