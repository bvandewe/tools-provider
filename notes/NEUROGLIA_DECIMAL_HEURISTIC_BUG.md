# Neuroglia Framework Bug Report: Decimal Heuristic in JSON Deserializer

## Issue Summary

The `_infer_and_deserialize` method in `neuroglia/serialization/json.py` has a heuristic that causes `decimal.InvalidOperation` errors when deserializing nested dictionaries containing field names that match monetary patterns (e.g., "price", "cost", "amount", "total", "fee").

## Environment

- **Neuroglia Version**: Latest (as of 2025-12-07)
- **Python Version**: 3.12
- **File**: `/neuroglia/serialization/json.py`
- **Method**: `_infer_and_deserialize` (around line 500-515)

## Error Message

```
decimal.InvalidOperation: [<class 'decimal.ConversionSyntax'>]
```

## Stack Trace

```python
File "/usr/local/lib/python3.12/site-packages/neuroglia/serialization/json.py", line 523, in _infer_and_deserialize
    return {k: self._infer_and_deserialize(f"{field_name}_{k}", v, target_type) for k, v in value.items()}
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/neuroglia/serialization/json.py", line 509, in _infer_and_deserialize
    return Decimal(value)
           ^^^^^^^^^^^^^^
decimal.InvalidOperation: [<class 'decimal.ConversionSyntax'>]
```

## Root Cause Analysis

The problematic code is in `_infer_and_deserialize`:

```python
def _infer_and_deserialize(self, field_name: str, value: Any, target_type: type) -> Any:
    # ... earlier code ...

    if isinstance(value, str):
        # Try to detect decimal/money fields by name patterns
        if any(pattern in field_name.lower() for pattern in ["price", "cost", "amount", "total", "fee"]):
            try:
                from decimal import Decimal
                return Decimal(value)
            except (ValueError, TypeError):  # <-- BUG: Missing InvalidOperation
                pass
```

**Two issues:**

1. **Missing exception handler**: The `except` clause only catches `ValueError` and `TypeError`, but `Decimal()` can also raise `decimal.InvalidOperation` for invalid syntax.

2. **Overly broad field name matching**: When recursively processing nested dictionaries, the method builds compound field names like `input_schema_properties_price_type`. The substring match on "price" triggers the Decimal conversion attempt on values like `"number"` (a JSON Schema type string), which is not a valid decimal.

## Reproduction Case

### Minimal Reproducer

```python
from decimal import Decimal

# This is what neuroglia tries to do when it sees a field name containing "price"
# and the value is a string
field_name = "input_schema_properties_price_type"  # Built from nested dict traversal
value = "number"  # JSON Schema type, not a decimal number

if "price" in field_name.lower():
    result = Decimal(value)  # Raises InvalidOperation!
```

### Real-World Scenario

When storing OpenAPI schemas in MongoDB via `Dict[str, Any]` fields, the nested structure contains JSON Schema definitions like:

```json
{
  "input_schema": {
    "properties": {
      "price": {
        "type": "number",
        "description": "Price in USD"
      }
    }
  }
}
```

During deserialization, neuroglia recursively processes this dict and builds field names:

- `input_schema_properties_price_type` → value: `"number"`
- `input_schema_properties_price_description` → value: `"Price in USD"`

Both trigger the Decimal heuristic because "price" is in the field name, but neither value is a valid decimal.

## Proposed Fix

### Option 1: Add Missing Exception Handler (Minimal Fix)

```python
if any(pattern in field_name.lower() for pattern in ["price", "cost", "amount", "total", "fee"]):
    try:
        from decimal import Decimal, InvalidOperation
        return Decimal(value)
    except (ValueError, TypeError, InvalidOperation):  # Added InvalidOperation
        pass
```

### Option 2: More Conservative Heuristic (Recommended)

Only apply the Decimal heuristic when the field name **ends with** a monetary pattern, not just contains it. This prevents false positives from nested paths:

```python
# Only match when the field name ends with the pattern (not contains)
monetary_patterns = ["price", "cost", "amount", "total", "fee"]
field_name_parts = field_name.lower().split("_")
last_part = field_name_parts[-1] if field_name_parts else ""

if last_part in monetary_patterns:
    try:
        from decimal import Decimal, InvalidOperation
        return Decimal(value)
    except (ValueError, TypeError, InvalidOperation):
        pass
```

### Option 3: Validate String Before Decimal Conversion

```python
import re

if any(pattern in field_name.lower() for pattern in ["price", "cost", "amount", "total", "fee"]):
    # Only attempt Decimal conversion if the string looks like a number
    if re.match(r'^-?\d+\.?\d*$', value):
        try:
            from decimal import Decimal, InvalidOperation
            return Decimal(value)
        except (ValueError, TypeError, InvalidOperation):
            pass
```

## Impact

This bug affects any application that:

1. Uses `Dict[str, Any]` type hints for flexible schema storage
2. Stores nested JSON structures containing field names with monetary keywords
3. Has nested properties under fields named "price", "cost", "amount", "total", or "fee"

Common use cases affected:

- OpenAPI/JSON Schema storage
- Configuration objects with nested pricing structures
- Any domain model with nested dictionaries containing monetary field names

## Workaround

Until fixed, users can avoid this by:

1. Not using field names containing monetary patterns in nested dictionaries
2. Using more specific type hints instead of `Dict[str, Any]` (though this may not always be feasible)
3. Pre-processing data to rename problematic fields before storage

## Test Case

```python
import pytest
from decimal import InvalidOperation
from neuroglia.serialization.json import JsonSerializer

def test_nested_dict_with_price_field_deserializes_correctly():
    """Ensure nested dicts with 'price' in path don't trigger Decimal conversion errors."""

    serializer = JsonSerializer()

    # Simulate OpenAPI schema with price field
    data = {
        "input_schema": {
            "properties": {
                "price": {
                    "type": "number",
                    "description": "Price in USD"
                }
            }
        }
    }

    # This should NOT raise InvalidOperation
    # The "type": "number" should remain a string, not be converted to Decimal
    result = serializer.deserialize_from_text(
        json.dumps(data),
        SomeDataclass  # with input_schema: Dict[str, Any]
    )

    assert result.input_schema["properties"]["price"]["type"] == "number"
```

## Priority

**High** - This is a runtime error that causes application failures when processing common data structures like OpenAPI schemas.
