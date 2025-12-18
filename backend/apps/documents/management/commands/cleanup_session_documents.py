"""
Management command to clean up session-only documents.

Usage:
    python manage.py cleanup_session_documents
    python manage.py cleanup_session_documents --hours 12  # Custom TTL
    python manage.py cleanup_session_documents --dry-run   # Preview only
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.documents.models import Document
from core.clients.supabase_client import delete_documents_by_key, delete_file_from_storage

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up session-only documents older than specified hours (default: 24)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Delete session documents older than this many hours (default: 24)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']

        cutoff_time = timezone.now() - timedelta(hours=hours)

        # Find session-only documents older than cutoff
        session_docs = Document.objects.filter(
            is_persistent=False,
            created_at__lt=cutoff_time
        )

        count = session_docs.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'No session documents older than {hours} hours found.')
            )
            return

        self.stdout.write(f'Found {count} session documents older than {hours} hours.')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No documents will be deleted.'))
            for doc in session_docs[:20]:  # Show first 20
                self.stdout.write(f'  - {doc.original_filename} (created: {doc.created_at})')
            if count > 20:
                self.stdout.write(f'  ... and {count - 20} more')
            return

        # Delete each document
        deleted_count = 0
        errors = []

        for doc in session_docs:
            try:
                # Delete vectors from Supabase
                vector_result = delete_documents_by_key(doc.document_key, str(doc.user_id))
                if not vector_result.get('success'):
                    logger.warning(f'Failed to delete vectors for {doc.document_key}')

                # Delete file from storage if exists
                if doc.storage_path:
                    try:
                        delete_file_from_storage(doc.storage_path)
                    except Exception as e:
                        logger.warning(f'Failed to delete storage file: {e}')

                # Delete Django record
                doc.delete()
                deleted_count += 1

            except Exception as e:
                errors.append(f'{doc.original_filename}: {str(e)}')
                logger.error(f'Error deleting document {doc.document_key}: {e}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count}/{count} session documents.')
        )

        if errors:
            self.stdout.write(self.style.ERROR(f'Errors ({len(errors)}):'))
            for error in errors[:10]:
                self.stdout.write(f'  - {error}')
