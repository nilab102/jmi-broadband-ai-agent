#!/usr/bin/env python3
"""
Test script to verify the recommendations fix.
"""

import sys
import os
import asyncio

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def test_recommendations():
    """Test that recommendations work now."""

    print("🔍 Testing recommendations fix...")

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

        user_id = "test_recommendations"

        # First set up some parameters
        print("📝 Setting up broadband parameters...")

        await tool._handle_parameter_update(
            user_id=user_id,
            postcode="E14 9WB",
            speed_in_mb="55Mb",
            providers="Virgin Media"
        )

        # Now try to get recommendations
        print("📝 Testing get_recommendations...")

        result = await tool.execute(
            user_id=user_id,
            action_type="get_recommendations"
        )

        print("✅ Recommendations result:")
        print(result[:500] + ('...' if len(result) > 500 else ''))

        # Check if it succeeded (not an error)
        if "❌ Error generating recommendations" in result:
            print("❌ FAILURE: Recommendations still failing")
            return False
        else:
            print("✅ SUCCESS: Recommendations working!")
            return True

    except Exception as e:
        print(f"❌ Error testing recommendations: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_recommendations())
    if success:
        print("\n🎉 Recommendations fix verified!")
    else:
        print("\n💥 Recommendations still have issues.")
