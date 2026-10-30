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
    EMBEDDING_PROVIDER: str = Field(default="pinecone", description="Embedding provider (pinecone, fake, openai)")
    EMBEDDING_MODEL: str = Field(default="llama-text-embed-v2", description="Embedding model name")
    EMBEDDING_DIMENSION: int = Field(default=1024, description="Vector dimension matching index")

    # Recommendation Weights (Must sum to ~1.0)
    WEIGHT_VECTOR: float = Field(default=0.40, description="Weight for vector similarity score")
    WEIGHT_SPECIALTY: float = Field(default=0.25, description="Weight for candidate specialty match")
    WEIGHT_EXPERIENCE: float = Field(default=0.15, description="Weight for clinical experience")
    WEIGHT_FEE: float = Field(default=0.10, description="Weight for budget/fee fit")
    WEIGHT_AVAILABILITY: float = Field(default=0.10, description="Weight for upcoming appointment availability")

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

