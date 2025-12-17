"""
Pydantic settings for RAG Chatbot.
Centralizes all environment variable configuration with validation.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Django
    django_secret_key: str = Field(
        default="django-insecure-dev-key-change-in-production",
        description="Django secret key",
    )
    django_debug: bool = Field(default=True, description="Debug mode")
    django_allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated allowed hosts",
    )

    # Database (PostgreSQL)
    db_name: str = Field(default="rag_chatbot", description="Database name")
    db_host: str = Field(default="localhost", description="Database host")
    db_user: str = Field(default="postgres", description="Database user")
    db_password: str = Field(default="", description="Database password")
    db_port: int = Field(default=5432, description="Database port")

    # Supabase
    supabase_url: Optional[str] = Field(default=None, description="Supabase URL")
    supabase_key: Optional[str] = Field(default=None, description="Supabase anon key")

    # Gemini (Google AI)
    google_api_key: Optional[str] = Field(default=None, description="Google API key for Gemini")

    # Tavily (Web Search)
    tavily_api_key: Optional[str] = Field(default=None, description="Tavily API key")

    # CORS
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated CORS allowed origins",
    )

    @property
    def allowed_hosts_list(self) -> List[str]:
        """Parse allowed hosts into a list."""
        return [h.strip() for h in self.django_allowed_hosts.split(",") if h.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS allowed origins into a list."""
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        """Build PostgreSQL database URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
