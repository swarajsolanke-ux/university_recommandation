
from sqlite import get_db
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ApplicationService:
    
    
    @staticmethod
    def create_application(user_id: int, university_id: int, major_id: int, notes: Optional[str] = None) -> Dict:
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Check if application already exists
            cursor.execute("""
                SELECT id, status FROM applications 
                WHERE user_id = ? AND university_id = ? AND major_id = ?
            """, (user_id, university_id, major_id))
            
            existing = cursor.fetchone()
            print(f"existing application check:{existing}")
            if existing:
                app_id, status = existing
                if status != 'Draft':
                    conn.close()
                    return {
                        "error": f"Application already exists with status: {status}",
                        "application_id": app_id,
                        "status": status
                    }
            
            # Create new application
            cursor.execute("""
                INSERT INTO applications (user_id, university_id, major_id, status, notes)
                VALUES (?, ?, ?, 'Draft', ?)
            """, (user_id, university_id, major_id, notes))
            
            app_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Application {app_id} created for user {user_id}")
            print(f"application create with the id:{app_id}")
            return {
                "application_id": app_id,
                "status": "Draft",
                "message": "Application created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating application: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_application_details(application_id: int) -> Optional[Dict]:
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Get application info
            cursor.execute("""
                SELECT 
                    a.id, a.user_id, a.university_id, a.major_id, a.status,
                    a.application_date, a.last_updated, a.notes, a.admin_notes,
                    u.name as university_name, u.country, u.city,
                    m.major_name as major_name
                FROM applications a
                JOIN universities u ON a.university_id = u.id
                JOIN university_majors m ON a.major_id = m.id
                WHERE a.id = ?
            """, (application_id,))
            
            app = cursor.fetchone()
            print(f"Application details fetched: {app}")
            if not app:
                conn.close()
                return None
            
            # Get uploaded documents
            cursor.execute("""
                SELECT id, document_type, file_name, file_path, uploaded_at, is_verified
                FROM application_documents
                WHERE application_id = ?
                ORDER BY uploaded_at DESC
            """, (application_id,))
            
            documents = cursor.fetchall()
            conn.close()
            print(f"documents detailes fetched:{documents}")
            return {
                "id": app[0],
                "user_id": app[1],
                "university_id": app[2],
                "major_id": app[3],
                "status": app[4],
                "application_date": app[5],
                "last_updated": app[6],
                "notes": app[7],
                "admin_notes": app[8],
                "university_name": app[9],
                "country": app[10],
                "city": app[11],
                "major_name": app[12],
                "documents": [
                    {
                        "id": doc[0],
                        "document_type": doc[1],
                        "file_name": doc[2],
                        "file_path": doc[3],
                        "uploaded_at": doc[4],
                        "is_verified": bool(doc[5])
                    }
                    for doc in documents
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting application details: {e}")
            return None
    
    @staticmethod
    def get_user_applications(user_id: int, status_filter: Optional[str] = None) -> List[Dict]:
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    a.id, a.status, a.application_date, a.last_updated,
                    u.name as university_name, u.country,
                    m.major_name as major_name
                FROM applications a
                JOIN universities u ON a.university_id = u.id
                JOIN university_majors m ON a.major_id = m.id
                WHERE a.user_id = ?
            """
            
            params = [user_id]
            
            if status_filter:
                query += " AND a.status = ?"
                params.append(status_filter)
            
            print(f"Executing query: {query}, params: {params}")
            query += " ORDER BY a.last_updated DESC"
            
            cursor.execute(query, params)
            applications = cursor.fetchall()
            print(f"fetched application:{applications}")
            # Get document count for each application
            result = []
            for app in applications:
                cursor.execute("""
                    SELECT COUNT(*) FROM application_documents
                    WHERE application_id = ?
                """, (app[0],))
                doc_count = cursor.fetchone()[0]
                
                result.append({
                    "id": app[0],
                    "status": app[1],
                    "application_date": app[2],
                    "last_updated": app[3],
                    "university_name": app[4],
                    "country": app[5],
                    "major_name": app[6],
                    "document_count": doc_count
                })
            
        
            conn.close()
            print(f"Returning user applications: {len(result)} applications and their details:{result}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting user applications: {e}")
            return []
    
    @staticmethod
    def submit_application(application_id: int) -> Dict:
        """
        Submit an application (change status from Draft to Submitted)
        
        Args:
            application_id: ID of the application
            
        Returns:
            Dict with success status and message
        """
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Check current status
            cursor.execute("SELECT status FROM applications WHERE id = ?", (application_id,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return {"error": "Application not found"}
            
            current_status = result[0]
            
            if current_status != 'Draft':
                conn.close()
                return {"error": f"Cannot submit application with status: {current_status}"}
            
            # Check if required documents are uploaded (at least one document)
            cursor.execute("""
                SELECT COUNT(*) FROM application_documents
                WHERE application_id = ?
            """, (application_id,))
            
            doc_count = cursor.fetchone()[0]
            
            if doc_count == 0:
                conn.close()
                return {
                    "error": "Cannot submit application without documents",
                    "message": "Please upload at least one document before submitting"
                }
            
            # Update status to Submitted
            cursor.execute("""
                UPDATE applications
                SET status = 'Submitted', last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (application_id,))
            
            # Get user_id for notification
            cursor.execute("SELECT user_id FROM applications WHERE id = ?", (application_id,))
            user_id = cursor.fetchone()[0]
            
            # Create notification
           
            NotificationService.create_notification(
                db=conn,
                user_id=user_id,
                title="Application Submitted",
                message=f"Your application has been successfully submitted and is now under review.",
                notification_type="success",
                link=f"/applications/{application_id}"
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Application {application_id} submitted successfully")
            
            return {
                "success": True,
                "status": "Submitted",
                "message": "Application submitted successfully",
                "next_steps": [
                    "Your application is now under review",
                    "You will receive notifications about status updates",
                    "Estimated review time: 5-7 business days"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error submitting application: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def update_application_status(application_id: int, new_status: str, admin_notes: Optional[str] = None) -> Dict:
        """
        Update application status (Admin function)
        
        Args:
            application_id: ID of the application
            new_status: New status value
            admin_notes: Optional notes from admin
            
        Returns:
            Dict with success status
        """
        valid_statuses = ['Draft', 'Submitted', 'Under Review', 'Missing Documents', 
                         'Conditional Offer', 'Final Offer', 'Rejected']
        
        if new_status not in valid_statuses:
            return {"error": f"Invalid status: {new_status}"}
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Get user_id
            cursor.execute("SELECT user_id FROM applications WHERE id = ?", (application_id,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return {"error": "Application not found"}
            
            user_id = result[0]
            
            # Update status
            if admin_notes:
                cursor.execute("""
                    UPDATE applications
                    SET status = ?, admin_notes = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_status, admin_notes, application_id))
            else:
                cursor.execute("""
                    UPDATE applications
                    SET status = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_status, application_id))
            
            # Create notification based on status
            
            
            notification_messages = {
                'Under Review': ("Application Under Review", "Your application is now being reviewed by the university."),
                'Missing Documents': ("Missing Documents", "Please upload the missing documents to proceed with your application."),
                'Conditional Offer': ("Conditional Offer Received", "Congratulations! You have received a conditional offer."),
                'Final Offer': ("Final Offer Received", "Congratulations! You have received a final offer of admission!"),
                'Rejected': ("Application Update", "Your application status has been updated.")
            }
            
            if new_status in notification_messages:
                title, message = notification_messages[new_status]
                notif_type = "success" if "Offer" in new_status else "warning" if new_status == "Missing Documents" else "info"
                
                NotificationService.create_notification(
                    db=conn,
                    user_id=user_id,
                    title=title,
                    message=message,
                    notification_type=notif_type,
                    link=f"/applications/{application_id}"
                )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Application {application_id} status updated to {new_status}")
            
            return {
                "success": True,
                "status": new_status,
                "message": "Application status updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating application status: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def delete_application(application_id: int, user_id: int) -> Dict:
        """
        Delete a draft application
        
        Args:
            application_id: ID of the application
            user_id: ID of the user (for authorization)
            
        Returns:
            Dict with success status
        """
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Check if application exists and belongs to user
            cursor.execute("""
                SELECT status FROM applications
                WHERE id = ? AND user_id = ?
            """, (application_id, user_id))
            
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return {"error": "Application not found or unauthorized"}
            
            status = result[0]
            
            if status != 'Draft':
                conn.close()
                return {"error": "Can only delete draft applications"}
            
            # Delete application (documents will be cascade deleted)
            cursor.execute("DELETE FROM applications WHERE id = ?", (application_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Application {application_id} deleted")
            
            return {
                "success": True,
                "message": "Application deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting application: {e}")
            return {"error": str(e)}
