from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from .. import crud, models, schemas, ai_analyzer
from ..db import get_db
from ..auth import get_current_user

router = APIRouter(
    prefix="/api/workouts",
    tags=["Dziennik (Treningi)"]
)

@router.post("", response_model=schemas.Workout, summary="Dodaj nową aktywność fizyczną")
async def create_workout_entry(
    request: schemas.WorkoutCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """
    Analizuje opis treningu, szacuje spalone kalorie i zapisuje go w dzienniku.
    """
    if not current_user.weight:
        raise HTTPException(status_code=400, detail="Uzupełnij swoją wagę w profilu, aby oszacować spalone kalorie.")

    analysis = await ai_analyzer.analyze_workout(request.name, current_user.weight)
    
    # Używamy nazwy zwróconej przez AI, aby odrzucić nielogiczne treningi
    workout_data = schemas.WorkoutCreate(
        name=analysis['name'],
        calories_burned=analysis['calories_burned'],
        date=request.date
    )
    
    # Nie zapisuj treningu, jeśli AI go odrzuciło
    if workout_data.calories_burned == 0 and workout_data.name == "Nierozpoznana aktywność":
        raise HTTPException(status_code=400, detail="Podana aktywność nie jest rozpoznawana jako trening.")

    return crud.create_workout(db=db, workout=workout_data, user_id=current_user.id)


@router.get("", response_model=List[schemas.Workout], summary="Pobierz treningi z danego dnia")
def read_workouts(
    target_date: date, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Zwraca listę wszystkich treningów użytkownika z określonego dnia."""
    return crud.get_workouts_by_date_range(db=db, user_id=current_user.id, start_date=target_date, end_date=target_date)


@router.delete("/{workout_id}", status_code=204, summary="Usuń trening z dziennika")
def delete_workout_entry(
    workout_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Usuwa wpis o treningu z dziennika."""
    if not crud.delete_workout(db=db, workout_id=workout_id, user_id=current_user.id):
        raise HTTPException(status_code=404, detail="Trening nie znaleziony")
    return