#!/usr/bin/env python3
"""
Tools package for JMI Broadband AI Agent voice backend.
Contains page-specific tools and base tool functionality for broadband and dashboard operations.
"""

__version__ = "1.0.0"
__author__ = "JMI Broadband AI Agent Team"

# Tool imports
from .base_tool import BaseTool
from .dashboard_tool import DashboardTool
from .broadband_tool import BroadbandTool

# Tool factory functions
from .dashboard_tool import create_dashboard_tool
from .broadband_tool import create_broadband_tool

__all__ = [
    # Base tool
    "BaseTool",

    # Page-specific tools
    "DashboardTool",
    "BroadbandTool",

    # Factory functions
    "create_dashboard_tool",
    "create_broadband_tool",
]