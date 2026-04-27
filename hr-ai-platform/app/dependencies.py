"""Shared service singletons (LLM, memory store)."""

from langchain_nvidia_ai_endpoints import ChatNVIDIA

from app.config import settings

# --- LLM ---

_llm_instance: ChatNVIDIA | None = None


def get_llm() -> ChatNVIDIA:
    """Return a singleton ChatNVIDIA instance using global defaults."""
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


# --- Per-agent LLM cache ---
# Each agent can have its own model/temperature/top_p/max_tokens settings.
# Instances are cached and invalidated when the admin updates an agent's config.

_agent_llm_cache: dict[str, ChatNVIDIA] = {}


def get_llm_for_agent(agent_name: str) -> ChatNVIDIA:
    """Return a ChatNVIDIA instance configured for a specific agent.

    Reads per-agent model settings from the agent registry.
    Falls back to global defaults if no per-agent config exists.
    """
    if agent_name in _agent_llm_cache:
        return _agent_llm_cache[agent_name]

    from api.routes.agents import get_agent_model_config

    cfg = get_agent_model_config(agent_name)
    instance = ChatNVIDIA(
        model=cfg["model_name"],
        api_key=settings.nvidia_api_key,
        temperature=cfg["temperature"],
        top_p=cfg["top_p"],
        max_tokens=cfg["max_tokens"],
    )
    _agent_llm_cache[agent_name] = instance
    return instance


def invalidate_agent_llm(agent_name: str) -> None:
    """Remove cached LLM instance for an agent so it gets re-created on next use."""
    _agent_llm_cache.pop(agent_name, None)


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
