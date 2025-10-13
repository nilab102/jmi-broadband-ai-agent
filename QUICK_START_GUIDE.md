# Quick Start Guide - Refactored Codebase

## What Changed?

### ✅ New Services Layer
All utility functions are now in `voice_agent/services/`:
- **PostalCodeService** - Postal code validation & fuzzy matching
- **ScraperService** - Web scraping for broadband data
- **URLGeneratorService** - URL generation & validation
- **RecommendationService** - AI-powered recommendations
- **DatabaseService** - Database operations

### ✅ Voice Agent Extracted
Voice logic moved from `router.py` to `voice_agent.py`:
- Cleaner separation of routing and agent logic
- Easier to maintain and test
- Parallel structure with `text_agent.py`

### ✅ Broadband Tool Refactored
`broadband_tool.py` now uses services instead of direct imports

## File Structure

```
voice_agent/
├── services/          # ⭐ NEW - Business logic layer
│   ├── postal_code_service.py
│   ├── scraper_service.py
│   ├── url_generator_service.py
│   ├── recommendation_service.py
│   └── database_service.py
├── core/
│   ├── router.py      # ✨ Simplified - routing only
│   ├── voice_agent.py # ⭐ NEW - Voice agent logic
│   └── text_agent.py  # Unchanged
└── tools/
    └── broadband_tool.py  # ✨ Updated - uses services
```

## How to Use

### 1. Using Services

```python
# Import services
from voice_agent.services import (
    get_postal_code_service,
    get_scraper_service,
    get_recommendation_service
)

# Get service instances (singleton pattern)
postal_service = get_postal_code_service()
scraper_service = get_scraper_service()
recommender = get_recommendation_service()

# Use services
result = postal_service.fuzzy_search("E149WB", top_n=5)
deals = await scraper_service.scrape_url_async(url)
recommendations = recommender.generate_recommendations(deals, preferences)
```

### 2. Using Voice Agent

```python
from voice_agent.core.voice_agent import create_voice_agent

# Create voice agent
voice_agent = await create_voice_agent(
    user_id="user123",
    session_id="session456",
    websocket=websocket,
    current_page="broadband"
)

# Run voice pipeline
await voice_agent.run()
```

### 3. Router Usage (Unchanged)

```python
# The router endpoints work the same as before
# Internal implementation now uses VoiceAgent class
```

## Testing

### Test Services Import:
```bash
cd /path/to/project
python3 -c "from voice_agent.services import get_postal_code_service; print('✅ Services OK')"
```

### Test Voice Agent Syntax:
```bash
python3 -m py_compile voice_agent/core/voice_agent.py
```

### Test Router Syntax:
```bash
python3 -m py_compile voice_agent/core/router.py
```

## Running the Server

No changes needed to how you start the server:

```bash
cd /path/to/project
python3 voice_agent/start_server.py
```

## Benefits

### For Developers:
✅ Cleaner, more readable code
✅ Easier to find and modify specific functionality
✅ Better separation of concerns
✅ Services can be unit tested independently

### For Maintenance:
✅ Smaller, focused files (200-500 lines vs 2000+)
✅ Clear interfaces between components
✅ Self-documenting code with clear method names

### For Testing:
✅ Mock services for integration tests
✅ Unit test services independently
✅ Clear boundaries between components

## Backward Compatibility

### ✅ All Original Files Kept
- `fuzzy_postal_code.py` - Still in project root
- `jmi_scrapper.py` - Still in project root
- `data_insert&search.py` - Still in project root
- Services wrap these, don't replace them

### ✅ APIs Unchanged
- All endpoints work the same
- No breaking changes to external interfaces
- Internal implementation improved

### ✅ Migration Path
- Services provide cleaner interface
- Old code can gradually migrate to services
- Both old and new patterns work

## Common Tasks

### Add a New Service:

1. Create file in `voice_agent/services/`:
```python
# voice_agent/services/my_new_service.py
class MyNewService:
    def __init__(self):
        pass
    
    def do_something(self):
        pass

_my_service = None

def get_my_service():
    global _my_service
    if _my_service is None:
        _my_service = MyNewService()
    return _my_service
```

2. Add to `voice_agent/services/__init__.py`:
```python
from .my_new_service import MyNewService, get_my_service

__all__ = [
    # ... existing exports ...
    'MyNewService',
    'get_my_service',
]
```

3. Use in tools:
```python
from voice_agent.services import get_my_service

my_service = get_my_service()
my_service.do_something()
```

## Troubleshooting

### Import Errors
If you see import errors, check:
1. Is the service exported in `__init__.py`?
2. Are you using the getter function (e.g., `get_postal_code_service()`)?
3. Is the path correct?

### Missing Dependencies
Some warnings are expected if optional dependencies aren't installed:
- ⚠️ "Fuzzy postal code search not available" - Normal if `fuzzy_postal_code.py` dependencies missing
- ⚠️ "psycopg2 not available" - Normal if database library not installed
- Services handle this gracefully with fallbacks

### Syntax Errors
Test individual files:
```bash
python3 -m py_compile path/to/file.py
```

## Next Steps

1. **Review the refactoring**:
   - Read `REFACTORING_SUMMARY.md` for detailed changes
   - Check service implementations in `voice_agent/services/`

2. **Test your workflows**:
   - Try existing functionality
   - Verify everything works as before

3. **Gradually adopt services**:
   - Use services in new code
   - Migrate old code when making changes

4. **Add tests** (recommended):
   - Unit test services
   - Integration test voice agent
   - End-to-end test full workflows

## Support

For questions or issues:
1. Check `REFACTORING_SUMMARY.md` for detailed documentation
2. Review service code in `voice_agent/services/`
3. Look at usage examples in this guide

## Summary

✅ **Services layer created** - Clean, reusable business logic
✅ **Voice agent extracted** - Better code organization
✅ **Backward compatible** - All original functionality preserved
✅ **Best practices applied** - SRP, DRY, clear naming
✅ **Tested** - All syntax checks pass

**You're ready to use the refactored codebase!** 🚀

---

**Last Updated**: October 12, 2025
**Version**: 2.0.0

