"""Shared service singletons (LLM, memory store)."""

from langchain_nvidia_ai_endpoints import ChatNVIDIA

from app.config import settings

# --- LLM ---

_llm_instance: ChatNVIDIA | None = None


def get_llm() -> ChatNVIDIA:
    """Return a singleton ChatNVIDIA instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatNVIDIA(
            model=settings.model_name,
            api_key=settings.nvidia_api_key,
            temperature=1,
            top_p=1,
            max_tokens=4096,
        )
    return _llm_instance


# --- Memory store ---
# Auto-selects PostgreSQL if DATABASE_URL is set, otherwise InMemoryStore.

_memory_store = None


def get_memory_store():
    """Return a singleton memory store.

    Uses PostgreSQL if DATABASE_URL is configured, otherwise falls back
    to the in-memory dict store.
    """
    global _memory_store
    if _memory_store is None:
        if settings.database_url:
            from memory.store import PostgresMemoryStore

            _memory_store = PostgresMemoryStore()
        else:
            from memory.store import InMemoryStore

            _memory_store = InMemoryStore()
    return _memory_store
