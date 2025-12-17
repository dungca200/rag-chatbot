from typing import List, Optional, Dict
from openai import OpenAI
from supabase import create_client, Client
import logging
from settings import settings
from rag.utils.text_processing import TextProcessor

class SupabaseRetriever:
    """
    A retriever class that performs semantic search on documents stored in Supabase.
    """
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.company_id = None
        self.text_processor = TextProcessor()
        self.logger = logging.getLogger(__name__)

    def set_company_id(self, company_id: int):
        self.company_id = company_id

    def get_document_by_key(self, document_key: str) -> Optional[Dict]:
        """
        Directly fetch a document by its parent key using RPC function.
        """
        try:
            result = self.supabase.rpc(
                'get_document_by_parent_key',
                {
                    'search_parent_key': document_key
                }
            ).execute()
            
            if result.data and len(result.data) > 0:
                doc = result.data[0]
                return {
                    'key': doc['key'],
                    'content': doc['content'],
                    'similarity': 1.0,  # Direct match
                    'chunks_used': [doc['key']],
                    'resources': [doc['key']]
                }
            self.logger.warning(f"No document found with parent key.")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching document by parent key: {str(e)}")
            return None

    def semantic_search(self, query: str, top_k: int = 1, document_key: str = None) -> List[dict]:
        """
        Performs semantic search on documents. If document_key is provided,
        retrieves the specific document instead of performing semantic search.
        """
        try:
            chunks = self.text_processor.chunk_text(query)
            query_embedding = self.text_processor.get_embedding(chunks)
            
            result = self.supabase.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding,
                    'search_company_id': self.company_id,
                    'search_key': document_key,
                    'match_threshold': 0.15,
                    'match_count': 10
                }
            ).execute()

            if not result.data:
                return []

            if document_key:
                result.data = [doc for doc in result.data if doc['key'].startswith(document_key)]
                if not result.data:
                    return []

            # Store original content before grouping
            for doc in result.data:
                doc['original_content'] = doc['content']
                doc['parent_key'] = doc['key'].split('_chunk_')[0]

            grouped_results = {}
            for doc in result.data:
                parent_key = doc['parent_key']
                if parent_key not in grouped_results:
                    grouped_results[parent_key] = []
                grouped_results[parent_key].append(doc)

            sorted_documents = sorted(grouped_results.items(), 
                                   key=lambda x: x[1][0]['similarity'], 
                                   reverse=True)
            
            top_document_key, all_chunks = sorted_documents[0]
            
            # Calculate combined scores
            query_terms = set(query.lower().split())
            for chunk in all_chunks:
                chunk_terms = set(chunk['content'].lower().split())
                term_overlap = len(query_terms & chunk_terms)
                chunk['combined_score'] = (term_overlap * 0.5) + (chunk['similarity'] * 0.5)

            all_chunks.sort(key=lambda x: x['combined_score'], reverse=True)
            top_chunks = all_chunks[:top_k]
            
            combined_content = "\n".join(chunk['original_content'] for chunk in top_chunks)
            
            final_results = [{
                'key': top_document_key,
                'content': combined_content,
                'similarity': top_chunks[0]['similarity'],
                'chunks_used': [chunk['key'] for chunk in top_chunks],
                'resources': [top_document_key]
            }]
            return final_results

        except Exception as e:
            self.logger.error(f"Error in semantic search: {str(e)}")
            return []
