"""POST /chat — main conversation endpoint."""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends

from api.schemas.request import ChatRequest
from api.schemas.response import ChatResponse
from app.auth import get_optional_user
from db.connection import get_db_session
from db.models import UserModel, ConversationModel
from orchestrator.graph import build_graph
from orchestrator.state import HRState
from utils.helpers import generate_trace_id, get_timestamp
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# Compile the orchestrator graph once
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: Optional[UserModel] = Depends(get_optional_user),
) -> ChatResponse:
    """Process an employee chat message through the orchestrator.

    If authenticated, uses the logged-in user's username as user_id.
    Otherwise falls back to user_id from the request body.
    """
    # Use authenticated user if available, else fall back to request body
    user_id = current_user.username if current_user else request.user_id

    trace_id = generate_trace_id()
    timestamp = get_timestamp()

    # Load recent conversation history from DB for context
    conversation_history = []
    try:
        session = get_db_session()
        rows = (
            session.query(ConversationModel)
            .filter(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.timestamp.desc())
            .limit(5)
            .all()
        )
        session.close()
        rows.reverse()  # chronological order
        conversation_history = [
            {"role": "user", "content": r.message, "role2": "assistant", "content2": r.response}
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"Could not load conversation history: {e}")

    logger.info(
        f"[{trace_id}] Chat request from user {user_id}: "
        f"{request.message[:80]}..."
    )

    try:
        initial_state: HRState = {
            "user_id": user_id,
            "message": request.message,
            "intent": "",
            "confidence": 0.0,
            "emotion": "",
            "severity": "",
            "complaint_type": "",
            "response": "",
            "escalation_action": "",
            "conversation_history": conversation_history,
            "trace_id": trace_id,
            "timestamp": timestamp,
            "agent_used": "",
            "metadata": {},
        }

        graph = _get_graph()
        result = await asyncio.to_thread(graph.invoke, initial_state)

        logger.info(
            f"[{trace_id}] Chat completed — intent={result.get('intent')}, "
            f"agent={result.get('agent_used')}"
        )

        return ChatResponse(
            user_id=user_id,
            response=result.get("response", "I'm sorry, I couldn't process your request."),
            intent=result.get("intent", ""),
            confidence=result.get("confidence", 0.0),
            agent_used=result.get("agent_used", ""),
            trace_id=trace_id,
            metadata=result.get("metadata", {}),
        )

    except Exception as e:
        logger.error(f"[{trace_id}] Error processing chat: {e}")
        return ChatResponse(
            user_id=user_id,
            response="Something went wrong. Please try again later.",
            trace_id=trace_id,
            metadata={"error": str(e)},
        )
