---
description: Create a new Django REST Framework API endpoint with validation, error handling, and type hints
model: opus
---

Create a new Django REST Framework API endpoint following modern best practices for solo developers.

## Requirements

API Endpoint: $ARGUMENTS

## Implementation Guidelines

### 1. **Django REST Framework** (Recommended)
Use ViewSets or APIView in your Django app with proper URL routing

### 2. **Validation**
- Use DRF Serializers for runtime validation
- Validate input early (before DB/API calls)
- Return clear validation error messages

### 3. **Error Handling**
- Global error handling with try/catch
- Consistent error response format
- Appropriate HTTP status codes
- Never expose sensitive error details

### 4. **Type Hints**
- Use Python type hints for function signatures
- Shared type definitions with Pydantic or dataclasses
- Proper typing for serializers

### 5. **Security**
- Input sanitization
- CORS configuration with django-cors-headers
- Rate limiting with django-ratelimit
- Authentication/authorization checks

### 6. **Response Format**
```python
# Success
{"data": {...}, "success": True}

# Error
{"error": "message", "details": {...}, "success": False}
```

## Code Structure

Create a complete API endpoint with:

1. **View File** - `views.py` with APIView or ViewSet
2. **Serializer** - `serializers.py` for validation
3. **URL Config** - `urls.py` with proper routing
4. **Type Definitions** - Type hints or Pydantic models
5. **Example Usage** - Client-side fetch example

## Best Practices to Follow

[/] Early validation before expensive operations
[/] Proper HTTP status codes (200, 201, 400, 401, 404, 500)
[/] Consistent error response format
[/] Python type hints throughout
[/] Minimal logic in views (use services/utils)
[/] Environment variable validation with django-environ
[/] Request/response logging for debugging
[!] No sensitive data in responses
[!] No database queries without validation
[!] No inline business logic (extract to services)

Generate production-ready code that I can immediately use in my Django project.
