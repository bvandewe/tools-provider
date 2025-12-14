"""Utility tools for common operations.

Tools for general-purpose utilities:
- get_current_datetime: Get current date/time in various formats
- calculate: Safe math expression evaluation
- generate_uuid: Generate UUIDs
- encode_decode: Base64, URL, HTML, hex encoding/decoding
- regex_extract: Extract text using regex patterns
- json_transform: Apply JSONPath expressions
- text_stats: Analyze text statistics
"""

import base64
import html
import json
import logging
import math
import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, unquote
from uuid import uuid4

from .base import BuiltinToolResult, UserContext

logger = logging.getLogger(__name__)


async def execute_get_current_datetime(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the get_current_datetime tool."""
    timezone_name = arguments.get("timezone", "UTC")
    output_format = arguments.get("format", "all")

    try:
        now = datetime.now(UTC)

        try:
            import zoneinfo

            tz = zoneinfo.ZoneInfo(timezone_name)
            now_tz = now.astimezone(tz)
        except Exception:
            now_tz = now
            logger.warning(f"Unknown timezone: {timezone_name}, using UTC")

        if output_format == "iso":
            result = now_tz.isoformat()
        elif output_format == "unix":
            result = int(now_tz.timestamp())
        elif output_format == "human":
            result = now_tz.strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")
        else:
            result = {
                "iso": now_tz.isoformat(),
                "unix": int(now_tz.timestamp()),
                "human": now_tz.strftime("%A, %B %d, %Y at %I:%M:%S %p %Z"),
                "date": now_tz.strftime("%Y-%m-%d"),
                "time": now_tz.strftime("%H:%M:%S"),
                "timezone": timezone_name,
            }

        return BuiltinToolResult(success=True, result=result)

    except Exception as e:
        return BuiltinToolResult(success=False, error=f"Failed to get datetime: {str(e)}")


async def execute_calculate(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the calculate tool with safe math evaluation."""
    expression = arguments.get("expression", "")
    precision = arguments.get("precision", 10)

    if not expression:
        return BuiltinToolResult(success=False, error="Expression is required")

    safe_dict = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "sqrt": math.sqrt,
        "floor": math.floor,
        "ceil": math.ceil,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        "pi": math.pi,
        "e": math.e,
    }

    try:
        if not re.match(r"^[\d\s\+\-\*/\.\(\)\,\w]+$", expression):
            return BuiltinToolResult(success=False, error="Expression contains invalid characters")

        result = eval(expression, {"__builtins__": {}}, safe_dict)  # noqa: S307  # nosec B307

        if isinstance(result, float):
            result = round(result, precision)

        return BuiltinToolResult(success=True, result=result, metadata={"expression": expression})

    except ZeroDivisionError:
        return BuiltinToolResult(success=False, error="Division by zero")
    except Exception as e:
        return BuiltinToolResult(success=False, error=f"Calculation error: {str(e)}")


async def execute_generate_uuid(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the generate_uuid tool."""
    count = min(max(arguments.get("count", 1), 1), 100)
    output_format = arguments.get("format", "standard")

    uuids = []
    for _ in range(count):
        new_uuid = uuid4()
        if output_format == "hex":
            uuids.append(new_uuid.hex)
        elif output_format == "urn":
            uuids.append(new_uuid.urn)
        else:
            uuids.append(str(new_uuid))

    result = uuids[0] if count == 1 else uuids
    return BuiltinToolResult(success=True, result=result)


async def execute_encode_decode(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the encode_decode tool."""
    text = arguments.get("text", "")
    encoding = arguments.get("encoding", "")
    operation = arguments.get("operation", "")

    if not text:
        return BuiltinToolResult(success=False, error="Text is required")
    if not encoding:
        return BuiltinToolResult(success=False, error="Encoding is required")
    if operation not in ("encode", "decode"):
        return BuiltinToolResult(success=False, error="Operation must be 'encode' or 'decode'")

    try:
        if encoding == "base64":
            if operation == "encode":
                result = base64.b64encode(text.encode()).decode()
            else:
                result = base64.b64decode(text.encode()).decode()

        elif encoding == "url":
            if operation == "encode":
                result = quote(text, safe="")
            else:
                result = unquote(text)

        elif encoding == "html":
            if operation == "encode":
                result = html.escape(text)
            else:
                result = html.unescape(text)

        elif encoding == "hex":
            if operation == "encode":
                result = text.encode().hex()
            else:
                result = bytes.fromhex(text).decode()

        else:
            return BuiltinToolResult(success=False, error=f"Unknown encoding: {encoding}")

        return BuiltinToolResult(success=True, result=result)

    except Exception as e:
        return BuiltinToolResult(success=False, error=f"{operation.title()} error: {str(e)}")


async def execute_regex_extract(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the regex_extract tool."""
    text = arguments.get("text", "")
    pattern = arguments.get("pattern", "")
    flags_str = arguments.get("flags", "")
    max_matches = min(arguments.get("max_matches", 100), 1000)

    if not text:
        return BuiltinToolResult(success=False, error="Text is required")
    if not pattern:
        return BuiltinToolResult(success=False, error="Pattern is required")

    flags = 0
    if "i" in flags_str:
        flags |= re.IGNORECASE
    if "m" in flags_str:
        flags |= re.MULTILINE
    if "s" in flags_str:
        flags |= re.DOTALL

    try:
        compiled = re.compile(pattern, flags)
        matches = []

        for i, match in enumerate(compiled.finditer(text)):
            if i >= max_matches:
                break

            match_info: dict[str, Any] = {
                "match": match.group(),
                "start": match.start(),
                "end": match.end(),
            }

            if match.groupdict():
                match_info["groups"] = match.groupdict()
            elif match.groups():
                match_info["groups"] = list(match.groups())

            matches.append(match_info)

        return BuiltinToolResult(
            success=True,
            result=matches,
            metadata={"pattern": pattern, "match_count": len(matches)},
        )

    except re.error as e:
        return BuiltinToolResult(success=False, error=f"Invalid regex: {str(e)}")


async def execute_json_transform(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the json_transform tool."""
    data = arguments.get("data")
    path = arguments.get("path", "")

    if data is None:
        return BuiltinToolResult(success=False, error="Data is required")
    if not path:
        return BuiltinToolResult(success=False, error="Path is required")

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            return BuiltinToolResult(success=False, error=f"Invalid JSON: {str(e)}")

    try:
        result = _apply_jsonpath(data, path)
        return BuiltinToolResult(success=True, result=result)

    except Exception as e:
        return BuiltinToolResult(success=False, error=f"JSONPath error: {str(e)}")


async def execute_text_stats(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the text_stats tool."""
    text = arguments.get("text", "")
    include_freq = arguments.get("include_word_frequency", False)

    if not text:
        return BuiltinToolResult(success=False, error="Text is required")

    char_count = len(text)
    char_count_no_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))

    words = re.findall(r"\b\w+\b", text.lower())
    word_count = len(words)

    sentences = re.split(r"[.!?]+", text)
    sentence_count = len([s for s in sentences if s.strip()])

    paragraphs = re.split(r"\n\s*\n", text)
    paragraph_count = len([p for p in paragraphs if p.strip()])

    avg_word_length = sum(len(w) for w in words) / word_count if word_count else 0
    reading_time_minutes = word_count / 200

    result: dict[str, Any] = {
        "character_count": char_count,
        "character_count_no_spaces": char_count_no_spaces,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "average_word_length": round(avg_word_length, 2),
        "reading_time_minutes": round(reading_time_minutes, 1),
    }

    if include_freq:
        word_freq = Counter(words).most_common(10)
        result["top_words"] = [{"word": w, "count": c} for w, c in word_freq]

    return BuiltinToolResult(success=True, result=result)


def _apply_jsonpath(data: Any, path: str) -> Any:
    """Apply a simple JSONPath expression to data."""
    if not path or path == "$":
        return data

    if path.startswith("$"):
        path = path[1:]
    if path.startswith("."):
        path = path[1:]

    if not path:
        return data

    result = data
    parts = re.findall(r"\.?(\w+|\[\d+\]|\[\*\]|\*)", path)

    for part in parts:
        if result is None:
            return None

        if part == "*" or part == "[*]":
            if isinstance(result, list):
                result = result
            elif isinstance(result, dict):
                result = list(result.values())
            else:
                return None

        elif part.startswith("[") and part.endswith("]"):
            try:
                idx = int(part[1:-1])
                if isinstance(result, list) and -len(result) <= idx < len(result):
                    result = result[idx]
                else:
                    return None
            except ValueError:
                return None

        else:
            if isinstance(result, dict) and part in result:
                result = result[part]
            elif isinstance(result, list):
                result = [item.get(part) if isinstance(item, dict) else None for item in result]
            else:
                return None

    return result
