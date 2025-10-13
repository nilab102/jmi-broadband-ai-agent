#!/usr/bin/env python3
"""
Test script for the new conversational broadband flow.
Tests the broadband tool directly without full server stack.
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def test_broadband_tool_directly():
    """Test the broadband tool directly with parameter updates."""

    print("🚀 Testing broadband tool parameter updates directly...")

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

        print(f"\n{'='*60}")
        print("🧪 TESTING: Conversational parameter accumulation")
        print(f"{'='*60}")

        # Test conversational flow
        test_steps = [
            ("Postcode only", {"postcode": "E14 9WB"}),
            ("Add speed", {"speed_in_mb": "100Mb"}),
            ("Change speed", {"speed_in_mb": "55Mb"}),
            ("Add contract", {"contract_length": "24 months"}),
            ("Add provider", {"providers": "Hyperoptic"})
        ]

        for step_name, params in test_steps:
            print(f"\n📝 Step: {step_name}")
            print(f"Parameters: {params}")
            print("-" * 40)

            # Call the parameter update method
            result = await tool._handle_parameter_update(user_id, **params)

            print(f"✅ Result: {result[:300]}{'...' if len(result) > 300 else ''}")

            # Small delay
            await asyncio.sleep(0.5)

        # Test URL generation with accumulated parameters
        print(f"\n{'='*60}")
        print("🧪 TESTING: URL generation with accumulated parameters")
        print(f"{'='*60}")

        result = await tool._handle_parameter_update(user_id)
        print(f"✅ Final result: {result[:500]}{'...' if len(result) > 500 else ''}")

        print(f"\n{'='*60}")
        print("🎉 Direct tool tests completed successfully!")
        print(f"{'='*60}")

    except Exception as e:
        print(f"❌ Error testing broadband tool: {e}")
        import traceback
        traceback.print_exc()

async def test_original_issue():
    """Test the original issue that was failing."""

    print(f"\n{'='*60}")
    print("🧪 TESTING: Original issue reproduction")
    print(f"{'='*60}")

    try:
        from voice_agent.tools.broadband_tool import BroadbandTool
        from pipecat.processors.frameworks.rtvi import RTVIProcessor

        class MockRTVIProcessor:
            def __init__(self):
                self.task = None

        rtvi_processor = MockRTVIProcessor()
        tool = BroadbandTool(rtvi_processor)

        user_id = "test_user"

        # Simulate the original failing call: action_type="query" with individual parameters
        print("📝 Original failing call: action_type='query' with postcode and speed_in_mb")

        result = await tool.execute(
            user_id=user_id,
            action_type="query",
            postcode="E14 9WB",
            speed_in_mb="55Mb"
        )

        print("✅ Result received (should now work):")
        print(result[:500] + ('...' if len(result) > 500 else ''))

        print("🎉 Original issue test passed!")

    except Exception as e:
        print(f"❌ Original issue test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function."""
    print("🔧 Starting direct broadband tool tests...")

    # Test direct tool functionality
    await test_broadband_tool_directly()
    await test_original_issue()

if __name__ == "__main__":
    asyncio.run(main())
