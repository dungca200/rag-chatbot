from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model"""
    email = models.EmailField(unique=True)

    class Meta:
        db_table = 'auth_user'
