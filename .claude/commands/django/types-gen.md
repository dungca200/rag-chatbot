---
description: Generate Python types and models from PostgreSQL database schema
model: opus
---

Generate Python type definitions from the PostgreSQL database schema.

## Command

Run the following command to inspect and generate models:

```bash
python manage.py inspectdb > models_generated.py
```

Or for specific tables:

```bash
python manage.py inspectdb users posts comments > models_generated.py
```

## Setup for Type Generation

### 1. **Using Django's inspectdb**

```bash
# Generate models from existing database
python manage.py inspectdb > myapp/models_generated.py

# Review and move to models.py
# Clean up field types as needed
```

### 2. **Usage in Code**

```python
# models.py
from django.db import models

class User(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users'

# Type hints with dataclasses or Pydantic
from pydantic import BaseModel

class UserSchema(BaseModel):
    id: int
    email: str
    name: str

    class Config:
        from_attributes = True
```

### 3. **Create Pydantic Schemas for API**

```python
# schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: str
    name: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True
```

### 4. **DRF Serializers as Types**

```python
# serializers.py
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']

class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'name']
```

### 5. **When to Regenerate**

Run `python manage.py inspectdb` after:
- Creating new tables directly in PostgreSQL
- Adding/removing columns
- Changing column types
- Adding new database objects

### 6. **Best Practices**

-  Keep models.py as source of truth
-  Use DRF serializers for API validation
-  Add type hints to function signatures
-  Use Pydantic for complex validation
-  Run migrations after model changes
[!] Don't manually edit database without migrations
[!] Don't skip type annotations

### 7. **Migration Workflow**

```bash
# After model changes
python manage.py makemigrations
python manage.py migrate

# Check migration SQL
python manage.py sqlmigrate myapp 0001
```

## Troubleshooting

**Issue**: inspectdb not finding tables
```bash
# Check database connection
python manage.py dbshell
\dt  # List tables in PostgreSQL
```

**Issue**: Wrong field types generated
```python
# Manually adjust in models.py
# inspectdb is a starting point, not final
```

**Issue**: Missing relationships
```python
# Add ForeignKey relationships manually
user = models.ForeignKey(User, on_delete=models.CASCADE)
```

Generate and use proper type definitions to catch database-related bugs at development time instead of runtime.
