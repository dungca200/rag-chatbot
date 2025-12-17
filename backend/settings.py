from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Django Core
    DJANGO_SECRET_KEY: str
    DJANGO_DEBUG: int
    DJANGO_ALLOWED_HOSTS: str

    # Database (PostgreSQL)
    DB_NAME: str
    DB_HOST: str
    DB_USER: str
    DB_PASSWORD: str
    DB_PORT: int

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Gemini (Google AI)
    GOOGLE_API_KEY: str

    # Tavily (Web Search)
    TAVILY_API_KEY: str

    # CORS
    CORS_ALLOWED_ORIGINS: str

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow",
    }


settings = Settings()
