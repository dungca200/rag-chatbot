---
description: Test API endpoints with automated test generation
model: opus
---

Generate comprehensive API tests for the specified endpoint.

## Target

$ARGUMENTS

## Test Strategy for Solo Developers

Create practical, maintainable tests using modern tools:

### 1. **Testing Approach**
- Unit tests for validation logic
- Integration tests for full API flow
- Edge case coverage
- Error scenario testing

### 2. **Tools** (choose based on project)
- **pytest-django** - Fast, modern (recommended)
- **Django TestCase** - Built-in, widely used
- **DRF APITestCase** - REST framework testing
- **responses** - API mocking

### 3. **Test Coverage**

**Happy Paths**
- Valid inputs return expected results
- Proper status codes
- Correct response structure

**Error Paths**
- Invalid input validation
- Authentication failures
- Rate limiting
- Server errors
- Missing required fields

**Edge Cases**
- Empty requests
- Malformed JSON
- Large payloads
- Special characters
- SQL injection attempts
- XSS attempts

### 4. **Test Structure**

```python
class TestAPIEndpoint(APITestCase):
    """Test cases for API endpoint"""

    def setUp(self):
        """Set up test fixtures"""
        pass

    # Success Cases
    def test_valid_request_returns_success(self):
        pass

    def test_returns_correct_status_code(self):
        pass

    # Validation
    def test_rejects_invalid_input(self):
        pass

    def test_validates_required_fields(self):
        pass

    # Error Handling
    def test_handles_server_errors(self):
        pass

    def test_returns_proper_error_format(self):
        pass
```

### 5. **What to Generate**

1. **Test File** - Complete test suite with all scenarios
2. **Fixtures** - Realistic test data with Factory Boy
3. **Helper Functions** - Reusable test utilities
4. **Setup/Teardown** - Database/state management
5. **Quick Test Script** - pytest command to run tests

## Key Testing Principles

[/] Test behavior, not implementation
[/] Clear, descriptive test names
[/] Arrange-Act-Assert pattern
[/] Independent tests (no shared state)
[/] Fast execution (<5s for unit tests)
[/] Realistic mock data
[/] Test error messages
[!] Don't test framework internals
[!] Don't mock what you don't own
[!] Avoid brittle tests

## Additional Scenarios to Cover

1. **Authentication/Authorization**
   - Valid tokens
   - Expired tokens
   - Missing tokens
   - Invalid permissions

2. **Data Validation**
   - Type mismatches
   - Out of range values
   - SQL injection
   - XSS payloads

3. **Rate Limiting**
   - Within limits
   - Exceeding limits
   - Reset behavior

4. **Performance**
   - Response times
   - Large dataset handling
   - Concurrent requests

## Example Test File

```python
import pytest
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from factory import Factory

class UserFactory(Factory):
    class Meta:
        model = User

    username = "testuser"
    email = "test@example.com"


class TestUserAPI(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('user-detail', args=[self.user.id])

    def test_get_user_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)

    def test_unauthenticated_request_fails(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_id_returns_404(self):
        url = reverse('user-detail', args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

Generate production-ready tests I can run immediately with `pytest`.
