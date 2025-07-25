from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from typing import List

# Dodajemy import utils
from .. import crud, models, schemas, utils
from ..db import get_db
from ..auth import get_current_user

router = APIRouter(
    prefix="/api/summary",
    tags=["Podsumowanie Dnia"]
)

@router.get("/{target_date}", response_model=schemas.DailySummary)
def get_daily_summary(
    target_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Pobiera pełne podsumowanie danych z wybranego dnia."""
    meals = crud.get_meals_by_date(db, user_id=current_user.id, target_date=target_date)
    # Pobieramy treningi za pomocą nowej funkcji CRUD
    workouts = crud.get_workouts_by_date_range(db, user_id=current_user.id, start_date=target_date, end_date=target_date)
    # Pobieramy wpisy o wodzie za pomocą nowej funkcji CRUD
    water_entries = db.query(models.WaterEntry).filter(
        models.WaterEntry.owner_id == current_user.id, 
        func.date(models.WaterEntry.date) == target_date
    ).all()

    calories_consumed = sum(e.calories for m in meals for e in m.entries)
    calories_burned = sum(w.calories_burned for w in workouts)
    water_consumed = sum(w.amount for w in water_entries)
    
    effective_calorie_goal = current_user.calorie_goal or 0
    if current_user.add_workout_calories_to_goal:
        effective_calorie_goal += calories_burned

    # Obliczamy datę osiągnięcia celu
    goal_date = utils.calculate_goal_achievement_date(current_user)

    summary = schemas.DailySummary(
        date=target_date,
        calories_consumed=calories_consumed,
        protein_consumed=sum(e.protein for m in meals for e in m.entries),
        fat_consumed=sum(e.fat for m in meals for e in m.entries),
        carbs_consumed=sum(e.carbs for m in meals for e in m.entries),
        water_consumed=water_consumed,
        calories_burned=calories_burned,
        total_calories_burned_today=calories_burned,
        calorie_goal=effective_calorie_goal,
        protein_goal=current_user.protein_goal or 0,
        fat_goal=current_user.fat_goal or 0,
        carb_goal=current_user.carb_goal or 0,
        water_goal=current_user.water_goal or 0,
        meals=meals,
        water_entries=water_entries,
        workouts=workouts,
        goal_achievement_date=goal_date # Dodajemy datę do odpowiedzi
    )
    return summary