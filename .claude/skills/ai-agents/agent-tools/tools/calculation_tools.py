#!/usr/bin/env python3
"""
Calculation Tools for AI Agents.

Provides tools for mathematical operations, statistics, and conversions.
Returns precise calculated results instead of AI approximations.

Example:
    User: "What's 15% of 2,450?"
    Agent uses: calculate("2450 * 0.15")
    Returns: 367.5 (exact result)
"""

import math
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Schemas
# ============================================================================

class CalculateInput(BaseModel):
    """Input for calculation."""
    expression: str = Field(description="Mathematical expression to evaluate")


class StatisticsInput(BaseModel):
    """Input for statistics calculation."""
    numbers: list[float] = Field(description="List of numbers to analyze")
    operation: str = Field(description="Operation: mean, median, mode, std, variance, min, max, sum, range")


class ConvertInput(BaseModel):
    """Input for unit conversion."""
    value: float = Field(description="Value to convert")
    from_unit: str = Field(description="Source unit")
    to_unit: str = Field(description="Target unit")


class FinancialInput(BaseModel):
    """Input for financial calculation."""
    principal: float = Field(description="Principal amount")
    rate: float = Field(description="Interest rate (as percentage, e.g., 5 for 5%)")
    time: float = Field(description="Time period")
    calc_type: str = Field(description="Type: simple_interest, compound_interest, roi, discount")


# ============================================================================
# Basic Calculation Tools
# ============================================================================

@tool(args_schema=CalculateInput)
def calculate(expression: str) -> dict:
    """Evaluate a mathematical expression safely.

    Use this tool for any calculations, math problems, or numerical operations.
    Examples:
    - "2 + 2" → 4
    - "sqrt(16)" → 4.0
    - "15 * 0.2" → 3.0
    - "sin(pi/2)" → 1.0

    Supported functions: sqrt, sin, cos, tan, log, log10, exp, abs, round, pow, pi, e

    Args:
        expression: Mathematical expression to evaluate

    Returns:
        Calculation result
    """
    # Safe evaluation with limited builtins
    allowed_names = {
        # Math functions
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        "floor": math.floor,
        "ceil": math.ceil,
        "factorial": math.factorial,
        # Constants
        "pi": math.pi,
        "e": math.e,
        "inf": math.inf,
    }

    try:
        # Evaluate safely
        result = eval(expression, {"__builtins__": {}}, allowed_names)

        return {
            "success": True,
            "expression": expression,
            "result": result
        }

    except ZeroDivisionError:
        return {"success": False, "error": "Division by zero"}
    except ValueError as e:
        return {"success": False, "error": f"Math error: {str(e)}"}
    except SyntaxError:
        return {"success": False, "error": "Invalid expression syntax"}
    except Exception as e:
        return {"success": False, "error": f"Calculation failed: {str(e)}"}


# ============================================================================
# Statistics Tools
# ============================================================================

@tool(args_schema=StatisticsInput)
def statistics(numbers: list[float], operation: str) -> dict:
    """Calculate statistics on a list of numbers.

    Use this tool for statistical analysis.
    Examples:
    - Calculate average sales: statistics([100, 150, 200], "mean")
    - Find the middle value: statistics([1, 2, 3, 4, 5], "median")

    Args:
        numbers: List of numbers to analyze
        operation: mean, median, mode, std, variance, min, max, sum, range

    Returns:
        Statistical result
    """
    import statistics as stats

    if not numbers:
        return {"success": False, "error": "Empty list provided"}

    operation = operation.lower()

    try:
        if operation == "mean":
            result = stats.mean(numbers)
        elif operation == "median":
            result = stats.median(numbers)
        elif operation == "mode":
            try:
                result = stats.mode(numbers)
            except stats.StatisticsError:
                return {"success": False, "error": "No unique mode found"}
        elif operation == "std" or operation == "stdev":
            result = stats.stdev(numbers) if len(numbers) > 1 else 0
        elif operation == "variance":
            result = stats.variance(numbers) if len(numbers) > 1 else 0
        elif operation == "min":
            result = min(numbers)
        elif operation == "max":
            result = max(numbers)
        elif operation == "sum":
            result = sum(numbers)
        elif operation == "range":
            result = max(numbers) - min(numbers)
        elif operation == "count":
            result = len(numbers)
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

        return {
            "success": True,
            "operation": operation,
            "result": result,
            "count": len(numbers)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def descriptive_stats(numbers: list[float]) -> dict:
    """Get comprehensive descriptive statistics.

    Use this tool when you need multiple statistics at once.

    Args:
        numbers: List of numbers to analyze

    Returns:
        Complete statistical summary
    """
    import statistics as stats

    if not numbers:
        return {"success": False, "error": "Empty list provided"}

    try:
        sorted_nums = sorted(numbers)
        n = len(numbers)

        result = {
            "success": True,
            "count": n,
            "sum": sum(numbers),
            "mean": stats.mean(numbers),
            "median": stats.median(numbers),
            "min": min(numbers),
            "max": max(numbers),
            "range": max(numbers) - min(numbers),
        }

        if n > 1:
            result["std"] = stats.stdev(numbers)
            result["variance"] = stats.variance(numbers)

        # Quartiles
        if n >= 4:
            result["q1"] = sorted_nums[n // 4]
            result["q3"] = sorted_nums[3 * n // 4]

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Unit Conversion Tools
# ============================================================================

# Conversion factors to base units
CONVERSIONS = {
    # Length (base: meters)
    "m": 1, "meter": 1, "meters": 1,
    "km": 1000, "kilometer": 1000, "kilometers": 1000,
    "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
    "mm": 0.001, "millimeter": 0.001, "millimeters": 0.001,
    "mi": 1609.344, "mile": 1609.344, "miles": 1609.344,
    "ft": 0.3048, "foot": 0.3048, "feet": 0.3048,
    "in": 0.0254, "inch": 0.0254, "inches": 0.0254,
    "yd": 0.9144, "yard": 0.9144, "yards": 0.9144,

    # Weight (base: kilograms)
    "kg": 1, "kilogram": 1, "kilograms": 1,
    "g": 0.001, "gram": 0.001, "grams": 0.001,
    "mg": 0.000001, "milligram": 0.000001,
    "lb": 0.453592, "pound": 0.453592, "pounds": 0.453592,
    "oz": 0.0283495, "ounce": 0.0283495, "ounces": 0.0283495,

    # Temperature handled separately

    # Volume (base: liters)
    "l": 1, "liter": 1, "liters": 1,
    "ml": 0.001, "milliliter": 0.001, "milliliters": 0.001,
    "gal": 3.78541, "gallon": 3.78541, "gallons": 3.78541,
    "qt": 0.946353, "quart": 0.946353, "quarts": 0.946353,
    "pt": 0.473176, "pint": 0.473176, "pints": 0.473176,
    "cup": 0.236588, "cups": 0.236588,

    # Time (base: seconds)
    "s": 1, "sec": 1, "second": 1, "seconds": 1,
    "min": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
    "wk": 604800, "week": 604800, "weeks": 604800,
}


@tool(args_schema=ConvertInput)
def convert_units(value: float, from_unit: str, to_unit: str) -> dict:
    """Convert between different units.

    Use this tool for unit conversions.
    Supports: length, weight, volume, time, temperature

    Examples:
    - convert_units(5, "km", "miles")
    - convert_units(100, "celsius", "fahrenheit")
    - convert_units(1, "hour", "minutes")

    Args:
        value: Value to convert
        from_unit: Source unit
        to_unit: Target unit

    Returns:
        Converted value
    """
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()

    # Handle temperature separately
    temp_units = ["c", "celsius", "f", "fahrenheit", "k", "kelvin"]
    if from_unit in temp_units or to_unit in temp_units:
        return _convert_temperature(value, from_unit, to_unit)

    # Check if units exist
    if from_unit not in CONVERSIONS:
        return {"success": False, "error": f"Unknown unit: {from_unit}"}
    if to_unit not in CONVERSIONS:
        return {"success": False, "error": f"Unknown unit: {to_unit}"}

    try:
        # Convert to base unit, then to target
        base_value = value * CONVERSIONS[from_unit]
        result = base_value / CONVERSIONS[to_unit]

        return {
            "success": True,
            "original": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "result": result
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def _convert_temperature(value: float, from_unit: str, to_unit: str) -> dict:
    """Convert temperature between Celsius, Fahrenheit, and Kelvin."""
    from_unit = from_unit[0].lower()  # Normalize to first letter
    to_unit = to_unit[0].lower()

    # Convert to Celsius first
    if from_unit == "c":
        celsius = value
    elif from_unit == "f":
        celsius = (value - 32) * 5 / 9
    elif from_unit == "k":
        celsius = value - 273.15
    else:
        return {"success": False, "error": f"Unknown temperature unit: {from_unit}"}

    # Convert from Celsius to target
    if to_unit == "c":
        result = celsius
    elif to_unit == "f":
        result = celsius * 9 / 5 + 32
    elif to_unit == "k":
        result = celsius + 273.15
    else:
        return {"success": False, "error": f"Unknown temperature unit: {to_unit}"}

    return {
        "success": True,
        "original": value,
        "from_unit": from_unit,
        "to_unit": to_unit,
        "result": round(result, 4)
    }


# ============================================================================
# Financial Calculation Tools
# ============================================================================

@tool(args_schema=FinancialInput)
def financial_calc(
    principal: float,
    rate: float,
    time: float,
    calc_type: str
) -> dict:
    """Perform financial calculations.

    Use this tool for interest, ROI, and discount calculations.

    Args:
        principal: Principal amount
        rate: Interest rate as percentage (e.g., 5 for 5%)
        time: Time period (years for interest, varies for others)
        calc_type: simple_interest, compound_interest, roi, discount, present_value

    Returns:
        Financial calculation result
    """
    rate_decimal = rate / 100
    calc_type = calc_type.lower().replace(" ", "_")

    try:
        if calc_type == "simple_interest":
            interest = principal * rate_decimal * time
            total = principal + interest
            return {
                "success": True,
                "calc_type": "Simple Interest",
                "principal": principal,
                "rate": f"{rate}%",
                "time": time,
                "interest": round(interest, 2),
                "total": round(total, 2)
            }

        elif calc_type == "compound_interest":
            # Assuming annual compounding
            total = principal * (1 + rate_decimal) ** time
            interest = total - principal
            return {
                "success": True,
                "calc_type": "Compound Interest (Annual)",
                "principal": principal,
                "rate": f"{rate}%",
                "time": time,
                "interest": round(interest, 2),
                "total": round(total, 2)
            }

        elif calc_type == "roi":
            # time = final value, rate = not used
            # Treat principal as initial, time as final value
            roi = ((time - principal) / principal) * 100
            return {
                "success": True,
                "calc_type": "ROI",
                "initial_value": principal,
                "final_value": time,
                "roi_percent": round(roi, 2)
            }

        elif calc_type == "discount":
            discount_amount = principal * rate_decimal
            final_price = principal - discount_amount
            return {
                "success": True,
                "calc_type": "Discount",
                "original_price": principal,
                "discount_percent": f"{rate}%",
                "discount_amount": round(discount_amount, 2),
                "final_price": round(final_price, 2)
            }

        elif calc_type == "present_value":
            pv = principal / (1 + rate_decimal) ** time
            return {
                "success": True,
                "calc_type": "Present Value",
                "future_value": principal,
                "rate": f"{rate}%",
                "time": time,
                "present_value": round(pv, 2)
            }

        else:
            return {
                "success": False,
                "error": f"Unknown calc_type: {calc_type}. Use: simple_interest, compound_interest, roi, discount, present_value"
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def percentage(value: float, percent: float, operation: str = "of") -> dict:
    """Calculate percentages.

    Use this tool for percentage calculations.
    Examples:
    - "What is 15% of 200?" → percentage(200, 15, "of")
    - "What percent is 30 of 150?" → percentage(30, 150, "is_what_percent")
    - "200 plus 10%?" → percentage(200, 10, "increase")

    Args:
        value: The base value
        percent: The percentage value
        operation: "of" (percent of value), "is_what_percent" (value is what % of percent), "increase", "decrease"

    Returns:
        Percentage calculation result
    """
    operation = operation.lower()

    try:
        if operation == "of":
            result = value * (percent / 100)
            return {
                "success": True,
                "operation": f"{percent}% of {value}",
                "result": round(result, 4)
            }

        elif operation == "is_what_percent":
            # value is what percent of 'percent'
            result = (value / percent) * 100
            return {
                "success": True,
                "operation": f"{value} is what % of {percent}",
                "result": round(result, 4)
            }

        elif operation == "increase":
            increase = value * (percent / 100)
            result = value + increase
            return {
                "success": True,
                "operation": f"{value} + {percent}%",
                "increase": round(increase, 4),
                "result": round(result, 4)
            }

        elif operation == "decrease":
            decrease = value * (percent / 100)
            result = value - decrease
            return {
                "success": True,
                "operation": f"{value} - {percent}%",
                "decrease": round(decrease, 4),
                "result": round(result, 4)
            }

        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Export all tools
# ============================================================================

CALCULATION_TOOLS = [
    calculate,
    statistics,
    descriptive_stats,
    convert_units,
    financial_calc,
    percentage
]
