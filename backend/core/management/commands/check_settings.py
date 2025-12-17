"""Management command to verify Pydantic settings are working."""
from django.core.management.base import BaseCommand

from settings import settings


class Command(BaseCommand):
    help = "Verify Pydantic settings are loaded correctly"

    def handle(self, *args, **options):
        self.stdout.write("Checking Pydantic settings...\n")

        # Check Django settings
        self.stdout.write(f"  DJANGO_DEBUG: {settings.django_debug}")
        self.stdout.write(f"  ALLOWED_HOSTS: {settings.allowed_hosts_list}")

        # Check API keys (show if configured, not the actual value)
        google_api = "configured" if settings.google_api_key else "NOT SET"
        supabase_url = "configured" if settings.supabase_url else "NOT SET"
        supabase_key = "configured" if settings.supabase_key else "NOT SET"
        tavily_api = "configured" if settings.tavily_api_key else "NOT SET"

        self.stdout.write(f"  GOOGLE_API_KEY: {google_api}")
        self.stdout.write(f"  SUPABASE_URL: {supabase_url}")
        self.stdout.write(f"  SUPABASE_KEY: {supabase_key}")
        self.stdout.write(f"  TAVILY_API_KEY: {tavily_api}")

        # Check database settings
        self.stdout.write(f"  DB_NAME: {settings.db_name}")
        self.stdout.write(f"  DB_HOST: {settings.db_host}")

        self.stdout.write(self.style.SUCCESS("\nSettings loaded successfully!"))
