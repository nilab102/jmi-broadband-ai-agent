#!/usr/bin/env python3
"""
Configuration package for agent voice backend.
Handles environment-specific settings and application configuration.
"""

__version__ = "1.0.0"
__author__ = "Voice Agent Team"

from .environment import EnvironmentConfig, get_backend_url
from .settings import Settings, get_settings

__all__ = [
    "EnvironmentConfig",
    "get_backend_url", 
    "Settings",
    "get_settings"
]