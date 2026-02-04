from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from services.application_service import ApplicationService
from middleware.auth_middleware import require_admin
from sqlite import get_db
import sqlite3

router = APIRouter(prefix="/api/admin/applications", tags=["Admin Applications"])

@router.get("/")
def get_all_applications(
    status: Optional[str] = Query(None),
    university_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: dict = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db)
):
    
    try:
        cursor = db.cursor()
        
        # Build query
        query = """
            SELECT 
                a.id, a.user_id, a.status, a.application_date, a.last_updated,
                u.name as university_name, u.country,
                m.name as major_name,
                sp.full_name as student_name
            FROM applications a
            JOIN universities u ON a.university_id = u.id
            JOIN majors m ON a.major_id = m.id
            JOIN student_profiles sp ON a.user_id = sp.user_id
        """
        
        where_clauses = []
        params = []
        
        if status:
            where_clauses.append("a.status = ?")
            params.append(status)
            
        if university_id:
            where_clauses.append("a.university_id = ?")
            params.append(university_id)
            
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
      
        count_query = "SELECT COUNT(*) FROM (" + query + ")"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        
        query += " ORDER BY a.last_updated DESC LIMIT ? OFFSET ?"
        offset = (page - 1) * page_size
        params.extend([page_size, offset])
        
        cursor.execute(query, params)
        apps = cursor.fetchall()
        
        applications = []
        for row in apps:
            # Get document count
            cursor.execute("SELECT COUNT(*) FROM application_documents WHERE application_id = ?", (row[0],))
            doc_count = cursor.fetchone()[0]
            
            applications.append({
                "id": row[0],
                "user_id": row[1],
                "status": row[2],
                "application_date": row[3],
                "last_updated": row[4],
                "university_name": row[5],
                "country": row[6],
                "major_name": row[7],
                "student_name": row[8],
                "document_count": doc_count
            })
            
        return {
            "applications": applications,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{application_id}/status")
def update_status(
    application_id: int,
    status_update: dict,
    current_admin: dict = Depends(require_admin)
):
    """
    Update application status and add admin notes
    """
    new_status = status_update.get("status")
    admin_notes = status_update.get("admin_notes")
    
    if not new_status:
        raise HTTPException(status_code=400, detail="New status is required")
        
    result = ApplicationService.update_application_status(
        application_id=application_id,
        new_status=new_status,
        admin_notes=admin_notes
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@router.patch("/documents/{document_id}/verify")
def verify_document(
    document_id: int,
    verification: dict,
    current_admin: dict = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Verify or reject a document
    """
    is_verified = verification.get("is_verified", False)
    
    try:
        cursor = db.cursor()
        cursor.execute(
            "UPDATE application_documents SET is_verified = ? WHERE id = ?",
            (1 if is_verified else 0, document_id)
        )
        db.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Document not found")
            
        return {"success": True, "is_verified": is_verified}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
def get_dashboard_stats(current_admin: dict = Depends(require_admin), db: sqlite3.Connection = Depends(get_db)):
    """
    Get application statistics for admin dashboard
    """
    try:
        cursor = db.cursor()
        
        # Applications by status
        cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Recent applications (last 7 days)
        cursor.execute("SELECT COUNT(*) FROM applications WHERE application_date > date('now', '-7 days')")
        recent_count = cursor.fetchone()[0]
        
        # Total applications
        cursor.execute("SELECT COUNT(*) FROM applications")
        total_count = cursor.fetchone()[0]
        
        # Pending verification count
        cursor.execute("SELECT COUNT(*) FROM application_documents WHERE is_verified = 0")
        pending_verification = cursor.fetchone()[0]
        
        return {
            "total_applications": total_count,
            "status_distribution": status_counts,
            "recent_applications_7d": recent_count,
            "pending_verifications": pending_verification
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
