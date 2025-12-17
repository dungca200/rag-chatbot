import logging
from functools import lru_cache
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from settings import settings

logger = logging.getLogger(__name__)

# Embedding dimension for Gemini
EMBEDDING_DIMENSION = 768


@lru_cache
def get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """Get cached Gemini embeddings model."""
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=settings.GOOGLE_API_KEY
    )


@lru_cache
def get_chat_model(temperature: float = 0.7) -> ChatGoogleGenerativeAI:
    """Get cached Gemini chat model."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature
    )


def embed_query(text: str) -> List[float]:
    """Embed a single query text and return 768-dim vector."""
    try:
        model = get_embeddings_model()
        embedding = model.embed_query(text)
        logger.info(f"Generated embedding with {len(embedding)} dimensions")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise


def embed_documents(texts: List[str]) -> List[List[float]]:
    """Embed multiple documents and return list of 768-dim vectors."""
    try:
        model = get_embeddings_model()
        embeddings = model.embed_documents(texts)
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings
    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        raise


def generate_response(prompt: str, temperature: float = 0.7) -> str:
    """Generate a response using Gemini chat model."""
    try:
        model = get_chat_model(temperature)
        response = model.invoke(prompt)
        return response.content
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        raise
