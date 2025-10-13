# Codebase Organization

This document explains the organization of the JMI Broadband AI Agent codebase and the relationship between standalone modules and the service layer.

## Architecture Overview

The codebase follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  (voice_agent/tools/, voice_agent/core/, voice_agent/functions/) │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│              (voice_agent/services/)                         │
│  - PostalCodeService                                         │
│  - ScraperService                                            │
│  - URLGeneratorService                                       │
│  - RecommendationService                                     │
│  - DatabaseService                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Core Implementation Layer                   │
│                    (Root Directory)                          │
│  - fuzzy_postal_code.py                                      │
│  - jmi_scrapper.py                                           │
│  - broadband_url_generator.py (moved to voice_agent/)       │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

### Root Directory

#### Configuration Files
- `postcode_cache.pkl` - Cached postal code data (also in voice_agent/lib/)
- `postcodes_only.csv` - Source data for postal codes
- `import_log.txt` - Import operation logs

### `/voice_agent/lib/` Directory

**Purpose**: Core library modules containing pure algorithms and business logic

These are **core implementation modules** that the service layer wraps:

- **`fuzzy_postal_code.py`** (~635 lines)
  - Implements BK-Tree and Trie data structures for ultra-fast fuzzy postal code search
  - Handles 2.7M+ UK postcodes with dynamic distance calculation
  - Used by: `voice_agent/services/postal_code_service.py`
  - **Why it's here**: Core algorithm with no dependencies on voice_agent structure

- **`jmi_scrapper.py`** (~776 lines)
  - Web scraper for broadband comparison websites
  - Handles dynamic JavaScript rendering with Playwright
  - Used by: `voice_agent/services/scraper_service.py`
  - **Why it's here**: Standalone scraping logic that can be tested independently

- **`postcode_cache.pkl`** - Cached postal code data for fast startup

### `/scripts/` Directory

**Purpose**: Development and testing utilities (not production code)

- **`debug_contract_patterns.py`** - Test contract length pattern extraction
- **`data_insert&search.py`** - Database connection test script
- **`check_table_structure.py`** - Database schema inspection tool

**Note**: These scripts are for development only and are not imported by production code.

### `/voice_agent/` Directory

#### `/voice_agent/lib/` - Core Library Modules

Contains pure implementations of algorithms and business logic:
- **No dependencies on voice_agent structure**
- Can be tested independently
- Wrapped by the service layer

Files:
- `fuzzy_postal_code.py` - Fuzzy postal code search
- `jmi_scrapper.py` - Web scraping engine
- `postcode_cache.pkl` - Cached data

#### `/voice_agent/services/` - Service Layer

The service layer provides a **clean interface** to the core implementations with:
- Lifecycle management (initialization, shutdown)
- Error handling and logging
- Singleton patterns where appropriate
- Consistent API across all services

**Services:**

1. **`postal_code_service.py`**
   - Wraps `voice_agent.lib.fuzzy_postal_code`
   - Provides `PostalCodeService` class
   - Factory function: `get_postal_code_service()`

2. **`scraper_service.py`**
   - Wraps `voice_agent.lib.jmi_scrapper`
   - Provides `ScraperService` class
   - Factory function: `get_scraper_service()`

3. **`url_generator_service.py`**
   - Wraps `voice_agent/broadband_url_generator.py`
   - Provides `URLGeneratorService` class
   - Factory function: `get_url_generator_service()`

4. **`recommendation_service.py`**
   - Wraps Gemini AI for recommendations
   - Provides `RecommendationService` class
   - Factory function: `get_recommendation_service()`

5. **`database_service.py`**
   - Database operations and connection management
   - Provides `DatabaseService` class
   - Factory function: `get_database_service()`

#### `/voice_agent/tools/` - Tool Layer

- **`broadband_tool.py`** - Main orchestrator for broadband operations
  - Uses services via dependency injection
  - Delegates to modular functions in `/voice_agent/functions/broadband/`

#### `/voice_agent/functions/broadband/` - Modular Functions

Highly focused modules for specific broadband operations:
- `parameter_extraction.py` - Extract parameters from natural language
- `postcode_operations.py` - Postcode validation and fuzzy search
- `provider_matching.py` - Provider fuzzy matching
- `url_operations.py` - URL generation handlers
- `data_operations.py` - Data scraping operations
- `recommendation_engine.py` - AI recommendations
- `comparison_operations.py` - Provider comparisons
- `filter_operations.py` - Data filtering
- `helpers.py` - Utility functions

#### `/voice_agent/core/` - Core Application

- `router.py` - FastAPI application and routing
- `agent_manager.py` - Agent lifecycle management
- `conversation_manager.py` - Conversation state management
- `voice_agent.py` - Voice agent implementation
- `text_agent.py` - Text agent implementation

## Design Principles

### 1. Separation of Concerns

**Core Implementation** (Root .py files)
- Pure algorithms and business logic
- No lifecycle management
- Can be tested independently
- Reusable across projects

**Service Layer** (voice_agent/services/)
- Wraps core implementations
- Handles initialization and shutdown
- Provides consistent API
- Manages dependencies

**Application Layer** (voice_agent/tools/, functions/, core/)
- Uses services via dependency injection
- Orchestrates business workflows
- Handles user interactions

### 2. Dependency Flow

```
Application → Services → Core Implementations
```

**CORRECT:**
```python
# In broadband_tool.py - Use service layer
from voice_agent.services import get_postal_code_service
postal_service = get_postal_code_service()
```

**ALSO CORRECT (for core algorithm development/testing):**
```python
# Direct import for testing core algorithms
from voice_agent.lib.fuzzy_postal_code import FastPostalCodeSearch
searcher = FastPostalCodeSearch(connection_string)
```

**INCORRECT:**
```python
# DON'T DO THIS - old import path
from fuzzy_postal_code import FastPostalCodeSearch  # ❌ File moved!
searcher = FastPostalCodeSearch(connection_string)
```

### 3. Why Move to voice_agent/lib/?

**Reasons for moving `fuzzy_postal_code.py`, `jmi_scrapper.py` to voice_agent/lib/:**

1. **Eliminates sys.path Manipulation**: No more fragile path hacking in service files

2. **Clean Imports**: `from voice_agent.lib.fuzzy_postal_code import ...` is standard Python

3. **Better Organization**: All voice_agent code in voice_agent/ directory

4. **Maintains Separation**: 
   - `lib/` = Core implementations (algorithms)
   - `services/` = Service wrappers (interfaces)
   - Still separate directories, clear purposes

5. **Professional Structure**: Standard Python package layout used by major projects

6. **Still Reusable**: Modules remain independent, just with better import paths

## Migration History

### Before Refactoring
- All code in `broadband_tool.py` (2,330 lines)
- Direct imports of core modules
- Difficult to test and maintain

### After Refactoring
- Service layer created (voice_agent/services/)
- Modular functions extracted (voice_agent/functions/broadband/)
- `broadband_tool.py` reduced to 803 lines (orchestrator)
- Utility scripts moved to `/scripts/`
- Clean dependency flow established

## Best Practices

### For Application Developers

1. **Always use the service layer**
   ```python
   from voice_agent.services import get_postal_code_service
   service = get_postal_code_service()
   ```

2. **Never import root .py files directly** (except for constants)
   ```python
   # OK - importing constants
   from voice_agent.broadband_url_generator import BroadbandConstants
   
   # NOT OK - bypassing service layer
   from fuzzy_postal_code import FastPostalCodeSearch  # ❌
   ```

3. **Use dependency injection**
   ```python
   def __init__(self, postal_service: PostalCodeService):
       self.postal_service = postal_service
   ```

### For Core Module Developers

1. **Keep core modules independent**
   - No imports from voice_agent/
   - Pure Python with minimal dependencies
   - Can run standalone

2. **Provide clear interfaces**
   - Well-documented classes and functions
   - Type hints
   - Examples in `if __name__ == "__main__"`

3. **Focus on algorithms**
   - No lifecycle management
   - No logging (or minimal)
   - Pure business logic

## File Locations Quick Reference

| What | Where | Why |
|------|-------|-----|
| Core algorithms | voice_agent/lib/ | Pure implementations, no dependencies |
| Service wrappers | voice_agent/services/ | Clean interface, lifecycle management |
| Application logic | voice_agent/tools/, functions/ | Business workflows, orchestration |
| Utility scripts | scripts/ | Development and testing tools |
| Configuration | Root config files | Project-wide settings and data |

## Summary

The codebase is organized to maximize:
- **Maintainability**: Clear separation of concerns
- **Testability**: Independent modules
- **Reusability**: Standalone core implementations
- **Clarity**: Obvious dependency flow

The service layer is the **single point of entry** for all core functionality, ensuring consistent behavior and easy maintenance.

