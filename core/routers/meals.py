from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from .. import crud, models, schemas, auth
from ..db import get_db

router = APIRouter(
    prefix="/api", # Ten router ma ścieżki zdefiniowane w endpointach
    tags=["Dziennik (Posiłki i Woda)"],
    responses={404: {"description": "Not found"}},
)

# --- ENDPOINTY DLA POSIŁKÓW (MEALS) ---
# Ścieżka jest teraz zdefiniowana w dekoratorze
@router.post("/meals", response_model=schemas.Meal)
def create_meal(
    meal: schemas.MealCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Tworzy nowy kontener na posiłek (np. Śniadanie, Obiad) dla danego dnia."""
    return crud.create_user_meal(db=db, meal=meal, user_id=current_user.id)

@router.post("/meals/{meal_id}/entries", response_model=schemas.MealEntry)
def add_meal_entry(
    meal_id: int,
    entry: schemas.MealEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Dodaje pojedynczy wpis (produkt) do istniejącego posiłku."""
    db_meal = db.query(models.Meal).filter(models.Meal.id == meal_id, models.Meal.owner_id == current_user.id).first()
    if not db_meal:
        raise HTTPException(status_code=404, detail="Posiłek nie został znaleziony lub nie należy do Ciebie.")
    return crud.add_entry_to_meal(db=db, entry=entry, meal_id=meal_id)

@router.get("/meals", response_model=List[schemas.Meal])
def read_meals(
    date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Pobiera wszystkie posiłki użytkownika z określonego dnia."""
    return crud.get_meals_by_date(db=db, user_id=current_user.id, target_date=date)

@router.delete("/meals/{meal_id}", status_code=204)
def delete_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Usuwa cały posiłek (np. całe śniadanie) wraz ze wszystkimi jego wpisami."""
    if not crud.delete_meal(db=db, meal_id=meal_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Posiłek nie został znaleziony.")
    return {"ok": True}

@router.put("/meals/entries/{entry_id}", response_model=schemas.MealEntry)
def update_meal_entry(
    entry_id: int,
    entry_update: schemas.MealEntryCreate, # Używamy schematu Create, bo zawiera wszystkie potrzebne pola
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Aktualizuje istniejący wpis w posiłku."""
    updated_entry = crud.update_meal_entry(db=db, entry_id=entry_id, user_id=current_user.id, entry_update=entry_update)
    if not updated_entry:
        raise HTTPException(status_code=404, detail="Wpis posiłku nie został znaleziony lub nie masz do niego uprawnień.")
    return updated_entry

@router.delete("/meals/entries/{entry_id}", status_code=204)
def delete_meal_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Usuwa pojedynczy wpis (produkt) z posiłku."""
    if not crud.delete_meal_entry(db=db, entry_id=entry_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Wpis posiłku nie został znaleziony.")
    return {"ok": True}

# --- NOWE, BRAKUJĄCE ENDPOINTY DLA WODY (WATER) ---
@router.post("/water", response_model=schemas.WaterEntry)
def add_water(
    water_entry: schemas.WaterEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Dodaje wpis o spożyciu wody."""
    return crud.add_water_entry(db=db, water_entry=water_entry, user_id=current_user.id)

@router.delete("/water/{entry_id}", status_code=204)
def delete_water(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Usuwa wpis o spożyciu wody."""
    if not crud.delete_water_entry(db=db, water_entry_id=entry_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Wpis wody nie został znaleziony.")
    return {"ok": True}
