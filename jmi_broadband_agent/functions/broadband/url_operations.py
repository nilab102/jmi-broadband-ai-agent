"""
URL Operations - Handle URL generation and natural language query processing.
Provides functions for generating broadband comparison URLs and processing user queries.
"""

from typing import Dict, Optional, Any
from datetime import datetime
from loguru import logger

from .helpers import normalize_contract_length


async def handle_generate_url(
    user_id: str,
    postcode: str = None,
    speed_in_mb: str = None,
    contract_length: str = None,
    phone_calls: str = None,
    product_type: str = None,
    providers: str = None,
    current_provider: str = None,
    sort_by: str = None,
    new_line: str = None,
    context: str = None,
    url_generator=None,
    send_websocket_fn=None,
    create_output_fn=None,
    handle_clarify_fn=None
) -> str:
    """
    Handle URL generation with explicit parameters.
    
    Args:
        user_id: User ID
        postcode: Postcode
        speed_in_mb: Speed requirement
        contract_length: Contract length
        phone_calls: Phone calls preference
        product_type: Product type
        providers: Providers filter
        current_provider: Current provider
        sort_by: Sort preference
        new_line: New line option
        context: Additional context
        url_generator: URL generator service
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        handle_clarify_fn: Function to handle missing params clarification
        
    Returns:
        Success message with URL or error message
    """
    try:
        # Validate postcode
        if not postcode:
            if handle_clarify_fn:
                return await handle_clarify_fn(user_id, "Please provide your postcode.", context)
            return "❌ Please provide your postcode."
        
        # Set defaults for optional parameters
        params = {
            'postcode': postcode,
            'speed_in_mb': speed_in_mb or '30Mb',
            'contract_length': contract_length or '',
            'phone_calls': phone_calls or 'Show me everything',
            'product_type': product_type or 'broadband,phone',
            'providers': providers or '',
            'current_provider': current_provider or '',
            'sort_by': sort_by or 'Recommended',
            'new_line': new_line or ''
        }
        
        # Normalize contract_length to ensure correct URL formatting
        if params['contract_length']:
            params['contract_length'] = normalize_contract_length(params['contract_length'])
        
        url = url_generator.generate_url(params)
        
        if send_websocket_fn and create_output_fn:
            structured_output = create_output_fn(
                user_id=user_id,
                action_type="url_generated",
                param="url",
                value=url,
                interaction_type="url_generation",
                clicked=True,
                element_name="generate_url",
                context=context,
                generated_params=params
            )
            
            await send_websocket_fn(
                message_type="url_action",
                action="url_generated",
                data=structured_output
            )
        
        return f"✅ Broadband comparison URL generated!\n\n**URL:** {url}\n\n**Parameters:**\n" + \
               "\n".join([f"• {k}: {v}" for k, v in params.items() if v])
    
    except Exception as e:
        logger.error(f"❌ Error generating URL: {e}")
        return f"❌ Error generating URL: {str(e)}"


async def handle_natural_language_query(
    user_id: str,
    query: str,
    context: str = None,
    parameter_extractor=None,
    postcode_validator=None,
    url_generator=None,
    conversation_state: Dict = None,
    send_websocket_fn=None,
    create_output_fn=None,
    handle_clarify_fn=None,
    handle_filter_fn=None
) -> str:
    """
    Handle natural language broadband queries with AUTO-SELECT fuzzy postcode search.
    
    Args:
        user_id: User ID
        query: Natural language query
        context: Additional context
        parameter_extractor: Parameter extraction service
        postcode_validator: Postcode validation service
        url_generator: URL generator service
        conversation_state: Conversation state dictionary
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        handle_clarify_fn: Function to handle missing params
        handle_filter_fn: Function to handle filter data
        
    Returns:
        Response message with URL or error
    """
    try:
        # Extract parameters from query
        extracted_params = parameter_extractor.extract_parameters(query, skip_postcode_validation=True)
        
        # Check if we have enough information
        if 'postcode' not in extracted_params or not extracted_params['postcode']:
            if handle_clarify_fn:
                return await handle_clarify_fn(user_id, "I need your postcode to find broadband deals.", context)
            return "❌ I need your postcode to find broadband deals."
        
        # Check if there's already a confirmed postcode
        user_state = conversation_state.get(user_id, {}) if conversation_state else {}
        confirmed_postcode = user_state.get('confirmed_postcode')
        
        if not confirmed_postcode:
            # No confirmed postcode yet - trigger AUTO-SELECT fuzzy search
            raw_postcode = extracted_params['postcode']
            logger.info(f"🔍 New postcode detected: {raw_postcode} - triggering auto-select fuzzy search")
            
            # Run fuzzy search with auto-selection
            success, message, selected_postcode = await postcode_validator.search_with_fuzzy(
                user_id, raw_postcode, context,
                send_websocket_fn, create_output_fn
            )
            
            if not success or not selected_postcode:
                # Fuzzy search failed
                return message
            
            # Auto-selected successfully
            confirmed_postcode = selected_postcode
            logger.info(f"✅ Auto-selected postcode: {confirmed_postcode}")
        else:
            # Already have a confirmed postcode
            logger.info(f"✅ Using existing confirmed postcode: {confirmed_postcode}")
        
        # Use the confirmed/selected postcode
        extracted_params['postcode'] = confirmed_postcode
        
        # Check if this is a filter modification request
        has_filters = any(key.startswith('filter_') for key in extracted_params.keys())
        if has_filters and handle_filter_fn:
            return await handle_filter_fn(
                user_id,
                filter_speed=extracted_params.get('filter_speed'),
                filter_providers=extracted_params.get('filter_providers'),
                filter_contract=extracted_params.get('filter_contract'),
                filter_phone_calls=extracted_params.get('filter_phone_calls'),
                context=context
            )
        
        # Generate URL with extracted parameters
        # Ensure contract_length is normalized
        if 'contract_length' in extracted_params and extracted_params['contract_length']:
            extracted_params['contract_length'] = normalize_contract_length(extracted_params['contract_length'])
        
        url = url_generator.generate_url(extracted_params)
        
        # Store conversation state
        if conversation_state is not None:
            if user_id not in conversation_state:
                conversation_state[user_id] = {}
            conversation_state[user_id].update({
                'query': query,
                'extracted_params': extracted_params,
                'generated_url': url,
                'last_action': 'query',
                'timestamp': datetime.now().isoformat()
            })
        
        # Create structured output
        if send_websocket_fn and create_output_fn:
            structured_output = create_output_fn(
                user_id=user_id,
                action_type="url_generated",
                param="url,postcode",
                value=f"{url},{extracted_params['postcode']}",
                interaction_type="url_generation",
                clicked=False,
                element_name="generate_url",
                context=context,
                extracted_params=extracted_params,
                generated_url=url
            )
            
            await send_websocket_fn(
                message_type="url_action",
                action="url_generated",
                data=structured_output
            )
        
        response = f"✅ I've analyzed your query and generated a broadband comparison URL!\n\n" \
                  f"**Extracted Requirements:**\n" \
                  f"• Postcode: {extracted_params.get('postcode', 'Not specified')}\n" \
                  f"• Speed: {extracted_params.get('speed_in_mb', 'Not specified')}\n" \
                  f"• Contract: {extracted_params.get('contract_length', 'Not specified')}\n" \
                  f"• Phone Calls: {extracted_params.get('phone_calls', 'Not specified')}\n\n" \
                  f"**Generated URL:** {url}\n\n" \
                  f"You can now ask me to:\n" \
                  f"• Show recommendations for these parameters\n" \
                  f"• Compare specific providers\n" \
                  f"• Find the cheapest/fastest deals\n" \
                  f"• Refine your search criteria"
        
        return response
    
    except Exception as e:
        logger.error(f"❌ Error handling natural language query: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f"❌ Error processing query: {str(e)}"


async def handle_open_url(
    user_id: str,
    url: str = None,
    context: str = None,
    send_websocket_fn=None,
    create_output_fn=None
) -> str:
    """
    Handle opening a URL in a new tab.
    
    Args:
        user_id: User ID
        url: URL to open
        context: Additional context
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Success or error message
    """
    try:
        if not url:
            return "❌ Please provide a URL to open."
        
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            # Add https:// if no protocol specified
            url = f"https://{url}"
        
        # Create structured output
        if send_websocket_fn and create_output_fn:
            structured_output = create_output_fn(
                user_id=user_id,
                action_type="url_opened",
                param="url",
                value=url,
                interaction_type="url_open",
                clicked=True,
                element_name="open_url",
                context=context,
                url=url
            )
            
            await send_websocket_fn(
                message_type="url_action",
                action="open_url",
                data=structured_output
            )
        
        logger.info(f"🔗 Opening URL for user {user_id}: {url}")
        return f"✅ Opening URL: {url}"
    
    except Exception as e:
        logger.error(f"❌ Error opening URL: {e}")
        return f"❌ Error opening URL: {str(e)}"

