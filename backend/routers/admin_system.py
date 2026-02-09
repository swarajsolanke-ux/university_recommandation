from fastapi import APIRouter, HTTPException, Depends, Form, Body
from typing import List, Optional, Dict
from middleware.auth_middleware import require_admin
from sqlite import get_db
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/system", tags=["Admin System"])

@router.get("/stats")
def get_dashboard_stats(db: sqlite3.Connection = Depends(require_admin)):
    """Fetch high-level system statistics for admin dashboard"""
    user, conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    # Applications
    cursor.execute("SELECT COUNT(*) FROM applications")
    stats["total_applications"] = cursor.fetchone()[0]
    
    # Revenue
    cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'Completed'")
    stats["total_revenue"] = cursor.fetchone()[0] or 0
    
    # Students
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0")
    stats["total_students"] = cursor.fetchone()[0]
    
    # Active Partners
    cursor.execute("SELECT COUNT(*) FROM partners WHERE is_active = 1")
    stats["active_partners"] = cursor.fetchone()[0]
    
    return stats

@router.get("/ai-settings")
def get_ai_settings(db: sqlite3.Connection = Depends(require_admin)):
    """Fetch current AI weights and settings"""
    user, conn = db
    cursor = conn.cursor()
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
    db: sqlite3.Connection = Depends(require_admin)
):
    """Update AI performance weights"""
    user, conn = db
    try:
        cursor = conn.cursor()
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
        conn.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating AI settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payments/report")
def get_payment_report(db: sqlite3.Connection = Depends(require_admin)):
    """Get summarized payment reports"""
    user, conn = db
    cursor = conn.cursor()
    
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
def list_all_leads(db: sqlite3.Connection = Depends(require_admin)):
    """Fetch all service leads for administration"""
    user, conn = db
    cursor = conn.cursor()
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
