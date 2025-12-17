from typing import List, Dict
import numpy as np
from openai import OpenAI
from settings import settings
import logging
from typing import Union

logger = logging.getLogger(__name__)

class TextProcessor:
    def __init__(self):
        self.openai_client = OpenAI()
        self.chunk_size = 4000  # Safe size below the 8192 token limit
        self.embedding_dimension = 512  # dimension for text-embedding-3-small

    def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 20) -> List[str]:
        """Split text into chunks with overlap while preserving word boundaries"""
        words = text.split()
        chunks = []
        start_idx = 0
        
        while start_idx < len(words):
            chunk_words = words[start_idx:start_idx + chunk_size]
            chunks.append(' '.join(chunk_words))
            # Move the start index by chunk_size - overlap
            start_idx += (chunk_size - overlap)
            
        return chunks

    def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate embedding format and dimension"""
        if not isinstance(embedding, list):
            return False
        if len(embedding) != self.embedding_dimension:
            return False
        if not all(isinstance(x, (int, float)) for x in embedding):
            return False
        return True

    def get_embedding(self, text: Union[str, List[str]], store_chunks: bool = False) -> Union[List[float], List[Dict]]:
        """Generate embeddings for text, with option to return individual chunk embeddings"""
        try:
            if isinstance(text, list):
                # Generate individual embeddings for each chunk
                chunk_embeddings = []
                for chunk in text:
                    response = self.openai_client.embeddings.create(
                        model="text-embedding-3-small",
                        input=chunk,
                        dimensions=self.embedding_dimension
                    )
                    if store_chunks:
                        chunk_embeddings.append({
                            'content': chunk,
                            'embedding': response.data[0].embedding
                        })
                    else:
                        chunk_embeddings.append(response.data[0].embedding)
                
                if store_chunks:
                    return chunk_embeddings
                return list(np.mean(chunk_embeddings, axis=0))
            else:
                # For single texts within token limit
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text,
                    dimensions=self.embedding_dimension
                )
                final_embedding = response.data[0].embedding

            # Validate embedding before returning
            if not self.validate_embedding(final_embedding):
                raise ValueError("Invalid embedding format or dimension")
                
            return final_embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise