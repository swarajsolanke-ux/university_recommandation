from fastapi.responses import HTMLResponse
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from config import settings
from datetime import datetime
import sqlite3
from sqlite import get_db
from logger import logger 

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Validates JWT token and returns current user
    """
    if credentials is None:
        logger.warning("No authentication credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        logger.info(f"JWT payload decoded successfully for sub: {payload.get('sub')}")
        
        user_id: int = payload.get("sub")
        logger.info(f"extracted token for user_id:{user_id}")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if token is expired
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {"user_id": user_id, "email": payload.get("email")}
        
    except JWTError:
        logger.error("jwt decode error")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_active_user(current_user: dict = Depends(get_current_user),db: sqlite3.Connection = Depends(get_db)):
    """
    Validates that the current user is active
    """
   
    
    cursor = db.cursor()
    cursor.execute("SELECT is_active FROM users WHERE id = ?", (current_user["user_id"],))
    result = cursor.fetchone()
    
    if not result or not result[0]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    cursor.close()
    return current_user

def require_premium(current_user: dict = Depends(get_current_active_user),db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT is_premium FROM users WHERE id = ?", (current_user["user_id"],))
    result = cursor.fetchone()
    
    if not result or not result[0]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required for this feature"
        )
    cursor.close()
    return current_user



def is_admin_user(db, user_id:int)->bool:
    cursor = db.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    return bool(result and result[0]==1)
    
 
def require_admin(current_user: dict = Depends(get_current_active_user),db: sqlite3.Connection = Depends(get_db)):
    # cursor = db.cursor()
    # cursor.execute("SELECT is_admin FROM users WHERE id = ?", (current_user["user_id"],))
    # result = cursor.fetchone()
    # print(f"result:{result}")
    
    # if not result or not result[0]:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Administrative access required"
    #     )
    if not is_admin_user(db, current_user["user_id"]):
        raise HTTPException(403, "Administrative access required")  
   
    print("current user id ",current_user) 
    return current_user



# Optional authentication (doesn't fail if no token)
def get_optional_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Returns user if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None
