import os
import requests
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/api/auth",
    tags=["Uwierzytelnianie Google"]
)

@router.get("/api/auth/callback/google")
async def google_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error": "Brak kodu autoryzacyjnego"}, status_code=400)

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    token_json = token_resp.json()
    if "access_token" not in token_json:
        return JSONResponse({"error": "Token nieprawidłowy"}, status_code=400)

    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {token_json['access_token']}"}
    ).json()

    return JSONResponse({"user": user_info})
