from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from .. import crud, models, schemas, ai_analyzer, security, utils
from ..db import get_db
from ..auth import get_current_user

router = APIRouter(
    prefix="/api/users",
    tags=["Użytkownicy i Autoryzacja"]
)

# --- Endpointy Autoryzacji ---
@router.post("/register", response_model=schemas.User, summary="Rejestracja nowego użytkownika")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Użytkownik o tym adresie e-mail już istnieje.")
    return crud.create_user(db=db, user=user)

@router.post("/login", response_model=schemas.Token, summary="Logowanie i uzyskanie tokenu")
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not user.hashed_password or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy e-mail lub hasło.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Endpointy Zarządzania Użytkownikiem ---

@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """Pobiera dane zalogowanego użytkownika."""
    # Logika daty celu została przeniesiona do frontendu, ale możemy ją tu zostawić
    # jako pole obliczeniowe na backendzie dla spójności.
    current_user.goal_achievement_date = utils.calculate_goal_achievement_date(current_user)
    return current_user

@router.put("/me", response_model=schemas.User)
def update_user_me(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Aktualizuje profil zalogowanego użytkownika."""
    return crud.update_user(db=db, db_user=current_user, user_update=user_update)

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_me(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Usuwa konto zalogowanego użytkownika."""
    if not crud.delete_user(db, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Użytkownik nie został znaleziony.")
    return

# --- Endpoint do sugestii celów przez AI ---

@router.post("/suggest-goals", response_model=schemas.MacroSuggestion, tags=["Analiza AI i Sugestie"])
async def suggest_goals_endpoint(request: schemas.GoalSuggestionRequest):
    """Sugeruje kalorie i makroskładniki na podstawie danych użytkownika."""
    return await ai_analyzer.suggest_tdee_and_macros(request)