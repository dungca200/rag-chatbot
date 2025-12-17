"""
Pydantic settings for RAG Chatbot.
Centralizes all environment variable configuration with validation.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Django Core
    DJANGO_SECRET_KEY: str
    DJANGO_DEBUG: int = 1
    DJANGO_ALLOWED_HOSTS: str = "localhost,127.0.0.1"

    # Database (PostgreSQL)
    DB_NAME: str = "rag_chatbot"
    DB_HOST: str = "localhost"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_PORT: int = 5432

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # Gemini (Google AI)
    GOOGLE_API_KEY: str = ""

    # Tavily (Web Search)
    TAVILY_API_KEY: str = ""

    # CORS
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow",
    }


settings = Settings()
