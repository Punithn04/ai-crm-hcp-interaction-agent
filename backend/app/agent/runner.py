import uuid

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import GraphRecursionError
from sqlalchemy.orm import Session

from app.agent.graph import build_agent_graph

# In-memory per-thread state. Fine for a single-process demo; swap for a persistent
# checkpointer (e.g. LangGraph's Postgres/SQLite saver) for production use.
_THREAD_MESSAGES: dict[str, list] = {}
_THREAD_CTX: dict[str, dict] = {}

# Caps how many agent<->tool round trips a single turn may take. A well-behaved turn
# needs 2-4 (agent -> tool -> agent reply); this just stops a runaway loop from hanging.
RECURSION_LIMIT = 12


def run_chat_turn(db: Session, thread_id: str, user_message: str, hcp_id: uuid.UUID | None = None) -> dict:
    ctx = _THREAD_CTX.setdefault(thread_id, {"last_interaction_id": None, "hcp_id": hcp_id})
    if hcp_id is not None:
        ctx["hcp_id"] = hcp_id

    history = _THREAD_MESSAGES.setdefault(thread_id, [])
    history.append(HumanMessage(content=user_message))

    graph = build_agent_graph(db, ctx)
    try:
        result = graph.invoke({"messages": history}, {"recursion_limit": RECURSION_LIMIT})
        history[:] = result["messages"]
    except GraphRecursionError:
        history.append(
            AIMessage(
                content="I got stuck exploring follow-up actions on that one. "
                "The interaction may already be logged — check the form, or try rephrasing."
            )
        )

    last_ai = next((m for m in reversed(history) if isinstance(m, AIMessage)), None)
    reply = last_ai.content if last_ai else ""

    return {"reply": reply, "last_interaction_id": ctx.get("last_interaction_id")}
