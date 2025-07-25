from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas, challenges_database
from ..db import get_db
from ..auth import get_current_user
from ..enums import FriendshipStatus

router = APIRouter(
    prefix="/api/social",
    tags=["Społeczność"]
)

@router.get("/users/search", response_model=List[schemas.FriendInfo], summary="Wyszukaj użytkowników po e-mailu")
def search_users(
    email: str = Query(..., min_length=3, description="Fragment adresu e-mail użytkownika (min. 3 znaki)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not current_user.is_social_profile_active:
        raise HTTPException(status_code=403, detail="Twój profil społecznościowy jest nieaktywny.")
        
    found_users = crud.search_users_by_email(db, email_query=email, current_user_id=current_user.id)
    
    results = []
    for user in found_users:
        friendship = crud.get_friendship(db, user_id=current_user.id, friend_id=user.id)
        completed_challenges_db = crud.get_recently_completed_challenges_for_user(db, user_id=user.id)
        
        badges = []
        for c in completed_challenges_db:
            challenge_info = challenges_database.get_challenge_by_id(c.challenge_id)
            if challenge_info:
                badges.append(schemas.CompletedChallengeBadge(
                    title=challenge_info['title'],
                    end_date=c.end_date
                ))

        friend_info = schemas.FriendInfo(
            id=user.id, name=user.name, email=user.email,
            friendship_status=friendship.status if friendship else None,
            completed_challenges=badges
        )
        results.append(friend_info)
        
    return results

@router.post("/friends/request", response_model=schemas.Friendship, summary="Wyślij zaproszenie do znajomych")
def send_friend_request(
    friend_request: schemas.FriendshipCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if friend_request.friend_id == current_user.id:
        raise HTTPException(status_code=400, detail="Nie możesz wysłać zaproszenia do samego siebie.")

    friend_user = crud.get_user_by_id(db, user_id=friend_request.friend_id)
    if not friend_user or not friend_user.is_social_profile_active:
        raise HTTPException(status_code=404, detail="Użytkownik nie został znaleziony lub ma nieaktywny profil.")

    existing_friendship = crud.get_friendship(db, user_id=current_user.id, friend_id=friend_request.friend_id)
    if existing_friendship:
        raise HTTPException(status_code=400, detail=f"Istnieje już relacja z tym użytkownikiem (status: {existing_friendship.status.value}).")

    return crud.send_friend_request(db=db, user_id=current_user.id, friend_id=friend_request.friend_id)

@router.get("/friends/requests", response_model=List[schemas.FriendRequestWithUserInfo], summary="Pobierz oczekujące zaproszenia")
def get_pending_friend_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    pending_requests = crud.get_friend_requests(db, user_id=current_user.id)
    results = []
    for req in pending_requests:
        sender_info = crud.get_user_by_id(db, user_id=req.user_id)
        if sender_info:
            response_item = schemas.FriendRequestWithUserInfo(
                id=req.id, user_id=req.user_id, friend_id=req.friend_id,
                status=req.status, created_at=req.created_at,
                user_info=schemas.UserPublic.model_validate(sender_info)
            )
            results.append(response_item)
    return results

@router.post("/friends/requests/{friendship_id}/respond", response_model=schemas.Friendship, summary="Odpowiedz na zaproszenie")
def respond_to_friend_request(
    friendship_id: int,
    status: FriendshipStatus = Query(..., enum=[FriendshipStatus.ACCEPTED, FriendshipStatus.DECLINED]),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_friendship = crud.get_friendship_by_id(db, friendship_id=friendship_id)
    if not db_friendship or db_friendship.friend_id != current_user.id or db_friendship.status != FriendshipStatus.PENDING:
        raise HTTPException(status_code=404, detail="Zaproszenie nie zostało znalezione lub nie jest już aktywne.")

    return crud.update_friendship_status(db=db, db_friendship=db_friendship, status=status)

@router.get("/friends", response_model=List[schemas.FriendWithBadges], summary="Pobierz listę znajomych")
def get_friends_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    friends = crud.get_friends_list(db, user_id=current_user.id)
    results_with_badges = []
    for friend in friends:
        completed_challenges_db = crud.get_recently_completed_challenges_for_user(db, user_id=friend.id)
        badges = [
            schemas.CompletedChallengeBadge(title=challenges_database.get_challenge_by_id(c.challenge_id)['title'], end_date=c.end_date)
            for c in completed_challenges_db if challenges_database.get_challenge_by_id(c.challenge_id)
        ]
        friend_with_badges = schemas.FriendWithBadges(
            id=friend.id, name=friend.name, email=friend.email, completed_challenges=badges
        )
        results_with_badges.append(friend_with_badges)
    return results_with_badges

@router.delete("/friends/{friend_id}", status_code=204, summary="Usuń znajomego")
def delete_friend(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_friendship = crud.get_friendship(db, user_id=current_user.id, friend_id=friend_id)
    if not db_friendship or db_friendship.status != FriendshipStatus.ACCEPTED:
        raise HTTPException(status_code=404, detail="Nie znaleziono aktywnej relacji z tym użytkownikiem.")
    crud.delete_friendship(db, db_friendship=db_friendship)
    return None