from functools import lru_cache
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "MediMatch AI"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Supabase Configuration
    SUPABASE_URL: str = Field(default="", description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(default="", description="Supabase public anon key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="", description="Supabase service role secret key")
    DATABASE_URL: str = Field(default="", description="PostgreSQL connection string")

    # Pinecone Vector Search
    PINECONE_API_KEY: str = Field(default="", description="Pinecone API key")
    PINECONE_INDEX: str = Field(default="medimatch-doctors", description="Pinecone index name")

    # OpenRouter LLM
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API key")
    OPENROUTER_MODEL: str = Field(default="anthropic/claude-3.5-sonnet", description="OpenRouter model identifier")

    # Embedding Settings
    EMBEDDING_PROVIDER: str = Field(default="openai", description="Embedding provider")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="Embedding model name")

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def clean_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            # Clean common bracket mistake from Supabase placeholder: postgresql://postgres:[password]@...
            # If user entered postgresql://postgres:[pass]@..., strip brackets around the password
            return v.replace(":[", ":").replace("]@", "@")
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

