"""Agent configuration API — manage agent status and model settings."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_authority
from app.config import settings
from db.models import UserModel
from db.repositories.agent_config_repo import (
    get_all_agent_configs,
    get_agent_config,
    update_agent_config,
    is_agent_active as _db_is_agent_active,
    get_agent_model_params,
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ---------------------------------------------------------------------------
# Public helpers — used by dispatcher & dependencies
# ---------------------------------------------------------------------------

def is_agent_active(agent_name: str) -> bool:
    """Check if an agent is currently active (DB-backed)."""
    return _db_is_agent_active(agent_name)


def get_agent_display_name(agent_name: str) -> str:
    """Get the human-readable name of an agent."""
    cfg = get_agent_config(agent_name)
    return cfg["name"] if cfg else agent_name


def get_agent_model_config(agent_name: str) -> dict:
    """Return the model parameters for a given agent.

    Used by dependencies.get_llm_for_agent() to build per-agent LLM instances.
    Returns dict with model_name, temperature, top_p, max_tokens.
    """
    return get_agent_model_params(agent_name)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    intent: str
    is_active: bool
    model_name: str = ""
    temperature: float = 1.0
    top_p: float = 1.0
    max_tokens: int = 4096
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


class UpdateAgentRequest(BaseModel):
    """Partial update — every field is optional."""
    is_active: Optional[bool] = None
    model_name: Optional[str] = Field(None, min_length=1, max_length=200)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, ge=64, le=32768)


# ---------------------------------------------------------------------------
# Curated model catalogue — NVIDIA AI Endpoints + compatible models
# ---------------------------------------------------------------------------

# Each entry: (model_id, display_name, category, context_window, description)
# Categories: "recommended", "large", "medium", "small", "code", "vision"

CURATED_MODELS: list[dict] = [
    # ── Recommended for HR flows ──
    {
        "id": "meta/llama-3.3-70b-instruct",
        "name": "Llama 3.3 70B Instruct",
        "provider": "Meta",
        "category": "recommended",
        "context_window": 131072,
        "description": "Best balance of quality, speed, and cost. Ideal for complaint handling and multi-turn conversations.",
    },
    {
        "id": "meta/llama-3.1-70b-instruct",
        "name": "Llama 3.1 70B Instruct",
        "provider": "Meta",
        "category": "recommended",
        "context_window": 131072,
        "description": "Reliable workhorse model. Great for structured output and intent classification.",
    },
    {
        "id": "meta/llama-3.1-8b-instruct",
        "name": "Llama 3.1 8B Instruct",
        "provider": "Meta",
        "category": "recommended",
        "context_window": 131072,
        "description": "Fast and lightweight. Good for simple agents like leave/payroll queries.",
    },
    # ── Large frontier models ──
    {
        "id": "meta/llama-3.1-405b-instruct",
        "name": "Llama 3.1 405B Instruct",
        "provider": "Meta",
        "category": "large",
        "context_window": 131072,
        "description": "Largest open model. Maximum quality for complex complaint analysis. Slower and costlier.",
    },
    {
        "id": "nvidia/llama-3.1-nemotron-70b-instruct",
        "name": "Nemotron 70B Instruct",
        "provider": "NVIDIA",
        "category": "large",
        "context_window": 131072,
        "description": "NVIDIA-optimized variant of Llama 3.1 70B. Excellent instruction following.",
    },
    {
        "id": "deepseek-ai/deepseek-r1",
        "name": "DeepSeek R1",
        "provider": "DeepSeek",
        "category": "large",
        "context_window": 65536,
        "description": "Strong reasoning model. Good for complex complaint classification and policy analysis.",
    },
    # ── Medium models ──
    {
        "id": "google/gemma-2-27b-it",
        "name": "Gemma 2 27B IT",
        "provider": "Google",
        "category": "medium",
        "context_window": 8192,
        "description": "Solid mid-size model from Google. Good for payroll and leave queries.",
    },
    {
        "id": "mistralai/mistral-large-2-instruct",
        "name": "Mistral Large 2 Instruct",
        "provider": "Mistral AI",
        "category": "large",
        "context_window": 131072,
        "description": "Mistral's flagship. Strong multilingual support and structured output.",
    },
    {
        "id": "mistralai/mixtral-8x22b-instruct-v0.1",
        "name": "Mixtral 8x22B Instruct",
        "provider": "Mistral AI",
        "category": "large",
        "context_window": 65536,
        "description": "MoE architecture. Fast inference with high quality. Good all-rounder.",
    },
    {
        "id": "mistralai/mixtral-8x7b-instruct-v0.1",
        "name": "Mixtral 8x7B Instruct",
        "provider": "Mistral AI",
        "category": "medium",
        "context_window": 32768,
        "description": "Efficient MoE model. Good speed-to-quality ratio for simpler agents.",
    },
    # ── Small / fast models ──
    {
        "id": "meta/llama-3.2-3b-instruct",
        "name": "Llama 3.2 3B Instruct",
        "provider": "Meta",
        "category": "small",
        "context_window": 131072,
        "description": "Ultra-fast tiny model. Suitable for intent routing and simple responses.",
    },
    {
        "id": "google/gemma-2-9b-it",
        "name": "Gemma 2 9B IT",
        "provider": "Google",
        "category": "small",
        "context_window": 8192,
        "description": "Compact Google model. Good for default agent greetings and quick replies.",
    },
    {
        "id": "microsoft/phi-3-mini-128k-instruct",
        "name": "Phi 3 Mini 128K",
        "provider": "Microsoft",
        "category": "small",
        "context_window": 131072,
        "description": "Tiny but capable model with huge context. Fast for simple tasks.",
    },
    {
        "id": "mistralai/mistral-7b-instruct-v0.3",
        "name": "Mistral 7B Instruct v0.3",
        "provider": "Mistral AI",
        "category": "small",
        "context_window": 32768,
        "description": "Classic small model. Reliable for straightforward agent tasks.",
    },
    # ── Kept for backward compat ──
    {
        "id": "openai/gpt-oss-120b",
        "name": "GPT OSS 120B",
        "provider": "OpenAI (via NVIDIA)",
        "category": "large",
        "context_window": 131072,
        "description": "Current default model. Large OpenAI-compatible model on NVIDIA endpoints.",
    },
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/models")
async def list_available_models(
    current_user: UserModel = Depends(require_authority),
):
    """Return curated list of NVIDIA API models suitable for the platform.

    Attempts a live fetch from the NVIDIA API to validate availability,
    falling back to the static catalogue.
    """
    # Try live model listing via ChatNVIDIA
    live_model_ids: set[str] = set()
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        available = ChatNVIDIA.get_available_models(api_key=settings.nvidia_api_key)
        live_model_ids = {m.id for m in available if hasattr(m, "id")}
        logger.info(f"Fetched {len(live_model_ids)} models from NVIDIA API")
    except Exception as e:
        logger.warning(f"Could not fetch live model list: {e}")

    # Enrich curated list with availability info
    result = []
    for m in CURATED_MODELS:
        entry = {**m}
        if live_model_ids:
            entry["available"] = m["id"] in live_model_ids
        else:
            entry["available"] = True  # assume available when live check fails
        result.append(entry)

    # Add any live models not in our curated list (as "other" category)
    curated_ids = {m["id"] for m in CURATED_MODELS}
    for model_id in sorted(live_model_ids - curated_ids):
        # Only include chat-compatible models (skip embedding/reranker models)
        if any(skip in model_id for skip in ["embed", "rerank", "nv-rerankqa", "vlm"]):
            continue
        result.append({
            "id": model_id,
            "name": model_id.split("/")[-1].replace("-", " ").title(),
            "provider": model_id.split("/")[0] if "/" in model_id else "Unknown",
            "category": "other",
            "context_window": None,
            "description": "Discovered from NVIDIA API — not in curated list.",
            "available": True,
        })

    return {"models": result, "live_check": bool(live_model_ids)}

@router.get("", response_model=list[AgentResponse])
async def list_agents(
    current_user: UserModel = Depends(require_authority),
):
    """List all agents with their current status (from DB)."""
    configs = get_all_agent_configs()
    return [AgentResponse(**cfg) for cfg in configs]


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    body: UpdateAgentRequest,
    current_user: UserModel = Depends(require_authority),
):
    """Update an agent's status and/or model settings. Higher Authority only."""
    existing = get_agent_config(agent_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # --- Activation / deactivation guard ---
    if body.is_active is not None:
        if agent_id == "default_agent" and not body.is_active:
            raise HTTPException(
                status_code=400,
                detail="The General Assistant cannot be deactivated — it handles fallback queries.",
            )

    # --- Persist to DB ---
    updates = body.dict(exclude_none=True)
    updated = update_agent_config(agent_id, updates, current_user.username)

    # Invalidate cached LLM instance for this agent so the next call picks up changes
    try:
        from app.dependencies import invalidate_agent_llm
        invalidate_agent_llm(agent_id)
    except Exception:
        pass  # best-effort

    logger.info(f"Agent '{agent_id}' updated by {current_user.username}: {updates}")

    return AgentResponse(**updated)
