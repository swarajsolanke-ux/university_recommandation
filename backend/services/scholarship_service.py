from typing import List, Dict, Optional
import sqlite3
from sqlite import get_db
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO,format={'%(asctime)s - %(name)s - %(levelname)s - %(message)s'})
logger = logging.getLogger(__name__)
logger.info("logger sucessfuly initializd in scholarship service")
class ScholarshipService:
    @staticmethod
    def get_all_scholarships(country: Optional[str] = None, min_amount: Optional[int] = None) -> List[Dict]:
        """Fetch all active scholarships with optional filters"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            query = "SELECT * FROM scholarships WHERE is_active = 1"
            params = []
            
            if country:
                query += " AND (country = ?)"
                params.append(country)
            
            if min_amount:
                query += " AND amount >= ?"
                params.append(min_amount)
                
            cursor.execute(query, params)
            rows = cursor.fetchall()
            logger.info(f'fetched data from scholarship tables with filters country')
            scholarships = []
            seen=set()
            for row in rows:
                if row[1] not in  seen:
                    seen.add(row[1])
                    scholarships.append({
                        "id": row[0],
                        "name": row[1],
                        "country": row[2],
                        "provider": row[3],
                        "min_gpa": row[4],
                        "max_age": row[5],
                        "nationality_requirement": row[6],
                        "coverage": row[7],
                        "amount": row[8],
                        "deadline": row[9],
                        "description": row[10],
                        "required_documents": row[11],
                        "website": row[12]
                    })
            
            conn.close()
            logger.info(f"fetched {len(scholarships)} and all unique scholrship:{scholarships}")
            return scholarships
        except Exception as e:
            logger.error(f"Error fetching scholarships: {e}")
            return []

    @staticmethod
    def get_scholarship_by_id(scholarship_id: int) -> Optional[Dict]:
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM scholarships WHERE id = ?", (scholarship_id,))
            row = cursor.fetchone()
            logger.info(f"fetched data:{row[0]}")
            if not row:
                conn.close()
                return None
                
            scholarship = {
                "id": row[0],
                "name": row[1],
                "country": row[2],
                "provider": row[3],
                "min_gpa": row[4],
                "max_age": row[5],
                "nationality_requirement": row[6],
                "coverage": row[7],
                "amount": row[8],
                "deadline": row[9],
                "description": row[10],
                "required_documents": row[11],
                "website": row[12]
            }
            
            conn.close()
            return scholarship
        except Exception as e:
            logger.error(f"Error fetching scholarship {scholarship_id}: {e}")
            return None

    @staticmethod
    def calculate_eligibility(user_id: int, scholarship_id: int) -> Dict:
        try:
            conn = get_db()
            cursor = conn.cursor()
            print("cursor created sucessfullly")
            # Get student profile
            cursor.execute("SELECT gpa, nationality FROM student_profiles WHERE user_id = ?", (user_id,))
            student = cursor.fetchone()
            logger.info(f"fetched student profile data :{student}")
            if not student:
                conn.close()
                return {"eligible": False, "reason": "Student profile not found"}
                
            student_gpa, student_nationality = student
            
            # Get scholarship requirements
            cursor.execute("SELECT min_gpa, nationality_requirement FROM scholarships WHERE id = ?", (scholarship_id,))
            scholarship = cursor.fetchone()
            if not scholarship:
                conn.close()
                return {"eligible": False, "reason": "Scholarship not found"}
                
            min_gpa, nat_req = scholarship
            
            score = 100
            reasons = []
            

            print("running sucessfully")
            # Check GPA
            if (student_gpa) < (min_gpa):
                score -= 40
                reasons.append(f"GPA ({student_gpa}) is below required ({min_gpa})")
                print(f"GPA check failed :{reasons}")
            
            # Check Nationality
            if nat_req != "All nationalities" and student_nationality.lower() not in nat_req.lower():
                score -= 60
                reasons.append(f"Nationality ({student_nationality}) does not match requirement ({nat_req})")
            
            conn.close()
            return {
                "score": max(0, score),
                "eligible": score >= 60,
                "reasons": reasons
            }
        except Exception as e:
            logger.error(f"Error calculating eligibility: {e}")
            return {"eligible": False, "reason": str(e)}

    @staticmethod
    def create_scholarship_application(user_id: int, scholarship_id: int) -> Dict:
        """Create a new scholarship application draft"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Check for existing application
            cursor.execute(
                "SELECT id FROM scholarship_applications WHERE user_id = ? AND scholarship_id = ?",
                (user_id, scholarship_id)
            )
            if cursor.fetchone():
                conn.close()
                return {"error": "Application already exists"}
            
            # Calculate initial eligibility score
            eligibility = ScholarshipService.calculate_eligibility(user_id, scholarship_id)
            
            cursor.execute(
                """INSERT INTO scholarship_applications (user_id, scholarship_id, status, eligibility_score)
                VALUES (?, ?, 'Draft', ?)""",
                (user_id, scholarship_id, eligibility.get("score", 0))
            )
            
            app_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {"success": True, "application_id": app_id}
        except Exception as e:
            logger.error(f"Error creating scholarship application: {e}")
            return {"error": str(e)}
