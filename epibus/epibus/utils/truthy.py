def truthy(value):
    """
    JavaScript-like truthy evaluation

    In JavaScript, these values are falsy:
    - false
    - 0, -0, 0n (BigInt zero)
    - '', "", `` (empty strings)
    - null
    - undefined
    - NaN

    Everything else is truthy, including:
    - '0', 'false' (non-empty strings)
    - [] (empty array)
    - {} (empty object)
    - Any non-zero number including negative numbers

    Args:
        value: Any value to evaluate for truthiness

    Returns:
        bool: True if the value is truthy, False if falsy
    """
    # Handle None (equivalent to null/undefined)
    if value is None:
        return False

    # Handle strings
    if isinstance(value, str):
        # Empty string is falsy
        if value == '':
            return False

        # In JavaScript, string '0' is truthy, 'false' is truthy, etc.
        return True

    # Handle numeric values
    if isinstance(value, (int, float)):
        # Zero is falsy, any other number is truthy
        return value != 0

    # Handle boolean values
    if isinstance(value, bool):
        return value

    # In JavaScript, empty lists and dicts are truthy (unlike Python)
    # So we return True for these cases

    # Default case: use Python's truthiness for other types
    return bool(value)


def falsey(value):
    """
    JavaScript-like falsy evaluation (opposite of truthy)

    Args:
        value: Any value to evaluate for falsiness

    Returns:
        bool: True if the value is falsy, False if truthy
    """
    return not truthy(value)


# Function to convert string to appropriate value type based on content
def parse_value(value):
    """
    Parse a value into the appropriate type

    Args:
        value: Any value to parse

    Returns:
        Parsed value with appropriate type
    """
    # If it's not a string, return as is
    if not isinstance(value, str):
        return value

    # Try to convert to boolean
    if value.lower() in ('true', 't', 'yes', 'y', '1'):
        return True
    if value.lower() in ('false', 'f', 'no', 'n', '0'):
        return False

    # Try to convert to number
    try:
        # Try as integer first
        int_val = int(value)
        return int_val
    except ValueError:
        try:
            # Then try as float
            float_val = float(value)
            return float_val
        except ValueError:
            # If all else fails, keep as string
            return value
