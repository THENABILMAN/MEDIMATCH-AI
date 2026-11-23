"""Embedding Provider Abstraction for MediMatch AI.

Provides:
- BaseEmbeddingProvider: Abstract base class for embedding models.
- OllamaEmbeddingProvider: A local Hugging Face model (bge-m3, 1024-dim), served by Ollama.
- FakeEmbeddingProvider: Fast, deterministic unit vector generator for tests without external network dependencies.
- get_embedding_provider() & set_embedding_provider(): Factory and test fixture hooks.
"""

import hashlib
import logging
import math
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

logger = logging.getLogger("medimatch.search.embeddings")


class BaseEmbeddingProvider(ABC):
    """Abstract interface for generating vector embeddings."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the embedding vector dimension."""
        pass

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeds a list of document strings (passage mode)."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embeds a search query string (query mode)."""
        pass


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """A multilingual Hugging Face embedding model, run locally by Ollama."""

    def __init__(self) -> None:
        self._http = httpx.Client(
            base_url=settings.OLLAMA_URL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            limits=httpx.Limits(keepalive_expiry=120),
        )

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._http.post(
            "/api/embed",
            json={"model": settings.EMBEDDING_MODEL, "input": texts, "keep_alive": "1h"},
        )
        response.raise_for_status()
        return list(response.json()["embeddings"])

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic, local unit vector generator for tests.

    Produces normalized float vectors based on text hash, with zero network dependencies.
    """

    def __init__(self, dimension: int = 1024):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _hash_to_vector(self, text: str) -> list[float]:
        dim = self._dimension
        vec = [0.0] * dim
        tokens = text.lower().strip().split()
        if not tokens:
            # Deterministic default unit vector
            vec[0] = 1.0
            return vec

        for token in tokens:
            seed = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(min(len(seed), 32)):
                idx = (
                    int.from_bytes(seed[i : i + 2], "big") if i + 2 <= len(seed) else seed[i]
                ) % dim
                sign = 1.0 if seed[i] % 2 == 0 else -1.0
                val = (seed[i] / 255.0) * sign
                vec[idx] += val

        # Normalize to unit length (L2 norm)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            return [v / norm for v in vec]
        vec[0] = 1.0
        return vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_to_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._hash_to_vector(text)


_GLOBAL_EMBEDDING_PROVIDER: BaseEmbeddingProvider | None = None


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Returns the singleton embedding provider based on application settings."""
    global _GLOBAL_EMBEDDING_PROVIDER
    if _GLOBAL_EMBEDDING_PROVIDER is not None:
        return _GLOBAL_EMBEDDING_PROVIDER

    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "fake" and settings.ENVIRONMENT != "production":
        _GLOBAL_EMBEDDING_PROVIDER = FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
        return _GLOBAL_EMBEDDING_PROVIDER

    if provider == "ollama":
        _GLOBAL_EMBEDDING_PROVIDER = OllamaEmbeddingProvider()
        return _GLOBAL_EMBEDDING_PROVIDER

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")


def set_embedding_provider(provider: BaseEmbeddingProvider | None) -> None:
    """Overrides the global embedding provider (used in unit test fixtures)."""
    global _GLOBAL_EMBEDDING_PROVIDER
    _GLOBAL_EMBEDDING_PROVIDER = provider
