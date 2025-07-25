from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List
from sqlalchemy.orm import Session
import logging
from ..db import SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from .. import challenges_database, crud, models, schemas, ai_analyzer
from ..db import get_db
from ..auth import get_current_user
from ..enums import ChallengeStatus

router = APIRouter(
    prefix="/api/challenges",
    tags=["Wyzwania"]
)

@router.get("/challenges", response_model=List[schemas.Challenge], summary="Pobierz listę wszystkich wyzwań")
def get_all_challenges():
    """Zwraca 3 losowe wyzwania. Zapewnia poprawny Content-Type."""
    challenges = challenges_database.get_all_challenges()
    return JSONResponse(content=[challenge for challenge in challenges])

@router.get("/challenges/me", response_model=List[schemas.UserChallenge], summary="Pobierz moje wyzwania")
def get_my_challenges(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    user_challenges = crud.get_user_challenges(db, user_id=current_user.id)
    for uc in user_challenges:
        uc.challenge_info = challenges_database.get_challenge_by_id(uc.challenge_id)
    return user_challenges

@router.post("/challenges/{challenge_id}/join", response_model=schemas.UserChallenge, summary="Dołącz do wyzwania")
def join_challenge(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    challenge = challenges_database.get_challenge_by_id(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Wyzwanie nie zostało znalezione.")
    existing_challenge = crud.get_user_challenge(db, user_id=current_user.id, challenge_id=challenge_id)
    if existing_challenge and existing_challenge.status == ChallengeStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Już bierzesz udział w tym wyzwaniu.")
    return crud.create_user_challenge(db=db, user_id=current_user.id, challenge_id=challenge_id, duration_days=challenge['duration_days'])

async def verify_ended_challenges_task():
    logging.info("Starting independent background challenge verification task...")
    db = SessionLocal()
    try:
        challenges_to_verify = crud.get_active_challenges_to_verify(db)
        if not challenges_to_verify:
            logging.info("No challenges found to verify. Task finished.")
            return
        logging.info(f"Found {len(challenges_to_verify)} challenges to verify.")
        for user_challenge in challenges_to_verify:
            try:
                logging.info(f"Verifying challenge_id: {user_challenge.challenge_id} for user_id: {user_challenge.user_id}")
                challenge_info = challenges_database.get_challenge_by_id(user_challenge.challenge_id)
                if not challenge_info:
                    logging.warning(f"Could not find info for challenge_id: {user_challenge.challenge_id}. Skipping.")
                    continue
                logs = []
                if challenge_info['category'] == 'dieta':
                    meals = crud.get_meals_by_date_range(db, user_id=user_challenge.user_id, start_date=user_challenge.start_date, end_date=user_challenge.end_date)
                    logs = [entry.product_name for meal in meals for entry in meal.entries]
                elif challenge_info['category'] == 'aktywność':
                    workouts = crud.get_workouts_by_date_range(db, user_id=user_challenge.user_id, start_date=user_challenge.start_date, end_date=user_challenge.end_date)
                    logs = [w.name for w in workouts]
                is_completed = await ai_analyzer.verify_challenge_completion(challenge_title=challenge_info['title'], challenge_description=challenge_info['description'], user_logs=logs, category=challenge_info['category'])
                new_status = ChallengeStatus.COMPLETED if is_completed else ChallengeStatus.FAILED
                crud.update_user_challenge_status(db, user_challenge_id=user_challenge.id, status=new_status)
                logging.info(f"Challenge {user_challenge.id} for user {user_challenge.user_id} verified with status: {new_status.value}")
            except Exception as e:
                logging.error(f"Error verifying challenge {user_challenge.id}: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"A critical error occurred in the verification task: {e}", exc_info=True)
    finally:
        db.close()
    logging.info("Challenge verification task finished.")

@router.post("/challenges/verify", summary="Uruchom weryfikację zakończonych wyzwań", status_code=202)
def trigger_verification(background_tasks: BackgroundTasks):
    background_tasks.add_task(verify_ended_challenges_task)
    return {"message": "Proces weryfikacji wyzwań został przyjęty i uruchomiony w tle."}
