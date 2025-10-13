#!/usr/bin/env python3
"""
Debug script to test how text agent would handle 'add new line'.
"""

import sys
import os
import asyncio

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def test_text_agent_new_line():
    """Test how text agent handles 'add new line'."""

    print("🔍 Testing text agent parameter extraction for 'add new line'...")

    try:
        # Import parameter extractor
        from voice_agent.functions.broadband.parameter_extraction import ParameterExtractor

        # Create parameter extractor
        extractor = ParameterExtractor()
        extractor.initialize_patterns()

        # Test different ways user might say "add new line"
        test_queries = [
            "add new line",
            "include new line",
            "I want new line installation",
            "with new line",
            "new line please"
        ]

        for query in test_queries:
            print(f"\n📝 Testing query: '{query}'")

            # Extract parameters
            params = extractor.extract_parameters(query, skip_postcode_validation=True)

            print(f"Extracted parameters: {params}")

            # Check if new_line was extracted
            if params.get('new_line'):
                print(f"✅ new_line extracted: '{params['new_line']}'")
            else:
                print("❌ new_line not extracted")

        print("\n" + "="*60)
        print("🔍 Testing broadband tool with extracted parameters...")

        # Import broadband tool
        from voice_agent.tools.broadband_tool import BroadbandTool
        from pipecat.processors.frameworks.rtvi import RTVIProcessor

        # Create mock RTVI processor
        class MockRTVIProcessor:
            def __init__(self):
                self.task = None

        rtvi_processor = MockRTVIProcessor()
        tool = BroadbandTool(rtvi_processor)

        user_id = "debug_text_user"

        # Test what happens when text agent calls broadband tool with new_line parameter
        print("📝 Simulating text agent call with new_line='NewLine'...")

        result = await tool.execute(
            user_id=user_id,
            action_type="query",
            postcode="E14 9WB",
            speed_in_mb="55Mb",
            new_line="NewLine"
        )

        print("✅ Tool result:")
        print(result[:1000] + ('...' if len(result) > 1000 else ''))

        # Check URL
        if "https://broadband.justmovein.co/packages?location=E14+9WB" in result:
            if "#/" in result:
                print("✅ URL has hash part - full URL generated")
            else:
                print("❌ URL is truncated - missing hash part")

    except Exception as e:
        print(f"❌ Error testing text agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_text_agent_new_line())
