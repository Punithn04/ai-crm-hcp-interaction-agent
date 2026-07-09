from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.runner import run_chat_turn
from app.database import get_db
from app.schemas.interaction import ChatRequest, ChatResponse
from app.services import interactions as interaction_svc

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    result = run_chat_turn(db, payload.thread_id, payload.message, payload.hcp_id)

    interaction = None
    if result["last_interaction_id"] is not None:
        interaction = interaction_svc.get_interaction(db, result["last_interaction_id"])

    return ChatResponse(reply=result["reply"], interaction=interaction)
