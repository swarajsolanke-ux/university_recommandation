from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from typing import List, Optional
from services.scholarship_service import ScholarshipService
from middleware.auth_middleware import get_current_active_user
from sqlite import get_db
import sqlite3
import os
import shutil
from config import settings

router = APIRouter(prefix="/api/scholarships", tags=["Scholarships"])

@router.get("/")
def list_scholarships(
    country: Optional[str] = Query(None),
    min_amount: Optional[int] = Query(None)
):
    scholarships = ScholarshipService.get_all_scholarships(country, min_amount)
    return {"scholarships": scholarships}

@router.get("/{scholarship_id}")
def get_scholarship(scholarship_id: int):
    """Get detailed scholarship information"""
    scholarship = ScholarshipService.get_scholarship_by_id(scholarship_id)
    if not scholarship:
        raise HTTPException(status_code=404, detail="Scholarship not found")
    return scholarship

@router.get("/{scholarship_id}/eligibility")
def check_eligibility(
    scholarship_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Check user's eligibility for a scholarship"""
    result = ScholarshipService.calculate_eligibility(current_user["user_id"], scholarship_id)
    return result

@router.post("/{scholarship_id}/apply")
def apply_scholarship(
    scholarship_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a draft scholarship application"""
    result = ScholarshipService.create_scholarship_application(current_user["user_id"], scholarship_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/{application_id}/upload")
async def upload_scholarship_doc(
    application_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """Upload documents for a scholarship application"""
    try:
        # Create directory if it doesn't exist
        upload_dir = os.path.join(settings.UPLOAD_DIR, "scholarship", str(application_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO scholarship_documents (scholarship_app_id, document_type, file_path, file_name)
            VALUES (?, ?, ?, ?)""",
            (application_id, document_type, f"/static/storage/scholarship/{application_id}/{file.filename}", file.filename)
        )
        db.commit()
        
        return {"success": True, "file_name": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/my-applications")
def list_my_applications(
    current_user: dict = Depends(get_current_active_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """List current user's scholarship applications"""
    cursor = db.cursor()
    cursor.execute(
        """SELECT sa.id, sa.status, sa.eligibility_score, sa.last_updated, s.name as scholarship_name
        FROM scholarship_applications sa
        JOIN scholarships s ON sa.scholarship_id = s.id
        WHERE sa.user_id = ?""",
        (current_user["user_id"],)
    )
    rows = cursor.fetchall()
    
    applications = []
    for row in rows:
        applications.append({
            "id": row[0],
            "status": row[1],
            "eligibility_score": row[2],
            "last_updated": row[3],
            "scholarship_name": row[4]
        })
        
    return {"applications": applications}
