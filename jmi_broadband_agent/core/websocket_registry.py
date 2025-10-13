#!/usr/bin/env python3
"""
Enhanced WebSocket registry for agent voice backend.
Supports multiple users simultaneously with improved error handling and monitoring.
"""

from typing import Dict, Optional
from fastapi import WebSocket
import asyncio
from datetime import datetime
from loguru import logger


class WebSocketRegistry:
    """Enhanced WebSocket registry with connection monitoring."""
    
    def __init__(self):
        # User-specific store for tool WebSocket connections
        # Structure: {user_id: {"websocket": websocket, "connected_at": datetime, "last_ping": datetime}}
        self.user_tool_websockets: Dict[str, Dict] = {}
        
        # User-specific registry for product info websocket clients  
        # Structure: {user_id: {"websocket": websocket, "last_message": str, "connected_at": datetime}}
        self.user_product_info_clients: Dict[str, Dict] = {}
        
        # Session management for user tracking
        # Structure: {session_id: {"user_id": user_id, "connected_at": datetime}}
        self.session_user_mapping: Dict[str, Dict] = {}
    
    def register_tool_websocket(self, user_id: str, websocket: WebSocket) -> None:
        """Register a tool websocket for a specific user."""
        # Close existing connection if any
        if user_id in self.user_tool_websockets:
            existing_data = self.user_tool_websockets[user_id]
            existing_ws = existing_data.get("websocket")
            if existing_ws:
                try:
                    asyncio.create_task(existing_ws.close(code=1000, reason="New connection"))
                    logger.info(f"🔄 Closed existing tool WebSocket for user: {user_id}")
                except Exception:
                    logger.warning(f"⚠️ Could not close existing tool WebSocket for user: {user_id}")
        
        self.user_tool_websockets[user_id] = {
            "websocket": websocket,
            "connected_at": datetime.now(),
            "last_ping": datetime.now()
        }
        logger.info(f"🔧 Registered tool websocket for user: {user_id}")
        logger.info(f"🔧 Total tool websockets: {len(self.user_tool_websockets)}")

    def unregister_tool_websocket(self, user_id: str) -> None:
        """Unregister a tool websocket for a specific user."""
        if user_id in self.user_tool_websockets:
            del self.user_tool_websockets[user_id]
            logger.info(f"🧹 Unregistered tool websocket for user: {user_id}")
            logger.info(f"🔧 Remaining tool websockets: {len(self.user_tool_websockets)}")

    def get_tool_websocket(self, user_id: str) -> Optional[WebSocket]:
        """Get the tool websocket for a specific user."""
        data = self.user_tool_websockets.get(user_id)
        return data.get("websocket") if data else None
    
    def get_tool_websocket_info(self, user_id: str) -> Optional[Dict]:
        """Get tool websocket connection info for a specific user."""
        return self.user_tool_websockets.get(user_id)

    def register_product_info_client(self, user_id: str, websocket: WebSocket) -> None:
        """Register a product info websocket client for a specific user."""
        # Close existing connection if any
        if user_id in self.user_product_info_clients:
            existing_data = self.user_product_info_clients[user_id]
            existing_ws = existing_data.get("websocket")
            if existing_ws:
                try:
                    asyncio.create_task(existing_ws.close(code=1000, reason="New client connection"))
                    logger.info(f"🔄 Closed existing product info connection for user: {user_id}")
                except Exception:
                    logger.warning(f"⚠️ Could not close existing connection for user: {user_id}")
        
        self.user_product_info_clients[user_id] = {
            "websocket": websocket,
            "last_message": None,
            "connected_at": datetime.now()
        }
        logger.info(f"🔗 Registered product info client for user: {user_id}")
        logger.info(f"🔗 Total product info clients: {len(self.user_product_info_clients)}")

    def unregister_product_info_client(self, user_id: str) -> None:
        """Unregister a product info websocket client for a specific user."""
        if user_id in self.user_product_info_clients:
            del self.user_product_info_clients[user_id]
            logger.info(f"🧹 Unregistered product info client for user: {user_id}")

    def get_product_info_client(self, user_id: str) -> Optional[Dict]:
        """Get the product info client data for a specific user."""
        return self.user_product_info_clients.get(user_id)

    def set_product_info_last_message(self, user_id: str, message: str) -> None:
        """Set the last message for a specific user's product info client."""
        if user_id in self.user_product_info_clients:
            self.user_product_info_clients[user_id]["last_message"] = message

    def register_session_user(self, session_id: str, user_id: str) -> None:
        """Register a session with a user ID."""
        self.session_user_mapping[session_id] = {
            "user_id": user_id,
            "connected_at": datetime.now()
        }
        logger.info(f"🆔 Registered session {session_id} for user: {user_id}")

    def unregister_session_user(self, session_id: str) -> None:
        """Unregister a session."""
        if session_id in self.session_user_mapping:
            user_id = self.session_user_mapping[session_id]["user_id"]
            del self.session_user_mapping[session_id]
            logger.info(f"🧹 Unregistered session {session_id} for user: {user_id}")

    def get_user_from_session(self, session_id: str) -> Optional[str]:
        """Get the user ID from a session ID."""
        data = self.session_user_mapping.get(session_id)
        return data.get("user_id") if data else None
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information."""
        return self.session_user_mapping.get(session_id)

    def get_all_users(self) -> list:
        """Get all active user IDs."""
        # Get users from all sources: sessions, tool websockets, and product info clients
        session_users = [data["user_id"] for data in self.session_user_mapping.values()]
        tool_users = list(self.user_tool_websockets.keys())
        product_info_users = list(self.user_product_info_clients.keys())
        
        all_users = list(set(session_users + tool_users + product_info_users))
        logger.debug(f"[Registry] All users - Sessions: {session_users}, Tools: {tool_users}, ProductInfo: {product_info_users}, Combined: {all_users}")
        return all_users
    
    def get_active_connections_count(self) -> Dict[str, int]:
        """Get count of active connections by type."""
        return {
            "tool_websockets": len(self.user_tool_websockets),
            "product_info_clients": len(self.user_product_info_clients),
            "sessions": len(self.session_user_mapping)
        }
    
    async def ping_all_connections(self) -> Dict[str, int]:
        """Ping all active connections to check health."""
        tool_active = 0
        tool_failed = []
        
        for user_id, data in list(self.user_tool_websockets.items()):
            websocket = data["websocket"]
            try:
                await websocket.ping()
                data["last_ping"] = datetime.now()
                tool_active += 1
            except Exception as e:
                logger.warning(f"⚠️ Tool WebSocket ping failed for user {user_id}: {e}")
                tool_failed.append(user_id)
        
        # Remove failed connections
        for user_id in tool_failed:
            self.unregister_tool_websocket(user_id)
        
        product_active = 0
        product_failed = []
        
        for user_id, data in list(self.user_product_info_clients.items()):
            websocket = data["websocket"]
            try:
                await websocket.ping()
                product_active += 1
            except Exception as e:
                logger.warning(f"⚠️ Product info WebSocket ping failed for user {user_id}: {e}")
                product_failed.append(user_id)
        
        # Remove failed connections
        for user_id in product_failed:
            self.unregister_product_info_client(user_id)
        
        return {
            "tool_active": tool_active,
            "tool_failed": len(tool_failed),
            "product_active": product_active,
            "product_failed": len(product_failed)
        }

    async def send_to_user_tool_websocket(self, user_id: str, data: dict) -> bool:
        """Send data to a specific user's tool websocket."""
        websocket_data = self.user_tool_websockets.get(user_id)
        if websocket_data:
            websocket = websocket_data["websocket"]
            try:
                await websocket.send_json(data)
                logger.info(f"✅ Sent data to user {user_id} tool websocket")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to send data to user {user_id} tool websocket: {e}")
                self.unregister_tool_websocket(user_id)
                return False
        else:
            logger.warning(f"⚠️ No tool websocket found for user: {user_id}")
            return False

    async def send_to_user_product_info(self, user_id: str, message: str) -> bool:
        """Send message to a specific user's product info websocket."""
        client_data = self.user_product_info_clients.get(user_id)
        if client_data:
            websocket = client_data["websocket"]
            try:
                await websocket.send_text(message)
                self.set_product_info_last_message(user_id, message)
                logger.info(f"✅ Sent product info to user {user_id}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to send product info to user {user_id}: {e}")
                self.unregister_product_info_client(user_id)
                return False
        else:
            logger.warning(f"⚠️ No product info client found for user: {user_id}")
            return False

    async def broadcast_to_all_tool_websockets(self, data: dict, exclude_users: list = None) -> int:
        """Broadcast data to all tool websockets except excluded users."""
        exclude_users = exclude_users or []
        sent_count = 0
        failed_users = []
        
        for user_id, websocket_data in list(self.user_tool_websockets.items()):
            if user_id in exclude_users:
                continue
                
            websocket = websocket_data["websocket"]
            try:
                await websocket.send_json(data)
                sent_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to broadcast to user {user_id}: {e}")
                failed_users.append(user_id)
        
        # Remove failed connections
        for user_id in failed_users:
            self.unregister_tool_websocket(user_id)
        
        logger.info(f"📢 Broadcast sent to {sent_count} users, {len(failed_users)} failed")
        return sent_count


# Global registry instance
_registry_instance = None


def get_registry() -> WebSocketRegistry:
    """Get the global WebSocket registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = WebSocketRegistry()
    return _registry_instance


# Convenience functions for backward compatibility
def register_tool_websocket(user_id: str, websocket: WebSocket) -> None:
    """Register a tool websocket for a specific user."""
    get_registry().register_tool_websocket(user_id, websocket)


def unregister_tool_websocket(user_id: str) -> None:
    """Unregister a tool websocket for a specific user."""
    get_registry().unregister_tool_websocket(user_id)


def get_tool_websocket(user_id: str) -> Optional[WebSocket]:
    """Get the tool websocket for a specific user."""
    return get_registry().get_tool_websocket(user_id)


def register_product_info_client(user_id: str, websocket: WebSocket) -> None:
    """Register a product info websocket client for a specific user."""
    get_registry().register_product_info_client(user_id, websocket)


def unregister_product_info_client(user_id: str) -> None:
    """Unregister a product info websocket client for a specific user."""
    get_registry().unregister_product_info_client(user_id)


def get_product_info_client(user_id: str) -> Optional[Dict]:
    """Get the product info client data for a specific user."""
    return get_registry().get_product_info_client(user_id)


def set_product_info_last_message(user_id: str, message: str) -> None:
    """Set the last message for a specific user's product info client."""
    get_registry().set_product_info_last_message(user_id, message)


def register_session_user(session_id: str, user_id: str) -> None:
    """Register a session with a user ID."""
    get_registry().register_session_user(session_id, user_id)


def unregister_session_user(session_id: str) -> None:
    """Unregister a session."""
    get_registry().unregister_session_user(session_id)


def get_user_from_session(session_id: str) -> Optional[str]:
    """Get the user ID from a session ID."""
    return get_registry().get_user_from_session(session_id)


def get_all_users() -> list:
    """Get all active user IDs."""
    return get_registry().get_all_users()


async def send_to_user_tool_websocket(user_id: str, data: dict) -> bool:
    """Send data to a specific user's tool websocket."""
    return await get_registry().send_to_user_tool_websocket(user_id, data)


async def send_to_user_product_info(user_id: str, message: str) -> bool:
    """Send message to a specific user's product info websocket."""
    return await get_registry().send_to_user_product_info(user_id, message)


# Backward compatibility (deprecated - will be removed)
user_tool_websockets = {}  # This will be empty, use get_registry().user_tool_websockets instead
tool_websockets = user_tool_websockets  # For backward compatibility
product_info_ws_client = {"websocket": None}  # For backward compatibility