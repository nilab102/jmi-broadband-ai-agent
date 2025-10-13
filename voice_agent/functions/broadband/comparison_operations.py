"""
Comparison Operations - Handle provider comparisons and deal finding operations.
Provides functions for comparing providers, finding cheapest and fastest deals.
"""

from typing import Dict, List, Any, Optional
from loguru import logger


async def handle_compare_providers(
    user_id: str,
    providers: str,
    postcode: str = None,
    speed_in_mb: str = None,
    current_provider: str = None,
    new_line: str = None,
    context: str = None,
    conversation_state: Dict = None,
    scrape_data_fn=None,
    send_websocket_fn=None,
    create_output_fn=None
) -> str:
    """
    Handle provider comparison.
    
    Args:
        user_id: User ID
        providers: Comma-separated list of providers to compare
        postcode: Postcode
        speed_in_mb: Speed requirement
        current_provider: Current provider
        new_line: New line option
        context: Additional context
        conversation_state: Conversation state dictionary
        scrape_data_fn: Function to scrape data
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Dictionary with comparison results or error message
    """
    try:
        if not providers:
            return "❌ Please specify providers to compare."
        
        provider_list = [p.strip() for p in providers.split(',')]
        
        # Check if we have scraped data
        if not conversation_state or user_id not in conversation_state or 'scraped_data' not in conversation_state[user_id]:
            # Auto-scrape data if not available
            if scrape_data_fn:
                postcode = postcode or 'E14 9WB'
                scrape_result = await scrape_data_fn(
                    user_id=user_id,
                    postcode=postcode,
                    speed_in_mb=speed_in_mb,
                    contract_length=None,
                    phone_calls=None,
                    product_type=None,
                    providers=providers,
                    current_provider=current_provider,
                    new_line=new_line,
                    context=context
                )
                
                # If scraping returned an error message, return it
                if scrape_result and isinstance(scrape_result, str) and scrape_result.startswith("❌"):
                    return scrape_result
            else:
                return "❌ Unable to fetch broadband data. Please scrape data first."
        
        data = conversation_state[user_id]['scraped_data']
        if not data or 'error' in data or data.get('total_deals', 0) == 0:
            if data and 'error' in data and 'Browser scraping not available' in data.get('error', ''):
                return "❌ Data scraping is currently limited in this environment. Please use the generated URL to view deals directly."
            else:
                return "❌ Unable to fetch broadband data for provider comparison."
        
        deals = data.get('deals', [])
        
        # Filter deals by providers
        matching_deals = [deal for deal in deals if deal['provider']['name'] in provider_list]
        
        if not matching_deals:
            return f"❌ No deals found for providers: {', '.join(provider_list)}"
        
        # Create structured output
        if send_websocket_fn and create_output_fn:
            structured_output = create_output_fn(
                user_id=user_id,
                action_type="provider_comparison",
                param="providers_compared,total_matches",
                value=f"{', '.join(provider_list)},{len(matching_deals)}",
                interaction_type="provider_comparison",
                clicked=True,
                element_name="compare_providers",
                context=context,
                providers_compared=provider_list,
                matching_deals=matching_deals,
                total_matches=len(matching_deals)
            )
            
            await send_websocket_fn(
                message_type="comparison_action",
                action="provider_comparison",
                data=structured_output
            )
        
        # Return structured data
        return {
            'status': 'success',
            'message': f'Found {len(matching_deals)} deals for providers: {", ".join(provider_list)}',
            'data': {
                'providers_compared': provider_list,
                'matching_deals': matching_deals[:10],  # Top 10 matching deals
                'total_matches': len(matching_deals)
            },
            'suggestions': [
                'Compare specific deals',
                'Find the cheapest option among these',
                'Show fastest deals from these providers'
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error comparing providers: {e}")
        return f"❌ Error comparing providers: {str(e)}"


async def handle_get_cheapest(
    user_id: str,
    postcode: str = None,
    current_provider: str = None,
    new_line: str = None,
    context: str = None,
    conversation_state: Dict = None,
    scrape_data_fn=None,
    send_websocket_fn=None,
    create_output_fn=None
) -> str:
    """
    Handle cheapest deal requests.
    
    Args:
        user_id: User ID
        postcode: Postcode
        current_provider: Current provider
        new_line: New line option
        context: Additional context
        conversation_state: Conversation state dictionary
        scrape_data_fn: Function to scrape data
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Dictionary with cheapest deal or error message
    """
    try:
        # Check if we have scraped data
        if not conversation_state or user_id not in conversation_state or 'scraped_data' not in conversation_state[user_id]:
            # Scrape data if not available
            if scrape_data_fn:
                postcode = postcode or 'E14 9WB'
                scrape_result = await scrape_data_fn(
                    user_id=user_id,
                    postcode=postcode,
                    speed_in_mb=None,
                    contract_length=None,
                    phone_calls=None,
                    product_type=None,
                    providers=None,
                    current_provider=current_provider,
                    new_line=new_line,
                    context=context
                )
                
                # If scraping returned an error message, return it
                if scrape_result and isinstance(scrape_result, str) and scrape_result.startswith("❌"):
                    return scrape_result
            else:
                return "❌ Unable to fetch broadband data. Please scrape data first."
        
        if not conversation_state or user_id not in conversation_state or 'scraped_data' not in conversation_state[user_id]:
            return "❌ Unable to fetch broadband data at this time."
        
        data = conversation_state[user_id]['scraped_data']
        if 'error' in data:
            if 'Browser scraping not available' in data.get('error', ''):
                return "❌ Data scraping is currently limited in this environment. Please use the generated URL to view deals directly."
            else:
                return f"❌ Unable to fetch broadband data: {data.get('error', 'Unknown error')}"
        
        deals = data.get('deals', [])
        
        if not deals:
            return "❌ No deals available to find cheapest option."
        
        # Sort by monthly cost
        sorted_deals = sorted(deals,
                            key=lambda x: float(x['pricing']['monthly_cost'].replace('£', '').replace(',', '')))
        
        cheapest = sorted_deals[0]
        
        # Create structured output
        if send_websocket_fn and create_output_fn:
            structured_output = create_output_fn(
                user_id=user_id,
                action_type="cheapest_deal",
                param="provider,monthly_cost",
                value=f"{cheapest['provider']['name']},{cheapest['pricing']['monthly_cost']}",
                interaction_type="cheapest_search",
                clicked=True,
                element_name="get_cheapest",
                context=context,
                cheapest_deal=cheapest,
                total_deals_analyzed=len(deals)
            )
            
            await send_websocket_fn(
                message_type="cheapest_action",
                action="cheapest_deal_found",
                data=structured_output
            )
        
        # Return structured data
        return {
            'status': 'success',
            'message': f'Found the cheapest broadband deal: {cheapest["provider"]["name"]} - {cheapest["title"]}',
            'data': {
                'cheapest_deal': cheapest,
                'total_deals_analyzed': len(deals)
            },
            'suggestions': [
                'Compare this with other deals',
                'Check if this meets your speed requirements',
                'See if there are better value options'
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error finding cheapest deal: {e}")
        return f"❌ Error finding cheapest deal: {str(e)}"


async def handle_get_fastest(
    user_id: str,
    postcode: str = None,
    current_provider: str = None,
    new_line: str = None,
    context: str = None,
    conversation_state: Dict = None,
    scrape_data_fn=None,
    send_websocket_fn=None,
    create_output_fn=None
) -> str:
    """
    Handle fastest deal requests.
    
    Args:
        user_id: User ID
        postcode: Postcode
        current_provider: Current provider
        new_line: New line option
        context: Additional context
        conversation_state: Conversation state dictionary
        scrape_data_fn: Function to scrape data
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Dictionary with fastest deal or error message
    """
    try:
        # Check if we have scraped data
        if not conversation_state or user_id not in conversation_state or 'scraped_data' not in conversation_state[user_id]:
            # Scrape data if not available
            if scrape_data_fn:
                postcode = postcode or 'E14 9WB'
                scrape_result = await scrape_data_fn(
                    user_id=user_id,
                    postcode=postcode,
                    speed_in_mb=None,
                    contract_length=None,
                    phone_calls=None,
                    product_type=None,
                    providers=None,
                    current_provider=current_provider,
                    new_line=new_line,
                    context=context
                )
                
                # If scraping returned an error message, return it
                if scrape_result and isinstance(scrape_result, str) and scrape_result.startswith("❌"):
                    return scrape_result
            else:
                return "❌ Unable to fetch broadband data. Please scrape data first."
        
        if not conversation_state or user_id not in conversation_state or 'scraped_data' not in conversation_state[user_id]:
            return "❌ Unable to fetch broadband data at this time."
        
        data = conversation_state[user_id]['scraped_data']
        if 'error' in data:
            if 'Browser scraping not available' in data.get('error', ''):
                return "❌ Data scraping is currently limited in this environment. Please use the generated URL to view deals directly."
            else:
                return f"❌ Unable to fetch broadband data: {data.get('error', 'Unknown error')}"
        
        deals = data.get('deals', [])
        
        if not deals:
            return "❌ No deals available to find fastest option."
        
        # Sort by speed (highest first)
        sorted_deals = sorted(deals,
                            key=lambda x: int(x['speed']['numeric']),
                            reverse=True)
        
        fastest = sorted_deals[0]
        
        # Create structured output
        if send_websocket_fn and create_output_fn:
            structured_output = create_output_fn(
                user_id=user_id,
                action_type="fastest_deal",
                param="provider,speed",
                value=f"{fastest['provider']['name']},{fastest['speed']['display']}",
                interaction_type="fastest_search",
                clicked=True,
                element_name="get_fastest",
                context=context,
                fastest_deal=fastest,
                total_deals_analyzed=len(deals)
            )
            
            await send_websocket_fn(
                message_type="fastest_action",
                action="fastest_deal_found",
                data=structured_output
            )
        
        # Return structured data
        return {
            'status': 'success',
            'message': f'Found the fastest broadband deal: {fastest["provider"]["name"]} - {fastest["title"]}',
            'data': {
                'fastest_deal': fastest,
                'total_deals_analyzed': len(deals)
            },
            'suggestions': [
                'Compare this with cheaper options',
                'Check if this speed is available in your area',
                'See if there are better value high-speed deals'
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error finding fastest deal: {e}")
        return f"❌ Error finding fastest deal: {str(e)}"

