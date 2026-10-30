"""Embedding Provider Abstraction for MediMatch AI.

Provides:
- BaseEmbeddingProvider: Abstract base class for embedding models.
- PineconeInferenceEmbeddingProvider: Real provider using Pinecone Inference API (llama-text-embed-v2, 1024-dim).
- FakeEmbeddingProvider: Fast, deterministic unit vector generator for tests without external network dependencies.
- get_embedding_provider() & set_embedding_provider(): Factory and test fixture hooks.
"""

from abc import ABC, abstractmethod
import hashlib
import logging
import math
from typing import List, Optional
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
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
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of document strings (passage mode)."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embeds a search query string (query mode)."""
        pass


class PineconeInferenceEmbeddingProvider(BaseEmbeddingProvider):
    """Embeddings powered by Pinecone's hosted Inference API.

    Defaults to model 'llama-text-embed-v2' (1024 dimensions, cosine metric).
    Requires PINECONE_API_KEY from environment.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: Optional[int] = None,
    ):
        from pinecone import Pinecone

        self._api_key = api_key or settings.PINECONE_API_KEY
        self._model = model or settings.EMBEDDING_MODEL
        self._dimension = dimension or settings.EMBEDDING_DIMENSION
        self._client = Pinecone(api_key=self._api_key)

    @property
    def dimension(self) -> int:
        return self._dimension

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        logger.info(f"Generating document embeddings for {len(texts)} texts via {self._model}")
        res = self._client.inference.embed(
            model=self._model,
            inputs=texts,
            parameters={"input_type": "passage", "truncate": "END"},
        )
        return [item["values"] for item in res]

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def embed_query(self, text: str) -> List[float]:
        if not text or not text.strip():
            # Return zero vector for empty query
            return [0.0] * self._dimension

        logger.info(f"Generating query embedding via {self._model}")
        res = self._client.inference.embed(
            model=self._model,
            inputs=[text.strip()],
            parameters={"input_type": "query", "truncate": "END"},
        )
        return res[0]["values"]


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic, local unit vector generator for tests.

    Produces normalized float vectors based on text hash, with zero network dependencies.
    """

    def __init__(self, dimension: int = 1024):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _hash_to_vector(self, text: str) -> List[float]:
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
                idx = (int.from_bytes(seed[i : i + 2], "big") if i + 2 <= len(seed) else seed[i]) % dim
                sign = 1.0 if seed[i] % 2 == 0 else -1.0
                val = (seed[i] / 255.0) * sign
                vec[idx] += val

        # Normalize to unit length (L2 norm)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            return [v / norm for v in vec]
        vec[0] = 1.0
        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_to_vector(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._hash_to_vector(text)


_GLOBAL_EMBEDDING_PROVIDER: Optional[BaseEmbeddingProvider] = None


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Returns the singleton embedding provider based on application settings."""
    global _GLOBAL_EMBEDDING_PROVIDER
    if _GLOBAL_EMBEDDING_PROVIDER is not None:
        return _GLOBAL_EMBEDDING_PROVIDER

    # In test environment or if explicitly requested, use Fake provider
    if settings.ENVIRONMENT == "test" or settings.EMBEDDING_PROVIDER.lower() == "fake":
        _GLOBAL_EMBEDDING_PROVIDER = FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
        return _GLOBAL_EMBEDDING_PROVIDER

    # Pinecone Inference API (Default production provider)
    if settings.EMBEDDING_PROVIDER.lower() in ["pinecone", "nvidia"]:
        _GLOBAL_EMBEDDING_PROVIDER = PineconeInferenceEmbeddingProvider(
            api_key=settings.PINECONE_API_KEY,
            model=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
        )
        return _GLOBAL_EMBEDDING_PROVIDER

    # Fallback to Fake if unknown provider specified
    logger.warning(
        f"Unknown EMBEDDING_PROVIDER '{settings.EMBEDDING_PROVIDER}', falling back to FakeEmbeddingProvider"
    )
    _GLOBAL_EMBEDDING_PROVIDER = FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    return _GLOBAL_EMBEDDING_PROVIDER


def set_embedding_provider(provider: Optional[BaseEmbeddingProvider]) -> None:
    """Overrides the global embedding provider (used in unit test fixtures)."""
    global _GLOBAL_EMBEDDING_PROVIDER
    _GLOBAL_EMBEDDING_PROVIDER = provider

