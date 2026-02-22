"""Settings: add custom property/category/subcategory."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from property_pipeline.db import get_db
from property_pipeline.config import DB_PATH

from backend.auth import get_current_user

router = APIRouter(prefix="/api", tags=["lists"])


class AddListBody(BaseModel):
    value: str


@router.post("/lists/property")
def add_property(body: AddListBody, user: dict = Depends(get_current_user)):
    v = (body.value or "").strip()
    if not v:
        raise HTTPException(status_code=400, detail="Value required")
    with get_db(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO custom_list_entries (list_type, value) VALUES ('property', ?)",
            (v,),
        )
    return {"ok": True, "value": v}


@router.post("/lists/category")
def add_category(body: AddListBody, user: dict = Depends(get_current_user)):
    v = (body.value or "").strip()
    if not v:
        raise HTTPException(status_code=400, detail="Value required")
    with get_db(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO custom_list_entries (list_type, value) VALUES ('category', ?)",
            (v,),
        )
    return {"ok": True, "value": v}


@router.post("/lists/subcategory")
def add_subcategory(body: AddListBody, user: dict = Depends(get_current_user)):
    v = (body.value or "").strip()
    if not v:
        raise HTTPException(status_code=400, detail="Value required")
    with get_db(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO custom_list_entries (list_type, value) VALUES ('subcategory', ?)",
            (v,),
        )
    return {"ok": True, "value": v}
