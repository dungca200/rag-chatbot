import logging
from typing import List, Dict, Any
import traceback
import uuid
from django.db.models import F
from postgrest.exceptions import APIError
from supabase import create_client, Client
from openai import OpenAI
from settings import settings
from rag.utils.text_processing import TextProcessor
from aws.models import Document

class DocumentIndexer:
    """
    A class to handle indexing of documents from a PostgreSQL database to Supabase.
    
    This class uses Django ORM for database access instead of direct connections,
    leveraging connection pooling provided by Django.
    
    Methods
    -------
    __init__():
        Initializes the DocumentIndexer with necessary clients and connections.
    verify_supabase_tables():
        Verifies if the required Supabase tables exist and logs instructions if they don't.
    get_existing_supabase_documents() -> List[str]:
        Retrieves a list of document keys already present in Supabase.
    extract_text_from_blocks(line_blocks: dict) -> str:
        Extracts and combines text from line blocks.
    get_documents_to_process() -> List[dict]:
        Fetches documents from Django ORM that need processing.
    index_single_document(content: str, key: str, company_id: int) -> bool:
        Indexes a single document directly from its content.
    index_document(doc: dict) -> bool:
        Indexes a document from the ORM.
    process_documents():
        Main processing function to handle the indexing of documents.
    """
    def __init__(self):
        """
        Initialize the DocumentIndexer with required clients and services.
        
        Uses Django ORM for database operations, eliminating the need
        for a separate connection pool.
        """
        self.logger = logging.getLogger(__name__)
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        self.openai_client = OpenAI()
        self.text_processor = TextProcessor()
        self.verify_supabase_tables()

    def verify_supabase_tables(self):
        """
        Verify Supabase tables exist and provide creation instructions if they don't.
        
        Raises:
            Exception: If required tables are not found in Supabase.
        """
        try:
            # Try to query the table
            self.supabase.table('documents').select('id').limit(1).execute()
            self.logger.info("Successfully connected to Supabase documents table")
        except APIError as e:
            self.logger.error("Required tables not found in Supabase")
            raise Exception("Please create required tables in Supabase using the SQL commands shown in the log")

    def get_existing_supabase_documents(self) -> List[str]:
        """
        Get list of document keys already in Supabase.
        
        Returns:
            List[str]: List of document keys already indexed in Supabase.
        """
        try:
            response = self.supabase.table('documents').select('key').execute()
            return [doc['key'] for doc in response.data]
        except Exception as e:
            self.logger.error(f"Error fetching existing documents: {str(e)}")
            return []
        
    def extract_text_from_blocks(self, line_blocks: dict) -> str:
        """
        Extract and combine text from line_blocks.
        
        Args:
            line_blocks: JSON object containing blocks of text.
            
        Returns:
            str: Combined text from all blocks.
            
        Raises:
            ValueError: If line_blocks format is invalid.
        """
        try:
            combined_text = ' '.join(block['text'] for block in line_blocks['blocks'])
            return combined_text        
        except (KeyError, TypeError) as e:
            self.logger.error(f"Error extracting text from line_blocks: {str(e)}")
            raise ValueError("Invalid line_blocks format")
        
    def get_documents_to_process(self) -> List[Dict[str, Any]]:
        """
        Get documents from database that need processing using Django ORM.
        
        Returns:
            List[Dict[str, Any]]: Documents with AWS responses containing line blocks,
                                 matching the exact format of the original query.
        """
        try:
            # Generate correlation ID for tracking this operation
            correlation_id = str(uuid.uuid4())
            self.logger.info(f"[{correlation_id}] Fetching documents with line blocks")
            
            # Use Django ORM to match the original SQL query exactly
            # Avoiding field name conflicts by using different names in the query
            documents = Document.objects.select_related('aws_response').filter(
                aws_response__line_blocks__isnull=False
            ).values(
                'aws_response__id',
                'aws_response__key',
                'aws_response__line_blocks',
                'company_id',
                'id'
            )
            
            # Transform the query results to match the expected format from the original SQL query
            results = [
                {
                    'aws_response_id': doc['aws_response__id'],
                    'key': doc['aws_response__key'],
                    'line_blocks': doc['aws_response__line_blocks'],
                    'company_id': doc['company_id'],
                    'document_id': doc['id']
                }
                for doc in documents
            ]
            
            self.logger.info(f"[{correlation_id}] Found {len(results)} documents with line blocks")
            return results
            
        except Exception as e:
            self.logger.error(f"Error fetching documents to process: {str(e)}")
            self.logger.error(traceback.format_exc())
            return []

    def index_single_document(self, content: str, key: str, company_id: int) -> bool:
        """Index a single document with multiple chunks"""
        try:
            self.logger.info(f"Indexing document chunks for: {key}")
            
            # Generate chunks with overlap
            chunks = self.text_processor.chunk_text(content, chunk_size=512, overlap=20)
            
            # Get embeddings for each chunk
            chunk_embeddings = self.text_processor.get_embedding(chunks, store_chunks=True)
            
            # Store each chunk as a separate entry
            for idx, chunk_data in enumerate(chunk_embeddings):
                data = {
                    'key': f"{key}_chunk_{idx}",  # Unique key for each chunk
                    'company_id': company_id,
                    'content': chunk_data['content'],
                    'embedding': chunk_data['embedding'],
                    'parent_key': key  # Reference to original document
                }
                
                try:
                    self.supabase.table('documents').upsert(data).execute()
                    self.logger.info(f"Successfully indexed chunk {idx} for document {key}")
                except APIError as e:
                    self.logger.error(f"Failed to index chunk {idx} for document {key}: {str(e)}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error indexing document {key}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def index_document(self, doc: dict) -> bool:
        """Index a document from PostgreSQL aws_responses table"""
        try:
            if not doc['company_id']:
                self.logger.info(f"{doc['key']} is being processed... No company_id found. (Skipped)")
                return False
            
            # Extract text from line_blocks
            combined_text = self.extract_text_from_blocks(doc['line_blocks'])
            return self.index_single_document(combined_text, doc['key'], doc['company_id'])

        except Exception as e:
            self.logger.error(f"Error in index_document for {doc['key']}: {str(e)}")
            return False

    def process_documents(self):
        """Main processing function"""
        self.logger.info("Starting document indexing process...")
        
        try:
            # Get existing documents in Supabase
            existing_docs = self.get_existing_supabase_documents()
            self.logger.info(f"Found {len(existing_docs)} existing documents in Supabase")

            # Get documents to process
            documents = self.get_documents_to_process()
            self.logger.info(f"Found {len(documents)} total documents in PostgreSQL")

            # Process each document
            processed_count = 0
            skipped_count = 0
            already_exists_count = 0

            for doc in documents:
                if doc['key'] in existing_docs:
                    self.logger.info(f"{doc['key']} is already added into the database.")
                    already_exists_count += 1
                    continue

                success = self.index_document(doc)
                if success:
                    processed_count += 1
                else:
                    skipped_count += 1

            # Logs for Processing Summary
            self.logger.info("\nProcessing Summary:")
            self.logger.info(f"Total documents found: {len(documents)}")
            self.logger.info(f"Already in Supabase: {already_exists_count}")
            self.logger.info(f"Successfully processed: {processed_count}")
            self.logger.info(f"Skipped (no company_id): {skipped_count}")

        except Exception as e:
            self.logger.error(f"Error in process_documents: {str(e)}")
            self.logger.error(traceback.format_exc())
        finally:
            self.logger.info("Document indexing process completed")

    def __del__(self):
        """Cleanup any resources if needed."""
        pass  # No connection pool to clean up with Django ORM