"""MongoDB vector search: one collection of doctors, one of medical book passages.

Supabase stays the source of truth for doctors. MongoDB only says which ones are similar.
"""

import logging
from functools import lru_cache
from typing import Any, NamedTuple

from pymongo import MongoClient, ReplaceOne
from pymongo.collection import Collection
from pymongo.operations import SearchIndexModel

from app.core.config import settings
from app.search.embeddings import get_embedding_provider

logger = logging.getLogger("medimatch.search.vector_store")

INDEX_NAME = "vector_index"
DOCTOR_FILTERS = ["status", "specialty_names", "city"]


class Match(NamedTuple):
    id: str
    score: float


@lru_cache
def get_database() -> Any:
    client: MongoClient = MongoClient(
        settings.MONGODB_URI, serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS
    )
    return client[settings.MONGODB_DATABASE]


def ensure_vector_index(collection: Collection, filters: list[str] | None = None) -> None:
    """Creates the collection and its vector index if they are missing."""
    if collection.name not in collection.database.list_collection_names():
        collection.database.create_collection(collection.name)
    if any(index["name"] == INDEX_NAME for index in collection.list_search_indexes()):
        return
    fields: list[dict[str, Any]] = [
        {
            "type": "vector",
            "path": "embedding",
            "numDimensions": settings.EMBEDDING_DIMENSION,
            "similarity": "cosine",
        }
    ]
    fields += [{"type": "filter", "path": path} for path in filters or []]
    collection.create_search_index(
        SearchIndexModel(definition={"fields": fields}, name=INDEX_NAME, type="vectorSearch")
    )


def vector_search(
    collection: Collection,
    vector: list[float],
    top_k: int,
    project: dict[str, Any],
    where: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    stage: dict[str, Any] = {
        "index": INDEX_NAME,
        "path": "embedding",
        "queryVector": vector,
        "numCandidates": max(top_k * 15, 150),
        "limit": top_k,
    }
    if where:
        stage["filter"] = where
    score = {"score": {"$meta": "vectorSearchScore"}}
    return list(collection.aggregate([{"$vectorSearch": stage}, {"$project": project | score}]))


class DoctorStore:
    def __init__(self, collection: Collection):
        self._collection = collection

    def upsert(self, vectors: list[dict[str, Any]]) -> None:
        if vectors:
            self._collection.bulk_write(
                [
                    ReplaceOne(
                        {"_id": v["id"]},
                        {"_id": v["id"], "embedding": v["values"], **v["metadata"]},
                        upsert=True,
                    )
                    for v in vectors
                ]
            )

    def delete(self, ids: list[str]) -> None:
        self._collection.delete_many({"_id": {"$in": ids}})

    def query(self, vector: list[float], top_k: int, where: dict[str, Any]) -> list[Match]:
        rows = vector_search(self._collection, vector, top_k, {"_id": 1}, where)
        return [Match(str(row["_id"]), float(row["score"])) for row in rows]

    def exists(self, doctor_id: str) -> bool:
        return self._collection.find_one({"_id": doctor_id}, {"_id": 1}) is not None

    def count(self) -> int:
        return self._collection.count_documents({})

    def prepare(self) -> None:
        ensure_vector_index(self._collection, DOCTOR_FILTERS)


_store: Any | None = None


def get_vector_store() -> Any:
    global _store
    if _store is None:
        _store = DoctorStore(get_database()[settings.MONGODB_DOCTORS])
    return _store


def set_vector_store(store: Any | None) -> None:
    """Replaces the store in tests."""
    global _store
    _store = store


def search_books(query: str, top_k: int = 4) -> list[str]:
    """Passages from the medical books. The assistant still works with no books loaded."""
    if not settings.MONGODB_BOOKS:
        return []
    try:
        rows = vector_search(
            get_database()[settings.MONGODB_BOOKS],
            get_embedding_provider().embed_query(query),
            top_k,
            {"_id": 0, "text": 1, "source": 1},
        )
    except Exception as e:
        logger.warning(f"Book search failed: {type(e).__name__}")
        return []
    return [
        f"[{row.get('source') or 'book'}] {row['text'][: settings.BOOK_PASSAGE_CHARS]}"
        for row in rows
        if row.get("text")
    ]
