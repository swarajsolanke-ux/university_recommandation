from fastapi import APIRouter, HTTPException, Depends, Form, Body
from typing import List, Optional, Dict
from middleware.auth_middleware import require_admin
from sqlite import get_db
import sqlite3
import logging
from datetime import datetime
from logger import logger
from models.university import UniversityUpdate,UniversityBase
from models.scholarship import ScholarshipCreate, ScholarshipUpdate

router = APIRouter(prefix="/api/admin/system", tags=["Admin System"])

@router.get("/stats")
def get_dashboard_stats(current_user:dict=Depends(require_admin),db: sqlite3.Connection = Depends(get_db)):
    """Fetch high-level system statistics for admin dashboard"""
    cursor = db.cursor()
    
    stats = {}
    
    # Applications
    cursor.execute("SELECT COUNT(*) FROM applications")
    stats["total_applications"] = cursor.fetchone()[0]
    logger.info("total applications fetched sucessfully")
    
    # Revenue
    cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'Completed'")
    stats["total_revenue"] = cursor.fetchone()[0] or 0
    print(f"total revenue fetched : {stats['total_revenue']}")
    
    # Students
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0")
    stats["total_students"] = cursor.fetchone()[0]
    
    # Active Partners
    cursor.execute("SELECT COUNT(*) FROM partners WHERE is_active = 1")
    stats["active_partners"] = cursor.fetchone()[0]
    
    print("stats fetched sucessfully")
    cursor.close()
    return stats

@router.get("/ai-settings")
def get_ai_settings(db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Fetch current AI weights and settings"""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM ai_weights ORDER BY updated_at DESC LIMIT 1")
    row = cursor.fetchone()
    
    if not row:
        return {
            "gpa_weight": 0.3,
            "budget_weight": 0.25,
            "assessment_weight": 0.45
        }
        
    return {
        "acceptance_rate_weight": row[1],
        "scholarship_weight": row[2],
        "success_history_weight": row[3],
        "feedback_weight": row[4],
        "gpa_weight": row[5],
        "budget_weight": row[6],
        "assessment_weight": row[7]
    }

@router.post("/ai-settings")
def update_ai_settings(
    settings: Dict = Body(...),
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update AI performance weights"""
    try:
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO ai_weights 
            (acceptance_rate_weight, scholarship_weight, success_history_weight, feedback_weight, gpa_weight, budget_weight, assessment_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                settings.get("acceptance_rate_weight", 0.3),
                settings.get("scholarship_weight", 0.4),
                settings.get("success_history_weight", 0.2),
                settings.get("feedback_weight", 0.1),
                settings.get("gpa_weight", 0.3),
                settings.get("budget_weight", 0.25),
                settings.get("assessment_weight", 0.45)
            )
        )
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating AI settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payments/report")
def get_payment_report(db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Get summarized payment reports"""
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT p.id, u.email, f.feature_name, p.amount, p.payment_method, p.status, p.completed_at
        FROM payments p
        JOIN users u ON p.user_id = u.id
        JOIN premium_features f ON p.feature_id = f.id
        ORDER BY p.completed_at DESC
    """)
    rows = cursor.fetchall()
    
    reports = []
    for row in rows:
        reports.append({
            "id": row[0],
            "student_email": row[1],
            "feature": row[2],
            "amount": row[3],
            "method": row[4],
            "status": row[5],
            "date": row[6]
        })
    return {"reports": reports}

@router.get("/leads")
def list_all_leads(db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Fetch all service leads for administration"""
    cursor = db.cursor()
    cursor.execute("""
        SELECT l.id, l.student_name, l.student_email, l.student_phone, l.status, l.created_at, 
               p.name as partner_name, o.title as offer_title
        FROM service_leads l
        JOIN partners p ON l.partner_id = p.id
        JOIN service_offers o ON l.offer_id = o.id
        ORDER BY l.created_at DESC
    """)
    rows = cursor.fetchall()
    
    leads = []
    for row in rows:
        leads.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "phone": row[3],
            "status": row[4],
            "date": row[5],
            "partner": row[6],
            "offer": row[7]
        })
        
    return {"leads": leads}

# ================= University Management =================

@router.get("/universities")
def list_universities(db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Fetch all universities for administration"""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM universities ORDER BY id DESC")
    rows = cursor.fetchall()
    
    universities = []
    for row in rows:
        universities.append(dict(row))
    return {"universities": universities}

@router.post("/universities")
def create_university(university: UniversityBase, db: sqlite3.Connection = Depends(get_db),current_user:dict=Depends(require_admin)):
    """Create a new university record"""
    # user, conn = db
    try:
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO universities 
            (name, country, city, tuition_fee, min_gpa, language, scholarship_available, 
         overview, duration, accommodation_info, website, ranking, acceptance_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                university.name, university.country, university.city, university.tuition_fee,
                university.min_gpa, university.language, 1 if university.scholarship_available else 0,
                 university.overview, university.duration,
                university.accommodation_info, university.website, university.ranking, university.acceptance_rate
            )
        )
        db.commit()
        return {"success": True, "id": cursor.lastrowid}
    except Exception as e:
        logger.error(f"Error creating university: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/universities/{uni_id}")
def update_university(uni_id: int, university: UniversityUpdate, db: sqlite3.Connection = Depends(get_db),current_user:dict=Depends(require_admin)):
    """Update an existing university record"""
   
    try:
        cursor = db.cursor()
        # Dynamically build UPDATE query
        update_data = university.model_dump(exclude_unset=True)
        if not update_data:
            return {"success": True}
        
        fields = []
        values = []
        for k, v in update_data.items():
            fields.append(f"{k} = ?")
            if k == "scholarship_available" or k == "is_active":
                values.append(1 if v else 0)
            else:
                values.append(v)
        
        values.append(uni_id)
        query = f"UPDATE universities SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, values)
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating university: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/universities/{uni_id}")
def delete_university(uni_id: int, db: sqlite3.Connection = Depends(get_db),current_user:dict=Depends(require_admin)):
    """Soft delete (toggle active) a university"""
    
    try:
        cursor = db.cursor()
        cursor.execute("UPDATE universities SET is_active = 1 - is_active WHERE id = ?", (uni_id,))
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting university: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    


# ================= Scholarship Management =================

@router.get("/scholarships")
def list_scholarships(db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Fetch all scholarships for administration"""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM scholarships ORDER BY id DESC")
    rows = cursor.fetchall()
    
    scholarships = []
    for row in rows:
        scholarships.append(dict(row))
    return {"scholarships": scholarships}

@router.post("/scholarships")
def create_scholarship(scholarship: ScholarshipCreate, db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Create a new scholarship record"""
    try:
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO scholarships 
            (name, country, provider, min_gpa, max_age, nationality_requirement, 
             coverage, amount, deadline, description, required_documents, website)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                scholarship.name, scholarship.country, scholarship.provider, scholarship.min_gpa,
                scholarship.max_age, scholarship.nationality_requirement, scholarship.coverage,
                scholarship.amount, scholarship.deadline, scholarship.description,
                scholarship.required_documents, scholarship.website
            )
        )
        db.commit()
        return {"success": True, "id": cursor.lastrowid}
    except Exception as e:
        logger.error(f"Error creating scholarship: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/scholarships/{sch_id}")
def update_scholarship(sch_id: int, scholarship: ScholarshipUpdate, db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Update an existing scholarship record"""
    try:
        cursor = db.cursor()
        update_data = scholarship.model_dump(exclude_unset=True)
        if not update_data:
            return {"success": True}
        
        fields = []
        values = []
        for k, v in update_data.items():
            fields.append(f"{k} = ?")
            if k == "is_active":
                values.append(1 if v else 0)
            else:
                values.append(v)
        
        values.append(sch_id)
        query = f"UPDATE scholarships SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, values)
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating scholarship: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/scholarships/{sch_id}")
def delete_scholarship(sch_id: int, db: sqlite3.Connection = Depends(get_db), current_user: dict = Depends(require_admin)):
    """Soft delete (toggle active) a scholarship"""
    try:
        cursor = db.cursor()
        cursor.execute("UPDATE scholarships SET is_active = 1 - is_active WHERE id = ?", (sch_id,))
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting scholarship: {e}")
        raise HTTPException(status_code=500, detail=str(e))
