#!/usr/bin/env python3
"""
AI-Powered Parameter Extraction Service for Broadband Tool.
Uses Google Gemini with structured output for accurate natural language understanding.
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import lru_cache
from pydantic import BaseModel, Field, validator
from loguru import logger
import google.generativeai as genai

# Import broadband constants
from voice_agent.broadband_url_generator import BroadbandConstants


# ============================================================================
# PYDANTIC MODELS FOR STRUCTURED OUTPUT
# ============================================================================

class BroadbandParameters(BaseModel):
    """
    Structured output schema for broadband parameter extraction.
    Gemini will be forced to respond in this exact format.
    """
    
    postcode: Optional[str] = Field(
        None, 
        description="UK postcode or location name (e.g., 'SW1A 1AA', 'London', 'Manchester'). Extract any location reference."
    )
    
    speed_in_mb: Optional[str] = Field(
        None,
        description="Internet speed preference. Must be one of: '10Mb', '30Mb', '55Mb', '100Mb'. Extract from phrases like '100Mb', 'superfast', 'ultrafast', 'fast fibre'."
    )
    
    contract_length: Optional[str] = Field(
        None,
        description="Contract duration. Can be single value like '12 months' or multiple values like '12 months,24 months'. Extract from phrases like '12 month contract', '12 or 24 months'."
    )
    
    phone_calls: Optional[str] = Field(
        None,
        description="Phone call preference. Must be one of: 'Cheapest', 'Show me everything', 'Evening and Weekend', 'Anytime', 'No inclusive', 'No phone line'."
    )
    
    providers: Optional[str] = Field(
        None,
        description="Comma-separated list of provider names (e.g., 'BT,Sky,Virgin Media'). Extract any mentioned ISP or telecom provider."
    )
    
    current_provider: Optional[str] = Field(
        None,
        description="User's current broadband provider (for switching deals). Extract from phrases like 'currently with BT', 'switching from Sky'."
    )
    
    product_type: Optional[str] = Field(
        None,
        description="Product bundle type. Must be one of: 'broadband', 'broadband,phone', 'broadband,tv', 'broadband,phone,tv'."
    )
    
    sort_by: Optional[str] = Field(
        None,
        description="Sorting preference. Must be one of: 'Avg. Monthly Cost', 'Speed', 'Recommended'. Extract from 'cheapest', 'fastest', 'recommended'."
    )
    
    new_line: Optional[str] = Field(
        None,
        description="Whether user needs a new phone line. Set to 'NewLine' if mentioned, empty string otherwise."
    )
    
    intent: Optional[str] = Field(
        None,
        description="User's primary intent. One of: 'search', 'compare', 'filter', 'get_cheapest', 'get_fastest', 'get_recommendations', 'refine_search'."
    )
    
    confidence: Optional[float] = Field(
        None,
        description="Confidence score (0.0-1.0) in the extraction accuracy."
    )
    
    @validator('speed_in_mb')
    def validate_speed(cls, v):
        """Validate speed is in allowed list."""
        if v and v not in BroadbandConstants.VALID_SPEEDS:
            # Try to normalize common variations
            speed_map = {
                'fast': '30Mb',
                'superfast': '55Mb',
                'ultrafast': '100Mb',
                'standard': '10Mb'
            }
            normalized = speed_map.get(v.lower(), '30Mb')
            logger.info(f"🔧 Normalized speed '{v}' to '{normalized}'")
            return normalized
        return v
    
    @validator('phone_calls')
    def validate_phone_calls(cls, v):
        """Validate phone calls is in allowed list."""
        if v and v not in BroadbandConstants.VALID_PHONE_CALLS:
            # Try to normalize common variations
            call_map = {
                'unlimited': 'Anytime',
                'evening': 'Evening and Weekend',
                'weekend': 'Evening and Weekend',
                'none': 'No inclusive',
                'no calls': 'No inclusive'
            }
            normalized = call_map.get(v.lower(), 'Show me everything')
            logger.info(f"🔧 Normalized phone calls '{v}' to '{normalized}'")
            return normalized
        return v
    
    @validator('sort_by')
    def validate_sort(cls, v):
        """Validate and normalize sort preference."""
        if v:
            sort_map = {
                'cheapest': 'Avg. Monthly Cost',
                'fastest': 'Speed',
                'recommended': 'Recommended',
                'price': 'Avg. Monthly Cost',
                'cost': 'Avg. Monthly Cost'
            }
            normalized = sort_map.get(v.lower(), v)
            if normalized not in ['Avg. Monthly Cost', 'Speed', 'Recommended']:
                return 'Recommended'
            return normalized
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with only non-None values."""
        return {k: v for k, v in self.dict().items() if v is not None and k != 'confidence'}


# ============================================================================
# AI PARAMETER EXTRACTION SERVICE
# ============================================================================

class AIParameterExtractor:
    """
    AI-powered parameter extraction using Google Gemini with structured output.
    Provides more accurate and flexible natural language understanding than regex.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the AI parameter extractor.
        
        Args:
            api_key: Google API key (will use env var if not provided)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required for AI parameter extraction")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Use fast and efficient model
        self.model_name = "gemini-2.0-flash-exp"
        
        # Initialize model with structured output
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.1,  # Low temperature for consistent extraction
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
                "response_mime_type": "application/json",
            }
        )
        
        # Cache for recent extractions (query -> result)
        self._cache: Dict[str, BroadbandParameters] = {}
        self._cache_max_size = 100
        
        logger.info(f"✅ AI Parameter Extractor initialized with model: {self.model_name}")
    
    def _build_extraction_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Build the prompt for parameter extraction.
        
        Args:
            query: User's natural language query
            context: Optional context (previous parameters, user preferences)
        
        Returns:
            Formatted prompt for Gemini
        """
        
        context_info = ""
        if context:
            context_info = f"\n\n**Previous Context:**\n{json.dumps(context, indent=2)}"
        
        prompt = f"""You are an expert AI assistant that extracts broadband search parameters from natural language queries.

**Task:** Extract all relevant broadband search parameters from the user's query below. Use the exact format specified in the schema.

**User Query:** "{query}"
{context_info}

**Valid Options:**

Speed: {', '.join(BroadbandConstants.VALID_SPEEDS)}
- "10Mb" for standard broadband
- "30Mb" for fast fibre
- "55Mb" for superfast fibre
- "100Mb" for ultrafast fibre

Contract Lengths: {', '.join(BroadbandConstants.VALID_CONTRACT_LENGTHS)}
- Can be single value: "12 months"
- Can be multiple values: "12 months,24 months" (comma-separated, no spaces)

Phone Calls: {', '.join(BroadbandConstants.VALID_PHONE_CALLS)}

Product Types:
- "broadband" (broadband only)
- "broadband,phone" (broadband and phone)
- "broadband,tv" (broadband and TV)
- "broadband,phone,tv" (all three)

Providers: {', '.join(BroadbandConstants.VALID_PROVIDERS[:20])} (and more)
- Extract any mentioned provider names
- Can be comma-separated list: "BT,Sky,Virgin Media"

Sort By:
- "Avg. Monthly Cost" for cheapest/price-focused queries
- "Speed" for fastest/speed-focused queries
- "Recommended" for general queries

**Instructions:**
1. Extract ONLY parameters explicitly mentioned or strongly implied in the query
2. Leave fields as null if not mentioned
3. For contract_length with multiple values, format as: "12 months,24 months" (comma-separated, no spaces after comma)
4. For providers, use comma-separated format: "BT,Sky" (no spaces after comma)
5. Normalize provider names to match the valid list (e.g., "virgin" → "Virgin Media")
6. For speed, use exact format: "10Mb", "30Mb", "55Mb", or "100Mb"
7. Set confidence between 0.0 and 1.0 based on clarity of the query
8. Detect the user's primary intent (search, compare, filter, get_cheapest, get_fastest, etc.)

**Output Format:**
Return a valid JSON object matching the BroadbandParameters schema. Only include fields that were mentioned in the query.

**Examples:**

Query: "Find broadband in Manchester with 100Mb speed"
{{
  "postcode": "Manchester",
  "speed_in_mb": "100Mb",
  "intent": "search",
  "confidence": 0.95
}}

Query: "Show me deals with BT and Sky for 12 or 24 month contracts"
{{
  "providers": "BT,Sky",
  "contract_length": "12 months,24 months",
  "intent": "search",
  "confidence": 0.9
}}

Query: "What's the cheapest broadband in SW1A 1AA?"
{{
  "postcode": "SW1A 1AA",
  "sort_by": "Avg. Monthly Cost",
  "intent": "get_cheapest",
  "confidence": 1.0
}}

Query: "I'm currently with Virgin Media and want to switch"
{{
  "current_provider": "Virgin Media",
  "intent": "search",
  "confidence": 0.9
}}

Now extract parameters from the user's query above. Return ONLY the JSON object, no additional text."""
        
        return prompt
    
    async def extract_parameters(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> BroadbandParameters:
        """
        Extract parameters from natural language query using AI.
        
        Args:
            query: User's natural language query
            context: Optional context (previous parameters, user preferences)
            use_cache: Whether to use cached results for repeated queries
        
        Returns:
            BroadbandParameters object with extracted values
        """
        
        # Check cache first
        cache_key = f"{query.lower().strip()}_{json.dumps(context) if context else ''}"
        if use_cache and cache_key in self._cache:
            logger.info(f"🎯 Using cached parameter extraction for: {query[:50]}...")
            return self._cache[cache_key]
        
        try:
            # Build prompt
            prompt = self._build_extraction_prompt(query, context)
            
            # Call Gemini API
            logger.info(f"🤖 Extracting parameters with AI from: {query[:50]}...")
            start_time = datetime.now()
            
            response = await self.model.generate_content_async(prompt)
            
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"⚡ AI extraction completed in {elapsed_ms:.0f}ms")
            
            # Parse response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            # Parse JSON
            params_dict = json.loads(response_text)
            
            # Validate with Pydantic
            params = BroadbandParameters(**params_dict)
            
            # Cache result
            if use_cache:
                self._cache[cache_key] = params
                # Limit cache size
                if len(self._cache) > self._cache_max_size:
                    # Remove oldest entry
                    self._cache.pop(next(iter(self._cache)))
            
            logger.info(f"✅ Successfully extracted parameters: {params.to_dict()}")
            return params
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse AI response as JSON: {e}")
            logger.error(f"Response text: {response_text[:200]}")
            # Return empty parameters on failure
            return BroadbandParameters(confidence=0.0)
        
        except Exception as e:
            logger.error(f"❌ AI parameter extraction failed: {e}")
            # Return empty parameters on failure
            return BroadbandParameters(confidence=0.0)
    
    def extract_parameters_sync(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> BroadbandParameters:
        """
        Synchronous version of parameter extraction.
        
        Args:
            query: User's natural language query
            context: Optional context (previous parameters, user preferences)
            use_cache: Whether to use cached results
        
        Returns:
            BroadbandParameters object with extracted values
        """
        
        # Check cache first
        cache_key = f"{query.lower().strip()}_{json.dumps(context) if context else ''}"
        if use_cache and cache_key in self._cache:
            logger.info(f"🎯 Using cached parameter extraction for: {query[:50]}...")
            return self._cache[cache_key]
        
        try:
            # Build prompt
            prompt = self._build_extraction_prompt(query, context)
            
            # Call Gemini API (synchronous)
            logger.info(f"🤖 Extracting parameters with AI from: {query[:50]}...")
            start_time = datetime.now()
            
            response = self.model.generate_content(prompt)
            
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"⚡ AI extraction completed in {elapsed_ms:.0f}ms")
            
            # Parse response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            # Parse JSON
            params_dict = json.loads(response_text)
            
            # Validate with Pydantic
            params = BroadbandParameters(**params_dict)
            
            # Cache result
            if use_cache:
                self._cache[cache_key] = params
                # Limit cache size
                if len(self._cache) > self._cache_max_size:
                    # Remove oldest entry
                    self._cache.pop(next(iter(self._cache)))
            
            logger.info(f"✅ Successfully extracted parameters: {params.to_dict()}")
            return params
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse AI response as JSON: {e}")
            if 'response_text' in locals():
                logger.error(f"Response text: {response_text[:200]}")
            # Return empty parameters on failure
            return BroadbandParameters(confidence=0.0)
        
        except Exception as e:
            logger.error(f"❌ AI parameter extraction failed: {e}")
            # Return empty parameters on failure
            return BroadbandParameters(confidence=0.0)
    
    def clear_cache(self):
        """Clear the parameter extraction cache."""
        self._cache.clear()
        logger.info("🗑️ Parameter extraction cache cleared")


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_extractor_instance: Optional[AIParameterExtractor] = None


def get_parameter_extractor() -> AIParameterExtractor:
    """
    Get or create the singleton parameter extractor instance.
    
    Returns:
        AIParameterExtractor instance
    """
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = AIParameterExtractor()
    return _extractor_instance

