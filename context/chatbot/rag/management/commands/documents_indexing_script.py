from django.core.management.base import BaseCommand, CommandError
from rag.core.document_indexer import DocumentIndexer

class Command(BaseCommand):
    help = 'Index documents from PostgreSQL to Supabase'

    def handle(self, *args, **options):
        indexer = DocumentIndexer()
        try:
            indexer.process_documents()
            self.stdout.write(self.style.SUCCESS('Documents indexed successfully'))
        except Exception as e:
            raise CommandError(f'Indexing failed: {e}')
