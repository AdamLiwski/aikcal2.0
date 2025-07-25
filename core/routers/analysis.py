from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
import json
from typing import List

from .. import crud, models, schemas, ai_analyzer
from ..db import get_db
from ..auth import get_current_user

router = APIRouter(
    prefix="/api/analysis",
    tags=["Analiza AI i Sugestie"]
)

# --- GŁÓWNY ENDPOINT DO ANALIZY POSIŁKU ---
@router.post("/meal", response_model=schemas.AnalysisResponse)
async def analyze_meal_endpoint(
    request: schemas.AnalysisRequest,
):
    """
    Nowy, główny endpoint do analizy posiłku (tekst lub obraz).
    Uruchamia całą nową, wieloetapową logikę "Cache-First".
    """
    try:
        analysis_result = await ai_analyzer.analyze_meal_entry(
            text=request.text,
            image_base64=request.image_base64
        )
        if not analysis_result:
            raise HTTPException(status_code=400, detail="AI nie mogło przeanalizować tego produktu. Spróbuj opisać go inaczej.")
        return analysis_result
    except Exception as e:
        print(f"Błąd podczas analizy posiłku: {e}")
        raise HTTPException(status_code=500, detail=f"Wewnętrzny błąd serwera podczas analizy: {e}")

# --- ENDPOINTY DLA AI CHEFA ---
@router.get("/suggest-diet-plan", response_model=list[schemas.DietPlanSuggestion])
async def get_diet_plan_suggestion(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Generuje i zwraca nowy plan dietetyczny na podstawie preferencji użytkownika."""
    today = date.today()
    if current_user.last_request_date == today and current_user.diet_plan_requests >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Wykorzystano dzienny limit generowania planów. Wróć jutro!"
        )

    if current_user.last_request_date != today:
        current_user.diet_plan_requests = 0
        current_user.last_request_date = today

    macros = { "calorie_goal": current_user.calorie_goal, "protein_goal": current_user.protein_goal, "fat_goal": current_user.fat_goal, "carb_goal": current_user.carb_goal }
    plan = await ai_analyzer.suggest_diet_plan(current_user.preferences, macros)
    
    if not plan:
        raise HTTPException(status_code=500, detail="AI Chef nie mógł wygenerować planu.")
    
    current_user.diet_plan_requests += 1
    plan_json_string = json.dumps(plan, default=str)
    user_update = schemas.UserUpdate(last_diet_plan=plan_json_string)
    
    db.add(current_user)
    crud.update_user(db=db, db_user=current_user, user_update=user_update)
    
    return plan

# --- ENDPOINTY DLA ANALIZY TYGODNIOWEJ (pozostają bez zmian w logice) ---

@router.post("/generate", response_model=schemas.WeeklyAnalysisResponse)
async def generate_weekly_analysis_endpoint(
    request: schemas.AnalysisGenerateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Generuje analizę danych użytkownika dla podanego zakresu dat."""
    if current_user.last_analysis_generated_at and (datetime.now() - current_user.last_analysis_generated_at < timedelta(hours=24)):
        remaining_time = timedelta(hours=24) - (datetime.now() - current_user.last_analysis_generated_at)
        hours, rem = divmod(remaining_time.total_seconds(), 3600)
        minutes, _ = divmod(rem, 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Analiza może być generowana raz na 24 godziny. Spróbuj ponownie za {int(hours)}h {int(minutes)}min."
        )

    start_date, end_date = request.start_date, request.end_date
    meals = crud.get_meals_by_date_range(db, current_user.id, start_date, end_date)
    workouts = crud.get_workouts_by_date_range(db, current_user.id, start_date, end_date)
    weight_history = crud.get_weight_history_by_date_range(db, current_user.id, start_date, end_date)
    
    ai_coach_summary = await ai_analyzer.generate_weekly_analysis(
        {"meals": meals, "workouts": workouts, "weight_history": weight_history}, 
        user=current_user, start_date=start_date, end_date=end_date
    )

    analysis_data = schemas.WeeklyAnalysisResponse(ai_coach_summary=ai_coach_summary)
    user_update = schemas.UserUpdate(
        last_weekly_analysis=analysis_data.model_dump_json(),
        last_analysis_generated_at=datetime.now()
    )
    crud.update_user(db, db_user=current_user, user_update=user_update)
    return analysis_data

@router.get("/latest", response_model=schemas.WeeklyAnalysisResponse)
async def get_latest_weekly_analysis_endpoint(
    current_user: models.User = Depends(get_current_user)
):
    """Pobiera ostatnią zapisaną analizę z profilu użytkownika."""
    if not current_user.last_weekly_analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nie znaleziono żadnej analizy.")
    
    try:
        return schemas.WeeklyAnalysisResponse.model_validate_json(current_user.last_weekly_analysis)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Błąd wczytywania zapisanej analizy.")