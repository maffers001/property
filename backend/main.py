"""FastAPI app for property review frontend. Run from repo root: uvicorn backend.main:app --reload."""
import os
from pathlib import Path

# Ensure repo root is on path so property_pipeline can be imported
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in os.environ.get("PYTHONPATH", ""):
    import sys
    if _repo_root not in sys.path:
        sys.path.insert(0, str(_repo_root))

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.auth import verify_password, create_access_token, get_current_user


class LoginBody(BaseModel):
    password: str = ""

app = FastAPI(title="Property Review API", version="0.1.0")

# CORS: allow React dev (localhost) and production origin
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- Auth -----
@app.post("/api/auth/login")
def login(body: LoginBody):
    """Body: { "password": "..." }. Returns { "access_token": "..." } or 401."""
    password = (body.password or "").strip()
    if not password:
        raise HTTPException(status_code=401, detail="Password required")
    if not verify_password(password):
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"access_token": create_access_token(), "token_type": "bearer"}


# ----- Protected routes -----
@app.get("/api/me")
def me(user: dict = Depends(get_current_user)):
    return {"user": user.get("sub", "user")}


from backend.routers import draft, review_actions, reports, lists
app.include_router(draft.router)
app.include_router(review_actions.router)
app.include_router(reports.router)
app.include_router(lists.router)
