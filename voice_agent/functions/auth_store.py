#!/usr/bin/env python3
"""
Auth Store Module for agent.
Provides a simple cache-based auth token storage system.
Stores and retrieves authentication tokens against user IDs.
"""

import os
import sys
from typing import Dict, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from loguru import logger

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)



# Pydantic models for request/response
class AuthTokenRequest(BaseModel):
    """Request model for storing auth tokens."""
    user_id: str = Field(..., description="User ID to associate with the auth token")
    auth_token: str = Field(..., description="The authentication token to store")
    expires_in_minutes: Optional[int] = Field(30, description="Token expiration time in minutes (optional)")


class AuthTokenResponse(BaseModel):
    """Response model for auth token operations."""
    user_id: str
    status: str
    message: str
    timestamp: str
    expires_at: Optional[str] = None


class AuthTokenData(BaseModel):
    """Internal model for stored auth token data."""
    auth_token: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None


# In-memory storage for auth tokens
_auth_token_store: Dict[str, AuthTokenData] = {}


class AuthStore:
    """Auth token storage manager."""

    @staticmethod
    def store_token(user_id: str, auth_token: str, expires_in_minutes: Optional[int] = None) -> AuthTokenResponse:
        """Store an auth token for a user."""
        try:

            # Validate auth_token
            if not auth_token or not auth_token.strip():
                raise HTTPException(status_code=400, detail="Auth token cannot be empty")

            auth_token = auth_token.strip()

            # Calculate expiration
            created_at = datetime.now()
            expires_at = None
            if expires_in_minutes and expires_in_minutes > 0:
                expires_at = created_at + timedelta(minutes=expires_in_minutes)

            # Store the token
            token_data = AuthTokenData(
                auth_token=auth_token,
                created_at=created_at,
                expires_at=expires_at,
                last_accessed=None
            )

            _auth_token_store[user_id] = token_data

            logger.info(f"✅ Auth token stored for user: {user_id}")

            return AuthTokenResponse(
                user_id=user_id,
                status="success",
                message="Auth token stored successfully",
                timestamp=created_at.isoformat(),
                expires_at=expires_at.isoformat() if expires_at else None
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error storing auth token for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    @staticmethod
    def get_token(user_id: str) -> Optional[str]:
        """Retrieve an auth token for a user."""
        try:

            # Check if token exists
            if user_id not in _auth_token_store:
                logger.info(f"ℹ️ No auth token found for user: {user_id}")
                return None

            token_data = _auth_token_store[user_id]

            # Check if token is expired
            if token_data.expires_at and datetime.now() > token_data.expires_at:
                # Remove expired token
                del _auth_token_store[user_id]
                logger.info(f"🗑️ Expired auth token removed for user: {user_id}")
                return None

            # Update last accessed time
            token_data.last_accessed = datetime.now()
            _auth_token_store[user_id] = token_data

            logger.info(f"✅ Auth token retrieved for user: {user_id}")
            return token_data.auth_token

        except Exception as e:
            logger.error(f"❌ Error retrieving auth token for user {user_id}: {e}")
            return None

    @staticmethod
    def delete_token(user_id: str) -> bool:
        """Delete an auth token for a user."""
        try:

            if user_id in _auth_token_store:
                del _auth_token_store[user_id]
                logger.info(f"🗑️ Auth token deleted for user: {user_id}")
                return True
            else:
                logger.info(f"ℹ️ No auth token found to delete for user: {user_id}")
                return False

        except Exception as e:
            logger.error(f"❌ Error deleting auth token for user {user_id}: {e}")
            return False

    @staticmethod
    def get_all_tokens() -> Dict[str, Dict]:
        """Get all stored tokens (for debugging/admin purposes)."""
        tokens_info = {}
        for user_id, token_data in _auth_token_store.items():
            tokens_info[user_id] = {
                "created_at": token_data.created_at.isoformat(),
                "expires_at": token_data.expires_at.isoformat() if token_data.expires_at else None,
                "last_accessed": token_data.last_accessed.isoformat() if token_data.last_accessed else None,
                "is_expired": token_data.expires_at and datetime.now() > token_data.expires_at
            }
        return tokens_info

    @staticmethod
    def cleanup_expired_tokens() -> int:
        """Remove expired tokens and return count of removed tokens."""
        expired_users = []
        for user_id, token_data in _auth_token_store.items():
            if token_data.expires_at and datetime.now() > token_data.expires_at:
                expired_users.append(user_id)

        for user_id in expired_users:
            del _auth_token_store[user_id]

        if expired_users:
            logger.info(f"🧹 Cleaned up {len(expired_users)} expired auth tokens")

        return len(expired_users)


# Create FastAPI router
auth_store_router = APIRouter(
    tags=["Auth Store"],
    responses={
        404: {"description": "Token not found"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)


@auth_store_router.post("/auth/store", response_model=AuthTokenResponse)
async def store_auth_token(request: AuthTokenRequest):
    """
    Store an authentication token for a user.

    This endpoint allows manual storage of auth tokens against user IDs.
    The token will be cached in memory and can be retrieved later.
    """
    return AuthStore.store_token(
        user_id=request.user_id,
        auth_token=request.auth_token,
        expires_in_minutes=request.expires_in_minutes
    )


@auth_store_router.get("/auth/token/{user_id}")
async def get_auth_token(user_id: str):
    """
    Retrieve an authentication token for a user.

    Returns the stored auth token for the specified user ID.
    Returns null if no token is found or if the token has expired.
    """
    token = AuthStore.get_token(user_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Auth token not found or expired")

    return {
        "user_id": user_id,
        "auth_token": token,
        "timestamp": datetime.now().isoformat()
    }


@auth_store_router.delete("/auth/token/{user_id}")
async def delete_auth_token(user_id: str):
    """
    Delete an authentication token for a user.

    Removes the stored auth token for the specified user ID.
    """
    success = AuthStore.delete_token(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Auth token not found")

    return {
        "user_id": user_id,
        "status": "success",
        "message": "Auth token deleted successfully",
        "timestamp": datetime.now().isoformat()
    }


@auth_store_router.get("/auth/status/{user_id}")
async def check_auth_status(user_id: str):
    """
    Check the authentication status for a user.

    Returns information about whether a user has a valid auth token.
    """
    token = AuthStore.get_token(user_id)
    has_token = token is not None

    return {
        "user_id": user_id,
        "has_token": has_token,
        "timestamp": datetime.now().isoformat()
    }


@auth_store_router.get("/auth/health")
async def auth_store_health():
    """Health check for the auth store service."""
    token_count = len(_auth_token_store)

    # Clean up expired tokens during health check
    expired_count = AuthStore.cleanup_expired_tokens()

    return {
        "status": "healthy",
        "service": "auth_store",
        "total_tokens": token_count,
        "expired_tokens_cleaned": expired_count,
        "timestamp": datetime.now().isoformat()
    }


@auth_store_router.get("/auth/debug")
async def debug_auth_store():
    """Debug endpoint to view all stored tokens (development only)."""
    # This should be protected in production
    if os.getenv("ENVIRONMENT") == "production":
        raise HTTPException(status_code=403, detail="Debug endpoint not available in production")

    return {
        "total_tokens": len(_auth_token_store),
        "tokens": AuthStore.get_all_tokens(),
        "timestamp": datetime.now().isoformat()
    }


# Export the router for inclusion in main app
__all__ = ["auth_store_router", "AuthStore"]

