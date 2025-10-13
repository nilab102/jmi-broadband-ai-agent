#!/usr/bin/env python3
"""
Debug script to test broadband tool URL generation with new_line.
"""

import sys
import os
import asyncio

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def test_broadband_tool_new_line():
    """Test broadband tool with new_line parameter."""

    print("🔍 Testing broadband tool URL generation with new_line...")

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

        user_id = "debug_user"

        print("📝 Testing parameter update with new_line='NewLine'...")

        # Test with new_line set
        result = await tool._handle_parameter_update(
            user_id=user_id,
            postcode="E14 9WB",
            speed_in_mb="55Mb",
            new_line="NewLine"
        )

        print("✅ Result:")
        print(result[:1000] + ('...' if len(result) > 1000 else ''))

        # Check if URL is truncated
        if "https://broadband.justmovein.co/packages?location=E14+9WB" in result:
            if "#/" in result:
                print("✅ URL has hash part - full URL generated")
            else:
                print("❌ URL is truncated - missing hash part")
                print("❌ This explains the user's issue!")
        else:
            print("❌ URL not found in result")

        print("\n📝 Testing with new_line='' (empty)...")

        # Test with new_line empty
        result_empty = await tool._handle_parameter_update(
            user_id=user_id,
            new_line=""
        )

        print("✅ Result:")
        print(result_empty[:1000] + ('...' if len(result_empty) > 1000 else ''))

        # Check if URL is truncated
        if "https://broadband.justmovein.co/packages?location=E14+9WB" in result_empty:
            if "#/" in result_empty:
                print("✅ URL has hash part - full URL generated")
            else:
                print("❌ URL is truncated - missing hash part")

    except Exception as e:
        print(f"❌ Error testing broadband tool: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_broadband_tool_new_line())
