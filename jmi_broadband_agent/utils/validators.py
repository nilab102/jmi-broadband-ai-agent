#!/usr/bin/env python3
"""
Validation utilities for agent voice backend.
Contains common validation functions for user input and system parameters.
"""

import re
from typing import List, Optional
from jmi_broadband_agent.config.settings import get_settings


def validate_page_name(page_name: str) -> tuple[bool, str]:
    """
    Validate and normalize page name - now accepts any valid string.
    
    Args:
        page_name: Page name to validate
        
    Returns:
        Tuple of (is_valid, normalized_page_name)
    """
    if not page_name or not isinstance(page_name, str):
        return False, "Page name must be a non-empty string"
    
    # Normalize page name
    normalized = page_name.lower().strip().replace(" ", "-").replace("_", "-")
    
    # Accept any valid page name - no longer strict validation
    return True, normalized




def validate_api_key(api_key: str) -> tuple[bool, str]:
    """
    Validate Google API key format.
    
    Args:
        api_key: API key to validate
        
    Returns:
        Tuple of (is_valid, error_message_if_invalid)
    """
    if not api_key or not isinstance(api_key, str):
        return False, "API key must be a non-empty string"
    
    # Check for common placeholder patterns
    placeholders = ["your_", "ai...", "example", "placeholder", "here", "key_here"]
    
    key_lower = api_key.lower()
    for placeholder in placeholders:
        if placeholder in key_lower:
            return False, f"API key appears to be a placeholder containing '{placeholder}'"
    
    # Basic format validation for Google API key
    if not api_key.startswith("AI"):
        return False, "Google API key must start with 'AI'"
    
    if len(api_key) < 20:
        return False, "Google API key too short"
    
    return True, "Valid API key"


def validate_action_type(action_type: str, current_page: Optional[str] = None) -> tuple[bool, str]:
    """
    Validate action type and its compatibility with current page.
    
    Args:
        action_type: Action type to validate
        current_page: Current page name (optional)
        
    Returns:
        Tuple of (is_valid, error_message_if_invalid)
    """
    valid_actions = [
        "navigate", "click", "interact", 
        "search", "file_search", "file_upload", 
        "view_report", "generate_report"
    ]
    
    if not action_type or not isinstance(action_type, str):
        return False, "Action type must be a non-empty string"
    
    if action_type not in valid_actions:
        available_actions = ", ".join(valid_actions)
        return False, f"Invalid action type '{action_type}'. Available actions: {available_actions}"
    
    # Validate action compatibility with current page
    if current_page:
        settings = get_settings()
        page_config = settings.page_configs.get(current_page, {})
        
        if action_type == "search" and not page_config.get("search_enabled", False):
            return False, f"Database search not available on page '{current_page}'. Navigate to database-query page first."
        
        if action_type == "file_search" and not page_config.get("file_search_enabled", False):
            return False, f"File search not available on page '{current_page}'. Navigate to file-query page first."
        
        if action_type == "file_upload" and not page_config.get("file_upload_enabled", False):
            return False, f"File upload not available on page '{current_page}'. Navigate to file-query page first."
        
        if action_type in ["view_report", "generate_report"]:
            page_buttons = page_config.get("buttons", [])
            required_button = "view report" if action_type == "view_report" else "report generation"
            if required_button not in page_buttons:
                return False, f"Report operations not available on page '{current_page}'. Navigate to database-query page first."
    
    return True, "Valid action type"


def validate_context_format(context: str, action_type: str) -> tuple[bool, str]:
    """
    Validate context parameter format based on action type.
    
    Args:
        context: Context string to validate
        action_type: Action type that requires this context
        
    Returns:
        Tuple of (is_valid, error_message_if_invalid)
    """
    if not context:
        return True, "Context is optional"  # Context is generally optional
    
    if not isinstance(context, str):
        return False, "Context must be a string"
    
    # Validate specific context formats for certain actions
    if action_type == "click" and "set database" in context.lower():
        # Special validation for set database button - requires db_id
        if not re.search(r'db_id:\w+', context):
            return False, "Set database action requires db_id in context (e.g., 'db_id:123')"
    
    if action_type == "file_upload":
        # Validate file upload context format
        # Should contain file_descriptions and/or table_names
        if "file_descriptions:" not in context and "table_names:" not in context:
            return False, "File upload context should include file_descriptions and/or table_names"
    
    if action_type == "file_search":
        # Validate file search context format
        # May contain table_specific and tables information
        if "table_specific:" in context:
            if not re.search(r'table_specific:(true|false)', context.lower()):
                return False, "table_specific must be 'true' or 'false' in context"
    
    return True, "Valid context format"


def validate_search_query(query: str, action_type: str) -> tuple[bool, str]:
    """
    Validate search query based on action type.
    
    Args:
        query: Search query to validate
        action_type: Type of search action
        
    Returns:
        Tuple of (is_valid, error_message_if_invalid)
    """
    if not query or not isinstance(query, str):
        return False, "Search query must be a non-empty string"
    
    cleaned_query = query.strip()
    
    if len(cleaned_query) == 0:
        return False, "Search query cannot be empty after trimming whitespace"
    
    if len(cleaned_query) > 1000:
        return False, "Search query too long (max 1000 characters)"
    
    # Action-specific validation
    if action_type == "search":
        # Database search validation
        if len(cleaned_query) < 3:
            return False, "Database search query must be at least 3 characters"
    
    elif action_type == "file_search":
        # File search validation
        if len(cleaned_query) < 2:
            return False, "File search query must be at least 2 characters"
    
    return True, "Valid search query"


def validate_element_name(element_name: str, current_page: str) -> tuple[bool, str]:
    """
    Validate element name exists on current page.
    
    Args:
        element_name: Element name to validate
        current_page: Current page name
        
    Returns:
        Tuple of (is_valid, matched_element_or_error_message)
    """
    if not element_name or not isinstance(element_name, str):
        return False, "Element name must be a non-empty string"
    
    if not current_page:
        return False, "Current page must be specified"
    
    settings = get_settings()
    page_config = settings.page_configs.get(current_page, {})
    available_buttons = page_config.get("buttons", [])
    
    if not available_buttons:
        return False, f"Page '{current_page}' has no interactive elements"
    
    # Normalize element name for comparison
    element_name_normalized = element_name.lower().strip()
    
    # Find matching element
    for button in available_buttons:
        if button.lower() == element_name_normalized or element_name_normalized in button.lower():
            return True, button
    
    # No match found
    available_elements = ", ".join(available_buttons)
    return False, f"Element '{element_name}' not found on page '{current_page}'. Available elements: {available_elements}"


def validate_url(url: str) -> tuple[bool, str]:
    """
    Validate URL format and safety.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message_if_invalid_or_validated_url)
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"

    url = url.strip()

    if not url:
        return False, "URL cannot be empty after trimming whitespace"

    # Basic URL pattern validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)  # path

    if not url_pattern.match(url):
        return False, "Invalid URL format. URL must start with http:// or https://"

    # Additional safety checks
    if len(url) > 2000:
        return False, "URL too long (max 2000 characters)"

    # Check for potentially dangerous protocols
    dangerous_schemes = ['javascript:', 'data:', 'vbscript:', 'file:']
    if any(url.lower().startswith(scheme) for scheme in dangerous_schemes):
        return False, "Potentially unsafe URL scheme detected"

    return True, url


def sanitize_input(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize user input by removing potentially harmful content.

    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not input_str or not isinstance(input_str, str):
        return ""

    # Remove control characters and excessive whitespace
    sanitized = re.sub(r'[\x00-\x1f\x7f]', '', input_str)
    sanitized = re.sub(r'\s+', ' ', sanitized)
    sanitized = sanitized.strip()

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized