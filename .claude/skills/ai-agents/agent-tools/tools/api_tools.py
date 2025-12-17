#!/usr/bin/env python3
"""
API Tools for AI Agents.

Provides tools for making HTTP requests to external APIs.
Returns real data from external services.

Example:
    User: "What's the weather in Tokyo?"
    Agent uses: http_get("https://api.weather.com/tokyo")
    Returns: Actual weather data from API
"""

import os
from typing import Optional, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Schemas
# ============================================================================

class HttpGetInput(BaseModel):
    """Input for HTTP GET request."""
    url: str = Field(description="Full URL to request")
    headers: Optional[dict] = Field(default=None, description="Request headers")
    params: Optional[dict] = Field(default=None, description="Query parameters")
    timeout: int = Field(default=30, ge=1, le=120, description="Request timeout in seconds")


class HttpPostInput(BaseModel):
    """Input for HTTP POST request."""
    url: str = Field(description="Full URL to request")
    data: dict = Field(description="Request body as JSON")
    headers: Optional[dict] = Field(default=None, description="Request headers")
    timeout: int = Field(default=30, ge=1, le=120, description="Request timeout in seconds")


class WebhookInput(BaseModel):
    """Input for webhook notification."""
    url: str = Field(description="Webhook URL")
    payload: dict = Field(description="Payload to send")
    secret: Optional[str] = Field(default=None, description="Webhook secret for signing")


# ============================================================================
# HTTP Tools
# ============================================================================

@tool(args_schema=HttpGetInput)
def http_get(
    url: str,
    headers: dict = None,
    params: dict = None,
    timeout: int = 30
) -> dict:
    """Make an HTTP GET request to fetch data from an API.

    Use this tool when you need to retrieve data from external services.
    Examples:
    - Fetching weather data
    - Getting stock prices
    - Retrieving user profiles from external APIs

    Args:
        url: Full URL to request
        headers: Optional request headers (e.g., Authorization)
        params: Optional query parameters
        timeout: Request timeout in seconds (default: 30)

    Returns:
        Response data with status code
    """
    import httpx

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers, params=params)

            # Parse response
            content_type = response.headers.get("content-type", "")

            if "application/json" in content_type:
                data = response.json()
            else:
                data = response.text[:5000]  # Limit text response

            return {
                "success": True,
                "status_code": response.status_code,
                "data": data,
                "headers": dict(response.headers)
            }

    except httpx.TimeoutException:
        return {"success": False, "error": f"Request timed out after {timeout}s"}
    except httpx.RequestError as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@tool(args_schema=HttpPostInput)
def http_post(
    url: str,
    data: dict,
    headers: dict = None,
    timeout: int = 30
) -> dict:
    """Make an HTTP POST request to send data to an API.

    Use this tool when you need to send data to external services.
    Examples:
    - Creating resources in external systems
    - Submitting forms
    - Triggering external actions

    Args:
        url: Full URL to request
        data: Request body as JSON
        headers: Optional request headers
        timeout: Request timeout in seconds

    Returns:
        Response data with status code
    """
    import httpx

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=data, headers=headers)

            content_type = response.headers.get("content-type", "")

            if "application/json" in content_type:
                response_data = response.json()
            else:
                response_data = response.text[:5000]

            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "data": response_data
            }

    except httpx.TimeoutException:
        return {"success": False, "error": f"Request timed out after {timeout}s"}
    except httpx.RequestError as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@tool
def http_put(
    url: str,
    data: dict,
    headers: dict = None,
    timeout: int = 30
) -> dict:
    """Make an HTTP PUT request to update data in an API.

    Use this tool when you need to update resources in external services.

    Args:
        url: Full URL to request
        data: Request body as JSON
        headers: Optional request headers
        timeout: Request timeout in seconds

    Returns:
        Response data with status code
    """
    import httpx

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.put(url, json=data, headers=headers)

            content_type = response.headers.get("content-type", "")
            response_data = response.json() if "application/json" in content_type else response.text[:5000]

            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "data": response_data
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def http_delete(url: str, headers: dict = None, timeout: int = 30) -> dict:
    """Make an HTTP DELETE request to remove a resource.

    Use this tool when you need to delete resources from external services.

    Args:
        url: Full URL to request
        headers: Optional request headers
        timeout: Request timeout in seconds

    Returns:
        Response with status code
    """
    import httpx

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.delete(url, headers=headers)

            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "message": "Resource deleted" if response.status_code < 400 else response.text
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Webhook Tools
# ============================================================================

@tool(args_schema=WebhookInput)
def webhook_send(url: str, payload: dict, secret: str = None) -> dict:
    """Send a webhook notification.

    Use this tool to trigger webhooks in external services.
    Examples:
    - Notifying Slack channels
    - Triggering CI/CD pipelines
    - Sending alerts to monitoring systems

    Args:
        url: Webhook URL
        payload: Payload to send
        secret: Optional webhook secret for HMAC signing

    Returns:
        Webhook response status
    """
    import httpx
    import hmac
    import hashlib
    import json

    try:
        headers = {"Content-Type": "application/json"}

        # Add HMAC signature if secret provided
        if secret:
            payload_str = json.dumps(payload, sort_keys=True)
            signature = hmac.new(
                secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload, headers=headers)

            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "message": "Webhook sent successfully" if response.status_code < 400 else response.text
            }

    except Exception as e:
        return {"success": False, "error": f"Webhook failed: {str(e)}"}


# ============================================================================
# Pagination Tools
# ============================================================================

@tool
def api_paginate(
    url: str,
    page_param: str = "page",
    limit_param: str = "limit",
    limit: int = 100,
    max_pages: int = 10,
    headers: dict = None
) -> dict:
    """Fetch paginated results from an API.

    Use this tool when you need to retrieve all pages of results.
    Automatically handles pagination until no more results.

    Args:
        url: Base API URL
        page_param: Query parameter name for page number
        limit_param: Query parameter name for page size
        limit: Number of items per page
        max_pages: Maximum pages to fetch (safety limit)
        headers: Optional request headers

    Returns:
        All results combined from all pages
    """
    import httpx

    all_results = []
    page = 1

    try:
        with httpx.Client(timeout=30) as client:
            while page <= max_pages:
                params = {page_param: page, limit_param: limit}
                response = client.get(url, params=params, headers=headers)

                if response.status_code != 200:
                    break

                data = response.json()

                # Handle different pagination formats
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("results") or data.get("data") or data.get("items") or []
                else:
                    break

                if not items:
                    break

                all_results.extend(items)

                # Check if we got fewer items than limit (last page)
                if len(items) < limit:
                    break

                page += 1

        return {
            "success": True,
            "total_items": len(all_results),
            "pages_fetched": page,
            "data": all_results
        }

    except Exception as e:
        return {"success": False, "error": str(e), "partial_data": all_results}


# ============================================================================
# API Health Check
# ============================================================================

@tool
def api_health_check(url: str, timeout: int = 10) -> dict:
    """Check if an API endpoint is healthy/reachable.

    Use this tool to verify API availability before making requests.

    Args:
        url: URL to check (usually /health or base URL)
        timeout: Timeout in seconds

    Returns:
        Health status and response time
    """
    import httpx
    import time

    try:
        start = time.time()

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            elapsed = time.time() - start

            return {
                "success": True,
                "healthy": response.status_code < 400,
                "status_code": response.status_code,
                "response_time_ms": round(elapsed * 1000, 2)
            }

    except httpx.TimeoutException:
        return {"success": False, "healthy": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "healthy": False, "error": str(e)}


# ============================================================================
# Export all tools
# ============================================================================

API_TOOLS = [
    http_get,
    http_post,
    http_put,
    http_delete,
    webhook_send,
    api_paginate,
    api_health_check
]
