---
description: Add authentication, authorization, and security to API endpoints
model: opus
---

Add comprehensive security, authentication, and authorization to the specified API endpoint.

## Target API Endpoint

$ARGUMENTS

## Security Layers to Implement

###1. **Authentication** (Who are you?)
- Verify user identity
- Token validation (JWT, session, API keys)
- Handle expired/invalid tokens

### 2. **Authorization** (What can you do?)
- Role-based access control (RBAC)
- Resource-level permissions
- Check user ownership

### 3. **Input Validation**
- Sanitize all inputs
- SQL injection prevention
- XSS prevention
- Type validation with DRF Serializers

### 4. **Rate Limiting**
- Prevent abuse
- Per-user/IP limits
- Sliding window algorithm

### 5. **CORS** (if needed)
- Whitelist allowed origins
- Proper headers
- Credentials handling

## Implementation Approach

### For Django REST Framework:
```python
# Use DRF Authentication + Permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

class MyView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
```

### For Django Session Auth:
```python
# Use Django's built-in session auth
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated

class MyView(APIView):
    permission_classes = [IsAuthenticated]
```

### For JWT Auth:
```python
# Use djangorestframework-simplejwt
from rest_framework_simplejwt.authentication import JWTAuthentication

class MyView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
```

## Security Checklist

**Authentication**
[/] Verify authentication tokens
[/] Handle missing/invalid tokens (401)
[/] Check token expiration
[/] Secure token storage recommendations

**Authorization**
[/] Check user roles/permissions (403)
[/] Verify resource ownership
[/] Implement least privilege principle
[/] Log authorization failures

**Input Validation**
[/] Validate all inputs with DRF Serializers
[/] Sanitize SQL inputs (Django ORM handles this)
[/] Escape special characters
[/] Limit payload sizes

**Rate Limiting**
[/] Per-user limits
[/] Per-IP limits
[/] Clear error messages (429)
[/] Retry-After headers

**CORS**
[/] Whitelist specific origins
[/] Handle preflight requests
[/] Secure credentials
[/] Appropriate headers

**Error Handling**
[/] Don't expose stack traces
[/] Generic error messages
[/] Log detailed errors server-side
[/] Consistent error format

**Logging & Monitoring**
[/] Log authentication attempts
[/] Log authorization failures
[/] Track suspicious activity
[/] Monitor rate limit hits

## What to Generate

1. **Protected View** - Secured version of the API endpoint
2. **Permissions** - Custom permission classes
3. **Type Definitions** - User, permissions, roles
4. **Error Responses** - Standardized auth errors
5. **Usage Examples** - Client-side integration

## Common Patterns for Solo Developers

**Pattern 1: Simple Token Auth**
```python
# For internal tools, admin panels
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

class AdminView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
```

**Pattern 2: User-based Auth**
```python
# For user-facing apps
from rest_framework.permissions import IsAuthenticated

class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  # Authenticated user
```

**Pattern 3: Role-based Auth**
```python
# For apps with different user types
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff

class AdminOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
```

Generate production-ready, secure code that follows the principle of least privilege.
