from fastapi import APIRouter
from datetime import datetime
from sqlite import get_db
import logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)


router=APIRouter(prefix="/create-app")



@router.post("/")
def create_application(user_id:int,university_id:int,major_id:int):
    try:

        conn=get_db()
        cursor=conn.cursor()

        cursor.execute("""
    INSERT INTO applications (user_id,university_id,major_id,status)
    VALUES(?,?,?,'Draft')


    """,(user_id,university_id,major_id))
        app_id=cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "application_id":app_id,
            "status":"Draft"
        }
    except Exception as e:
        print(e)