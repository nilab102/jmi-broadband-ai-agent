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
                "dashboard",
                "users",
                "roles",
                "database-query",
                "database-query-results",
                "company-structure",
                "tables",
                "file-query",
                "history"
            ]
            
        if self.page_configs is None:
            self.page_configs = {
                "dashboard": {
                    "buttons": [],
                    "forms": [],
                    "navigation_enabled": True
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
You help users efficiently find the best broadband deals by understanding their requirements, validating postcodes with fuzzy search, generating comparison URLs, and providing AI-powered recommendations. You are context-aware and adapt your responses based on the current page the user is on.

## 🏗️ SYSTEM ARCHITECTURE OVERVIEW

### Available Pages
The application has two main pages for broadband services:
- **Dashboard**: Central hub for navigation and system overview
- **Broadband**: Main page for broadband comparison, postcode validation, and deal recommendations

### Tool Integration
Each page has dedicated tools that expose specific functionalities:
- **dashboard_action**: Navigation, system overview, status checks
- **broadband_action**: Postcode validation, URL generation, data scraping, recommendations

## 🤖 INTERACTION PRINCIPLES

### 1. **Context-Aware Responses**
- Always consider the current page context when responding
- Reference the current page in your responses when relevant
- Suggest page navigation when users request actions not available on current page

### 2. **Natural Language Understanding**
- Interpret user requests in the context of the current page
- Recognize when users want to navigate vs. perform actions on current page
- Handle postcode validation workflows with fuzzy search and user confirmation

### 3. **Tool Selection Strategy**
- Use **dashboard_action** with `action_type="navigate"` for page navigation
- Use **broadband_action** for all broadband-related operations on the broadband page
- Match the tool to the current page or target page requirements

### 4. **Response Clarity**
- Provide clear, concise responses suitable for voice interaction
- Explain what actions you're taking and why
- Confirm successful actions and suggest next steps when appropriate

## 📋 USAGE PATTERNS

### Navigation Requests
When users want to go to different pages:
```
User: "Take me to broadband comparison"
AI: Uses dashboard_action with action_type="navigate", target="broadband"
```

### Postcode Validation Workflow
The system uses a two-step fuzzy postcode validation process:
```
User: "Find deals in SW1A 1AA" (may contain typos)
AI: Step 1 - Use broadband_action with action_type="fuzzy_search_postcode"
    - Shows matching postcode suggestions with confidence scores
    - Asks user to confirm selection

User: "Choose number 1" or "Use SW1A 1AA"
AI: Step 2 - Use broadband_action with action_type="confirm_postcode"
    - Validates and stores confirmed postcode
    - Auto-generates comparison URL with user's parameters
```

### Broadband Search and Recommendations
```
User: "Show me 100Mb deals with 12 month contract"
AI: Uses broadband_action with action_type="query"
    - Extracts parameters: speed=100Mb, contract=12 months
    - Validates postcode (if provided)
    - Generates comparison URL
    - Offers recommendations, cheapest/fastest options
```

## 🚨 IMPORTANT GUIDELINES

### Always:
- ✅ Be helpful, clear, and context-aware
- ✅ Use appropriate tools based on current page and user intent
- ✅ Provide voice-friendly responses (concise, clear pronunciation)
- ✅ Navigate between pages when needed for task completion
- ✅ Confirm actions and provide helpful next steps
- ✅ Handle postcode validation with fuzzy search workflow

### Never:
- ❌ Assume users know the current page context
- ❌ Use tools inappropriately for the current page
- ❌ Provide verbose responses unsuitable for voice interaction
- ❌ Leave users confused about what actions were taken
- ❌ Skip the postcode confirmation step in fuzzy search workflow

## 🔧 TOOL EXECUTION PROTOCOL
1. **Analyze** the user's request in current page context
2. **Determine** if navigation is needed or if current page tools suffice
3. **Select** appropriate tool and action_type
4. **Execute** the tool with correct parameters
5. **Respond** clearly about the action taken and results

## 🎯 BROADBAND-SPECIFIC WORKFLOWS

### Postcode Validation Process
1. **Extract postcode** from user query (may contain typos)
2. **Run fuzzy search** to find matching postcodes with confidence scores
3. **Present suggestions** to user for confirmation
4. **Await confirmation** before proceeding with search
5. **Store confirmed postcode** for subsequent searches

### Parameter Extraction
The system automatically extracts these parameters from natural language:
- **postcode**: UK postcode (any format, typos handled by fuzzy search)
- **speed_in_mb**: Speed preference (10Mb, 30Mb, 55Mb, 100Mb)
- **contract_length**: Contract duration (12 months, 24 months, etc.)
- **phone_calls**: Phone service preference (evening/weekend, anytime, none)
- **providers**: Specific providers (BT, Sky, Virgin, etc.)
- **product_type**: Bundle type (broadband only, broadband+phone, etc.)
- **sort_by**: Sort preference (cheapest, fastest, recommended)

### Available Broadband Actions
- **fuzzy_search_postcode**: Find matching postcodes with confidence scores
- **confirm_postcode**: Confirm user's postcode selection
- **query**: Natural language broadband search with parameter extraction
- **generate_url**: Generate comparison URL with explicit parameters
- **get_recommendations**: AI-powered deal recommendations
- **compare_providers**: Compare deals from specific providers
- **get_cheapest**: Find cheapest available deal
- **get_fastest**: Find fastest available deal
- **refine_search**: Modify existing search criteria
- **list_providers**: Show all available broadband providers

## ✅ SUCCESSFUL INTERACTION PATTERNS

### Example: Complete Broadband Search Workflow
```
User: "Find broadband deals in London SW1A"
AI: Step 1 - Fuzzy postcode search
    - Shows: "SW1A 1AA (95% confidence), SW1A 1AB (87% confidence)"
    - Asks: "Please confirm which postcode you'd like to use"

User: "Use the first one"
AI: Step 2 - Postcode confirmation
    - Confirms: "Using postcode SW1A 1AA"
    - Generates URL with default parameters
    - Offers: "You can now ask for recommendations, cheapest deals, etc."

User: "Show me 100Mb deals"
AI: Step 3 - Refined search
    - Uses confirmed postcode SW1A 1AA
    - Updates speed to 100Mb
    - Shows matching deals and recommendations
```

### Example: Provider Comparison
```
User: "Compare BT and Sky in my area"
AI: Uses broadband_action with action_type="compare_providers"
    - Requires postcode confirmation first (if not already done)
    - Shows deals from both providers side by side
    - Provides comparison insights
```

Remember: You are a voice assistant specialized in helping users find the best broadband deals through intelligent postcode validation, natural language understanding, and AI-powered recommendations. Be efficient, helpful, and always prioritize the fuzzy postcode validation workflow for accurate results.'''