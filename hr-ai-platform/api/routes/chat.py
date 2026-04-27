"""POST /chat — main conversation endpoint."""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends

from api.schemas.request import ChatRequest
from api.schemas.response import ChatResponse
from app.auth import get_optional_user
from db.connection import get_db_session
from db.models import UserModel, ConversationModel, TicketModel, FeedbackModel
from orchestrator.graph import build_graph
from orchestrator.state import HRState
from utils.context import contains_ticket_notice
from utils.helpers import generate_id, generate_trace_id, get_timestamp
from utils.logger import get_logger
from utils.privacy import normalize_privacy_mode

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# Compile the orchestrator graph once
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _load_ticket_context(user_id: str) -> dict:
    """Load the user's ticket context for AI awareness.

    Returns a dict with:
      - open_tickets: list of open/in_progress tickets
      - resolved_tickets: list of resolved tickets (awaiting feedback)
      - closed_tickets: list of recently closed tickets with feedback
      - has_active_tickets: bool
      - has_unresolved_feedback: bool (resolved but no feedback yet)
    """
    session = get_db_session()
    try:
        tickets = (
            session.query(TicketModel)
            .filter(TicketModel.user_id == user_id)
            .order_by(TicketModel.created_at.desc())
            .limit(20)
            .all()
        )

        open_tickets = []
        resolved_tickets = []
        closed_tickets = []

        for t in tickets:
            info = {
                "ticket_id": t.ticket_id,
                "title": t.title,
                "severity": t.severity,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else "",
            }

            if t.status in ("open", "in_progress"):
                open_tickets.append(info)
            elif t.status == "resolved":
                fb = session.query(FeedbackModel).filter_by(
                    ticket_id=t.ticket_id, user_id=user_id
                ).first()
                info["has_feedback"] = fb is not None
                if fb:
                    info["rating"] = fb.rating
                    info["feedback_comment"] = fb.comment or ""
                resolved_tickets.append(info)
            elif t.status == "closed":
                fb = session.query(FeedbackModel).filter_by(
                    ticket_id=t.ticket_id, user_id=user_id
                ).first()
                info["has_feedback"] = fb is not None
                if fb:
                    info["rating"] = fb.rating
                closed_tickets.append(info)

        has_unresolved = any(
            not t.get("has_feedback") for t in resolved_tickets
        )

        return {
            "open_tickets": open_tickets,
            "resolved_tickets": resolved_tickets,
            "closed_tickets": closed_tickets,
            "has_active_tickets": len(open_tickets) > 0,
            "has_unresolved_feedback": has_unresolved,
        }
    except Exception as e:
        logger.warning(f"Could not load ticket context: {e}")
        return {
            "open_tickets": [],
            "resolved_tickets": [],
            "closed_tickets": [],
            "has_active_tickets": False,
            "has_unresolved_feedback": False,
        }
    finally:
        session.close()


def _resolve_thread_id(user_id: str) -> str:
    """Reuse an active complaint thread when the last complaint is still in intake."""
    session = get_db_session()
    try:
        rows = (
            session.query(ConversationModel)
            .filter(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.timestamp.desc())
            .limit(12)
            .all()
        )
        for row in rows:
            if (row.intent or "") != "employee_complaint":
                continue
            thread_id = getattr(row, "thread_id", "") or ""
            if thread_id and not contains_ticket_notice(row.response or ""):
                return thread_id
            break
    except Exception as e:
        logger.warning(f"Could not resolve thread id: {e}")
    finally:
        session.close()
    return generate_id("THR")


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
    thread_id = _resolve_thread_id(user_id)

    # Load recent conversation history from DB for context
    conversation_history = []
    try:
        session = get_db_session()
        rows = (
            session.query(ConversationModel)
            .filter(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.timestamp.desc())
            .limit(10)
            .all()
        )
        session.close()
        rows.reverse()  # chronological order
        conversation_history = [
            {"role": "user", "content": r.message, "role2": "assistant", "content2": r.response}
            for r in rows
        ]
        logger.info(f"[{trace_id}] Loaded {len(conversation_history)} history turns for user {user_id}")
    except Exception as e:
        logger.warning(f"Could not load conversation history: {e}")

    logger.info(
        f"[{trace_id}] Chat request from user {user_id}: "
        f"{request.message[:80]}..."
    )

    try:
        # Load ticket context for AI awareness
        ticket_context = _load_ticket_context(user_id)

        initial_state: HRState = {
            "user_id": user_id,
            "message": request.message,
            "privacy_mode": normalize_privacy_mode(request.privacy_mode),
            "thread_id": thread_id,
            "intent": "",
            "confidence": 0.0,
            "emotion": "",
            "severity": "",
            "complaint_type": "",
            "response": "",
            "escalation_action": "",
            "conversation_history": conversation_history,
            "ticket_context": ticket_context,
            "trace_id": trace_id,
            "timestamp": timestamp,
            "agent_used": "",
            "metadata": {},
        }

        graph = _get_graph()
        result = await asyncio.wait_for(
            asyncio.to_thread(graph.invoke, initial_state),
            timeout=180,  # 3 minute max for complete graph run
        )

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

    except asyncio.TimeoutError:
        logger.error(f"[{trace_id}] Chat timed out after 180s")
        return ChatResponse(
            user_id=user_id,
            response="Sorry, the request took too long. The AI model may be under heavy load. Please try again in a moment.",
            trace_id=trace_id,
            metadata={"error": "timeout"},
        )

    except Exception as e:
        logger.error(f"[{trace_id}] Error processing chat: {e}")
        return ChatResponse(
            user_id=user_id,
            response="Something went wrong. Please try again later.",
            trace_id=trace_id,
            metadata={"error": str(e)},
        )
