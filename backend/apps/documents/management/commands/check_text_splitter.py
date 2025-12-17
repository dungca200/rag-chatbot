from django.core.management.base import BaseCommand

from apps.documents.services import split_document


class Command(BaseCommand):
    help = 'Test the text splitter'

    def handle(self, *args, **options):
        self.stdout.write("\n=== Text Splitter Test ===\n")

        # Sample text (longer than chunk size to test splitting)
        sample_text = """
        Machine learning is a subset of artificial intelligence that focuses on developing
        algorithms and statistical models that enable computer systems to improve their
        performance on a specific task through experience.

        Deep learning is a subset of machine learning that uses neural networks with many
        layers (hence "deep") to analyze various factors of data. Deep learning is especially
        useful for processing unstructured data like images, audio, and text.

        Natural language processing (NLP) is a branch of artificial intelligence that helps
        computers understand, interpret, and manipulate human language. NLP draws from many
        disciplines, including computer science and computational linguistics.

        Computer vision is a field of artificial intelligence that trains computers to
        interpret and understand the visual world. Using digital images from cameras and
        videos and deep learning models, machines can accurately identify and classify objects.

        Reinforcement learning is an area of machine learning concerned with how intelligent
        agents ought to take actions in an environment in order to maximize the notion of
        cumulative reward.
        """ * 3  # Repeat to make it longer

        self.stdout.write(f"Input text length: {len(sample_text)} chars")

        chunks = split_document(
            content=sample_text,
            document_key="test_doc_123",
            filename="test_document.txt",
            file_type="txt",
            chunk_size=500,
            chunk_overlap=100
        )

        self.stdout.write(f"Chunks created: {len(chunks)}")

        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            self.stdout.write(f"\n--- Chunk {i} ---")
            self.stdout.write(f"Key: {chunk.get('key')}")
            self.stdout.write(f"Parent Key: {chunk.get('parent_key')}")
            self.stdout.write(f"Content length: {len(chunk.get('content', ''))}")
            self.stdout.write(f"Metadata: {chunk.get('metadata')}")
            self.stdout.write(f"Preview: {chunk.get('content', '')[:100]}...")

        if len(chunks) > 3:
            self.stdout.write(f"\n... and {len(chunks) - 3} more chunks")

        self.stdout.write(self.style.SUCCESS("\n✓ Text splitter test complete"))
