from fastapi import APIRouter, HTTPException, Depends, Query, Form
from typing import List, Optional, Dict
from middleware.auth_middleware import get_current_active_user
from sqlite import get_db
import sqlite3
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/services", tags=["Student Services"])

@router.get("/offers")
def get_offers(
    category: Optional[str] = Query(None),
    db: sqlite3.Connection = Depends(get_db)
):
    """Fetch all active partner offers"""
    cursor = db.cursor()
    query = """
        SELECT o.id, o.title, o.description, o.discount_percentage, o.image_url, 
               p.name as partner_name, p.category, p.logo_url
        FROM service_offers o
        JOIN partners p ON o.partner_id = p.id
        WHERE o.is_active = 1 AND p.is_active = 1
    """
    params = []
    if category:
        query += " AND p.category = ?"
        params.append(category)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    offers = []
    for row in rows:
        offers.append({
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "discount": row[3],
            "image": row[4],
            "partner_name": row[5],
            "category": row[6],
            "partner_logo": row[7]
        })
    return {"offers": offers}

@router.post("/lead")
def create_lead(
    offer_id: int = Form(...),
    student_name: str = Form(...),
    student_email: str = Form(...),
    student_phone: str = Form(...),
    message: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_active_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """Capture a student lead for a partner offer"""
    try:
        cursor = db.cursor()
        
        # Get partner_id from offer
        cursor.execute("SELECT partner_id FROM service_offers WHERE id = ?", (offer_id,))
        partner_result = cursor.fetchone()
        if not partner_result:
            raise HTTPException(status_code=404, detail="Offer not found")
        partner_id = partner_result[0]
        
        cursor.execute(
            """INSERT INTO service_leads (user_id, partner_id, offer_id, student_name, student_email, student_phone, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (current_user["user_id"], partner_id, offer_id, student_name, student_email, student_phone, message)
        )
        db.commit()
        
        return {"success": True, "message": "Your interest has been shared with our partner!"}
    except Exception as e:
        logger.error(f"Error creating lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-leads")
def get_my_leads(
    current_user: dict = Depends(get_current_active_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """Get list of services the student has shown interest in"""
    cursor = db.cursor()
    cursor.execute(
        """SELECT l.id, l.status, l.created_at, o.title, p.name as partner_name, p.category
        FROM service_leads l
        JOIN service_offers o ON l.offer_id = o.id
        JOIN partners p ON l.partner_id = p.id
        WHERE l.user_id = ?""",
        (current_user["user_id"],)
    )
    rows = cursor.fetchall()
    
    leads = []
    for row in rows:
        leads.append({
            "id": row[0],
            "status": row[1],
            "date": row[2],
            "offer_title": row[3],
            "partner": row[4],
            "category": row[5]
        })
    return {"leads": leads}
