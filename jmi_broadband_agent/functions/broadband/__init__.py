"""
Broadband Tool Functions - Modular function library for broadband operations.
Organized into logical modules for better maintainability.
"""

# Helper functions (standalone utilities)
from .helpers import (
    create_structured_output,
    normalize_contract_length,
    normalize_contract_single,
    extract_contract_lengths,
    interpret_speed_adjective,
    interpret_phone_calls,
    interpret_product_type,
    interpret_sort_preference,
    validate_uk_postcode_format,
    format_currency,
    parse_currency,
    extract_numeric_speed
)

# Classes and their factory functions
from .parameter_extraction import (
    ParameterExtractor,
    create_parameter_extractor
)

from .postcode_operations import (
    PostcodeValidator,
    handle_postcode_confirmation
)

from .provider_matching import (
    ProviderMatcher,
    create_provider_matcher
)

from .recommendation_engine import (
    RecommendationEngine,
    create_recommendation_engine
)

# Handler functions from url_operations
from .url_operations import (
    handle_generate_url,
    handle_natural_language_query,
    handle_open_url
)

# Handler functions from data_operations
from .data_operations import (
    handle_scrape_data,
    handle_list_providers,
    handle_clarify_missing_params
)

# Handler functions from comparison_operations
from .comparison_operations import (
    handle_compare_providers,
    handle_get_cheapest,
    handle_get_fastest
)

# Handler functions from filter_operations
from .filter_operations import (
    apply_filters,
    handle_filter_data,
    handle_refine_search
)

__all__ = [
    # Helpers (standalone functions)
    'create_structured_output',
    'normalize_contract_length',
    'normalize_contract_single',
    'extract_contract_lengths',
    'interpret_speed_adjective',
    'interpret_phone_calls',
    'interpret_product_type',
    'interpret_sort_preference',
    'validate_uk_postcode_format',
    'format_currency',
    'parse_currency',
    'extract_numeric_speed',
    
    # Classes and factories
    'ParameterExtractor',
    'create_parameter_extractor',
    'PostcodeValidator',
    'ProviderMatcher',
    'create_provider_matcher',
    'RecommendationEngine',
    'create_recommendation_engine',
    
    # Handler functions
    'handle_postcode_confirmation',
    'handle_generate_url',
    'handle_natural_language_query',
    'handle_open_url',
    'handle_scrape_data',
    'handle_list_providers',
    'handle_clarify_missing_params',
    'handle_compare_providers',
    'handle_get_cheapest',
    'handle_get_fastest',
    'apply_filters',
    'handle_filter_data',
    'handle_refine_search',
]

