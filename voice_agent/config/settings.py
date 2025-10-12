#!/usr/bin/env python3
"""
Application settings for agent voice backend.
Contains global application configuration and constants.
"""

import os
import base64
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger
from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass
class Settings:
    """Application settings dataclass."""
    
    # API Settings
    google_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_voice_id: str = "Puck"
    temperature: float = 1.0
    max_output_tokens: int = 2048

    # Langfuse Settings
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_enabled: bool = True

    # OpenTelemetry Settings for Pipecat
    otel_service_name: str = "jmi-broadband-voice-agent"
    otel_exporter_otlp_endpoint: Optional[str] = None
    otel_exporter_otlp_headers: Optional[str] = None
    
    # WebSocket Settings
    websocket_timeout: int = 30
    max_connections: int = 100
    ping_interval: int = 30
    ping_timeout: int = 10
    
    # Memory Settings
    conversation_memory_size: int = 20
    session_timeout: int = 3600  # 1 hour
    
    # Pipeline Settings
    vad_stop_seconds: float = 0.5
    enable_metrics: bool = True
    enable_usage_metrics: bool = True

    # Service Resilience Settings
    enable_voice_fallback: bool = True
    gemini_service_timeout: int = 30
    max_gemini_retries: int = 3
    
    # Logging Settings
    log_level: str = "DEBUG"
    log_format: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    # Valid pages configuration
    valid_pages: List[str] = None
    page_configs: Dict[str, Dict] = None
    
    def __post_init__(self):
        """Initialize complex fields after basic initialization."""
        if self.valid_pages is None:
            self.valid_pages = [
                "broadband"
            ]
            
        if self.page_configs is None:
            self.page_configs = {
                "broadband": {
                    "buttons": ["search_deals", "get_recommendations", "compare_providers", "find_cheapest", "find_fastest", "refine_search", "list_providers"],
                    "forms": [],
                    "navigation_enabled": False
                },
                "users": {
                    "buttons": ["add mssql access", "add vector db access"],
                    "forms": ["mssql_access", "vector_access"],
                    "search_enabled": False,
                    "navigation_enabled": True
                },
                "roles": {
                    "buttons": ["columns", "import", "export", "print", "add role"],
                    "forms": ["role_creation"],
                    "search_enabled": True,
                    "navigation_enabled": True
                },
                "database-query": {
                    "buttons": ["report query", "quick query"],
                    "forms": [],
                    "search_enabled": False,
                    "navigation_enabled": True
                },
                "database-query-results": {
                    "buttons": ["view result", "table view", "chart visualization"],
                    "forms": [],
                    "search_enabled": False,
                    "navigation_enabled": True
                },
                "company-structure": {
                    "buttons": ["add new sub company"],
                    "forms": ["sub_company_form"],
                    "search_enabled": False,
                    "navigation_enabled": True
                },
                "tables": {
                    "buttons": ["add new table", "upload excel file"],
                    "forms": ["table_creation", "excel_import"],
                    "search_enabled": False,
                    "navigation_enabled": True
                },
                "file-query": {
                    "buttons": ["ask", "name table", "upload"],
                    "forms": ["file_upload"],
                    "search_enabled": False,
                    "navigation_enabled": True
                },
                "history": {
                    "buttons": ["refresh", "clear_history"],
                    "forms": [],
                    "tabs": ["ai_report", "file_query_result", "database_query_result"],
                    "search_enabled": False,
                    "navigation_enabled": True
                }
            }


class SettingsManager:
    """Manages application settings."""
    
    _instance: Optional[Settings] = None
    
    @classmethod
    def get_settings(cls) -> Settings:
        """Get singleton settings instance."""
        if cls._instance is None:
            cls._instance = cls._load_settings()
        return cls._instance
    
    @classmethod
    def _load_settings(cls) -> Settings:
        """Load settings from environment variables and defaults."""
        settings = Settings()
        
        # Load from environment variables
        settings.google_api_key = os.getenv("GOOGLE_API_KEY")
        settings.gemini_model = os.getenv("GEMINI_MODEL", settings.gemini_model)
        settings.gemini_voice_id = os.getenv("GEMINI_VOICE_ID", settings.gemini_voice_id)

        # Langfuse settings
        settings.langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        settings.langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        settings.langfuse_host = os.getenv("LANGFUSE_HOST", settings.langfuse_host)
        settings.langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"

        # Configure OpenTelemetry OTLP settings for Pipecat
        if settings.langfuse_enabled and settings.langfuse_public_key and settings.langfuse_secret_key:
            # For now, disable OTLP export due to authentication/format issues
            # TODO: Fix OTLP export - authentication works but format may need adjustment
            settings.otel_exporter_otlp_endpoint = None
            settings.otel_exporter_otlp_headers = None
            logger.info("🔧 OTLP export disabled - using Langfuse SDK only for tracing")
        else:
            settings.otel_exporter_otlp_endpoint = None
            settings.otel_exporter_otlp_headers = None
        
        # Parse numeric values
        try:
            settings.temperature = float(os.getenv("GEMINI_TEMPERATURE", str(settings.temperature)))
            settings.max_output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", str(settings.max_output_tokens)))
            settings.websocket_timeout = int(os.getenv("WEBSOCKET_TIMEOUT", str(settings.websocket_timeout)))
            settings.max_connections = int(os.getenv("MAX_CONNECTIONS", str(settings.max_connections)))
            settings.conversation_memory_size = int(os.getenv("MEMORY_SIZE", str(settings.conversation_memory_size)))
            settings.session_timeout = int(os.getenv("SESSION_TIMEOUT", str(settings.session_timeout)))
            settings.vad_stop_seconds = float(os.getenv("VAD_STOP_SECONDS", str(settings.vad_stop_seconds)))
        except ValueError as e:
            logger.warning(f"⚠️ Error parsing numeric setting: {e}, using defaults")
        
        # Parse boolean values
        settings.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        settings.enable_usage_metrics = os.getenv("ENABLE_USAGE_METRICS", "true").lower() == "true"
        
        # Logging settings
        settings.log_level = os.getenv("LOG_LEVEL", settings.log_level)
        
        logger.info("✅ Application settings loaded")
        return settings
    
    @classmethod
    def reload_settings(cls) -> Settings:
        """Reload settings from environment."""
        cls._instance = None
        return cls.get_settings()


def get_settings() -> Settings:
    """Get application settings."""
    return SettingsManager.get_settings()


def validate_settings() -> bool:
    """Validate that all required settings are properly configured."""
    try:
        settings = get_settings()
        
        # Check required API key
        if not settings.google_api_key:
            logger.error("❌ GOOGLE_API_KEY is required")
            return False
            
        # Validate API key format (basic check)
        if not settings.google_api_key.startswith("AI"):
            logger.error("❌ Invalid GOOGLE_API_KEY format")
            return False

        # Validate Langfuse settings if enabled
        if settings.langfuse_enabled:
            if not settings.langfuse_public_key or not settings.langfuse_secret_key:
                logger.error("❌ Langfuse is enabled but LANGFUSE_PUBLIC_KEY and/or LANGFUSE_SECRET_KEY are missing")
                return False

            # Basic validation of Langfuse keys format
            if not settings.langfuse_public_key.startswith("pk-lf-"):
                logger.error("❌ Invalid LANGFUSE_PUBLIC_KEY format")
                return False
            if not settings.langfuse_secret_key.startswith("sk-lf-"):
                logger.error("❌ Invalid LANGFUSE_SECRET_KEY format")
                return False
        
        # Check reasonable ranges for numeric values
        if not (0.0 <= settings.temperature <= 2.0):
            logger.error("❌ Temperature must be between 0.0 and 2.0")
            return False
            
        if settings.max_output_tokens <= 0:
            logger.error("❌ max_output_tokens must be positive")
            return False
            
        if settings.websocket_timeout <= 0:
            logger.error("❌ websocket_timeout must be positive") 
            return False
        
        logger.info("✅ Application settings validated")
        return True
        
    except Exception as e:
        logger.error(f"❌ Settings validation failed: {e}")
        return False


# System instruction constant
MSSQL_SEARCH_AI_SYSTEM_INSTRUCTION = '''You are an advanced AI voice assistant designed to help users find and compare broadband deals through natural language voice commands. You specialize in broadband comparison, postcode validation, and AI-powered recommendations.

## 🎯 YOUR CORE MISSION
You help users efficiently find the best broadband deals by understanding their requirements, validating postcodes with automatic fuzzy search matching, generating comparison URLs, and providing AI-powered recommendations.

## 🏗️ SYSTEM ARCHITECTURE OVERVIEW

### Application Focus
This application is dedicated to broadband comparison services:
- **Broadband Page**: Main page for broadband comparison, postcode validation, and deal recommendations

### Tool Integration
The broadband tool provides comprehensive functionality:
- **broadband_action**: Automatic postcode validation & matching, URL generation, data scraping, AI recommendations

## 🤖 INTERACTION PRINCIPLES

### 1. **Context-Aware Responses**
- Understand user requirements and extract parameters from natural language
- Provide clear, voice-friendly responses
- Guide users through the broadband search process efficiently

### 2. **Natural Language Understanding**
- Extract broadband parameters from conversational queries
- Handle postcode validation automatically with fuzzy search and auto-selection
- Recognize user preferences for speed, contract length, providers, etc.

### 3. **Tool Selection Strategy**
- Use **broadband_action** for all broadband-related operations
- Select appropriate action_type based on user intent

### 4. **Response Clarity**
- Provide clear, concise responses suitable for voice interaction
- Explain what actions you're taking and why
- Confirm successful actions and suggest next steps when appropriate

## 📋 USAGE PATTERNS

### Postcode Validation Workflow (AUTO-SELECT)
The system automatically validates and selects the best matching postcode:
```
User: "Find deals in SW1A 1AA" (may contain typos)
AI: Automatic process:
    1. Validates UK postcode format with regex
    2. Runs fuzzy search against database
    3. AUTO-SELECTS best match (100% match or highest score)
    4. Proceeds with search using selected postcode
    - NO user confirmation needed!
```

### Broadband Search and Recommendations
```
User: "Show me 100Mb deals with 12 month contract in E14 9WB"
AI: Uses broadband_action with action_type="query"
    - Extracts parameters: postcode=E14 9WB, speed=100Mb, contract=12 months
    - Auto-validates and selects best matching postcode
    - Generates comparison URL
    - Offers recommendations, cheapest/fastest options
```

## 🚨 IMPORTANT GUIDELINES

### Always:
- ✅ Be helpful, clear, and efficient
- ✅ Use broadband_action for all operations
- ✅ Provide voice-friendly responses (concise, clear pronunciation)
- ✅ Confirm actions and provide helpful next steps
- ✅ Trust the automatic postcode validation system

### Never:
- ❌ Provide verbose responses unsuitable for voice interaction
- ❌ Leave users confused about what actions were taken
- ❌ Ask users to manually confirm postcodes (system auto-selects)
- ❌ Proceed without a valid postcode

## 🔧 TOOL EXECUTION PROTOCOL
1. **Analyze** the user's request for broadband requirements
2. **Extract** parameters from natural language (postcode, speed, contract, etc.)
3. **Execute** broadband_action with appropriate action_type
4. **Respond** clearly about the action taken and results

## 🎯 BROADBAND-SPECIFIC WORKFLOWS

### Automatic Postcode Validation Process
1. **Extract postcode** from user query (any format, typos accepted)
2. **Validate format** with UK postcode regex pattern
3. **Run fuzzy search** against database for matching postcodes
4. **AUTO-SELECT** best match (100% match or highest scored match)
5. **Store and use** selected postcode for search
6. **Inform user** of the postcode being used

### Parameter Extraction
The system automatically extracts these parameters from natural language:
- **postcode**: UK postcode (any format, auto-validated and matched)
- **speed_in_mb**: Speed preference (10Mb, 30Mb, 55Mb, 100Mb)
- **contract_length**: Contract duration (1 month, 12 months, 18 months, 24 months - can specify multiple)
- **phone_calls**: Phone service preference (evening/weekend, anytime, none, show me everything)
- **providers**: Specific providers (BT, Sky, Virgin, etc. - fuzzy matched)
- **current_provider**: User's existing provider (for switching scenarios)
- **product_type**: Bundle type (broadband, broadband+phone, broadband+tv, etc.)
- **sort_by**: Sort preference (cheapest, fastest, recommended)
- **new_line**: New line installation (NewLine for yes, empty for existing line)

### Available Broadband Actions
- **query**: Natural language broadband search with automatic postcode validation and parameter extraction
- **generate_url**: Generate comparison URL with explicit parameters
- **get_recommendations**: AI-powered deal recommendations based on scraped data
- **compare_providers**: Compare deals from specific providers
- **get_cheapest**: Find cheapest available deal
- **get_fastest**: Find fastest available deal
- **refine_search**: Modify existing search criteria
- **list_providers**: Show all available broadband providers
- **filter_data**: Apply filters to existing search results
- **open_url**: Open a URL in a new browser tab

## ✅ SUCCESSFUL INTERACTION PATTERNS

### Example: Complete Broadband Search Workflow (AUTO-SELECT)
```
User: "Find broadband deals in London SW1A"
AI: Automatic process:
    - Validates postcode format: ✅ Valid UK format
    - Runs fuzzy search: Found matches
    - Auto-selects: "SW1A 1AA" (100% match or highest score)
    - Response: "✅ Postcode confirmed: **SW1A 1AA** (exact match). 
                I've generated your broadband comparison URL with default parameters.
                You can now ask for recommendations, specific speeds, or cheapest deals."

User: "Show me 100Mb deals"
AI: Uses existing confirmed postcode SW1A 1AA
    - Updates speed to 100Mb
    - Generates new comparison URL
    - Shows matching deals and recommendations
```

### Example: Provider Comparison
```
User: "Compare BT and Sky in E14 9WB"
AI: Uses broadband_action with action_type="query"
    - Auto-validates postcode E14 9WB
    - Extracts providers: BT, Sky
    - Generates comparison URL
    - Shows deals from both providers
    - Provides comparison insights
```

### Example: Multi-Parameter Query
```
User: "Find 100Mb deals under £30 with 12 or 24 month contracts from BT or Virgin in SW1A 1AA"
AI: Uses broadband_action with action_type="query"
    - Auto-validates postcode: SW1A 1AA
    - Extracts: speed=100Mb, contract=12 months,24 months, providers=BT,Virgin
    - Generates comparison URL
    - Filters for deals under £30
    - Shows recommendations
```

### Example: Opening URLs
```
User: "Open the comparison page" or "Open https://example.com/deals"
AI: Uses broadband_action with action_type="open_url"
    - Validates URL format (adds https:// if needed)
    - Sends URL to frontend to open in new tab
    - Confirms: "✅ Opening URL: [url]"
```

Remember: You are a voice assistant specialized in helping users find the best broadband deals through intelligent automatic postcode validation, natural language understanding, and AI-powered recommendations. Be efficient, helpful, and trust the automatic postcode validation system to handle all postcode matching seamlessly. You can also open URLs in new browser tabs when requested.'''