#!/usr/bin/env python
"""
Cron job script for cleaning up session-only documents.

This script is designed to be run as a Railway Cron Service.
It cleans up session-only documents older than 24 hours.

Usage (Railway Cron):
    python scripts/cleanup_cron.py

Environment variables required:
    - DATABASE_URL
    - SUPABASE_URL
    - SUPABASE_SERVICE_KEY
"""
import os
import sys
import django

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from datetime import timedelta
from django.utils import timezone
from apps.documents.models import Document
from core.clients.supabase_client import delete_documents_by_key, delete_file_from_storage


def cleanup_session_documents(hours: int = 24) -> dict:
    """
    Clean up session-only documents older than specified hours.

    Returns:
        dict with deleted_count and errors
    """
    cutoff_time = timezone.now() - timedelta(hours=hours)

    session_docs = Document.objects.filter(
        is_persistent=False,
        created_at__lt=cutoff_time
    )

    count = session_docs.count()

    if count == 0:
        print(f"[CLEANUP] No session documents older than {hours} hours found.")
        return {"deleted_count": 0, "errors": []}

    print(f"[CLEANUP] Found {count} session documents to clean up.")

    deleted_count = 0
    errors = []

    for doc in session_docs:
        try:
            # Delete vectors from Supabase
            delete_documents_by_key(doc.document_key, str(doc.user_id))

            # Delete file from storage if exists
            if doc.storage_path:
                try:
                    delete_file_from_storage(doc.storage_path)
                except Exception as e:
                    print(f"[CLEANUP] Warning: Failed to delete storage file: {e}")

            # Delete Django record
            doc.delete()
            deleted_count += 1

        except Exception as e:
            errors.append(f"{doc.original_filename}: {str(e)}")
            print(f"[CLEANUP] Error deleting {doc.document_key}: {e}")

    print(f"[CLEANUP] Successfully deleted {deleted_count}/{count} session documents.")

    return {
        "deleted_count": deleted_count,
        "total_found": count,
        "errors": errors
    }


if __name__ == "__main__":
    print("[CLEANUP] Starting session document cleanup...")
    result = cleanup_session_documents(hours=24)
    print(f"[CLEANUP] Complete. Deleted: {result['deleted_count']}")

    if result['errors']:
        print(f"[CLEANUP] Errors: {len(result['errors'])}")
        sys.exit(1)

    sys.exit(0)
