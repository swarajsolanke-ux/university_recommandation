from fastapi import APIRouter
from sqlite import get_db


router=APIRouter(prefix="/submit")

@router.post("/submit-app")
def submit_application(application_id:int):
    conn=get_db()
    cursor=conn.cursor()

    cursor.execute("""
UPDATE applications
SET status="Submitted",last_updated=CURRENT_TIMESTAMP WHERE id=? """,(application_id,))
    
    conn.commit()
    conn.close()

    return {
        "messages":"updated sucessfully"
    }