from fastapi import APIRouter
from sqlite import get_db
import logger 
router = APIRouter(prefix="/admin")

@router.get("/ai-weights")
def get_weights():
    db = get_db()
    logger.info("fetched database weights from db")
    return dict(db.execute("SELECT * FROM ai_weights").fetchone())
