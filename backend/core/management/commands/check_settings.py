"""Management command to verify Pydantic settings are loaded correctly."""
from django.core.management.base import BaseCommand

from settings import settings


class Command(BaseCommand):
    help = "Verify Pydantic settings are loaded correctly"

    def handle(self, *args, **options):
        self.stdout.write("Checking Pydantic settings...\n")

        # Check Django settings
        self.stdout.write(f"  DJANGO_DEBUG: {settings.DJANGO_DEBUG}")
        self.stdout.write(f"  DJANGO_ALLOWED_HOSTS: {settings.DJANGO_ALLOWED_HOSTS}")

        # Check API keys (show if configured, not the actual value)
        google_api = "configured" if settings.GOOGLE_API_KEY else "NOT SET"
        supabase_url = "configured" if settings.SUPABASE_URL else "NOT SET"
        supabase_key = "configured" if settings.SUPABASE_KEY else "NOT SET"
        tavily_api = "configured" if settings.TAVILY_API_KEY else "NOT SET"

        self.stdout.write(f"  GOOGLE_API_KEY: {google_api}")
        self.stdout.write(f"  SUPABASE_URL: {supabase_url}")
        self.stdout.write(f"  SUPABASE_KEY: {supabase_key}")
        self.stdout.write(f"  TAVILY_API_KEY: {tavily_api}")

        # Check database settings
        self.stdout.write(f"  DB_NAME: {settings.DB_NAME}")
        self.stdout.write(f"  DB_HOST: {settings.DB_HOST}")

        self.stdout.write(self.style.SUCCESS("\nSettings loaded successfully!"))
