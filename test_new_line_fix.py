#!/usr/bin/env python3
"""
Test script to verify the new_line parameter fix.
"""

import asyncio
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def test_new_line_parameter():
    """Test that new_line parameter works in URL generation."""

    print("🧪 Testing new_line parameter in URL generation...")

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

        user_id = "test_user"

        print("📝 Testing new_line parameter update...")

        # Test setting new_line parameter
        result = await tool._handle_parameter_update(
            user_id=user_id,
            postcode="E14 9WB",
            speed_in_mb="55Mb",
            new_line="NewLine"
        )

        print("✅ Result:")
        print(result)

        # Check if "NewLine" appears in the result
        if "NewLine" in result:
            print("✅ SUCCESS: new_line parameter is working!")
        else:
            print("❌ FAILURE: new_line parameter not found in result")

        # Test with different new_line value
        print("\n📝 Testing different new_line value...")

        result2 = await tool._handle_parameter_update(
            user_id=user_id,
            new_line="NewLine"
        )

        print("✅ Result:")
        print(result2)

        # Check if "NewLine" appears in the result
        if "NewLine" in result2:
            print("✅ SUCCESS: new_line parameter update is working!")
        else:
            print("❌ FAILURE: new_line parameter update not working")

    except Exception as e:
        print(f"❌ Error testing new_line parameter: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function."""
    print("🔧 Starting new_line parameter test...")

    await test_new_line_parameter()

if __name__ == "__main__":
    asyncio.run(main())
