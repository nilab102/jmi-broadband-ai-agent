#!/usr/bin/env python3
"""
Debug script to test contract length patterns and processor.
"""

import re
from jmi_broadband_agent.broadband_url_generator import BroadbandConstants

def _extract_contract_lengths(match: str) -> str:
    """
    Extract and format multiple contract lengths from natural language.
    """
    if not match or not match.strip():
        return ""

    # Convert to lowercase for easier processing
    match_lower = match.lower().strip()

    # Split by common separators and clean up
    # Handle: commas, "or", "and", mixed separators
    parts = re.split(r'\s*(?:,|or|and)\s*', match_lower)

    # Extract numbers from each part
    valid_lengths = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract number from this part
        num_match = re.search(r'(\d+)', part)
        if num_match:
            length_int = int(num_match.group(1))
            # Only accept valid contract lengths
            if f"{length_int} months" in BroadbandConstants.VALID_CONTRACT_LENGTHS:
                valid_lengths.append(f"{length_int} months")

    if not valid_lengths:
        return ""

    # Remove duplicates and sort
    valid_lengths = list(set(valid_lengths))
    valid_lengths.sort(key=lambda x: int(x.split()[0]))

    # Join with commas (no spaces around commas, as expected by URL generator)
    return ','.join(valid_lengths)

def debug_patterns():
    patterns = [
        # Broad patterns to capture multiple contract lengths (must come first)
        (r'(?:contract[:\s]*)?(\d+(?:\s*(?:or|and|,)\s*\d+)+.*?months?)', '_extract_contract_lengths'),
        (r'(?:contract[:\s]*)?(\d+.*?months?\s*,.*?months?)', '_extract_contract_lengths'),
        # Single contract lengths (existing patterns)
        (r'(\d+)\s*month\s*contract', 'lambda_single'),
        (r'contract[:\s]*(\d+)\s*month', 'lambda_single'),
        (r'(\d+)\s*months?', 'lambda_single'),
    ]

    test_queries = [
        "12 months, 24 months",
        "12 or 24 months",
        "12 and 24 months",
        "12, 24 months",
        "contract 12 months, 24 months"
    ]

    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        query_lower = query.lower()

        for i, (pattern, processor_type) in enumerate(patterns):
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                captured = match.group(1) if match.groups() else match.group(0)
                print(f"  Pattern {i+1} ({processor_type}): MATCHED '{captured}'")

                if processor_type == '_extract_contract_lengths':
                    processed = _extract_contract_lengths(captured)
                    print(f"    Processed result: '{processed}'")

                break
            else:
                print(f"  Pattern {i+1} ({processor_type}): no match")

if __name__ == "__main__":
    debug_patterns()
