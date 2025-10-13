"""
URL Generator Service - Handles broadband comparison URL generation.
Wraps the broadband_url_generator module for clean service-oriented architecture.
"""

import sys
import os
from typing import Dict, Optional
from loguru import logger

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from voice_agent.broadband_url_generator import (
        BroadbandURLGenerator,
        BroadbandConstants,
        BroadbandSearchParams,
        ParameterValidator,
        URLEncoder,
        InvalidPostcodeError,
        InvalidSpeedError,
        InvalidContractLengthError,
        InvalidPhoneCallsError,
        InvalidProductTypeError,
        InvalidProviderError,
        InvalidSortOptionError,
        InvalidNewLineError
    )
    URL_GENERATOR_AVAILABLE = True
except ImportError as e:
    URL_GENERATOR_AVAILABLE = False
    logger.warning(f"⚠️ URL generator module not available: {e}")


class URLGeneratorService:
    """
    Service for generating broadband comparison URLs.
    Provides a clean interface for URL construction and validation.
    """
    
    def __init__(self):
        """Initialize the URL generator service."""
        self.generator = None
        
        if URL_GENERATOR_AVAILABLE:
            try:
                self.generator = BroadbandURLGenerator()
                logger.info("✅ URL generator service initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize URL generator: {e}")
                self.generator = None
        else:
            logger.warning("⚠️ URL generator not available")
    
    def generate_url(self, params: Dict) -> str:
        """
        Generate a broadband comparison URL from parameters.
        
        Args:
            params: Dictionary of search parameters
            
        Returns:
            Generated URL string
        """
        if not self.generator:
            return self._get_fallback_url(params)
        
        try:
            # Extract parameters
            postcode = params.get('postcode', '')
            speed = params.get('speed_in_mb') or params.get('speed')
            contract = params.get('contract_length')
            providers = params.get('providers')
            phone_calls = params.get('phone_calls')
            product_type = params.get('product_type')
            sort_by = params.get('sort_by')
            
            # Generate URL using the generator
            url = self.generator.generate_url(
                postcode=postcode,
                speed_in_mb=speed,
                contract_length=contract,
                providers=providers,
                phone_calls=phone_calls,
                product_type=product_type,
                sort_by=sort_by
            )
            
            logger.info(f"✅ Generated URL for postcode: {postcode}")
            return url
            
        except Exception as e:
            logger.error(f"❌ URL generation error: {e}")
            return self._get_fallback_url(params)
    
    def validate_parameters(self, params: Dict) -> tuple[bool, Optional[str]]:
        """
        Validate broadband search parameters.
        
        Args:
            params: Dictionary of parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not URL_GENERATOR_AVAILABLE:
            return True, None  # Skip validation if generator not available
        
        try:
            # Validate required parameters
            if not params.get('postcode'):
                return False, "Postcode is required"
            
            # Validate speed if provided
            if params.get('speed_in_mb') or params.get('speed'):
                speed = params.get('speed_in_mb') or params.get('speed')
                if not self._is_valid_speed(speed):
                    return False, f"Invalid speed: {speed}"
            
            # Validate contract length if provided
            if params.get('contract_length'):
                contract = params.get('contract_length')
                if not self._is_valid_contract(contract):
                    return False, f"Invalid contract length: {contract}"
            
            # Validate providers if provided
            if params.get('providers'):
                providers = params.get('providers')
                if isinstance(providers, str):
                    providers = [p.strip() for p in providers.split(',')]
                for provider in providers:
                    if not self._is_valid_provider(provider):
                        return False, f"Invalid provider: {provider}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"❌ Parameter validation error: {e}")
            return False, str(e)
    
    def _is_valid_speed(self, speed: str) -> bool:
        """Check if speed value is valid."""
        if not URL_GENERATOR_AVAILABLE:
            return True
        
        valid_speeds = BroadbandConstants.VALID_SPEEDS
        return speed in valid_speeds
    
    def _is_valid_contract(self, contract: str) -> bool:
        """Check if contract length is valid."""
        if not URL_GENERATOR_AVAILABLE:
            return True
        
        valid_contracts = BroadbandConstants.VALID_CONTRACT_LENGTHS
        return contract in valid_contracts
    
    def _is_valid_provider(self, provider: str) -> bool:
        """Check if provider name is valid."""
        if not URL_GENERATOR_AVAILABLE:
            return True
        
        valid_providers = BroadbandConstants.VALID_PROVIDERS
        # Case-insensitive check
        return any(provider.lower() == vp.lower() for vp in valid_providers)
    
    def _get_fallback_url(self, params: Dict) -> str:
        """
        Generate a fallback URL when generator is unavailable.
        
        Args:
            params: Dictionary of parameters
            
        Returns:
            Basic URL string
        """
        postcode = params.get('postcode', 'E14 9WB')
        base_url = "https://broadband.justmovein.co/packages"
        
        # Simple URL encoding
        from urllib.parse import quote_plus
        encoded_postcode = quote_plus(postcode)
        
        return f"{base_url}?location={encoded_postcode}"
    
    def get_available_speeds(self) -> list:
        """Get list of available speed options."""
        if URL_GENERATOR_AVAILABLE:
            return BroadbandConstants.VALID_SPEEDS
        return ["10Mb", "50Mb", "100Mb", "200Mb", "500Mb", "1000Mb"]
    
    def get_available_contracts(self) -> list:
        """Get list of available contract lengths."""
        if URL_GENERATOR_AVAILABLE:
            return BroadbandConstants.VALID_CONTRACT_LENGTHS
        return ["12 months", "18 months", "24 months"]
    
    def get_available_providers(self) -> list:
        """Get list of available providers."""
        if URL_GENERATOR_AVAILABLE:
            return BroadbandConstants.VALID_PROVIDERS
        return ["BT", "Sky", "Virgin Media", "TalkTalk", "Plusnet", "Vodafone"]
    
    def get_available_phone_calls(self) -> list:
        """Get list of available phone call options."""
        if URL_GENERATOR_AVAILABLE:
            return BroadbandConstants.VALID_PHONE_CALLS
        return ["Cheapest", "UK landline", "UK & mobile", "Unlimited"]
    
    def parse_url_parameters(self, url: str) -> Dict:
        """
        Parse parameters from a broadband comparison URL.
        
        Args:
            url: URL to parse
            
        Returns:
            Dictionary of extracted parameters
        """
        from urllib.parse import urlparse, parse_qs
        
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Extract common parameters
            result = {}
            
            if 'location' in params:
                result['postcode'] = params['location'][0]
            
            # Parse fragment parameters (after #)
            if parsed.fragment:
                fragment_params = parsed.fragment.split('?')
                if len(fragment_params) > 1:
                    fragment_query = parse_qs(fragment_params[1])
                    
                    if 'speedInMb' in fragment_query:
                        result['speed_in_mb'] = fragment_query['speedInMb'][0]
                    
                    if 'contractLength' in fragment_query:
                        result['contract_length'] = fragment_query['contractLength'][0]
                    
                    if 'providers' in fragment_query:
                        result['providers'] = fragment_query['providers'][0]
                    
                    if 'phoneCalls' in fragment_query:
                        result['phone_calls'] = fragment_query['phoneCalls'][0]
            
            return result
            
        except Exception as e:
            logger.error(f"❌ URL parsing error: {e}")
            return {}


# Global instance for easy access
_url_generator_service = None


def get_url_generator_service() -> URLGeneratorService:
    """
    Get or create the global URL generator service instance.
    
    Returns:
        URLGeneratorService instance
    """
    global _url_generator_service
    if _url_generator_service is None:
        _url_generator_service = URLGeneratorService()
    return _url_generator_service

