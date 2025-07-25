# core/routers/auth_actions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import crud, models, schemas, security, email_utils, auth
from ..db import get_db

router = APIRouter(
    prefix="/api/auth",
    tags=["Akcje Uwierzytelniające"]
)

@router.post("/request-password-reset", status_code=202)
async def request_password_reset(
    request_data: schemas.PasswordResetRequest,
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, email=request_data.email)
    if user:
        token = security.create_access_token(data={"sub": user.email, "type": "reset"})
        crud.create_password_reset_token(db, user_id=user.id, token=token)
        reset_link = f"https://aikcal.app/reset-password?token={token}" # Użyj nowej domeny
        
        await email_utils.send_email(
            subject="AIKcal - Reset Hasła",
            recipients=[user.email],
            body=f"<p>Witaj {user.name or ''},</p><p>Aby zresetować hasło, kliknij w poniższy link:</p>"
                 f"<p><a href='{reset_link}'>{reset_link}</a></p>"
                 f"<p>Link jest ważny przez 1 godzinę.</p>"
        )
    return {"message": "Jeśli konto istnieje, e-mail z instrukcjami został wysłany."}

@router.post("/reset-password")
def reset_password(
    request_data: schemas.PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_password_reset_token(db, token=request_data.token)
    if not user:
        raise HTTPException(status_code=400, detail="Nieprawidłowy lub nieważny token.")
    
    hashed_password = security.get_password_hash(request_data.new_password)
    user.hashed_password = hashed_password
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()
    return {"message": "Hasło zostało pomyślnie zmienione."}

# Tutaj w przyszłości dodamy endpointy do weryfikacji e-mail