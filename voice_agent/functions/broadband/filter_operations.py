"""
Filter Operations - Handle data filtering and search refinement.
Provides functions for filtering deals and refining search criteria.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

from .helpers import normalize_contract_length


async def handle_filter_data(
    user_id: str,
    filter_speed: str = None,
    filter_providers: str = None,
    filter_contract: str = None,
    filter_phone_calls: str = None,
    filter_new_line: str = None,
    context: str = None,
    conversation_state: Dict = None,
    filter_state: Dict = None,
    send_websocket_fn=None,
    create_output_fn=None
) -> str:
    """
    Handle filtering of scraped data with new criteria.
    
    Args:
        user_id: User ID
        filter_speed: Speed filter
        filter_providers: Providers filter
        filter_contract: Contract length filter
        filter_phone_calls: Phone calls filter
        filter_new_line: New line filter
        context: Additional context
        conversation_state: Conversation state dictionary
        filter_state: Filter state dictionary
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Dictionary with filtered results or error message
    """
    try:
        # Get current scraped data
        if not conversation_state or user_id not in conversation_state or 'scraped_data' not in conversation_state[user_id]:
            return "❌ Please scrape data first before applying filters."
        
        data = conversation_state[user_id]['scraped_data']
        if not data or 'error' in data or data.get('total_deals', 0) == 0:
            return "❌ No data available to filter."
        
        deals = data.get('deals', [])
        
        if not deals:
            return "❌ No deals available to filter."
        
        # Get current filter state
        if filter_state is not None:
            if user_id not in filter_state:
                filter_state[user_id] = {}
            
            # Update filters
            if filter_speed:
                filter_state[user_id]['speed'] = filter_speed
            if filter_providers:
                filter_state[user_id]['providers'] = filter_providers
            if filter_contract:
                filter_state[user_id]['contract'] = filter_contract
            if filter_phone_calls:
                filter_state[user_id]['phone_calls'] = filter_phone_calls
            if filter_new_line:
                filter_state[user_id]['new_line'] = filter_new_line
            
            # Apply filters to deals
            filtered_deals = apply_filters(deals, filter_state[user_id])
        else:
            # No filter state provided, return all deals
            filtered_deals = deals
        
        # Create structured output
        if send_websocket_fn and create_output_fn:
            structured_output = create_output_fn(
                user_id=user_id,
                action_type="data_filtered",
                param="total_filtered",
                value=str(len(filtered_deals)),
                interaction_type="data_filtering",
                clicked=True,
                element_name="filter_data",
                context=context,
                filtered_data=filtered_deals,
                applied_filters=filter_state[user_id] if filter_state else {},
                total_filtered=len(filtered_deals)
            )
            
            await send_websocket_fn(
                message_type="filter_action",
                action="data_filtered",
                data=structured_output
            )
        
        # Return structured data
        return {
            'status': 'success',
            'message': f'Filtered to {len(filtered_deals)} deals',
            'data': {
                'total_filtered': len(filtered_deals),
                'filtered_deals': filtered_deals[:10],  # Top 10 filtered deals
                'applied_filters': filter_state[user_id] if filter_state else {},
                'total_original': len(deals)
            },
            'suggestions': [
                'Get recommendations from filtered results',
                'Compare filtered deals',
                'Find cheapest/fastest from filtered results',
                'Apply additional filters'
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error filtering data: {e}")
        return f"❌ Error filtering data: {str(e)}"


def apply_filters(deals: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """
    Apply filters to the deals list.
    
    Args:
        deals: List of deals to filter
        filters: Dictionary of filter criteria
        
    Returns:
        Filtered list of deals
    """
    filtered_deals = deals
    
    # Filter by speed
    if 'speed' in filters:
        target_speed = int(filters['speed'].replace('Mb', ''))
        filtered_deals = [deal for deal in filtered_deals if int(deal['speed']['numeric']) >= target_speed]
    
    # Filter by providers
    if 'providers' in filters and filters['providers']:
        provider_list = [p.strip() for p in filters['providers'].split(',')]
        filtered_deals = [deal for deal in filtered_deals if deal['provider']['name'] in provider_list]
    
    # Filter by contract length
    if 'contract' in filters:
        target_contract = filters['contract']
        filtered_deals = [deal for deal in filtered_deals if target_contract in deal['contract']['length_months']]
    
    # Filter by phone calls
    if 'phone_calls' in filters and filters['phone_calls'] != 'Show me everything':
        target_calls = filters['phone_calls']
        filtered_deals = [deal for deal in filtered_deals if target_calls.lower() in deal['features']['phone_calls'].lower()]
    
    # Note: new_line filter is a URL-level parameter, not applicable to individual deals
    
    return filtered_deals


async def handle_refine_search(
    user_id: str,
    contract_length: str = None,
    context: str = None,
    conversation_state: Dict = None,
    url_generator=None,
    send_websocket_fn=None,
    create_output_fn=None
) -> str:
    """
    Handle search refinement.
    
    Args:
        user_id: User ID
        contract_length: New contract length filter
        context: Additional context
        conversation_state: Conversation state dictionary
        url_generator: URL generator service
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Refinement options or new search URL
    """
    try:
        if not conversation_state or user_id not in conversation_state:
            # No previous search found - treat as new search
            logger.info(f"🔄 No previous search found for user {user_id}, performing new search")
            
            if contract_length and url_generator:
                # Normalize contract length
                normalized_contract = normalize_contract_length(contract_length) if contract_length else None
                
                # Get postcode from context or use default
                postcode = conversation_state.get(user_id, {}).get('confirmed_postcode', 'E14 9WB') if conversation_state else 'E14 9WB'
                
                # Create minimal extracted params
                extracted_params = {
                    'postcode': postcode,
                    'contract_length': normalized_contract
                }
                
                # Generate URL
                url = url_generator.generate_url(extracted_params)
                
                # Store conversation state
                if conversation_state is not None:
                    conversation_state[user_id] = {
                        'query': f"Refine search with contract: {contract_length}",
                        'extracted_params': extracted_params,
                        'generated_url': url,
                        'last_action': 'refine_search',
                        'timestamp': datetime.now().isoformat()
                    }
                
                if create_output_fn:
                    return create_output_fn(
                        user_id=user_id,
                        action_type="url_generated",
                        param="url,contract_length",
                        value=f"{url},{contract_length}",
                        interaction_type="url_generation",
                        current_page="broadband",
                        previous_page=None,
                        clicked=False,
                        element_name="refine_search",
                        context=context,
                        extracted_params=extracted_params,
                        generated_url=url
                    )
                else:
                    return f"✅ Generated URL with contract: {contract_length}\n{url}"
            else:
                return "❌ No previous search found and no contract length provided. Please provide search parameters first."
        
        state = conversation_state[user_id]
        
        # Prepare refinement options
        current_params = {}
        refinement_options = {
            'speed': 'I want 100Mb speed or make it faster',
            'contract': 'change to 24 months or shorter contract',
            'providers': 'include BT and Sky or only Virgin Media',
            'price_range': 'under £30 per month or cheapest available',
            'phone_calls': 'add evening calls or no phone line'
        }
        
        if 'extracted_params' in state:
            params = state['extracted_params']
            current_params = {
                'postcode': params.get('postcode', 'Not set'),
                'speed': params.get('speed_in_mb', 'Not set'),
                'contract': params.get('contract_length', 'Not set'),
                'phone_calls': params.get('phone_calls', 'Not set')
            }
        
        # Create structured output
        if send_websocket_fn and create_output_fn:
            structured_output = create_output_fn(
                user_id=user_id,
                action_type="refinement_options",
                param="refinement_available",
                value="true",
                interaction_type="refinement",
                clicked=True,
                element_name="refine_search",
                context=context,
                current_parameters=current_params,
                refinement_options=refinement_options
            )
            
            await send_websocket_fn(
                message_type="refinement_action",
                action="refinement_options",
                data=structured_output
            )
        
        # Return structured data for search refinement
        return {
            'status': 'refinement_options',
            'message': 'Here are your search refinement options',
            'data': {
                'current_parameters': current_params,
                'refinement_options': refinement_options
            },
            'suggestions': [
                'Specify what you want to change',
                'Use natural language like "make it faster"',
                'Try different combinations'
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error in refine search: {e}")
        return f"❌ Error refining search: {str(e)}"

