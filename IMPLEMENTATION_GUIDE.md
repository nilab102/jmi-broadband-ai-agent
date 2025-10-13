# Broadband Tool Refactoring - Implementation Guide

## 🎯 Quick Start

### What's Been Done ✅
1. Created `voice_agent/functions/broadband/` directory
2. Created `__init__.py` with all exports
3. Created `helpers.py` with 12 utility functions
4. Created comprehensive refactoring plan

### What's Next ⏳
Create 7 remaining module files and refactor `broadband_tool.py` to use them.

---

## 📝 Step-by-Step Implementation

### Step 1: Extract Functions to Modules

For each module, follow this pattern:

#### Example: parameter_extraction.py

```python
"""
Parameter Extraction - Extract parameters from natural language queries.
"""

from typing import Dict, Optional, List, Tuple
from loguru import logger
import re

from .helpers import (
    interpret_speed_adjective,
    interpret_phone_calls,
    interpret_product_type,
    interpret_sort_preference,
    extract_contract_lengths,
    normalize_contract_single
)


class ParameterExtractor:
    """Extract broadband parameters from natural language."""
    
    def __init__(self, ai_extractor=None, valid_providers=None):
        """
        Initialize parameter extractor.
        
        Args:
            ai_extractor: Optional AI extraction service
            valid_providers: List of valid provider names
        """
        self.ai_extractor = ai_extractor
        self.valid_providers = valid_providers or []
        self.patterns = None
        
    def initialize_patterns(self, provider_matcher):
        """
        Initialize regex patterns for extraction.
        
        Args:
            provider_matcher: ProviderMatcher instance for fuzzy matching
        """
        self.patterns = {
            'postcode': [
                (r'\b([A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2})\b', 'postcode', lambda x: x.strip().upper()),
                # ... more patterns
            ],
            'speed_in_mb': [
                (r'(\d+)\s*mb?\s*speed', 'speed_in_mb', lambda x: f"{x}Mb"),
                (r'fast|superfast|ultrafast', 'speed_in_mb', interpret_speed_adjective),
            ],
            # ... more pattern groups
        }
    
    def extract_parameters(self, query: str, skip_validation: bool = False) -> Dict[str, str]:
        """
        Extract parameters from query.
        
        Args:
            query: Natural language query
            skip_validation: Whether to skip postcode validation
            
        Returns:
            Dictionary of extracted parameters
        """
        # Try AI extraction first
        if self.ai_extractor:
            try:
                result = self._extract_with_ai(query)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"AI extraction failed: {e}")
        
        # Fall back to regex
        return self._extract_with_regex(query, skip_validation)
    
    def _extract_with_ai(self, query: str) -> Optional[Dict[str, str]]:
        """Extract using AI service."""
        # Implementation here
        pass
    
    def _extract_with_regex(self, query: str, skip_validation: bool) -> Dict[str, str]:
        """Extract using regex patterns."""
        # Implementation here
        pass


def initialize_parameter_patterns(extractor: ParameterExtractor):
    """
    Initialize parameter extraction patterns.
    
    Args:
        extractor: ParameterExtractor instance
        
    Returns:
        Dictionary of patterns
    """
    # Return pattern dictionary
    pass
```

### Step 2: Update broadband_tool.py

```python
# At the top, import from modules
from voice_agent.functions.broadband import (
    ParameterExtractor,
    PostcodeValidator,
    ProviderMatcher,
    RecommendationEngine,
    handle_generate_url,
    handle_scrape_data,
    handle_compare_providers,
    # ... other imports
)

class BroadbandTool(BaseTool):
    def __init__(self, rtvi_processor, task=None, initial_current_page="broadband"):
        super().__init__(rtvi_processor, task, initial_current_page)
        
        # Initialize services
        self.postal_code_service = get_postal_code_service()
        self.scraper_service = get_scraper_service()
        # ... other services
        
        # Initialize modular components
        self.parameter_extractor = ParameterExtractor(
            ai_extractor=self.ai_extractor,
            valid_providers=BroadbandConstants.VALID_PROVIDERS
        )
        
        self.postcode_validator = PostcodeValidator(
            postal_code_service=self.postal_code_service,
            conversation_state=self.conversation_state
        )
        
        self.provider_matcher = ProviderMatcher(
            valid_providers=BroadbandConstants.VALID_PROVIDERS,
            fuzzy_searcher=self.fuzzy_searcher
        )
        
        self.recommendation_engine = RecommendationEngine(
            recommendation_service=self.recommendation_service
        )
        
        # Initialize parameter patterns with provider matcher
        self.parameter_extractor.initialize_patterns(self.provider_matcher)
    
    async def execute(self, user_id: str, action_type: str, **kwargs) -> str:
        """Execute broadband action - delegates to handlers."""
        
        # Initialize session
        self._initialize_user_session(user_id)
        
        # Route to appropriate handler
        if action_type == "query":
            return await handle_natural_language_query(
                user_id=user_id,
                query=kwargs.get('query'),
                context=kwargs.get('context'),
                parameter_extractor=self.parameter_extractor,
                postcode_validator=self.postcode_validator,
                url_generator=self.url_generator,
                conversation_state=self.conversation_state,
                send_websocket_fn=self.send_websocket_message,
                create_output_fn=self._create_structured_output
            )
        
        elif action_type == "generate_url":
            return await handle_generate_url(
                user_id=user_id,
                postcode=kwargs.get('postcode'),
                speed_in_mb=kwargs.get('speed_in_mb'),
                contract_length=kwargs.get('contract_length'),
                phone_calls=kwargs.get('phone_calls'),
                product_type=kwargs.get('product_type'),
                providers=kwargs.get('providers'),
                current_provider=kwargs.get('current_provider'),
                sort_by=kwargs.get('sort_by'),
                new_line=kwargs.get('new_line'),
                context=kwargs.get('context'),
                url_generator=self.url_generator,
                send_websocket_fn=self.send_websocket_message,
                create_output_fn=self._create_structured_output
            )
        
        # ... other action types
```

---

## 🔧 Function Signature Pattern

All handler functions should follow this pattern for consistency:

```python
async def handle_<action_name>(
    # Required parameters
    user_id: str,
    
    # Action-specific parameters
    param1: str,
    param2: Optional[str] = None,
    
    # Common parameters
    context: Optional[str] = None,
    
    # Injected dependencies (services)
    service1=None,
    service2=None,
    
    # Injected dependencies (state)
    conversation_state: Dict = None,
    
    # Injected dependencies (functions)
    send_websocket_fn=None,
    create_output_fn=None
) -> str:
    """
    Handle <action description>.
    
    Args:
        user_id: User identifier
        param1: Description of param1
        param2: Optional description of param2
        context: Additional context
        service1: Service dependency
        service2: Another service
        conversation_state: Conversation state dictionary
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Result message or structured dictionary
    """
    try:
        # Implementation here
        
        # Create structured output
        output = create_output_fn(
            user_id=user_id,
            action_type="action_completed",
            param="param_name",
            value="param_value",
            interaction_type="action",
            clicked=True,
            element_name="action_button",
            context=context
        )
        
        # Send to WebSocket
        await send_websocket_fn(
            message_type="action_message",
            action="action_completed",
            data=output
        )
        
        return "Success message"
        
    except Exception as e:
        logger.error(f"Error in handle_<action_name>: {e}")
        return f"❌ Error: {str(e)}"
```

---

## 📋 Checklist for Each Module

When creating each module file, ensure:

- [ ] Clear docstring at the top explaining purpose
- [ ] All necessary imports at the top
- [ ] Functions follow naming convention (`handle_*` for handlers)
- [ ] All functions have docstrings with Args and Returns
- [ ] Type hints on all parameters and returns
- [ ] Proper error handling with try/except
- [ ] Logging statements for debugging
- [ ] No hardcoded values (use constants)
- [ ] Dependencies injected as parameters
- [ ] Returns consistent types (str or Dict)

---

## 🧪 Testing Strategy

### 1. Unit Test Each Module

```python
# test_helpers.py
import pytest
from voice_agent.functions.broadband.helpers import normalize_contract_length

def test_normalize_contract_length():
    assert normalize_contract_length("12 months") == "12 months"
    assert normalize_contract_length("12 months, 24 months") == "12 months,24 months"
    assert normalize_contract_length("") == ""
```

### 2. Integration Test with BroadbandTool

```python
# test_broadband_tool.py
import pytest
from voice_agent.tools.broadband_tool import BroadbandTool

@pytest.mark.asyncio
async def test_execute_query():
    tool = BroadbandTool(rtvi_processor=mock_processor)
    result = await tool.execute(
        user_id="test_user",
        action_type="query",
        query="Find broadband in E14 9WB"
    )
    assert "URL" in result or "postcode" in result.lower()
```

---

## 🎯 Priority Implementation Order

### Week 1: Critical Path
1. **parameter_extraction.py** ⭐ HIGHEST PRIORITY
   - Used by all query operations
   - ~400 lines
   
2. **postcode_operations.py** ⭐ HIGH PRIORITY
   - Critical for all searches
   - ~450 lines
   
3. **url_operations.py** ⭐ HIGH PRIORITY
   - Core functionality
   - ~350 lines

### Week 2: Core Features
4. **data_operations.py**
   - Scraping and listing
   - ~350 lines
   
5. **recommendation_engine.py**
   - AI recommendations
   - ~300 lines

### Week 3: Additional Features
6. **comparison_operations.py**
   - Compare, cheapest, fastest
   - ~350 lines
   
7. **filter_operations.py**
   - Filtering and refinement
   - ~300 lines
   
8. **provider_matching.py**
   - Provider fuzzy matching
   - ~250 lines

### Week 4: Integration & Testing
9. **Refactor broadband_tool.py**
   - Update to use modules
   - ~1 day
   
10. **Testing**
    - Unit tests for each module
    - Integration tests
    - ~2 days

---

## 💡 Tips & Best Practices

### 1. Start Small
Don't try to refactor everything at once. Start with one module (helpers.py is done!), test it, then move to the next.

### 2. Keep Old Code for Reference
Don't delete the original `broadband_tool.py` until everything works. Rename it to `broadband_tool_old.py` as backup.

### 3. Use Type Hints
Type hints make code self-documenting:
```python
def handle_something(user_id: str, data: Dict[str, Any]) -> str:
```

### 4. Write Docstrings
Good docstrings eliminate need for comments:
```python
def extract_parameters(query: str) -> Dict[str, str]:
    """
    Extract broadband parameters from natural language query.
    
    Args:
        query: Natural language query like "Find 100Mb in London"
        
    Returns:
        Dictionary with keys: postcode, speed_in_mb, etc.
    """
```

### 5. Test As You Go
Test each module immediately after creating it. Don't wait until the end.

---

## 📊 Progress Tracking

Use this checklist to track your progress:

### Module Creation
- [x] helpers.py ✅
- [ ] parameter_extraction.py
- [ ] postcode_operations.py
- [ ] provider_matching.py
- [ ] url_operations.py
- [ ] data_operations.py
- [ ] recommendation_engine.py
- [ ] comparison_operations.py
- [ ] filter_operations.py

### Refactoring
- [ ] Update broadband_tool.py to use modules
- [ ] Remove extracted functions from broadband_tool.py
- [ ] Update imports
- [ ] Test integration

### Testing
- [ ] Unit tests for each module
- [ ] Integration tests
- [ ] End-to-end tests
- [ ] Performance tests

### Documentation
- [ ] Module docstrings
- [ ] Function docstrings
- [ ] Usage examples
- [ ] README update

---

## 🚀 Expected Results

### Before
- 1 file, 2,330 lines
- Hard to navigate
- Difficult to test
- Slow to modify

### After
- 10 files, ~350 lines each
- Easy to navigate
- Easy to test each component
- Fast to modify and extend
- Professional code organization

---

## 📞 Need Help?

If you get stuck:
1. Refer to the refactoring plan (`BROADBAND_TOOL_REFACTORING_PLAN.md`)
2. Look at `helpers.py` as an example
3. Follow the function signature pattern above
4. Start with the simplest module first

**Remember**: This is a significant refactoring, but the result will be a much more maintainable and professional codebase!

---

**Status**: Phase 1 Started (helpers.py complete, 8 modules remaining)
**Next**: Create parameter_extraction.py
**Estimated Time**: 8-9 hours total

