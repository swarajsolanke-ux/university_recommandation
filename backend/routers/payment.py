from fastapi import APIRouter, HTTPException, Depends, Form
from typing import List, Optional, Dict
from middleware.auth_middleware import get_current_active_user
from sqlite import get_db
import sqlite3
from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["Payments"])

@router.get("/features")
def get_premium_features(db: sqlite3.Connection = Depends(get_db)):
    """List all available premium features"""
    cursor = db.cursor()
    cursor.execute("SELECT id, feature_name, description, price, duration_days FROM premium_features WHERE is_active = 1")
    rows = cursor.fetchall()
    
    features = []
    for row in rows:
        features.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "duration": row[4]
        })
    return {"features": features}

@router.post("/checkout")
def create_payment(
    feature_id: int = Form(...),
    method: str = Form(...), # KNET, ApplePay, Card
    current_user: dict = Depends(get_current_active_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """Process a mock payment and activate the feature"""
    try:
        cursor = db.cursor()
        
        # Get feature details
        cursor.execute("SELECT feature_name, price, duration_days FROM premium_features WHERE id = ?", (feature_id,))
        feature = cursor.fetchone()
        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")
            
        name, price, duration = feature
        transaction_id = str(uuid.uuid4())
        
        # Create payment record
        cursor.execute(
            """INSERT INTO payments (user_id, feature_id, amount, payment_method, transaction_id, status, completed_at)
            VALUES (?, ?, ?, ?, ?, 'Completed', CURRENT_TIMESTAMP)""",
            (current_user["user_id"], feature_id, price, method, transaction_id)
        )
        
        # Activate premium status for user
        # In a real app, you might have a user_features table. 
        # For simplicity, we'll just update the is_premium flag in users table.
        cursor.execute("UPDATE users SET is_premium = 1 WHERE id = ?", (current_user["user_id"],))
        
        db.commit()
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "message": f"Successfully activated {name}!"
        }
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def get_premium_status(
    current_user: dict = Depends(get_current_active_user),
    db: sqlite3.Connection = Depends(get_db)
):
    """Check if the user has active premium status"""
    cursor = db.cursor()
    cursor.execute("SELECT is_premium FROM users WHERE id = ?", (current_user["user_id"],))
    is_premium = cursor.fetchone()[0]
    
    # Get last successful payment
    cursor.execute(
        """SELECT p.completed_at, f.feature_name 
        FROM payments p
        JOIN premium_features f ON p.feature_id = f.id
        WHERE p.user_id = ? AND p.status = 'Completed'
        ORDER BY p.completed_at DESC LIMIT 1""",
        (current_user["user_id"],)
    )
    last_payment = cursor.fetchone()
    
    return {
        "is_premium": bool(is_premium),
        "last_feature": last_payment[1] if last_payment else None,
        "active_since": last_payment[0] if last_payment else None
    }
