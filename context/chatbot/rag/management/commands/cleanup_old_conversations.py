from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from rag.models import Conversation
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleanup old conversations that have not been updated recently'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete conversations older than specified days (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get conversations to delete
        conversations = Conversation.objects.filter(last_updated__lt=cutoff_date)
        count = conversations.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'Would delete {count} conversations older than {days} days'
                )
            )
            return
        
        # Delete old conversations
        deleted_count = conversations.delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {deleted_count} conversations older than {days} days'
            )
        )
        logger.info(f'Cleaned up {deleted_count} old conversations')
