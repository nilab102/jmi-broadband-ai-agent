#!/usr/bin/env python3
"""
Debug script to check what's happening with new_line parameter.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_url_generation_with_new_line():
    """Test URL generation with new_line parameter."""

    print("🔍 Debugging new_line parameter in URL generation...")

    try:
        # Import the URL generator service
        from voice_agent.services.url_generator_service import get_url_generator_service

        # Get the service
        service = get_url_generator_service()

        # Test parameters with new_line
        test_params = {
            'postcode': 'E14 9WB',
            'speed_in_mb': '55Mb',
            'contract_length': '',
            'phone_calls': 'Show me everything',
            'product_type': 'broadband,phone',
            'providers': '',
            'current_provider': '',
            'sort_by': 'Recommended',
            'new_line': 'NewLine'
        }

        print(f"📝 Test parameters: {test_params}")

        # Generate URL
        url = service.generate_url(test_params)

        print(f"✅ Generated URL: {url}")

        # Check if URL contains hash part
        if '#/' in url:
            print("✅ URL has hash part - parameters included")
        else:
            print("❌ URL missing hash part - parameters not included")

        # Check if newLine appears in URL
        if 'newLine=NewLine' in url:
            print("✅ newLine parameter found in URL")
        else:
            print("❌ newLine parameter NOT found in URL")

        # Test with empty new_line
        print("\n📝 Testing with empty new_line...")
        test_params_empty = test_params.copy()
        test_params_empty['new_line'] = ''

        url_empty = service.generate_url(test_params_empty)
        print(f"✅ Generated URL (empty new_line): {url_empty}")

        if '#/' in url_empty:
            print("✅ URL has hash part - parameters included")
        else:
            print("❌ URL missing hash part - parameters not included")

    except Exception as e:
        print(f"❌ Error during URL generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_url_generation_with_new_line()
