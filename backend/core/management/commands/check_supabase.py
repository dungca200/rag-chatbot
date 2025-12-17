"""Management command to verify Supabase connection."""
from django.core.management.base import BaseCommand

from core.clients.supabase_client import health_check, get_supabase_client


class Command(BaseCommand):
    help = "Verify Supabase connection is working"

    def handle(self, *args, **options):
        self.stdout.write("Checking Supabase connection...\n")

        if health_check():
            self.stdout.write(self.style.SUCCESS("Supabase connection successful!"))

            # Test RPC function
            self.stdout.write("\nTesting match_documents RPC...")
            try:
                client = get_supabase_client()
                # Test with empty embedding (768 dimensions for Gemini)
                test_embedding = [0.0] * 768
                result = client.rpc(
                    'match_documents',
                    {
                        'query_embedding': test_embedding,
                        'filter_user_id': '00000000-0000-0000-0000-000000000000',
                        'match_threshold': 0.0,
                        'match_count': 1
                    }
                ).execute()
                self.stdout.write(self.style.SUCCESS("  match_documents RPC works!"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  match_documents RPC failed: {str(e)}"))
        else:
            self.stdout.write(self.style.ERROR("Supabase connection failed!"))
            self.stdout.write("\nMake sure you have:")
            self.stdout.write("  1. SUPABASE_URL set in .env")
            self.stdout.write("  2. SUPABASE_KEY set in .env")
            self.stdout.write("  3. Run the SQL schema in Supabase SQL Editor")
