import logging
from functools import lru_cache
from typing import List

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from settings import settings

logger = logging.getLogger(__name__)

# Embedding dimension for OpenAI text-embedding-3-small
EMBEDDING_DIMENSION = 1536


@lru_cache
def get_embeddings_model() -> OpenAIEmbeddings:
    """Get cached OpenAI embeddings model."""
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.OPENAI_API_KEY
    )


@lru_cache
def get_chat_model(temperature: float = 0.7) -> ChatOpenAI:
    """Get cached OpenAI chat model."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=settings.OPENAI_API_KEY,
        temperature=temperature
    )


def embed_query(text: str) -> List[float]:
    """Embed a single query text and return 1536-dim vector."""
    try:
        model = get_embeddings_model()
        embedding = model.embed_query(text)
        logger.info(f"Generated embedding with {len(embedding)} dimensions")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise


def embed_documents(texts: List[str]) -> List[List[float]]:
    """Embed multiple documents and return list of 1536-dim vectors."""
    try:
        model = get_embeddings_model()
        embeddings = model.embed_documents(texts)
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings
    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        raise


def generate_response(prompt: str, temperature: float = 0.7) -> str:
    """Generate a response using OpenAI chat model."""
    try:
        model = get_chat_model(temperature)
        response = model.invoke(prompt)
        return response.content
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        raise
