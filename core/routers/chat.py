from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas, ai_analyzer
from ..db import get_db
from ..auth import get_current_user

router = APIRouter(
    prefix="/api/chat",
    tags=["AI Trener (Czat)"]
)

@router.get("/conversations", response_model=List[schemas.ConversationInfo])
def get_user_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Pobiera listę wszystkich konwersacji użytkownika."""
    return crud.get_user_conversations(db, user_id=current_user.id)

@router.post("/conversations", response_model=schemas.Conversation)
def create_new_conversation(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Tworzy nowy, pusty wątek rozmowy."""
    return crud.create_conversation(db, user_id=current_user.id)

@router.get("/conversations/{conversation_id}", response_model=schemas.Conversation)
def get_conversation_details(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Pobiera jedną, konkretną konwersację wraz z całą historią wiadomości."""
    conversation = crud.get_conversation_by_id(db, conversation_id=conversation_id, user_id=current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Konwersacja nie została znaleziona.")
    return conversation

@router.post("/conversations/{conversation_id}/messages", response_model=schemas.ChatMessage)
async def send_message_to_conversation(
    conversation_id: int,
    request: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Wysyła nową wiadomość do istniejącej konwersacji i zwraca odpowiedź AI."""
    conversation = crud.get_conversation_by_id(db, conversation_id=conversation_id, user_id=current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Konwersacja nie została znaleziona.")

    # 1. Zapisz wiadomość od użytkownika w bazie
    crud.add_message_to_conversation(db, conversation_id=conversation.id, role="user", content=request.message)

    # 2. Uzyskaj odpowiedź od AI, przekazując cały obiekt konwersacji
    response_text = await ai_analyzer.get_chat_response(db, current_user, conversation, request.message)

    # 3. Zapisz odpowiedź AI w bazie
    ai_message = crud.add_message_to_conversation(db, conversation_id=conversation.id, role="ai", content=response_text)

    return ai_message

@router.post("/conversations/{conversation_id}/pin", response_model=schemas.ConversationInfo)
def toggle_pin_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Przypina lub odpina wybraną konwersację."""
    conversation = crud.get_conversation_by_id(db, conversation_id=conversation_id, user_id=current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Konwersacja nie została znaleziona.")
    
    conversation.is_pinned = not conversation.is_pinned
    db.commit()
    db.refresh(conversation)
    return conversation

@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Usuwa całą konwersację."""
    conversation = crud.get_conversation_by_id(db, conversation_id=conversation_id, user_id=current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Konwersacja nie została znaleziona.")
    
    db.delete(conversation)
    db.commit()
    return