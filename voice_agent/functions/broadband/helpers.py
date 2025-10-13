"""
Helper Functions - Utility functions for broadband tool operations.
Contains data formatting, normalization, and interpretation functions.
"""

import re
import json
from datetime import datetime
from typing import Dict, Any
from loguru import logger

from voice_agent.broadband_url_generator import BroadbandConstants


def create_structured_output(
    user_id: str,
    action_type: str,
    param: str,
    value: str,
    interaction_type: str,
    current_page: str,
    previous_page: str = None,
    **additional_fields
) -> Dict[str, Any]:
    """
    Create clean structured output for broadband tool.
    
    Args:
        user_id: User ID
        action_type: Type of action performed
        param: Parameter name
        value: Parameter value
        interaction_type: Type of interaction
        current_page: Current page
        previous_page: Previous page
        **additional_fields: Additional fields to include
        
    Returns:
        Structured output dictionary
    """
    # Base output without unnecessary fields
    base_output = {
        "Action_type": action_type,
        "param": param,
        "value": value,
        "page": current_page,
        "previous_page": previous_page,
        "interaction_type": interaction_type,
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "success": True,
        "error_message": None
    }
    
    # Add additional fields
    merged_output = {**base_output, **additional_fields}
    
    # Convert list/dict values to JSON strings, but keep specific fields as proper JSON objects
    json_object_fields = {
        "scraped_data", "recommendations", "criteria", "total_recommendations",
        "providers_compared", "matching_deals", "total_matches", "cheapest_deal",
        "fastest_deal", "total_deals_analyzed", "current_parameters", "refinement_options",
        "required_parameters", "extracted_params", "generated_url", "generated_params",
        "filtered_data", "applied_filters", "total_filtered", "postcode_suggestions"
    }
    
    for key, val in merged_output.items():
        if isinstance(val, (list, dict)):
            if key not in json_object_fields:
                merged_output[key] = json.dumps(val)
    
    return merged_output


def normalize_contract_length(contract_length: str) -> str:
    """
    Normalize contract length parameter for URL formatting.
    Removes spaces around commas and validates format.
    
    Args:
        contract_length: Contract length string
        
    Returns:
        Normalized contract length string or empty string
    """
    if not contract_length or not contract_length.strip():
        return ''
    
    # If it already contains commas without spaces, return as-is
    if ',' in contract_length and ' ,' not in contract_length and ', ' not in contract_length:
        return contract_length
    
    # Use extract_contract_lengths to normalize
    return extract_contract_lengths(contract_length) or contract_length


def normalize_contract_single(match: str) -> str:
    """
    Normalize single contract length with correct singular/plural form.
    
    Args:
        match: The captured number as string
        
    Returns:
        Normalized contract length string ("1 month" or "X months")
    """
    number = int(match)
    return f"{number} month" if number == 1 else f"{number} months"


def extract_contract_lengths(match: str) -> str:
    """
    Extract and format multiple contract lengths from natural language.
    
    Handles patterns like:
    - "1 or 12 months" -> "1 month,12 months"
    - "12 and 24 months" -> "12 months,24 months"
    - "12, 24 months" -> "12 months,24 months"
    
    Args:
        match: The matched string from regex pattern
        
    Returns:
        Formatted contract length string for URL generation
    """
    if not match or not match.strip():
        return ""
    
    # Convert to lowercase for easier processing
    match_lower = match.lower().strip()
    
    # Split by common separators
    parts = re.split(r'\s*(?:,|or|and)\s*', match_lower)
    
    # Extract numbers from each part
    valid_lengths = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Extract number from this part
        num_match = re.search(r'(\d+)', part)
        if num_match:
            length_int = int(num_match.group(1))
            # Format with correct singular/plural form
            formatted_length = f"{length_int} month" if length_int == 1 else f"{length_int} months"
            # Only accept valid contract lengths
            if formatted_length in BroadbandConstants.VALID_CONTRACT_LENGTHS:
                valid_lengths.append(formatted_length)
    
    if not valid_lengths:
        return ""
    
    # Remove duplicates and sort
    valid_lengths = list(set(valid_lengths))
    valid_lengths.sort(key=lambda x: int(x.split()[0]))
    
    # Join with commas (no spaces)
    return ','.join(valid_lengths)


def interpret_speed_adjective(match: str) -> str:
    """
    Interpret speed adjectives to actual speed values.
    
    Args:
        match: Speed adjective (fast, superfast, ultrafast)
        
    Returns:
        Speed value in Mb format
    """
    speed_map = {
        'fast': '30Mb',
        'superfast': '55Mb',
        'ultrafast': '100Mb'
    }
    return speed_map.get(match.lower(), '30Mb')


def interpret_phone_calls(match) -> str:
    """
    Interpret phone call preferences from natural language.
    
    Args:
        match: Phone call preference string or tuple
        
    Returns:
        Standardized phone call preference
    """
    # Handle both string and tuple inputs from regex
    if isinstance(match, tuple):
        match = match[0] if match else ''
    
    call_map = {
        'evening': 'Evening and Weekend',
        'weekend': 'Evening and Weekend',
        'anytime': 'Anytime',
        'unlimited': 'Anytime'
    }
    return call_map.get(match.lower(), match.title())


def interpret_product_type(match) -> str:
    """
    Interpret product type combinations from natural language.
    
    Args:
        match: Product type string or tuple
        
    Returns:
        Formatted product type string
    """
    # Handle both string and tuple inputs from regex
    if isinstance(match, tuple):
        # For regex groups, filter out empty strings and join
        match_str = ' and '.join([str(m) for m in match if m and str(m).strip()])
    else:
        match_str = str(match).strip()
    
    # Clean the string and split
    match_str = match_str.lower()
    types = [t.strip() for t in match_str.split(' and ') if t.strip()]
    
    if len(types) == 1:
        return types[0]
    elif len(types) == 2:
        return f"{types[0]},{types[1]}"
    else:
        return "broadband,phone"


def interpret_sort_preference(match: str) -> str:
    """
    Interpret sort preferences from natural language.
    
    Args:
        match: Sort preference keyword
        
    Returns:
        Standardized sort option
    """
    sort_map = {
        'cheapest': 'Avg. Monthly Cost',
        'fastest': 'Speed',
        'recommended': 'Recommended'
    }
    return sort_map.get(match.lower(), 'Recommended')


def validate_uk_postcode_format(postcode: str) -> bool:
    """
    Validate UK postcode format using official regex pattern.
    
    Pattern covers:
    - GIR 0AA (special case)
    - Standard UK formats (A9 9AA, A99 9AA, AA9 9AA, AA99 9AA, A9A 9AA, AA9A 9AA)
    
    Args:
        postcode: Postcode string to validate
        
    Returns:
        True if valid UK postcode format, False otherwise
    """
    if not postcode or not postcode.strip():
        return False
    
    # UK postcode regex pattern (allows spaces)
    uk_postcode_pattern = r'^((GIR\s*0AA)|[A-Z]{1}\d{1}\s*\d{1}[A-Z]{2}|[A-Z]{2}\d{1}\s*\d{1}[A-Z]{2}|[A-Z]{1}\d{2}\s*\d{1}[A-Z]{2}|[A-Z]{2}\d{2}\s*\d{1}[A-Z]{2}|[A-Z]{2}\d{1}[A-Z]{1}\s*\d{1}[A-Z]{2}|[A-Z]{1}\d{1}[A-Z]{1}\s*\d{1}[A-Z]{2})$'
    
    # Normalize: uppercase and normalize spaces
    normalized = postcode.strip().upper()
    
    # Try with current spacing
    if re.match(uk_postcode_pattern, normalized, re.IGNORECASE):
        return True
    
    # Try without spaces (in case user didn't include space)
    no_space = normalized.replace(' ', '')
    # Add space before last 3 characters (standard UK format)
    if len(no_space) >= 5:
        formatted = no_space[:-3] + ' ' + no_space[-3:]
        if re.match(uk_postcode_pattern, formatted, re.IGNORECASE):
            return True
    
    return False


def format_currency(amount: float) -> str:
    """
    Format amount as currency string.
    
    Args:
        amount: Amount to format
        
    Returns:
        Formatted currency string (e.g., "£25.00")
    """
    return f"£{amount:.2f}"


def parse_currency(currency_str: str) -> float:
    """
    Parse currency string to float.
    
    Args:
        currency_str: Currency string (e.g., "£25.00", "$25", "25.00")
        
    Returns:
        Float value
    """
    try:
        # Remove currency symbols and commas
        cleaned = re.sub(r'[£$,]', '', currency_str.strip())
        return float(cleaned)
    except (ValueError, AttributeError):
        return 0.0


def extract_numeric_speed(speed_str: str) -> int:
    """
    Extract numeric speed value from string.
    
    Args:
        speed_str: Speed string (e.g., "100Mb", "1000 Mbps")
        
    Returns:
        Numeric speed value in Mb
    """
    try:
        match = re.search(r'(\d+)', speed_str)
        if match:
            return int(match.group(1))
        return 0
    except (ValueError, AttributeError):
        return 0

