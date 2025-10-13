"""
Data Operations - Handle data scraping, provider listing, and parameter clarification.
Provides functions for fetching broadband data and handling user requests.
"""

from typing import Dict, Optional, Any, List
from loguru import logger

from .helpers import normalize_contract_length


async def handle_scrape_data(
    user_id: str,
    postcode: str = None,
    speed_in_mb: str = None,
    contract_length: str = None,
    phone_calls: str = None,
    product_type: str = None,
    providers: str = None,
    current_provider: str = None,
    new_line: str = None,
    context: str = None,
    url_generator=None,
    scraper_service=None,
    scraped_data_cache: Dict = None,
    conversation_state: Dict = None,
    send_websocket_fn=None,
    create_output_fn=None
) -> str:
    """
    Handle data scraping for broadband recommendations.
    
    Args:
        user_id: User ID
        postcode: Postcode
        speed_in_mb: Speed requirement
        contract_length: Contract length
        phone_calls: Phone calls preference
        product_type: Product type
        providers: Providers filter
        current_provider: Current provider
        new_line: New line option
        context: Additional context
        url_generator: URL generator service
        scraper_service: Scraper service
        scraped_data_cache: Cache for scraped data
        conversation_state: Conversation state dictionary
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Dictionary with scraped data or error message
    """
    try:
        # Normalize contract_length
        normalized_contract = normalize_contract_length(contract_length or '')
        
        # Generate URL first
        params = {
            'postcode': postcode or 'E14 9WB',
            'speed_in_mb': speed_in_mb or '30Mb',
            'contract_length': normalized_contract,
            'phone_calls': phone_calls or 'Show me everything',
            'product_type': product_type or 'broadband,phone',
            'providers': providers or '',
            'current_provider': current_provider or '',
            'sort_by': 'Recommended',
            'new_line': new_line or ''
        }
        url = url_generator.generate_url(params)
        
        # Check cache first
        cache_key = f"{postcode}_{speed_in_mb}_{contract_length}_{providers}"
        if scraped_data_cache and cache_key in scraped_data_cache:
            data = scraped_data_cache[cache_key]
        else:
            # Scrape data using scraper service
            data = await scraper_service.scrape_url_fast_async(url)
            
            # Check if scraping was successful
            if data and 'error' not in data and data.get('total_deals', 0) > 0:
                if scraped_data_cache is not None:
                    scraped_data_cache[cache_key] = data
            elif data and 'error' in data:
                # Handle API failure gracefully
                error_msg = data.get('error', 'Unknown error occurred')
                note = data.get('note', '')
                
                if 'Browser scraping not available' in error_msg:
                    error_response = f"❌ Data scraping is currently limited in this environment. However, I've generated the comparison URL for you. {note}"
                else:
                    error_response = f"❌ Unable to fetch broadband data: {error_msg}. Please try again later or check your connection."
                
                # Store the error data
                if scraped_data_cache is not None:
                    scraped_data_cache[cache_key] = data
                return error_response
            else:
                # Handle empty results
                error_response = "❌ No broadband deals found for your criteria. Please try adjusting your search parameters."
                if scraped_data_cache is not None:
                    scraped_data_cache[cache_key] = data
                return error_response
        
        # Store in conversation state
        if conversation_state is not None:
            if user_id not in conversation_state:
                conversation_state[user_id] = {}
            conversation_state[user_id]['scraped_data'] = data
        
        # Create structured output
        if send_websocket_fn and create_output_fn:
            structured_output = create_output_fn(
                user_id=user_id,
                action_type="data_scraped",
                param="total_deals,location",
                value=f"{data.get('total_deals', 0)},{data.get('metadata', {}).get('location', 'Unknown')}",
                interaction_type="data_scraping",
                clicked=True,
                element_name="scrape_data",
                context=context,
                scraped_data=data,
                total_deals=data.get('total_deals', 0),
                location=data.get('metadata', {}).get('location', 'Unknown'),
                filters_applied=data.get('filters_applied', {})
            )
            
            await send_websocket_fn(
                message_type="data_action",
                action="data_scraped",
                data=structured_output
            )
        
        total_deals = data.get('total_deals', 0)
        if total_deals > 0:
            return {
                'status': 'success',
                'message': f'Successfully scraped {total_deals} broadband deals',
                'data': {
                    'total_deals': total_deals,
                    'location': data.get('metadata', {}).get('location', 'Unknown'),
                    'filters_applied': data.get('filters_applied', {}),
                    'deals': data.get('deals', [])
                },
                'suggestions': [
                    'Get recommendations based on your preferences',
                    'Compare specific providers',
                    'Find the cheapest or fastest deals'
                ]
            }
        else:
            return {
                'status': 'no_results',
                'message': 'No deals found for the specified criteria',
                'suggestions': [
                    'Try adjusting your search parameters',
                    'Change the speed requirement',
                    'Modify the contract length',
                    'Select different providers'
                ]
            }
    
    except Exception as e:
        logger.error(f"❌ Error scraping data: {e}")
        return f"❌ Error scraping data: {str(e)}"


async def handle_list_providers(
    user_id: str,
    context: str = None,
    valid_providers: List[str] = None,
    send_websocket_fn=None,
    create_output_fn=None
) -> str:
    """
    Handle listing all available broadband providers.
    
    Args:
        user_id: User ID
        context: Additional context
        valid_providers: List of valid provider names
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Formatted list of providers or error message
    """
    try:
        if not valid_providers:
            return "❌ No providers list available."
        
        # Create structured output
        if send_websocket_fn and create_output_fn:
            structured_output = create_output_fn(
                user_id=user_id,
                action_type="providers_listed",
                param="total_providers",
                value=str(len(valid_providers)),
                interaction_type="provider_listing",
                clicked=True,
                element_name="list_providers",
                context=context,
                providers_list=valid_providers,
                total_providers=len(valid_providers)
            )
            
            await send_websocket_fn(
                message_type="providers_action",
                action="providers_listed",
                data=structured_output
            )
        
        # Format response for user
        response = f"📱 **Available Broadband Providers ({len(valid_providers)} total):**\n\n"
        for i, provider in enumerate(valid_providers[:20], 1):  # Show first 20
            response += f"**{i}. {provider}**\n"
        
        if len(valid_providers) > 20:
            response += f"\n... and {len(valid_providers) - 20} more providers\n"
        
        response += "\n💡 You can specify providers like 'hyperoptic, bt' or 'all providers'"
        
        return response
    
    except Exception as e:
        logger.error(f"❌ Error listing providers: {e}")
        return f"❌ Error listing providers: {str(e)}"


async def handle_clarify_missing_params(
    user_id: str,
    custom_message: str = None,
    context: str = None,
    send_websocket_fn=None,
    create_output_fn=None
) -> str:
    """
    Handle missing parameter clarification.
    
    Args:
        user_id: User ID
        custom_message: Optional custom message
        context: Additional context
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Dictionary with clarification request
    """
    try:
        # Create structured output
        if send_websocket_fn and create_output_fn:
            structured_output = create_output_fn(
                user_id=user_id,
                action_type="clarification_needed",
                param="missing_parameters",
                value="postcode,speed,contract,phone_calls",
                interaction_type="clarification",
                clicked=False,
                element_name="clarify_missing_params",
                context=context,
                required_parameters={
                    'postcode': 'Your postcode or location (any format accepted)',
                    'speed': 'Speed preference (e.g., 30Mb, 55Mb, 100Mb)',
                    'contract': 'Contract length (e.g., 12 months, 24 months)',
                    'phone_calls': 'Phone calls (e.g., evening and weekend, anytime, none)'
                }
            )
            
            await send_websocket_fn(
                message_type="clarification_action",
                action="clarification_needed",
                data=structured_output
            )
        
        # Return structured data for parameter clarification
        message = custom_message or 'I need more information to help you find the best broadband deals'
        
        return {
            'status': 'needs_clarification',
            'message': message,
            'data': {
                'required_parameters': {
                    'postcode': 'Your postcode or location (any format accepted)',
                    'speed': 'Speed preference (e.g., 30Mb, 55Mb, 100Mb)',
                    'contract': 'Contract length (e.g., 12 months, 24 months)',
                    'phone_calls': 'Phone calls (e.g., evening and weekend, anytime, none)'
                }
            },
            'suggestions': [
                'Provide your postcode and preferences',
                'Use natural language like "Find deals in E14 9WB with 100Mb speed"',
                'Specify what you want to change or refine'
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error in clarify missing params: {e}")
        return f"❌ Error: {str(e)}"

