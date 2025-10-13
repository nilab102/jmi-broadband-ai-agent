#!/usr/bin/env python3
"""
Test script to verify provider fuzzy matching fix.
"""

import sys
import os
import asyncio

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def test_provider_fix():
    """Test that provider fuzzy matching now works."""

    print("🔍 Testing provider fuzzy matching fix...")

    try:
        # Import the broadband tool
        from voice_agent.tools.broadband_tool import BroadbandTool
        from pipecat.processors.frameworks.rtvi import RTVIProcessor

        # Create a mock RTVI processor
        class MockRTVIProcessor:
            def __init__(self):
                self.task = None

        rtvi_processor = MockRTVIProcessor()

        # Create broadband tool
        tool = BroadbandTool(rtvi_processor)

        user_id = "test_provider_fix"

        print("📝 Testing provider 'virgin' (should be corrected to 'Virgin Media')...")

        # Test with virgin provider
        result = await tool._handle_parameter_update(
            user_id=user_id,
            postcode="E14 9WB",
            speed_in_mb="55Mb",
            providers="virgin"
        )

        print("✅ Result:")
        print(result[:1000] + ('...' if len(result) > 1000 else ''))

        # Check if URL contains Virgin Media
        if "Virgin Media" in result:
            print("✅ SUCCESS: Provider corrected from 'virgin' to 'Virgin Media'")
        else:
            print("❌ FAILURE: Provider not corrected")

        # Check if URL is complete (not truncated)
        if "https://broadband.justmovein.co/packages?location=E14+9WB" in result:
            if "#/" in result:
                print("✅ SUCCESS: URL is complete with hash part")
            else:
                print("❌ FAILURE: URL is truncated - missing hash part")
        else:
            print("❌ FAILURE: URL not found in result")

        print("\n📝 Testing 'vergin' typo (should also be corrected)...")

        # Test with typo
        result2 = await tool._handle_parameter_update(
            user_id=user_id,
            providers="vergin"
        )

        print("✅ Result:")
        print(result2[:1000] + ('...' if len(result2) > 1000 else ''))

        if "Virgin Media" in result2:
            print("✅ SUCCESS: Typo 'vergin' corrected to 'Virgin Media'")
        else:
            print("❌ FAILURE: Typo not corrected")

    except Exception as e:
        print(f"❌ Error testing provider fix: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_provider_fix())
