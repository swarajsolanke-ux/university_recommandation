from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import Optional, List
from services.application_service import ApplicationService
from services.notification_service import get_user_notifications, get_unread_count, mark_notification_read, mark_all_read
from sqlite import get_db
from config import settings
import os
import shutil
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/applications", tags=["Applications"])


# ============= Request/Response Models =============

class ApplicationCreateRequest(BaseModel):
    user_id: int
    university_id: int
    major_id: int
    notes: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    status: str
    admin_notes: Optional[str] = None


# ============= Application Endpoints =============

@router.post("/create")
def create_application(request: ApplicationCreateRequest):
    """Create a new application in Draft status"""
    result = ApplicationService.create_application(
        user_id=request.user_id,
        university_id=request.university_id,
        major_id=request.major_id,
        notes=request.notes
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/{application_id}")
def get_application(application_id: int):
    """Get detailed information about an application"""
    result = ApplicationService.get_application_details(application_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return result


@router.get("/user/{user_id}")
def get_user_applications(user_id: int, status: Optional[str] = None):
    """Get all applications for a user, optionally filtered by status"""
    applications = ApplicationService.get_user_applications(user_id, status)
    
    # Get status counts
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status, COUNT(*) 
        FROM applications 
        WHERE user_id = ? 
        GROUP BY status
    """, (user_id,))
    
    status_counts = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    
    return {
        "applications": applications,
        "total_count": len(applications),
        "status_counts": status_counts
    }


@router.post("/{application_id}/upload")
async def upload_document(
    application_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a document for an application"""
    
    # Validate application exists
    app_details = ApplicationService.get_application_details(application_id)
    if not app_details:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Validate file type (only PDFs for now)
    if not file.filename.endswith('.pdf'):
        logger.warning("kindly upload pdf only")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Create upload directory if it doesn't exist
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{application_id}_{document_type}_{timestamp}_{file.filename}"
        logger.info("unique name generated from the model")
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Save to database
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO application_documents (application_id, document_type, file_path, file_name)
            VALUES (?, ?, ?, ?)
        """, (application_id, document_type, file_path, filename))
        
        doc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Document uploaded: {filename} for application {application_id}")
        
        return {
            "success": True,
            "document_id": doc_id,
            "filename": filename,
            "document_type": document_type,
            "uploaded_at": datetime.now().isoformat(),
            "status": "uploaded"
        }
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/{application_id}/submit")
def submit_application(application_id: int):
    """Submit an application (change status from Draft to Submitted)"""
    result = ApplicationService.submit_application(application_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.patch("/{application_id}/status")
def update_application_status(application_id: int, update: ApplicationStatusUpdate):
    """Update application status (Admin only)"""
    result = ApplicationService.update_application_status(
        application_id=application_id,
        new_status=update.status,
        admin_notes=update.admin_notes
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result





@router.delete("/{application_id}")
def delete_application(application_id: int, user_id: int):
    """Delete a draft application"""
    result = ApplicationService.delete_application(application_id, user_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result





# ============= Notification Endpoints =============

@router.get("/notifications/{user_id}")
def get_notifications(user_id: int, unread_only: bool = False):
    """Get notifications for a user"""
    conn = get_db()
    
    is_read = None if not unread_only else False
    notifications = get_user_notifications(conn, user_id, is_read=is_read)
    unread_count = get_unread_count(conn, user_id)
    
    conn.close()
    
    return {
        "notifications": notifications,
        "unread_count": unread_count
    }






@router.post("/notifications/{notification_id}/read")
def mark_notification_as_read(notification_id: int, user_id: int):
    """Mark a notification as read"""
    conn = get_db()
    success = mark_notification_read(conn, notification_id, user_id)
    conn.close()
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True}



@router.post("/notifications/user/{user_id}/read-all")
def mark_all_notifications_read(user_id: int):
    """Mark all notifications as read for a user"""
    conn = get_db()
    count = mark_all_read(conn, user_id)
    conn.close()
    
    return {
        "success": True,
        "marked_count": count
    }




# ============= Helper Endpoints =============

@router.get("/requirements/{university_id}/{major_id}")
def get_application_requirements(university_id: int, major_id: int):
    """Get required documents and requirements for a university/major combination"""
    
    # Standard required documents
    required_documents = [
        {
            "type": "transcript",
            "name": "Academic Transcript",
            "description": "Official academic records",
            "required": True
        },
        {
            "type": "sop",
            "name": "Statement of Purpose",
            "description": "Personal statement explaining your motivation",
            "required": True
        },
        {
            "type": "lor",
            "name": "Letter of Recommendation",
            "description": "Recommendation letter from professor or employer",
            "required": True
        },
        {
            "type": "resume",
            "name": "Resume/CV",
            "description": "Your curriculum vitae",
            "required": False
        },
        {
            "type": "passport",
            "name": "Passport Copy",
            "description": "Valid passport identification",
            "required": True
        }
    ]
    
    return {
        "university_id": university_id,
        "major_id": major_id,
        "required_documents": required_documents,
        "additional_info": "Please ensure all documents are in PDF format and clearly legible."
    }
