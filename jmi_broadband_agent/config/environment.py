#!/usr/bin/env python3
"""
Environment configuration for agent voice backend.
Handles dev/prod environment settings with HTTPS support.
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass
from loguru import logger
from dotenv import load_dotenv

# Load environment variables without overriding existing ones
load_dotenv(override=False)


@dataclass
class EnvironmentConfig:
    """Environment configuration dataclass."""
    environment: str
    backend_url: str
    frontend_url: str
    use_https: bool
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    google_api_key: Optional[str] = None


class EnvironmentManager:
    """Manages environment-specific configurations."""
    
    ENVIRONMENTS = {
        "development": {
            "backend_url": "https://localhost:8200",
            "frontend_url": "https://localhost:3000",
            "use_https": False
        },
        "production": {
            "backend_url": "https://176.9.16.194:8200",
            "frontend_url": "https://176.9.16.194:3000",
            "use_https": False
        }
    }
    
    @classmethod
    def get_config(cls) -> EnvironmentConfig:
        """Get environment configuration based on ENVIRONMENT variable."""
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        logger.info("🔧 === ENVIRONMENT CONFIGURATION ===")
        logger.info(f"🔧 ENVIRONMENT: {environment}")
        logger.info(f"🔧 DEV_BACKEND_URL: {os.getenv('DEV_BACKEND_URL', 'NOT_SET')}")
        logger.info(f"🔧 PROD_BACKEND_URL: {os.getenv('PROD_BACKEND_URL', 'NOT_SET')}")
        logger.info(f"🔧 GOOGLE_API_KEY set: {bool(os.getenv('GOOGLE_API_KEY'))}")
        logger.info(f"🔧 Current working directory: {os.getcwd()}")
        
        # Get base configuration
        if environment not in cls.ENVIRONMENTS:
            logger.warning(f"⚠️ Unknown environment '{environment}', defaulting to development")
            environment = "development"
            
        base_config = cls.ENVIRONMENTS[environment].copy()
        
        # Override with environment-specific URLs if set
        if environment == "development":
            if os.getenv("DEV_BACKEND_URL"):
                base_config["backend_url"] = os.getenv("DEV_BACKEND_URL")
            if os.getenv("DEV_FRONTEND_URL"):
                base_config["frontend_url"] = os.getenv("DEV_FRONTEND_URL")
        elif environment == "production":
            if os.getenv("PROD_BACKEND_URL"):
                base_config["backend_url"] = os.getenv("PROD_BACKEND_URL")
            if os.getenv("PROD_FRONTEND_URL"):
                base_config["frontend_url"] = os.getenv("PROD_FRONTEND_URL")
        
        # Override cert paths from environment if set
        if os.getenv("SSL_CERT_PATH"):
            base_config["cert_path"] = os.getenv("SSL_CERT_PATH")
        if os.getenv("SSL_KEY_PATH"):
            base_config["key_path"] = os.getenv("SSL_KEY_PATH")
            
        # Create configuration object
        config = EnvironmentConfig(
            environment=environment,
            backend_url=base_config["backend_url"],
            frontend_url=base_config["frontend_url"],
            use_https=base_config["use_https"],
            cert_path=base_config.get("cert_path"),
            key_path=base_config.get("key_path"),
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        logger.info(f"🌐 Backend URL: {config.backend_url}")
        logger.info(f"🌐 Frontend URL: {config.frontend_url}")
        logger.info(f"🔒 HTTPS enabled: {config.use_https}")
        logger.info(f"🔑 SSL cert path: {config.cert_path}")
        logger.info("🔧 ================================")
        
        return config


def get_backend_url() -> str:
    """Get the appropriate backend URL based on environment."""
    config = EnvironmentManager.get_config()
    return config.backend_url


def get_frontend_url() -> str:
    """Get the appropriate frontend URL based on environment."""
    config = EnvironmentManager.get_config()
    return config.frontend_url


def is_production() -> bool:
    """Check if running in production environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def is_development() -> bool:
    """Check if running in development environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "development"


def get_ssl_config() -> tuple:
    """Get SSL certificate and key paths."""
    config = EnvironmentManager.get_config()
    return config.cert_path, config.key_path


def validate_environment() -> bool:
    """Validate that the environment is properly configured."""
    try:
        config = EnvironmentManager.get_config()

        # Check Google API key
        if not config.google_api_key:
            logger.error("❌ GOOGLE_API_KEY not set")
            return False

        # Check SSL configuration if HTTPS is enabled
        if config.use_https:
            if config.environment == "development":
                # Check if cert files exist for development
                if config.cert_path and not os.path.exists(config.cert_path):
                    logger.error(f"❌ SSL certificate not found: {config.cert_path}")
                    return False
                if config.key_path and not os.path.exists(config.key_path):
                    logger.error(f"❌ SSL key not found: {config.key_path}")
                    return False
            elif config.environment == "production":
                # For production, SSL paths should be set via environment
                if not config.cert_path:
                    logger.warning("⚠️ SSL_CERT_PATH not set for production")
                if not config.key_path:
                    logger.warning("⚠️ SSL_KEY_PATH not set for production")

        logger.info("✅ Environment configuration validated")
        return True

    except Exception as e:
        logger.error(f"❌ Environment validation failed: {e}")
        return False



def get_ssl_verify() -> bool:
    """Get SSL verification setting from environment variables."""
    verify = os.getenv("SSL_VERIFY", "False").lower() == "true"
    logger.info(f"🔒 SSL verification enabled: {verify}")
    return verify