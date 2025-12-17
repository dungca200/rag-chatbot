#!/usr/bin/env python3
"""
Utility Tools for AI Agents.

Provides general-purpose utilities: datetime, formatting, validation, ID generation.
Returns precise utility results for common operations.

Example:
    User: "What's the current time in Tokyo?"
    Agent uses: get_datetime(timezone="Asia/Tokyo")
    Returns: Actual current time in Tokyo
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Schemas
# ============================================================================

class DateTimeInput(BaseModel):
    """Input for datetime operations."""
    timezone: str = Field(default="UTC", description="Timezone name (e.g., 'America/New_York')")
    format: Optional[str] = Field(default=None, description="Output format (e.g., '%Y-%m-%d %H:%M:%S')")


class FormatDataInput(BaseModel):
    """Input for data formatting."""
    data: dict = Field(description="Data to format")
    template: str = Field(description="Template string with {key} placeholders")


class ValidateDataInput(BaseModel):
    """Input for data validation."""
    data: dict = Field(description="Data to validate")
    schema: dict = Field(description="Validation schema")


# ============================================================================
# DateTime Tools
# ============================================================================

@tool(args_schema=DateTimeInput)
def get_datetime(timezone: str = "UTC", format: str = None) -> dict:
    """Get the current date and time.

    Use this tool when users ask about current time, date, or day.
    Examples:
    - "What time is it?"
    - "What's today's date?"
    - "Current time in Tokyo?"

    Args:
        timezone: Timezone name (default: UTC)
        format: Optional strftime format string

    Returns:
        Current datetime information
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)

        result = {
            "success": True,
            "timezone": timezone,
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "timestamp": now.timestamp()
        }

        if format:
            result["formatted"] = now.strftime(format)

        return result

    except Exception as e:
        return {"success": False, "error": f"DateTime error: {str(e)}"}


@tool
def parse_datetime(
    date_string: str,
    format: str = None,
    timezone: str = "UTC"
) -> dict:
    """Parse a datetime string into components.

    Use this tool to extract date/time parts from strings.

    Args:
        date_string: String to parse
        format: Expected format (auto-detect if not provided)
        timezone: Timezone to apply

    Returns:
        Parsed datetime components
    """
    from dateutil import parser

    try:
        if format:
            dt = datetime.strptime(date_string, format)
        else:
            dt = parser.parse(date_string)

        return {
            "success": True,
            "input": date_string,
            "year": dt.year,
            "month": dt.month,
            "day": dt.day,
            "hour": dt.hour,
            "minute": dt.minute,
            "second": dt.second,
            "weekday": dt.strftime("%A"),
            "iso": dt.isoformat()
        }

    except Exception as e:
        return {"success": False, "error": f"Parse error: {str(e)}"}


@tool
def date_diff(
    date1: str,
    date2: str,
    unit: str = "days"
) -> dict:
    """Calculate the difference between two dates.

    Use this tool to find time elapsed or remaining.
    Examples:
    - "Days until December 31?"
    - "Time since project start?"

    Args:
        date1: First date string
        date2: Second date string
        unit: Unit for result: days, hours, minutes, seconds, weeks

    Returns:
        Time difference in specified unit
    """
    from dateutil import parser

    try:
        dt1 = parser.parse(date1)
        dt2 = parser.parse(date2)

        diff = dt2 - dt1
        total_seconds = diff.total_seconds()

        unit = unit.lower()
        if unit == "seconds":
            result = total_seconds
        elif unit == "minutes":
            result = total_seconds / 60
        elif unit == "hours":
            result = total_seconds / 3600
        elif unit == "days":
            result = diff.days + (diff.seconds / 86400)
        elif unit == "weeks":
            result = (diff.days + diff.seconds / 86400) / 7
        else:
            return {"success": False, "error": f"Unknown unit: {unit}"}

        return {
            "success": True,
            "date1": date1,
            "date2": date2,
            "difference": round(result, 2),
            "unit": unit,
            "total_days": diff.days,
            "is_future": result > 0
        }

    except Exception as e:
        return {"success": False, "error": f"Date diff error: {str(e)}"}


@tool
def date_add(
    date_string: str,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    weeks: int = 0
) -> dict:
    """Add time to a date.

    Use this tool to calculate future or past dates.
    Examples:
    - "What date is 30 days from now?"
    - "When is 2 weeks before the deadline?"

    Args:
        date_string: Starting date
        days: Days to add (negative to subtract)
        hours: Hours to add
        minutes: Minutes to add
        weeks: Weeks to add

    Returns:
        New date after addition
    """
    from dateutil import parser

    try:
        dt = parser.parse(date_string)
        delta = timedelta(days=days, hours=hours, minutes=minutes, weeks=weeks)
        new_dt = dt + delta

        return {
            "success": True,
            "original": date_string,
            "added": {
                "days": days,
                "hours": hours,
                "minutes": minutes,
                "weeks": weeks
            },
            "result": new_dt.isoformat(),
            "result_date": new_dt.strftime("%Y-%m-%d"),
            "result_day": new_dt.strftime("%A")
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Formatting Tools
# ============================================================================

@tool(args_schema=FormatDataInput)
def format_data(data: dict, template: str) -> dict:
    """Format data using a template string.

    Use this tool to create formatted output from data.
    Template uses {key} placeholders.

    Example:
        data: {"name": "John", "age": 30}
        template: "Hello {name}, you are {age} years old"
        result: "Hello John, you are 30 years old"

    Args:
        data: Dictionary of values
        template: Template with {key} placeholders

    Returns:
        Formatted string
    """
    try:
        result = template.format(**data)
        return {
            "success": True,
            "template": template,
            "data": data,
            "result": result
        }

    except KeyError as e:
        return {"success": False, "error": f"Missing key in data: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def format_number(
    number: float,
    decimal_places: int = 2,
    thousands_separator: bool = True,
    currency: str = None
) -> dict:
    """Format a number for display.

    Use this tool to format numbers nicely for output.

    Args:
        number: Number to format
        decimal_places: Decimal places to show
        thousands_separator: Add commas for thousands
        currency: Optional currency symbol (e.g., "$", "EUR")

    Returns:
        Formatted number string
    """
    try:
        # Round to decimal places
        rounded = round(number, decimal_places)

        # Format with thousands separator
        if thousands_separator:
            if decimal_places > 0:
                formatted = f"{rounded:,.{decimal_places}f}"
            else:
                formatted = f"{int(rounded):,}"
        else:
            formatted = f"{rounded:.{decimal_places}f}"

        # Add currency
        if currency:
            formatted = f"{currency}{formatted}"

        return {
            "success": True,
            "original": number,
            "formatted": formatted,
            "decimal_places": decimal_places
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def format_list(
    items: list,
    separator: str = ", ",
    last_separator: str = None,
    prefix: str = "",
    suffix: str = ""
) -> dict:
    """Format a list of items into a string.

    Use this tool to create human-readable lists.

    Args:
        items: List of items
        separator: Separator between items
        last_separator: Separator before last item (e.g., " and ")
        prefix: Prefix for each item
        suffix: Suffix for each item

    Returns:
        Formatted list string
    """
    try:
        if not items:
            return {"success": True, "result": ""}

        formatted_items = [f"{prefix}{item}{suffix}" for item in items]

        if last_separator and len(formatted_items) > 1:
            result = separator.join(formatted_items[:-1])
            result = f"{result}{last_separator}{formatted_items[-1]}"
        else:
            result = separator.join(formatted_items)

        return {
            "success": True,
            "items": items,
            "result": result,
            "count": len(items)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Validation Tools
# ============================================================================

@tool(args_schema=ValidateDataInput)
def validate_data(data: dict, schema: dict) -> dict:
    """Validate data against a schema.

    Schema format:
    {
        "field_name": {
            "type": "string|int|float|bool|list|dict",
            "required": true/false,
            "min": number (for strings: min length),
            "max": number (for strings: max length),
            "pattern": "regex pattern for strings",
            "choices": ["allowed", "values"]
        }
    }

    Args:
        data: Data dictionary to validate
        schema: Validation schema

    Returns:
        Validation result with errors if any
    """
    import re

    errors = []
    validated_data = {}

    for field, rules in schema.items():
        value = data.get(field)

        # Check required
        if rules.get("required", False) and value is None:
            errors.append(f"{field}: Required field is missing")
            continue

        if value is None:
            continue

        # Check type
        expected_type = rules.get("type")
        if expected_type:
            type_map = {
                "string": str, "str": str,
                "int": int, "integer": int,
                "float": float, "number": (int, float),
                "bool": bool, "boolean": bool,
                "list": list, "array": list,
                "dict": dict, "object": dict
            }
            expected = type_map.get(expected_type)
            if expected and not isinstance(value, expected):
                errors.append(f"{field}: Expected {expected_type}, got {type(value).__name__}")
                continue

        # Check min/max for numbers
        if isinstance(value, (int, float)):
            if "min" in rules and value < rules["min"]:
                errors.append(f"{field}: Value {value} is less than minimum {rules['min']}")
            if "max" in rules and value > rules["max"]:
                errors.append(f"{field}: Value {value} is greater than maximum {rules['max']}")

        # Check min/max for strings (length)
        if isinstance(value, str):
            if "min" in rules and len(value) < rules["min"]:
                errors.append(f"{field}: Length {len(value)} is less than minimum {rules['min']}")
            if "max" in rules and len(value) > rules["max"]:
                errors.append(f"{field}: Length {len(value)} is greater than maximum {rules['max']}")

        # Check pattern
        if "pattern" in rules and isinstance(value, str):
            if not re.match(rules["pattern"], value):
                errors.append(f"{field}: Value does not match pattern {rules['pattern']}")

        # Check choices
        if "choices" in rules and value not in rules["choices"]:
            errors.append(f"{field}: Value must be one of {rules['choices']}")

        validated_data[field] = value

    return {
        "success": len(errors) == 0,
        "valid": len(errors) == 0,
        "errors": errors,
        "validated_data": validated_data if not errors else None
    }


@tool
def validate_email(email: str) -> dict:
    """Validate an email address format.

    Args:
        email: Email address to validate

    Returns:
        Whether email is valid
    """
    import re

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = bool(re.match(pattern, email))

    return {
        "success": True,
        "email": email,
        "valid": is_valid,
        "message": "Valid email format" if is_valid else "Invalid email format"
    }


@tool
def validate_url(url: str) -> dict:
    """Validate a URL format.

    Args:
        url: URL to validate

    Returns:
        Whether URL is valid
    """
    from urllib.parse import urlparse

    try:
        result = urlparse(url)
        is_valid = all([result.scheme, result.netloc])

        return {
            "success": True,
            "url": url,
            "valid": is_valid,
            "scheme": result.scheme,
            "netloc": result.netloc,
            "path": result.path
        }

    except Exception as e:
        return {"success": True, "url": url, "valid": False, "error": str(e)}


# ============================================================================
# ID Generation Tools
# ============================================================================

@tool
def generate_id(
    prefix: str = "",
    length: int = 8,
    include_timestamp: bool = False
) -> dict:
    """Generate a unique identifier.

    Use this tool when you need to create unique IDs.

    Args:
        prefix: Optional prefix for the ID
        length: Length of random part (default: 8)
        include_timestamp: Include timestamp in ID

    Returns:
        Generated unique ID
    """
    import secrets
    import time

    try:
        # Generate random part
        random_part = secrets.token_hex(length // 2)[:length]

        # Build ID
        parts = []
        if prefix:
            parts.append(prefix)
        if include_timestamp:
            parts.append(str(int(time.time())))
        parts.append(random_part)

        generated_id = "-".join(parts) if len(parts) > 1 else random_part

        return {
            "success": True,
            "id": generated_id,
            "prefix": prefix,
            "length": length
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def generate_uuid(version: int = 4) -> dict:
    """Generate a UUID.

    Args:
        version: UUID version (1 or 4)

    Returns:
        Generated UUID
    """
    try:
        if version == 1:
            result = str(uuid.uuid1())
        elif version == 4:
            result = str(uuid.uuid4())
        else:
            return {"success": False, "error": "UUID version must be 1 or 4"}

        return {
            "success": True,
            "uuid": result,
            "version": version
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Text Utility Tools
# ============================================================================

@tool
def slugify(text: str, separator: str = "-") -> dict:
    """Convert text to URL-friendly slug.

    Args:
        text: Text to convert
        separator: Separator character (default: -)

    Returns:
        URL-friendly slug
    """
    import re
    import unicodedata

    try:
        # Normalize unicode
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")

        # Convert to lowercase and replace spaces
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", separator, text)
        text = text.strip(separator)

        return {
            "success": True,
            "original": text,
            "slug": text
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def truncate(text: str, max_length: int, suffix: str = "...") -> dict:
    """Truncate text to a maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return {
            "success": True,
            "original_length": len(text),
            "result": text,
            "truncated": False
        }

    truncated = text[:max_length - len(suffix)] + suffix
    return {
        "success": True,
        "original_length": len(text),
        "result": truncated,
        "truncated": True
    }


# ============================================================================
# Export all tools
# ============================================================================

UTILITY_TOOLS = [
    get_datetime,
    parse_datetime,
    date_diff,
    date_add,
    format_data,
    format_number,
    format_list,
    validate_data,
    validate_email,
    validate_url,
    generate_id,
    generate_uuid,
    slugify,
    truncate
]
