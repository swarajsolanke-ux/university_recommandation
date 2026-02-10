from fastapi import APIRouter, Depends
from sqlite import get_db
from middleware.auth_middleware import require_admin
import sqlite3
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Legacy Admin"])

@router.get("/ai-weights")
def get_weights(db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(require_admin)):
    logger.info("fetched database weights from db")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM ai_weights ORDER BY updated_at DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        return {}
    return dict(row)
