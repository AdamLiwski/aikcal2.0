from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os
from dotenv import load_dotenv

# ✅ Ładujemy zmienne środowiskowe z katalogu głównego aplikacji
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
print("Redirect URI:", os.getenv("GOOGLE_REDIRECT_URI"))

# 📦 Importy backendu i routerów
from .db import engine
from . import security, models
from .routers import users, meals, analysis, workouts, social, summary, chat, challenges, auth_google, auth_actions # dodaj auth_actions

# 🔧 Tworzenie tabel w bazie danych przy starcie
models.Base.metadata.create_all(bind=engine)

# 🚀 Inicjalizacja aplikacji FastAPI
app = FastAPI(
    title="AIKcal API",
    description="Backend dla inteligentnej aplikacji dietetycznej AIKcal.",
    version="1.0.0",
)

# 🧩 Middleware
app.add_middleware(SessionMiddleware, secret_key=security.SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API ROUTERY ---
# Każdy router jest dołączany bez globalnego prefiksu.
# Pełny prefiks (np. "/api/users") jest zdefiniowany wewnątrz każdego pliku routera.
app.include_router(users.router)
app.include_router(meals.router)
app.include_router(analysis.router)
app.include_router(workouts.router)
app.include_router(social.router)
app.include_router(summary.router)
app.include_router(chat.router)
app.include_router(challenges.router)
app.include_router(auth_google.router)
app.include_router(auth_actions.router)

# 🎨 Serwowanie frontendu z katalogu frontend/
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

if not frontend_dir.exists() or not (frontend_dir / "index.html").exists():
    print(f"BŁĄD: Katalog frontendu '{frontend_dir}' lub plik 'index.html' nie istnieje.")
else:
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/{full_path:path}", tags=["Frontend"], include_in_schema=False)
    async def serve_frontend(full_path: str):
        # 🛡️ Proste zabezpieczenie przed path traversal
        if ".." in full_path:
            return FileResponse(frontend_dir / "index.html")
        
        requested_path = frontend_dir / full_path
        
        # 📄 Jeśli plik istnieje, serwuj go
        if requested_path.is_file() and requested_path.exists():
            return FileResponse(requested_path)
        
        # 🔁 W przeciwnym razie serwuj index.html (dla SPA routingu)
        return FileResponse(frontend_dir / "index.html")
# --- DODAJ TEN FRAGMENT KODU NA SAMYM KOŃCU PLIKU main.py ---
#
# Funkcja do debugowania, która pokaże wszystkie zarejestrowane ścieżki
@app.get("/routes", tags=["Debug"], include_in_schema=False)
def list_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name if hasattr(route, "name") else "N/A"
            })
    return routes
# --- DODAJ TEN FRAGMENT KODU NA SAMYM KOŃCU PLIKU main.py ---

@app.on_event("startup")
async def startup_event():
    """
    Funkcja uruchamiana przy starcie serwera, która wypisze w konsoli
    wszystkie zarejestrowane ścieżki API.
    """
    print("--- ZAREJESTROWANE ŚCIEŻKI API (START) ---")
    for route in app.routes:
        if hasattr(route, "path"):
            methods = ",".join(route.methods) if hasattr(route, "methods") else ""
            print(f"Ścieżka: {route.path}\t Metody: [{methods}]\t Nazwa: {route.name}")
    print("--- ZAREJESTROWANE ŚCIEŻKI API (KONIEC) ---")