"""
Postcode Operations - UK postcode validation and fuzzy search operations.
Handles postcode validation, fuzzy matching with auto-selection, and user confirmation.
"""

import re
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from loguru import logger

from .helpers import validate_uk_postcode_format


class PostcodeValidator:
    """
    Validator for UK postcodes with fuzzy search support.
    Auto-selects best matching postcode from database.
    """
    
    def __init__(self, postal_code_service, conversation_state: Dict):
        """
        Initialize postcode validator.
        
        Args:
            postal_code_service: Postal code service with fuzzy search
            conversation_state: Shared conversation state dictionary
        """
        self.postal_code_service = postal_code_service
        self.conversation_state = conversation_state
        self.fuzzy_searcher = postal_code_service.searcher if postal_code_service else None
    
    async def search_with_fuzzy(
        self, 
        user_id: str, 
        raw_postcode: str, 
        context: str = None,
        send_websocket_fn=None,
        create_output_fn=None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Search for postcode using fuzzy matching and AUTO-SELECT the best match.
        
        Workflow:
        1. Validate UK postcode format with regex
        2. If invalid format, return error
        3. If valid, run fuzzy search against database
        4. Auto-select: 100% match OR highest scored match
        5. Store selected postcode in conversation state
        6. Return success (no user confirmation needed)
        
        Args:
            user_id: User ID for session management
            raw_postcode: Raw postcode input from user (may have typos)
            context: Additional context
            send_websocket_fn: Function to send WebSocket messages
            create_output_fn: Function to create structured output
            
        Returns:
            Tuple of (success: bool, message: str, selected_postcode: Optional[str])
        """
        # STEP 1: Validate UK postcode format with regex
        if not validate_uk_postcode_format(raw_postcode):
            logger.warning(f"❌ Invalid UK postcode format: {raw_postcode}")
            error_msg = f"❌ Invalid UK postcode format: '{raw_postcode}'. Please provide a valid UK postcode (e.g., E14 9WB, SW1A 1AA)."
            return (False, error_msg, None)
        
        logger.info(f"✅ Postcode format validated: {raw_postcode}")
        
        # STEP 2: Check if fuzzy search is available
        if not self.fuzzy_searcher:
            logger.warning("⚠️ Fuzzy search not available - cannot validate against database")
            error_msg = f"⚠️ Fuzzy search not available. Cannot validate postcode '{raw_postcode}' against database."
            return (False, error_msg, None)
        
        try:
            logger.info(f"🔍 Running fuzzy search for postcode: {raw_postcode}")
            
            # STEP 3: Run fuzzy search with optimal parameters
            result = self.fuzzy_searcher.get_fuzzy_results(
                search_term=raw_postcode,
                top_n=10,  # Get top 10 matches for logging
                max_candidates=2000,
                use_dynamic_distance=True,
                use_weighted_scoring=True,
                parallel_threshold=500
            )
            
            if not result['results']:
                logger.warning(f"❌ No matching postcodes found for: {raw_postcode}")
                error_msg = f"❌ No matching postcodes found in database for '{raw_postcode}'. Please check and provide a valid UK postcode."
                return (False, error_msg, None)
            
            matches = result['results']
            metadata = result.get('metadata', {})
            
            # STEP 4: Auto-select best match
            best_match = matches[0]  # Highest scored match
            best_postcode, best_score = best_match
            
            if best_score >= 100.0:
                selected_postcode = best_postcode
                selection_reason = "100% exact match"
                logger.info(f"🎯 100% match found: {selected_postcode}")
            else:
                selected_postcode = best_postcode
                selection_reason = f"highest match ({best_score:.1f}%)"
                logger.info(f"🎯 Best match selected: {selected_postcode} (score: {best_score:.1f}%)")
            
            # STEP 5: Store selected postcode in conversation state
            if user_id not in self.conversation_state:
                self.conversation_state[user_id] = {}
            
            self.conversation_state[user_id]['confirmed_postcode'] = selected_postcode
            self.conversation_state[user_id]['postcode_fuzzy_search'] = {
                'raw_input': raw_postcode,
                'selected_postcode': selected_postcode,
                'selection_reason': selection_reason,
                'score': best_score,
                'all_matches': matches[:5],  # Store top 5 for reference
                'metadata': metadata,
                'timestamp': datetime.now().isoformat(),
                'auto_selected': True
            }
            
            # Send WebSocket message if function provided
            if send_websocket_fn and create_output_fn:
                structured_output = create_output_fn(
                    user_id=user_id,
                    action_type="postcode_auto_selected",
                    param="raw_postcode,selected_postcode,score",
                    value=f"{raw_postcode},{selected_postcode},{best_score}",
                    interaction_type="auto_selection",
                    clicked=True,
                    element_name="postcode_auto_select",
                    context=context,
                    raw_postcode=raw_postcode,
                    selected_postcode=selected_postcode,
                    selection_reason=selection_reason,
                    score=best_score,
                    search_time_ms=metadata.get('search_time_ms', 0)
                )
                
                await send_websocket_fn(
                    message_type="fuzzy_search_action",
                    action="postcode_auto_selected",
                    data=structured_output
                )
            
            # STEP 6: Return success message
            if best_score >= 100.0:
                success_msg = f"✅ Postcode confirmed: **{selected_postcode}** (exact match)"
            else:
                success_msg = f"✅ Postcode matched: **{selected_postcode}** (best match: {best_score:.1f}% confidence)"
            
            logger.info(f"✅ Auto-selected postcode: {selected_postcode} for input '{raw_postcode}'")
            
            return (True, success_msg, selected_postcode)
        
        except Exception as e:
            logger.error(f"❌ Error in fuzzy postcode search: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            error_msg = f"❌ Error searching for postcode: {str(e)}"
            return (False, error_msg, None)
    
    async def handle_confirmation(
        self,
        user_id: str,
        confirmed_postcode: str = None,
        original_postcode: str = None,
        context: str = None,
        url_generator=None,
        normalize_contract_fn=None,
        send_websocket_fn=None,
        create_output_fn=None
    ) -> str:
        """
        Handle user confirmation of postcode selection (LEGACY).
        This processes user's choice from fuzzy search results.
        
        Args:
            user_id: User ID
            confirmed_postcode: The postcode user confirmed
            original_postcode: Original postcode that triggered fuzzy search
            context: Additional context
            url_generator: URL generator service
            normalize_contract_fn: Function to normalize contract length
            send_websocket_fn: Function to send WebSocket messages
            create_output_fn: Function to create structured output
            
        Returns:
            Confirmation message with next steps
        """
        try:
            # Check if we have fuzzy search state
            if user_id not in self.conversation_state or 'postcode_fuzzy_search' not in self.conversation_state[user_id]:
                # Check for old postcode_suggestions format (backward compatibility)
                if user_id in self.conversation_state and 'postcode_suggestions' in self.conversation_state[user_id]:
                    if confirmed_postcode:
                        selected_postcode = confirmed_postcode
                    else:
                        return "❌ Please specify which postcode to use."
                else:
                    return "❌ No postcode search in progress. Please provide a postcode first."
            else:
                fuzzy_state = self.conversation_state[user_id]['postcode_fuzzy_search']
                matches = fuzzy_state.get('all_matches', [])
                
                # Parse user's confirmation
                selected_postcode = None
                
                if confirmed_postcode:
                    # Check if it looks like a UK postcode
                    postcode_pattern = r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d?[A-Z]{0,2}$'
                    if re.match(postcode_pattern, confirmed_postcode.upper().replace(' ', '')[:10]):
                        # Direct postcode
                        confirmed_upper = confirmed_postcode.upper().replace(' ', '')
                        for postcode, score in matches:
                            if postcode.replace(' ', '') == confirmed_upper:
                                selected_postcode = postcode
                                break
                        
                        if not selected_postcode:
                            # Run fuzzy search again
                            return await self.search_with_fuzzy(
                                user_id, confirmed_postcode, context,
                                send_websocket_fn, create_output_fn
                            )
                    else:
                        # Check if it's a selection command
                        selection_match = re.search(
                            r'^(?:choose\s+)?(?:select\s+)?(?:number\s+)?(\d+)|^(?:the\s+)?(first|second|third|fourth|fifth)', 
                            confirmed_postcode.lower()
                        )
                        
                        if selection_match:
                            if selection_match.group(1):
                                index = int(selection_match.group(1)) - 1
                            else:
                                word_to_num = {'first': 0, 'second': 1, 'third': 2, 'fourth': 3, 'fifth': 4}
                                word = selection_match.group(2)
                                index = word_to_num.get(word, 0)
                            
                            if 0 <= index < len(matches):
                                selected_postcode = matches[index][0]
                            else:
                                return f"❌ Invalid selection. Please choose a number between 1 and {len(matches)}."
                else:
                    return "❌ Please specify which postcode to use."
            
            # Store confirmed postcode
            self.conversation_state[user_id]['confirmed_postcode'] = selected_postcode
            if 'postcode_fuzzy_search' in self.conversation_state[user_id]:
                self.conversation_state[user_id]['postcode_fuzzy_search']['awaiting_confirmation'] = False
                self.conversation_state[user_id]['postcode_fuzzy_search']['confirmed_postcode'] = selected_postcode
            
            # Send WebSocket message
            if send_websocket_fn and create_output_fn:
                structured_output = create_output_fn(
                    user_id=user_id,
                    action_type="postcode_confirmed",
                    param="confirmed_postcode",
                    value=selected_postcode,
                    interaction_type="postcode_confirmation",
                    clicked=True,
                    element_name="confirm_postcode",
                    context=context,
                    confirmed_postcode=selected_postcode,
                    original_input=fuzzy_state.get('raw_input', original_postcode) if 'postcode_fuzzy_search' in self.conversation_state[user_id] else original_postcode
                )
                
                await send_websocket_fn(
                    message_type="confirmation_action",
                    action="postcode_confirmed",
                    data=structured_output
                )
            
            # Check for pending parameters
            pending_params = self.conversation_state[user_id].get('pending_search_params', {})
            
            if pending_params and any(pending_params.values()) and url_generator:
                # Generate URL with confirmed postcode
                all_params = {
                    'postcode': selected_postcode,
                    'speed_in_mb': pending_params.get('speed_in_mb', '30Mb'),
                    'contract_length': pending_params.get('contract_length', ''),
                    'phone_calls': pending_params.get('phone_calls', 'Show me everything'),
                    'product_type': pending_params.get('product_type', 'broadband,phone'),
                    'providers': pending_params.get('providers', ''),
                    'current_provider': pending_params.get('current_provider', ''),
                    'sort_by': pending_params.get('sort_by', 'Recommended'),
                    'new_line': pending_params.get('new_line', '')
                }
                
                try:
                    # Normalize contract length if function provided
                    if normalize_contract_fn and all_params['contract_length']:
                        all_params['contract_length'] = normalize_contract_fn(all_params['contract_length'])
                    
                    url = url_generator.generate_url(all_params)
                    
                    # Send URL generation message
                    if send_websocket_fn and create_output_fn:
                        structured_output_url = create_output_fn(
                            user_id=user_id,
                            action_type="url_generated",
                            param="url,postcode",
                            value=f"{url},{selected_postcode}",
                            interaction_type="url_generation",
                            current_page="broadband",
                            previous_page=None,
                            clicked=False,
                            element_name="generate_url",
                            context=context,
                            extracted_params=all_params,
                            generated_url=url
                        )
                        
                        await send_websocket_fn(
                            message_type="url_action",
                            action="url_generated",
                            data=structured_output_url
                        )
                    
                    response = f"✅ **Postcode Confirmed: {selected_postcode}**\n\n"
                    response += f"🎉 Perfect! I've generated your broadband comparison URL!\n\n"
                    response += f"**Your Search Parameters:**\n"
                    response += f"• Postcode: {selected_postcode}\n"
                    response += f"• Speed: {all_params['speed_in_mb']}\n"
                    response += f"• Contract: {all_params['contract_length']}\n"
                    response += f"• Phone Calls: {all_params['phone_calls']}\n\n"
                    response += f"**Generated URL:** {url}\n\n"
                    response += f"💡 You can now ask me to:\n"
                    response += f"• Show recommendations\n"
                    response += f"• Compare specific providers\n"
                    response += f"• Find the cheapest/fastest deals"
                    
                    # Clear pending params
                    self.conversation_state[user_id]['pending_search_params'] = {}
                    
                    return response
                
                except Exception as e:
                    logger.error(f"❌ Error generating URL after confirmation: {e}")
            
            # No pending params - show next steps
            response = f"✅ **Postcode Confirmed: {selected_postcode}**\n\n"
            response += f"Great! I'll use **{selected_postcode}** for your broadband search.\n\n"
            response += f"📝 **Next Steps:**\n"
            response += f"• I can now search for broadband deals in {selected_postcode}\n"
            response += f"• Specify your preferences (speed, contract, providers)\n\n"
            response += f"💡 Say: 'show me 100Mb deals with 12 month contract'"
            
            return response
        
        except Exception as e:
            logger.error(f"❌ Error in postcode confirmation: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"❌ Error confirming postcode: {str(e)}"


# Standalone functions for functional approach

async def search_postcode_with_fuzzy(
    user_id: str,
    raw_postcode: str,
    context: str = None,
    postal_code_service=None,
    conversation_state: Dict = None,
    send_websocket_fn=None,
    create_output_fn=None
) -> Tuple[bool, str, Optional[str]]:
    """
    Standalone function to search for postcode with fuzzy matching.
    
    Args:
        user_id: User ID
        raw_postcode: Raw postcode input
        context: Additional context
        postal_code_service: Postal code service
        conversation_state: Conversation state dictionary
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Tuple of (success, message, selected_postcode)
    """
    validator = PostcodeValidator(postal_code_service, conversation_state)
    return await validator.search_with_fuzzy(
        user_id, raw_postcode, context,
        send_websocket_fn, create_output_fn
    )


async def handle_postcode_confirmation(
    user_id: str,
    confirmed_postcode: str = None,
    original_postcode: str = None,
    context: str = None,
    postal_code_service=None,
    conversation_state: Dict = None,
    url_generator=None,
    normalize_contract_fn=None,
    send_websocket_fn=None,
    create_output_fn=None
) -> str:
    """
    Standalone function to handle postcode confirmation.
    
    Args:
        user_id: User ID
        confirmed_postcode: Confirmed postcode
        original_postcode: Original postcode
        context: Additional context
        postal_code_service: Postal code service
        conversation_state: Conversation state dictionary
        url_generator: URL generator service
        normalize_contract_fn: Function to normalize contract
        send_websocket_fn: Function to send WebSocket messages
        create_output_fn: Function to create structured output
        
    Returns:
        Confirmation message
    """
    validator = PostcodeValidator(postal_code_service, conversation_state)
    return await validator.handle_confirmation(
        user_id, confirmed_postcode, original_postcode, context,
        url_generator, normalize_contract_fn,
        send_websocket_fn, create_output_fn
    )

