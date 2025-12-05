# Neuroglia Framework Bug Report & Fix Proposal

## Issue: `_get_lambda_source_code` fails with multi-line method chains

**Severity:** High
**Component:** `neuroglia.data.queryable.Queryable`
**Affected Methods:** `where()`, `first_or_default()`, `last_or_default()`, `select()`
**Python Versions:** All (3.8+)

---

## Problem Description

The `_get_lambda_source_code` method in `Queryable` fails when lambdas are used in multi-line method chains (a very common pattern). The error manifests as:

```
TypeError: compile() arg 1 must be a string, bytes or AST object
```

or

```
SyntaxError: invalid syntax
```

### Root Cause

When using backslash continuation or implicit line continuation in method chains, `inspect.getsourcelines()` returns only the **current line**, which may start with a dot (`.`):

```python
# This common pattern triggers the bug:
queryable = await self.query_async()
return await queryable \
    .where(lambda source: source.is_enabled == True) \  # <-- Bug here!
    .order_by(lambda source: source.name) \
    .to_list_async()
```

The line `.where(lambda source: source.is_enabled == True)` is extracted by `inspect.getsourcelines()`, but this is **invalid Python syntax** (starts with `.`), causing `ast.parse()` to fail.

### Reproduction

```python
from neuroglia.data.infrastructure.mongo import MotorRepository

class MyRepository(MotorRepository[MyDto, str]):
    async def get_enabled_async(self):
        queryable = await self.query_async()
        # This fails:
        return await queryable \
            .where(lambda item: item.is_enabled == True) \
            .to_list_async()
```

**Error:**

```
File "neuroglia/data/queryable.py", line 217, in where
    lambda_tree = ast.parse(lambda_src)
TypeError: compile() arg 1 must be a string, bytes or AST object
```

---

## Proposed Fix

### Option 1: Wrap Invalid Syntax Lines (Recommended)

When the source line starts with `.`, prepend a dummy identifier to make it parseable, then adjust offsets accordingly.

**File:** `neuroglia/data/queryable.py`

```python
def _get_lambda_source_code(self, function: Callable, max_col_offset: int = None) -> Optional[str]:
    """Gets the source code of the specified lambda.

    Args:
        function (Callable): The lambda to get the source code of
        max_col_offset (int): The maximum column offset to walk the AST tree for the target lambda

    Returns:
        Optional[str]: The lambda source code, or None if extraction fails

    Notes:
        Credits to https://gist.github.com/Xion/617c1496ff45f3673a5692c3b0e3f75a

        This method handles the case where the lambda is on a continuation line
        that starts with '.' (common in method chaining). In such cases, the raw
        source line is invalid Python syntax, so we prepend a dummy identifier
        to make it parseable.
    """
    source_lines, _ = inspect.getsourcelines(function)
    if len(source_lines) != 1:
        return None

    source_text = os.linesep.join(source_lines).strip()

    # Handle continuation lines that start with '.' (method chaining)
    # These are invalid Python syntax on their own
    offset_adjustment = 0
    if source_text.startswith('.'):
        source_text = '_' + source_text  # Prepend dummy identifier
        offset_adjustment = 1

    try:
        source_ast = ast.parse(source_text)
    except SyntaxError:
        return None

    if max_col_offset is not None:
        max_col_offset = max_col_offset + offset_adjustment
    else:
        max_col_offset = len(source_text)

    lambda_node = next(
        (node for node in ast.walk(source_ast)
         if isinstance(node, ast.Lambda) and node.col_offset <= max_col_offset),
        None,
    )
    if lambda_node is None:
        return None

    lambda_text = source_text[lambda_node.col_offset : lambda_node.end_col_offset]
    return lambda_text
```

### Option 2: Use Regex Fallback

If AST parsing fails, use regex to extract the lambda:

```python
import re

def _get_lambda_source_code(self, function: Callable, max_col_offset: int = None) -> Optional[str]:
    source_lines, _ = inspect.getsourcelines(function)
    if len(source_lines) != 1:
        return None

    source_text = os.linesep.join(source_lines).strip()

    try:
        source_ast = ast.parse(source_text)
    except SyntaxError:
        # Fallback: Use regex to extract lambda when AST parsing fails
        # This handles continuation lines starting with '.'
        lambda_match = re.search(r'lambda\s+\w+\s*:\s*[^,)\]]+', source_text)
        if lambda_match:
            lambda_text = lambda_match.group(0)
            # Validate it's parseable
            try:
                ast.parse(lambda_text)
                return lambda_text
            except SyntaxError:
                pass
        return None

    # ... rest of original implementation
```

---

## Test Cases

The following test cases should be added to validate the fix:

```python
import pytest
from neuroglia.data.queryable import Queryable

class TestQueryableLambdaExtraction:
    """Test lambda extraction in various code layouts."""

    def test_single_line_lambda(self):
        """Lambda on single line should work."""
        # queryable.where(lambda x: x.enabled == True)
        pass  # Already works

    def test_multiline_method_chain_backslash(self):
        """Lambda in backslash-continued chain should work."""
        # result = queryable \
        #     .where(lambda x: x.enabled == True) \
        #     .to_list()
        pass  # Fix required

    def test_multiline_method_chain_parentheses(self):
        """Lambda in parenthesis-continued chain should work."""
        # result = (queryable
        #     .where(lambda x: x.enabled == True)
        #     .to_list())
        pass  # Fix required

    def test_lambda_with_boolean_literal(self):
        """Lambda comparing to True/False should work."""
        # .where(lambda x: x.is_active == True)
        pass

    def test_lambda_with_captured_variable(self):
        """Lambda with captured variable should work."""
        # status = "active"
        # .where(lambda x: x.status == status)
        pass
```

---

## Backward Compatibility

The proposed fix is **fully backward compatible**:

1. Single-line lambda usage (already working) continues to work unchanged
2. Multi-line chains that previously failed will now work
3. No API changes required
4. No changes to query execution logic

---

## Alternative Workarounds

Until the fix is merged, users can work around the issue by:

1. **Using MongoDB filter dictionaries directly:**

   ```python
   return await self.find_async({"is_enabled": True})
   ```

2. **Putting lambdas on single lines:**

   ```python
   # Instead of:
   result = queryable \
       .where(lambda x: x.enabled == True)

   # Use:
   result = queryable.where(lambda x: x.enabled == True)
   ```

3. **Using intermediate variables:**

   ```python
   filtered = queryable.where(lambda x: x.enabled == True)
   result = filtered.to_list()
   ```

---

## Implementation Notes

1. The fix adds minimal overhead (single string check for `.` prefix)
2. The `offset_adjustment` ensures `max_col_offset` filtering still works correctly
3. Consider adding a debug log when the fallback path is taken
4. The fix should be applied to all methods that call `_get_lambda_source_code`:
   - `where()`
   - `first_or_default()`
   - `last_or_default()`
   - `select()`

---

## References

- Related: Python `inspect.getsourcelines()` documentation
- Related: AST module continuation handling
- Credits: Original lambda extraction technique from https://gist.github.com/Xion/617c1496ff45f3673a5692c3b0e3f75a
