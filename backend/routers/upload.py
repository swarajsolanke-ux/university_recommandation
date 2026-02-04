# upload.py - Part of routers module
from fastapi import APIRouter, UploadFile,File
from config import settings
import shutil, os
from sqlite import get_db
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)
router = APIRouter(prefix="/upload")

# @router.post("/pdf-upload")
# def upload(file: UploadFile=File(...)):
#     path = os.path.join(Settings.UPLOAD_DIR, file.filename)
#     with open(path, "wb") as f:
#         shutil.copyfileobj(file.file, f)
#     print(file.filename)
#     return {"filename": file.filename,     
#         "uploaded_date": datetime.now().strftime("%d-%m-%Y"),
#         "status": "in-progress" }


@router.post("/pdf-upload")
def upload(application_id:int, document_type:str,file: UploadFile=File(...)):
    file_path=os.path.join(settings.UPLOAD_DIR, file.filename)
    print(f"file_path:{file_path}")
    with open(file_path,"wb") as f:
        shutil.copyfileobj(file.file,f)
    print("execute")
    try:
        conn=get_db()
        cursor=conn.cursor()
        print(cursor)
        cursor.execute("""
    INSERT INTO application_documents(application_id,document_type,file_path,file_name)
    VALUES(?,?,?,?)
    """,(application_id,document_type,file_path,file.filename)
        )
        
       
        conn.commit()
        conn.close()
        logger.info(f"file is stored sucessfully :{file.filename}")
        return {

            "filename":file.filename,
            "uploaded_date":datetime.now().strftime("%d/%m/%Y"),
            "status":"pending"
        }
    
    except Exception as e:
        logger.error(e)