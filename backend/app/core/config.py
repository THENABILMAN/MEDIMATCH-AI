from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CrisisHelpline(BaseModel):
    """A support line shown in crisis messages."""

    name: str = Field(min_length=1, max_length=100)
    number: str = Field(min_length=2, max_length=30)
    hours: str | None = Field(default=None, max_length=50)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "MediMatch AI"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "production"] = "development"

    # Supabase Configuration
    SUPABASE_URL: str = Field(default="", description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(default="", description="Supabase public anon key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        default="", description="Supabase service role secret key"
    )
    DATABASE_URL: str = Field(default="", description="PostgreSQL connection string")

    # MongoDB vector search. A local container or a MongoDB Atlas link both work
    MONGODB_URI: str = "mongodb://localhost:27018/?directConnection=true"
    MONGODB_DATABASE: str = "medimatch"
    MONGODB_DOCTORS: str = "doctors"
    MONGODB_BOOKS: str = Field(default="medical_books", description="Empty turns the books off")
    MONGODB_TIMEOUT_MS: int = Field(default=3000, ge=1)
    BOOK_PASSAGE_CHARS: int = Field(default=700, ge=100)

    # Local models from Hugging Face, served by Ollama
    OLLAMA_URL: str = "http://localhost:11434"
    LLM_MODEL: str = Field(default="medimatch", description="Built from backend/models/Modelfile")
    LLM_TEMPERATURE: float = Field(default=0.8, ge=0, le=2, description="For the reply")
    LLM_TIMEOUT_SECONDS: float = Field(
        default=120.0, gt=0, description="Covers loading the model the first time"
    )
    LLM_CONTEXT_TOKENS: int = Field(default=6144, ge=1024)
    LLM_MAX_TOKENS: int = Field(default=500, ge=50)
    LLM_HISTORY_MESSAGES: int = Field(default=16, ge=1)

    # When the assistant is sure enough to suggest doctors
    SURE_CONFIDENCE: int = Field(default=80, ge=0, le=100)
    MIN_QUESTIONS: int = Field(default=3, ge=0)
    MAX_QUESTIONS: int = Field(default=8, ge=1)

    # Embeddings. Books must be embedded with this same model
    EMBEDDING_PROVIDER: str = Field(default="ollama", description="ollama, or fake for tests")
    EMBEDDING_MODEL: str = "hf.co/gpustack/bge-m3-GGUF:Q8_0"
    EMBEDDING_DIMENSION: int = Field(default=1024, description="Matches the model and the index")

    # Vector Search
    SYNC_IN_BACKGROUND: bool = True
    VECTOR_CANDIDATES: int = Field(
        default=30, ge=1, description="Vector matches fetched before filtering"
    )

    # Recommendation Weights (must sum to 1.0)
    WEIGHT_VECTOR: float = Field(default=0.40, description="Weight for vector similarity score")
    WEIGHT_SPECIALTY: float = Field(
        default=0.25, description="Weight for candidate specialty match"
    )
    WEIGHT_EXPERIENCE: float = Field(default=0.15, description="Weight for clinical experience")
    WEIGHT_FEE: float = Field(default=0.10, description="Weight for budget/fee fit")
    WEIGHT_AVAILABILITY: float = Field(
        default=0.10, description="Weight for upcoming appointment availability"
    )

    # Number shown in every emergency alert
    EMERGENCY_NUMBER: str = Field(default="999", min_length=2, max_length=15, pattern=r"^\d+$")

    # TODO(owner): set this before launch, and verify every number by calling it yourself.
    # Nothing is filled in here on purpose. With an empty list, crisis messages show only
    # EMERGENCY_NUMBER. JSON, for example: [{"name": "...", "number": "...", "hours": "24 hours"}]
    CRISIS_HELPLINES: list[CrisisHelpline] = Field(default_factory=list)

    # Abuse limits, per minute
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN: int = Field(default=10, ge=1)
    RATE_LIMIT_REGISTER: int = Field(default=5, ge=1)
    RATE_LIMIT_CHAT: int = Field(default=20, ge=1)
    RATE_LIMIT_UPLOAD: int = Field(default=10, ge=1)

    # Upcoming appointments one patient can hold, so one account cannot take every slot
    MAX_ACTIVE_BOOKINGS: int = Field(default=5, ge=1)

    # Credential uploads, and the largest request of any kind
    MAX_UPLOAD_BYTES: int = Field(default=10 * 1024 * 1024, ge=1)
    MAX_REQUEST_BYTES: int = Field(default=11 * 1024 * 1024, ge=1)

    # Conversations and symptom sessions untouched for this long are erased
    CHAT_RETENTION_DAYS: int = Field(default=365, ge=1)

    # Longest a single Supabase database or Storage call can take
    SUPABASE_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0)

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def clean_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            # Clean common bracket mistake from Supabase placeholder: postgresql://postgres:[password]@...
            # If user entered postgresql://postgres:[pass]@..., strip brackets around the password
            return v.replace(":[", ":").replace("]@", "@")
        return v

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def reject_wildcard_cors_origin(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError(
                "BACKEND_CORS_ORIGINS cannot contain '*' when credentialed requests are enabled"
            )
        return v

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "Settings":
        total = (
            self.WEIGHT_VECTOR
            + self.WEIGHT_SPECIALTY
            + self.WEIGHT_EXPERIENCE
            + self.WEIGHT_FEE
            + self.WEIGHT_AVAILABILITY
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Recommendation weights must sum to 1.0, not {total}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
