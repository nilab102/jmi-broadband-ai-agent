#!/usr/bin/env python3
"""
Debug script to test provider extraction with fuzzy matching.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_provider_extraction():
    """Test provider parameter extraction with fuzzy matching."""

    print("🔍 Testing provider extraction with fuzzy matching...")

    try:
        # Import parameter extractor and provider matcher
        from voice_agent.functions.broadband.parameter_extraction import ParameterExtractor
        from voice_agent.functions.broadband.provider_matching import create_provider_matcher
        from voice_agent.broadband_url_generator import BroadbandConstants

        # Create provider matcher
        provider_matcher = create_provider_matcher(
            valid_providers=BroadbandConstants.VALID_PROVIDERS,
            fuzzy_searcher=None  # Will fall back to basic matching
        )

        # Create parameter extractor with provider matcher
        extractor = ParameterExtractor(provider_matcher=provider_matcher)
        extractor.initialize_patterns()

        # Test different provider inputs
        test_queries = [
            "virgin broadband",
            "with virgin",
            "from virgin",
            "virgin",
            "bt and sky",
            "BT, Sky, Virgin Media"
        ]

        for query in test_queries:
            print(f"\n📝 Testing query: '{query}'")

            # Extract parameters
            params = extractor.extract_parameters(query, skip_postcode_validation=True)

            print(f"Extracted providers: '{params.get('providers', '')}'")

            # Check if providers were extracted
            if params.get('providers'):
                print(f"✅ Providers extracted: '{params['providers']}'")
            else:
                print("❌ No providers extracted")

        print("\n" + "="*60)
        print("🔍 Testing fuzzy matching directly...")

        # Test fuzzy matching directly
        test_providers = ["virgin", "bt", "sky", "hyperoptic", "talktalk"]

        for provider in test_providers:
            print(f"\n📝 Testing fuzzy match for: '{provider}'")
            matched = provider_matcher.fuzzy_match(provider, threshold=50.0)
            print(f"Fuzzy match result: '{matched}'")

    except Exception as e:
        print(f"❌ Error testing provider extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_provider_extraction()
