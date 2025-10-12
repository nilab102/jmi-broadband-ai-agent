#!/usr/bin/env python3
"""
Broadband URL Generator for JustMoveIn broadband comparison service.
Generates valid comparison URLs with comprehensive parameter validation.
"""

from typing import Optional, List, Dict, Union
from urllib.parse import quote_plus, quote
from dataclasses import dataclass
import re


# ============================================================================
# CONSTANTS - All Valid Parameter Options
# ============================================================================

class BroadbandConstants:
    """All valid parameter values for the broadband comparison tool."""

    # Speed options
    VALID_SPEEDS = ["10Mb", "30Mb", "55Mb", "100Mb"]
    SPEED_DESCRIPTIONS = {
        "10Mb": "Standard (10Mb+)",
        "30Mb": "Fast Fibre (30Mb+)",
        "55Mb": "Superfast Fibre (55Mb+)",
        "100Mb": "Ultrafast Fibre (100Mb+)"
    }

    # Contract lengths
    VALID_CONTRACT_LENGTHS = ["1 month", "12 months", "18 months", "24 months"]

    # Phone call options
    VALID_PHONE_CALLS = [
        "Cheapest",
        "Show me everything",
        "Evening and Weekend",
        "Anytime",
        "No inclusive",
        "No phone line"
    ]
    PHONE_CALLS_DESCRIPTIONS = {
        "Cheapest": "Cheapest by provider",
        "Show me everything": "All call options",
        "Evening and Weekend": "Inclusive evening and weekend calls",
        "Anytime": "Inclusive anytime calls",
        "No inclusive": "No inclusive calls",
        "No phone line": "Deals without a phone line"
    }

    # Product types
    VALID_PRODUCT_TYPES = [
        "broadband",
        "broadband,phone",
        "broadband,tv",
        "broadband,phone,tv"
    ]
    PRODUCT_TYPE_DESCRIPTIONS = {
        "broadband": "Broadband only",
        "broadband,phone": "Broadband & Phone",
        "broadband,tv": "Broadband & TV",
        "broadband,phone,tv": "Broadband, Phone & TV"
    }

    # Available providers (based on location - can be dynamic)
    VALID_PROVIDERS = [
        "Virgin Media",
        "NOW Broadband",
        "Plusnet",
        "Airband",
        "BT",
        "Lightspeed",
        "Sky",
        "Vodafone",
        "Community Fibre",
        "4th Utility",
        "BRSK",
        "BeFibre",
        "Beebu",
        "Cuckoo",
        "Earth Broadband",
        "Fibrely",
        "Fibrus",
        "Gigaclear",
        "Go Fibre",
        "Hyperoptic",
        "KCOM",
        "POP Telecom",
        "Quickline",
        "Rise Fibre",
        "TrueSpeed",
        "YouFibre",
        "toob",
        "Hey Broadband",
        "Three",
        "Trooli",
        "Zzoomm",
        "Direct Save Telecom",
        "Onestream",
        "Rebel Internet"
    ]

    # Sort options
    VALID_SORT_OPTIONS = [
        "Recommended",
        "First Year Cost",
        "Avg. Monthly Cost",
        "Total Contract Cost",
        "Setup Costs",
        "Contract Length",
        "Speed",
        "Usage"
    ]

    # New line options
    VALID_NEW_LINE = ["", "NewLine"]

    # Fixed parameters
    MATRYOSHKA_SPEED = "Broadband"
    TAB = "alldeals"


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class BroadbandURLError(Exception):
    """Base exception for broadband URL generation errors."""
    pass


class InvalidPostcodeError(BroadbandURLError):
    """Raised when postcode is invalid."""
    pass


class InvalidSpeedError(BroadbandURLError):
    """Raised when speed parameter is invalid."""
    pass


class InvalidContractLengthError(BroadbandURLError):
    """Raised when contract length is invalid."""
    pass


class InvalidPhoneCallsError(BroadbandURLError):
    """Raised when phone calls option is invalid."""
    pass


class InvalidProductTypeError(BroadbandURLError):
    """Raised when product type is invalid."""
    pass


class InvalidProviderError(BroadbandURLError):
    """Raised when provider is invalid."""
    pass


class InvalidSortOptionError(BroadbandURLError):
    """Raised when sort option is invalid."""
    pass


class InvalidNewLineError(BroadbandURLError):
    """Raised when new line option is invalid."""
    pass


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

class ParameterValidator:
    """Validates all URL parameters with detailed error messages."""

    @staticmethod
    def validate_postcode(postcode: str) -> str:
        """
        Clean postcode without validation.

        Args:
            postcode: The postcode to clean

        Returns:
            Cleaned postcode string

        Raises:
            InvalidPostcodeError: If postcode is empty or not a string
        """
        if not postcode or not isinstance(postcode, str):
            raise InvalidPostcodeError(
                "Postcode is required and must be a string.\n"
                "Example: 'E14 9WB', 'SW1A 1AA', or any location identifier"
            )

        # Clean the postcode - just strip and uppercase, no format validation
        cleaned = postcode.strip().upper()

        return cleaned

    @staticmethod
    def validate_speed(speed: str) -> str:
        """
        Validate speed parameter.

        Args:
            speed: Speed value to validate

        Returns:
            Valid speed string

        Raises:
            InvalidSpeedError: If speed is invalid
        """
        if speed not in BroadbandConstants.VALID_SPEEDS:
            valid_options = "\n".join([
                f"  - {s}: {BroadbandConstants.SPEED_DESCRIPTIONS[s]}"
                for s in BroadbandConstants.VALID_SPEEDS
            ])
            raise InvalidSpeedError(
                f"Invalid speed: '{speed}'\n"
                f"Valid options:\n{valid_options}"
            )
        return speed

    @staticmethod
    def validate_contract_length(contract_length: str) -> str:
        """
        Validate contract length parameter.
        Supports single value or comma-separated multiple values.

        Args:
            contract_length: Contract length to validate

        Returns:
            Valid contract length string

        Raises:
            InvalidContractLengthError: If contract length is invalid
        """
        if not contract_length:
            return ""

        # Split by comma for multiple values
        lengths = [length.strip() for length in contract_length.split(',')]

        invalid_lengths = []
        for length in lengths:
            if length and length not in BroadbandConstants.VALID_CONTRACT_LENGTHS:
                invalid_lengths.append(length)

        if invalid_lengths:
            valid_options = "\n".join([
                f"  - {length}" for length in BroadbandConstants.VALID_CONTRACT_LENGTHS
            ])
            raise InvalidContractLengthError(
                f"Invalid contract length(s): {', '.join(invalid_lengths)}\n"
                f"Valid options:\n{valid_options}\n"
                f"Note: You can specify multiple values separated by commas, "
                f"e.g., '12 months,24 months'"
            )

        return contract_length

    @staticmethod
    def validate_phone_calls(phone_calls: str) -> str:
        """
        Validate phone calls parameter.

        Args:
            phone_calls: Phone calls option to validate

        Returns:
            Valid phone calls string

        Raises:
            InvalidPhoneCallsError: If phone calls option is invalid
        """
        if phone_calls not in BroadbandConstants.VALID_PHONE_CALLS:
            valid_options = "\n".join([
                f"  - '{opt}': {BroadbandConstants.PHONE_CALLS_DESCRIPTIONS[opt]}"
                for opt in BroadbandConstants.VALID_PHONE_CALLS
            ])
            raise InvalidPhoneCallsError(
                f"Invalid phone calls option: '{phone_calls}'\n"
                f"Valid options:\n{valid_options}"
            )
        return phone_calls

    @staticmethod
    def validate_product_type(product_type: str) -> str:
        """
        Validate product type parameter.

        Args:
            product_type: Product type to validate

        Returns:
            Valid product type string

        Raises:
            InvalidProductTypeError: If product type is invalid
        """
        if product_type not in BroadbandConstants.VALID_PRODUCT_TYPES:
            valid_options = "\n".join([
                f"  - '{opt}': {BroadbandConstants.PRODUCT_TYPE_DESCRIPTIONS[opt]}"
                for opt in BroadbandConstants.VALID_PRODUCT_TYPES
            ])
            raise InvalidProductTypeError(
                f"Invalid product type: '{product_type}'\n"
                f"Valid options:\n{valid_options}"
            )
        return product_type

    @staticmethod
    def validate_providers(providers: str) -> str:
        """
        Validate provider parameter.
        Supports single provider or comma-separated multiple providers.

        Args:
            providers: Provider name(s) to validate

        Returns:
            Valid providers string

        Raises:
            InvalidProviderError: If any provider is invalid
        """
        if not providers:
            return ""

        # Split by comma for multiple providers
        provider_list = [p.strip() for p in providers.split(',')]

        invalid_providers = []
        corrected_providers = []

        for provider in provider_list:
            if provider:
                # Find the correct case version
                found = False
                for valid_provider in BroadbandConstants.VALID_PROVIDERS:
                    if provider.lower() == valid_provider.lower():
                        corrected_providers.append(valid_provider)
                        found = True
                        break

                if not found:
                    invalid_providers.append(provider)
                    corrected_providers.append(provider)  # Keep original for error reporting

        if invalid_providers:
            # Show similar providers (fuzzy matching)
            suggestions = ParameterValidator._get_similar_providers(invalid_providers[0])
            suggestion_text = ""
            if suggestions:
                suggestion_text = f"\nDid you mean: {', '.join(suggestions)}?"

            valid_options = ", ".join(BroadbandConstants.VALID_PROVIDERS[:10]) + "..."
            raise InvalidProviderError(
                f"Invalid provider(s): {', '.join(invalid_providers)}\n"
                f"{suggestion_text}\n"
                f"Some valid providers: {valid_options}\n"
                f"Note: You can specify multiple providers separated by commas."
            )

        return ','.join(corrected_providers) if corrected_providers else ''

    @staticmethod
    def validate_sort_by(sort_by: str) -> str:
        """
        Validate sort option parameter.

        Args:
            sort_by: Sort option to validate

        Returns:
            Valid sort option string

        Raises:
            InvalidSortOptionError: If sort option is invalid
        """
        if sort_by not in BroadbandConstants.VALID_SORT_OPTIONS:
            valid_options = "\n".join([
                f"  - {opt}" for opt in BroadbandConstants.VALID_SORT_OPTIONS
            ])
            raise InvalidSortOptionError(
                f"Invalid sort option: '{sort_by}'\n"
                f"Valid options:\n{valid_options}"
            )
        return sort_by

    @staticmethod
    def validate_new_line(new_line: str) -> str:
        """
        Validate new line parameter.

        Args:
            new_line: New line option to validate

        Returns:
            Valid new line string

        Raises:
            InvalidNewLineError: If new line option is invalid
        """
        if new_line not in BroadbandConstants.VALID_NEW_LINE:
            raise InvalidNewLineError(
                f"Invalid new line option: '{new_line}'\n"
                f"Valid options: '' (empty) or 'NewLine'"
            )
        return new_line

    @staticmethod
    def _get_similar_providers(provider: str, max_suggestions: int = 3) -> List[str]:
        """
        Get similar provider names using simple string matching.

        Args:
            provider: The invalid provider name
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of similar provider names
        """
        provider_lower = provider.lower()
        suggestions = []

        for valid_provider in BroadbandConstants.VALID_PROVIDERS:
            valid_lower = valid_provider.lower()
            # Check if provider is substring or vice versa
            if provider_lower in valid_lower or valid_lower in provider_lower:
                suggestions.append(valid_provider)
            # Check first few characters
            elif len(provider_lower) >= 3 and valid_lower.startswith(provider_lower[:3]):
                suggestions.append(valid_provider)

        return suggestions[:max_suggestions]


# ============================================================================
# URL ENCODER
# ============================================================================

class URLEncoder:
    """Handles proper URL encoding for all parameters."""

    @staticmethod
    def encode_postcode(postcode: str) -> str:
        """
        Encode postcode for URL query string.
        Spaces should be encoded as '+' in query string.

        Args:
            postcode: Postcode to encode

        Returns:
            URL-encoded postcode
        """
        return quote_plus(postcode)

    @staticmethod
    def encode_parameter(value: str) -> str:
        """
        Encode parameter value for URL hash fragment.
        For parameters that may contain commas (like contract_length),
        spaces are encoded as %20 and commas are preserved.
        Consistently uses %20 for spaces (not +) for URL hash fragments.

        Args:
            value: Parameter value to encode

        Returns:
            URL-encoded parameter value
        """
        if not value:
            return ""

        # For hash fragment parameters, always encode spaces as %20
        # This maintains consistency between single and multiple values
        # and matches the expected URL format
        return value.replace(' ', '%20')

    @staticmethod
    def encode_providers(providers: str) -> str:
        """
        Special encoding for provider names.
        Handles multiple comma-separated values.

        Args:
            providers: Provider name(s)

        Returns:
            URL-encoded providers
        """
        if not providers:
            return ""

        # Split by comma, encode each, then rejoin
        provider_list = [p.strip() for p in providers.split(',')]

        # Find the correct case for each provider
        corrected_list = []
        for provider in provider_list:
            if provider:
                # Find the correct case version
                for valid_provider in BroadbandConstants.VALID_PROVIDERS:
                    if provider.lower() == valid_provider.lower():
                        corrected_list.append(valid_provider)
                        break
                else:
                    corrected_list.append(provider)  # Keep original if no match found

        encoded_list = [quote_plus(p) for p in corrected_list if p]
        return ','.join(encoded_list)


# ============================================================================
# MAIN URL GENERATOR
# ============================================================================

@dataclass
class BroadbandSearchParams:
    """Data class for broadband search parameters."""
    postcode: str
    speed_in_mb: str = "10Mb"
    contract_length: str = ""
    phone_calls: str = "Show me everything"
    product_type: str = "broadband,phone"
    providers: str = ""
    current_provider: str = ""
    new_line: str = ""
    sort_by: str = "Recommended"
    address_id: str = ""
    tv_channels: str = ""


class BroadbandURLGenerator:
    """
    Generates valid JustMoveIn broadband comparison URLs with comprehensive validation.
    """

    BASE_URL = "https://broadband.justmovein.co/packages"

    def __init__(self):
        self.validator = ParameterValidator()
        self.encoder = URLEncoder()

    def generate_url(
        self,
        postcode: str,
        speed_in_mb: str = "10Mb",
        contract_length: str = "",
        phone_calls: str = "Show me everything",
        product_type: str = "broadband,phone",
        providers: str = "",
        current_provider: str = "",
        new_line: str = "",
        sort_by: str = "Recommended",
        address_id: str = "",
        tv_channels: str = ""
    ) -> str:
        """
        Generate a valid broadband comparison URL with full validation.

        Args:
            postcode: UK postcode (required)
            speed_in_mb: Speed option (default: "10Mb")
            contract_length: Contract duration (default: "" - no filter)
            phone_calls: Phone call options (default: "Show me everything")
            product_type: Type of package (default: "broadband,phone")
            providers: Provider name(s), comma-separated
            current_provider: User's existing provider
            new_line: New line option
            sort_by: Sort order (default: "Recommended")
            address_id: Optional address identifier
            tv_channels: Optional TV channel filter

        Returns:
            Valid comparison URL

        Raises:
            BroadbandURLError: If any parameter is invalid

        Examples:
            >>> generator = BroadbandURLGenerator()
            >>> url = generator.generate_url(
            ...     postcode="E14 9WB",
            ...     speed_in_mb="100Mb",
            ...     providers="Hyperoptic"
            ... )
        """
        try:
            # Validate all parameters
            validated_params = self._validate_all_parameters(
                postcode=postcode,
                speed_in_mb=speed_in_mb,
                contract_length=contract_length,
                phone_calls=phone_calls,
                product_type=product_type,
                providers=providers,
                current_provider=current_provider,
                new_line=new_line,
                sort_by=sort_by,
                address_id=address_id,
                tv_channels=tv_channels
            )

            # Build URL
            url = self._build_url(validated_params)

            return url

        except BroadbandURLError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Catch any unexpected errors
            raise BroadbandURLError(
                f"Unexpected error generating URL: {str(e)}\n"
                f"Please check your parameters and try again."
            )

    def _validate_all_parameters(self, **kwargs) -> Dict[str, str]:
        """
        Validate all input parameters.

        Args:
            **kwargs: All parameter key-value pairs

        Returns:
            Dictionary of validated parameters

        Raises:
            BroadbandURLError: If any validation fails
        """
        validated = {}

        # Validate each parameter
        validated['postcode'] = self.validator.validate_postcode(kwargs['postcode'])
        validated['speed_in_mb'] = self.validator.validate_speed(kwargs['speed_in_mb'])
        validated['contract_length'] = self.validator.validate_contract_length(kwargs['contract_length'])
        validated['phone_calls'] = self.validator.validate_phone_calls(kwargs['phone_calls'])
        validated['product_type'] = self.validator.validate_product_type(kwargs['product_type'])
        validated['providers'] = self.validator.validate_providers(kwargs['providers'])
        validated['sort_by'] = self.validator.validate_sort_by(kwargs['sort_by'])
        validated['new_line'] = self.validator.validate_new_line(kwargs['new_line'])

        # These don't need validation (optional/free text)
        validated['current_provider'] = kwargs['current_provider']
        validated['address_id'] = kwargs['address_id']
        validated['tv_channels'] = kwargs['tv_channels']

        return validated

    def _build_url(self, params: Dict[str, str]) -> str:
        """
        Build the final URL from validated parameters.

        Args:
            params: Dictionary of validated parameters

        Returns:
            Complete URL string
        """
        # Encode postcode for query string
        encoded_postcode = self.encoder.encode_postcode(params['postcode'])

        # Build hash parameters in correct order
        hash_params = [
            f"addressId={self.encoder.encode_parameter(params['address_id'])}",
            f"contractLength={self.encoder.encode_parameter(params['contract_length'])}",
            f"currentProvider={self.encoder.encode_parameter(params['current_provider'])}",
            f"matryoshkaSpeed={BroadbandConstants.MATRYOSHKA_SPEED}",
            f"newLine={self.encoder.encode_parameter(params['new_line'])}",
            f"openProduct=",
            f"phoneCalls={self.encoder.encode_parameter(params['phone_calls'])}",
            f"productType={params['product_type']}",  # Don't encode commas
            f"providers={self.encoder.encode_providers(params['providers'])}",
            f"sortBy={self.encoder.encode_parameter(params['sort_by'])}",
            f"speedInMb={params['speed_in_mb']}",  # No encoding needed
            f"tab={BroadbandConstants.TAB}",
            f"tvChannels={self.encoder.encode_parameter(params['tv_channels'])}"
        ]

        hash_string = "&".join(hash_params)

        # Construct final URL
        final_url = f"{self.BASE_URL}?location={encoded_postcode}#/?{hash_string}"

        return final_url

    def generate_url_from_params(self, params: BroadbandSearchParams) -> str:
        """
        Generate URL from a BroadbandSearchParams object.

        Args:
            params: BroadbandSearchParams object

        Returns:
            Valid comparison URL
        """
        return self.generate_url(
            postcode=params.postcode,
            speed_in_mb=params.speed_in_mb,
            contract_length=params.contract_length,
            phone_calls=params.phone_calls,
            product_type=params.product_type,
            providers=params.providers,
            current_provider=params.current_provider,
            new_line=params.new_line,
            sort_by=params.sort_by,
            address_id=params.address_id,
            tv_channels=params.tv_channels
        )

    def get_valid_options(self) -> Dict[str, List[str]]:
        """
        Get all valid options for each parameter.
        Useful for building UIs or providing help.

        Returns:
            Dictionary mapping parameter names to valid options
        """
        return {
            "speeds": BroadbandConstants.VALID_SPEEDS,
            "contract_lengths": BroadbandConstants.VALID_CONTRACT_LENGTHS,
            "phone_calls": BroadbandConstants.VALID_PHONE_CALLS,
            "product_types": BroadbandConstants.VALID_PRODUCT_TYPES,
            "providers": BroadbandConstants.VALID_PROVIDERS,
            "sort_options": BroadbandConstants.VALID_SORT_OPTIONS,
            "new_line_options": BroadbandConstants.VALID_NEW_LINE
        }


# ============================================================================
# EXAMPLES AND TESTS
# ============================================================================

def demonstrate_usage():
    """Demonstrate various usage scenarios including error handling."""

    generator = BroadbandURLGenerator()

    print("=" * 80)
    print("BROADBAND URL GENERATOR - DEMONSTRATIONS")
    print("=" * 80)
    print()

    # Example 1: Basic valid URL
    print("1. Basic Hyperoptic Search (Valid)")
    print("-" * 80)
    try:
        url = generator.generate_url(
            postcode="E14 9WB",
            speed_in_mb="10Mb",
            providers="Hyperoptic"
        )
        print("✓ SUCCESS")
        print(f"URL: {url}")
    except BroadbandURLError as e:
        print(f"✗ ERROR: {e}")
    print()

    # Example 2: High speed with multiple contract lengths
    print("2. Fast Speed with Multiple Contract Lengths (Valid)")
    print("-" * 80)
    try:
        url = generator.generate_url(
            postcode="E14 9WB",
            speed_in_mb="100Mb",
            contract_length="12 months,24 months",
            providers="Hyperoptic",
            sort_by="First Year Cost"
        )
        print("✓ SUCCESS")
        print(f"URL: {url}")
    except BroadbandURLError as e:
        print(f"✗ ERROR: {e}")
    print()

    # Example 3: With TV package
    print("3. Broadband + Phone + TV Package (Valid)")
    print("-" * 80)
    try:
        url = generator.generate_url(
            postcode="SW1A 1AA",
            speed_in_mb="55Mb",
            contract_length="24 months",
            phone_calls="Anytime",
            product_type="broadband,phone,tv",
            providers="Hyperoptic"
        )
        print("✓ SUCCESS")
        print(f"URL: {url}")
    except BroadbandURLError as e:
        print(f"✗ ERROR: {e}")
    print()

    # Example 4: Multiple providers
    print("4. Multiple Providers (Valid)")
    print("-" * 80)
    try:
        url = generator.generate_url(
            postcode="E14 9WB",
            speed_in_mb="30Mb",
            providers="Hyperoptic,Onestream,POP Telecom"
        )
        print("✓ SUCCESS")
        print(f"URL: {url}")
    except BroadbandURLError as e:
        print(f"✗ ERROR: {e}")
    print()

    # Example 5: Invalid postcode
    print("5. Invalid Postcode (Error Case)")
    print("-" * 80)
    try:
        url = generator.generate_url(
            postcode="INVALID",
            speed_in_mb="10Mb"
        )
        print("✓ SUCCESS")
        print(f"URL: {url}")
    except BroadbandURLError as e:
        print(f"✗ ERROR:\n{e}")
    print()

    # Example 6: Invalid speed
    print("6. Invalid Speed (Error Case)")
    print("-" * 80)
    try:
        url = generator.generate_url(
            postcode="E14 9WB",
            speed_in_mb="500Mb"  # Invalid
        )
        print("✓ SUCCESS")
        print(f"URL: {url}")
    except BroadbandURLError as e:
        print(f"✗ ERROR:\n{e}")
    print()

    # Example 7: Invalid provider with suggestions
    print("7. Invalid Provider with Suggestions (Error Case)")
    print("-" * 80)
    try:
        url = generator.generate_url(
            postcode="E14 9WB",
            speed_in_mb="10Mb",
            providers="Hyperoptix"  # Typo - should be Hyperoptic
        )
        print("✓ SUCCESS")
        print(f"URL: {url}")
    except BroadbandURLError as e:
        print(f"✗ ERROR:\n{e}")
    print()

    # Example 8: Invalid contract length
    print("8. Invalid Contract Length (Error Case)")
    print("-" * 80)
    try:
        url = generator.generate_url(
            postcode="E14 9WB",
            speed_in_mb="10Mb",
            contract_length="6 months"  # Not available
        )
        print("✓ SUCCESS")
        print(f"URL: {url}")
    except BroadbandURLError as e:
        print(f"✗ ERROR:\n{e}")
    print()

    # Example 9: Invalid phone calls option
    print("9. Invalid Phone Calls Option (Error Case)")
    print("-" * 80)
    try:
        url = generator.generate_url(
            postcode="E14 9WB",
            speed_in_mb="10Mb",
            phone_calls="Unlimited calls"  # Invalid
        )
        print("✓ SUCCESS")
        print(f"URL: {url}")
    except BroadbandURLError as e:
        print(f"✗ ERROR:\n{e}")
    print()

    # Example 10: Get all valid options
    print("10. Get All Valid Options (Helper Method)")
    print("-" * 80)
    valid_options = generator.get_valid_options()
    print("Available speeds:")
    for speed in valid_options['speeds']:
        print(f"  - {speed}")
    print("\nAvailable contract lengths:")
    for length in valid_options['contract_lengths']:
        print(f"  - {length}")
    print()


# ============================================================================
# RUN DEMONSTRATIONS
# ============================================================================

if __name__ == "__main__":
    demonstrate_usage()
