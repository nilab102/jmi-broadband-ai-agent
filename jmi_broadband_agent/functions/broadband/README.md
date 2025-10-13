# Broadband Tool Functions - Modular Architecture

## 📖 Overview

This directory contains the modular function library for broadband tool operations, extracted from the monolithic `broadband_tool.py` (2,330 lines) into focused, maintainable modules.

## 🎯 Architecture Goals

Following software engineering best practices:
- ✅ **Single Responsibility Principle (SRP)** - Each module has one clear purpose
- ✅ **DRY (Don't Repeat Yourself)** - Reusable components, no duplication
- ✅ **Small Functions** - Functions are 20-100 lines, not 200+
- ✅ **Clear Naming** - Self-documenting code
- ✅ **Easy to Test** - Can unit test each module independently
- ✅ **Minimal Dependencies** - Dependency injection for flexibility
- ✅ **No Hardcoding** - Use constants and configuration

## 📂 Module Structure

```
broadband/
├── __init__.py                   # Module exports
├── helpers.py                    # ✅ Utility functions
├── parameter_extraction.py       # Parameter extraction from NL
├── postcode_operations.py        # Postcode validation & fuzzy search
├── provider_matching.py          # Provider fuzzy matching
├── url_operations.py             # URL generation handlers
├── data_operations.py            # Scraping & data handlers
├── recommendation_engine.py      # AI-powered recommendations
├── comparison_operations.py      # Compare, cheapest, fastest
└── filter_operations.py          # Data filtering & refinement
```

## 📦 Module Details

### helpers.py ✅ (280 lines)
**Purpose**: Utility functions for data formatting and normalization

**Key Functions**:
- `create_structured_output()` - Format output for WebSocket communication
- `normalize_contract_length()` - Normalize contract format for URLs
- `extract_contract_lengths()` - Extract multiple contract lengths from text
- `interpret_speed_adjective()` - Convert "fast" → "30Mb"
- `interpret_phone_calls()` - Interpret call preferences
- `interpret_product_type()` - Interpret product types
- `interpret_sort_preference()` - Interpret sort options
- `validate_uk_postcode_format()` - Validate UK postcode format
- `format_currency()` / `parse_currency()` - Currency utilities
- `extract_numeric_speed()` - Extract speed from strings

**Usage**:
```python
from jmi_broadband_agent.functions.broadband.helpers import (
    normalize_contract_length,
    create_structured_output
)

# Normalize contract length
normalized = normalize_contract_length("12 months, 24 months")
# Returns: "12 months,24 months"

# Create structured output
output = create_structured_output(
    user_id="user123",
    action_type="url_generated",
    param="url",
    value="https://...",
    interaction_type="url_generation",
    current_page="broadband"
)
```

### parameter_extraction.py (400 lines) ⏳
**Purpose**: Extract broadband parameters from natural language queries

**Key Components**:
- `ParameterExtractor` class - Main extraction logic
- `initialize_parameter_patterns()` - Pattern initialization
- AI-powered extraction with regex fallback

**Usage**:
```python
from jmi_broadband_agent.functions.broadband import ParameterExtractor

extractor = ParameterExtractor(
    ai_extractor=ai_service,
    valid_providers=provider_list
)

params = extractor.extract_parameters(
    "Find 100Mb broadband in E14 9WB with 12 month contract"
)
# Returns: {
#   'postcode': 'E14 9WB',
#   'speed_in_mb': '100Mb',
#   'contract_length': '12 months',
#   ...
# }
```

### postcode_operations.py (450 lines) ⏳
**Purpose**: Postcode validation and fuzzy search operations

**Key Components**:
- `PostcodeValidator` class - Validation and fuzzy matching
- `search_postcode_with_fuzzy()` - Auto-select best match
- `handle_postcode_confirmation()` - User confirmation (legacy)

**Usage**:
```python
from jmi_broadband_agent.functions.broadband import PostcodeValidator

validator = PostcodeValidator(
    postal_code_service=postal_service,
    conversation_state=state_dict
)

success, message, postcode = await validator.search_with_fuzzy(
    user_id="user123",
    raw_postcode="E149WB",  # Missing space
    context="broadband search"
)
# Auto-selects: "E14 9WB"
```

### url_operations.py (350 lines) ⏳
**Purpose**: URL generation and natural language query handling

**Key Functions**:
- `handle_generate_url()` - Generate comparison URL
- `handle_natural_language_query()` - Process NL queries
- `handle_open_url()` - Open URL in new tab

**Usage**:
```python
from jmi_broadband_agent.functions.broadband import handle_generate_url

result = await handle_generate_url(
    user_id="user123",
    postcode="E14 9WB",
    speed_in_mb="100Mb",
    contract_length="12 months",
    url_generator=url_service,
    send_websocket_fn=websocket.send,
    create_output_fn=create_output
)
```

### data_operations.py (350 lines) ⏳
**Purpose**: Data scraping and listing operations

**Key Functions**:
- `handle_scrape_data()` - Scrape broadband deals
- `handle_list_providers()` - List available providers
- `handle_clarify_missing_params()` - Request missing info

**Usage**:
```python
from jmi_broadband_agent.functions.broadband import handle_scrape_data

result = await handle_scrape_data(
    user_id="user123",
    postcode="E14 9WB",
    speed_in_mb="100Mb",
    scraper_service=scraper,
    scraped_data_cache=cache,
    conversation_state=state
)
```

### recommendation_engine.py (300 lines) ⏳
**Purpose**: AI-powered recommendation generation

**Key Components**:
- `RecommendationEngine` class - Generate recommendations
- Scoring algorithm based on preferences
- Filtering and ranking logic

**Usage**:
```python
from jmi_broadband_agent.functions.broadband import RecommendationEngine

engine = RecommendationEngine(recommendation_service)

result = await engine.handle_get_recommendations(
    user_id="user123",
    postcode="E14 9WB",
    speed_in_mb="100Mb",
    conversation_state=state,
    scrape_data_fn=scrape_data
)
```

### comparison_operations.py (350 lines) ⏳
**Purpose**: Provider comparison and deal finding

**Key Functions**:
- `handle_compare_providers()` - Compare specific providers
- `handle_get_cheapest()` - Find cheapest deal
- `handle_get_fastest()` - Find fastest deal

**Usage**:
```python
from jmi_broadband_agent.functions.broadband import (
    handle_compare_providers,
    handle_get_cheapest
)

# Compare providers
result = await handle_compare_providers(
    user_id="user123",
    providers="BT,Sky,Virgin",
    conversation_state=state
)

# Find cheapest
result = await handle_get_cheapest(
    user_id="user123",
    postcode="E14 9WB",
    conversation_state=state
)
```

### filter_operations.py (300 lines) ⏳
**Purpose**: Data filtering and search refinement

**Key Functions**:
- `handle_filter_data()` - Apply filters to deals
- `apply_filters()` - Filter logic
- `handle_refine_search()` - Refine search parameters

**Usage**:
```python
from jmi_broadband_agent.functions.broadband import (
    handle_filter_data,
    apply_filters
)

result = await handle_filter_data(
    user_id="user123",
    filter_speed="100Mb",
    filter_providers="BT,Sky",
    conversation_state=state,
    filter_state=filters
)
```

### provider_matching.py (250 lines) ⏳
**Purpose**: Provider name fuzzy matching

**Key Components**:
- `ProviderMatcher` class - Fuzzy match provider names
- Caching for performance
- Extract single or multiple providers

**Usage**:
```python
from jmi_broadband_agent.functions.broadband import ProviderMatcher

matcher = ProviderMatcher(
    valid_providers=provider_list,
    fuzzy_searcher=fuzzy_service
)

# Match single provider
provider = matcher.fuzzy_match("virgn media")  # "Virgin Media"

# Extract from text
providers = matcher.extract_providers_with_fuzzy("BT, sky, virgn")
# Returns: "BT,Sky,Virgin Media"
```

## 🔧 Integration with broadband_tool.py

The refactored `broadband_tool.py` becomes a slim orchestrator:

```python
from jmi_broadband_agent.functions.broadband import (
    ParameterExtractor,
    PostcodeValidator,
    ProviderMatcher,
    RecommendationEngine,
    handle_generate_url,
    handle_scrape_data,
    # ... other imports
)

class BroadbandTool(BaseTool):
    """Slim orchestrator - delegates to modular functions"""
    
    def __init__(self, rtvi_processor, task=None):
        super().__init__(rtvi_processor, task)
        
        # Initialize modular components
        self.parameter_extractor = ParameterExtractor(...)
        self.postcode_validator = PostcodeValidator(...)
        self.provider_matcher = ProviderMatcher(...)
        self.recommendation_engine = RecommendationEngine(...)
    
    async def execute(self, user_id, action_type, **kwargs):
        """Route to appropriate handler"""
        
        if action_type == "query":
            return await handle_natural_language_query(
                user_id=user_id,
                query=kwargs.get('query'),
                parameter_extractor=self.parameter_extractor,
                postcode_validator=self.postcode_validator,
                # ... dependencies
            )
        
        elif action_type == "generate_url":
            return await handle_generate_url(
                user_id=user_id,
                postcode=kwargs.get('postcode'),
                # ... parameters and dependencies
            )
        
        # ... other actions
```

## 🧪 Testing

Each module can be tested independently:

```python
# test_helpers.py
from jmi_broadband_agent.functions.broadband.helpers import normalize_contract_length

def test_normalize_contract_length():
    assert normalize_contract_length("12 months, 24 months") == "12 months,24 months"
    assert normalize_contract_length("") == ""

# test_parameter_extraction.py
from jmi_broadband_agent.functions.broadband import ParameterExtractor

def test_extract_parameters():
    extractor = ParameterExtractor()
    params = extractor.extract_parameters("100Mb in E14 9WB")
    assert params['speed_in_mb'] == '100Mb'
    assert params['postcode'] == 'E14 9WB'
```

## 📊 Benefits

### Before Refactoring
- ❌ 2,330 lines in one file
- ❌ Hard to navigate
- ❌ Difficult to test
- ❌ Slow to modify
- ❌ High cognitive load

### After Refactoring
- ✅ ~350 lines per module (manageable)
- ✅ Easy to navigate (logical organization)
- ✅ Easy to test (unit tests per module)
- ✅ Fast to modify (clear boundaries)
- ✅ Low cognitive load (one concept per file)

## 📚 Additional Resources

- **BROADBAND_TOOL_REFACTORING_PLAN.md** - Complete architectural plan
- **IMPLEMENTATION_GUIDE.md** - Step-by-step implementation
- **REFACTORING_STATUS.md** - Current progress tracker

## 🚀 Next Steps

1. Create remaining module files (8 modules)
2. Extract functions from broadband_tool.py
3. Update broadband_tool.py to use modules
4. Write unit tests for each module
5. Integration testing
6. Documentation and examples

---

**Status**: Foundation complete (helpers ✅), 8 modules remaining
**Completion**: ~15%
**Next**: Create parameter_extraction.py

