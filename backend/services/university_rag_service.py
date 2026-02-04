
import chromadb
from chromadb.config import Settings
import sqlite3
import json
from typing import List, Dict, Any, Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UniversityRAGService:
    def __init__(self, db_path: str = "University.db", chroma_path: str = "chroma_db_dir"):
        self.db_path = db_path
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        self.collection_name = "universities"
        
        
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            print(self.collection)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except:
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "University information for RAG"}
            )
            print(f"self.collection created sucessfully:{self.collection}")
            logger.info(f"Created new collection: {self.collection_name}")
            self._ingest_universities()
        
      
        try:
            self.llm = ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.0
            )
            print(f"self.llm model callled:{self.llm}")
            logger.info(f"Initialized Ollama model: {settings.OLLAMA_MODEL}")
        except Exception as e:
            logger.warning(f"Could not initialize Ollama: {e}")
            self.llm = None
    
    def _ingest_universities(self):
        logger.info("Starting university data ingestion into ChromaDB...")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Fetch all universities with their majors
        cursor.execute("""
            SELECT 
                u.id, u.name, u.country, u.city, u.tuition_fee, u.min_gpa, 
                u.language, u.scholarship_available, u.overview, u.duration,
                u.accommodation_info, u.website, u.ranking, u.acceptance_rate,
                GROUP_CONCAT(m.name, ', ') as majors
            FROM universities u
            LEFT JOIN university_majors um ON u.id = um.university_id
            LEFT JOIN majors m ON um.major_id = m.id
            WHERE u.is_active = 1
            GROUP BY u.id
        """)
        
        universities = cursor.fetchall()
        print(f"universities:",universities)
        print(f"universities fetch from the database")
        conn.close()
        
        documents = []
        metadatas = []
        ids = []
        
        for uni in universities:
            doc_text = f"""
            University: {uni['name']}
            Country: {uni['country']}, City: {uni['city']}
            Ranking: {uni['ranking']}
            Tuition Fee: ${uni['tuition_fee']} per year
            Minimum GPA: {uni['min_gpa']}
            Language: {uni['language']}
            Scholarship Available: {'Yes' if uni['scholarship_available'] else 'No'}
            Acceptance Rate: {uni['acceptance_rate']*100}%
            Duration: {uni['duration']}
            Overview: {uni['overview']}
            Accommodation: {uni['accommodation_info']}
            Majors Offered: {uni['majors'] or 'Various programs'}
            Website: {uni['website']}
            """
            
            documents.append(doc_text)
            metadatas.append({
                "id": uni['id'],
                "name": uni['name'],
                "country": uni['country'],
                "city": uni['city'],
                "tuition_fee": uni['tuition_fee'],
                "min_gpa": float(uni['min_gpa']),
                "scholarship": bool(uni['scholarship_available']),
                "ranking": uni['ranking'],
                "majors": uni['majors'] or ""
            })
            ids.append(f"uni_{uni['id']}")
        
        # Add to ChromaDB
        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Ingested {len(documents)} universities into ChromaDB")
        else:
            logger.warning("No universities found to ingest")
    
    def search_universities(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        n_results: int = 10
    ) -> List[Dict]:
    
        where_conditions = []
        
        if filters:
            if filters.get('scholarship_track'):
                where_conditions.append({'scholarship': True})
                print(f"where condition applied:{where_conditions}")
            
            if filters.get('country') and filters['country'] != '':
                where_conditions.append({'country': filters['country']})
                print(f"where condition is applied :{where_conditions}")
        
      
        where_clause = None
        if len(where_conditions) == 1:
            where_clause = where_conditions[0]
        elif len(where_conditions) > 1:
            where_clause = {'$and': where_conditions}
        
    
        has_post_filters = filters and (
            filters.get('max_tuition') or 
            filters.get('min_gpa') or 
            filters.get('major')
        )
        chromadb_results = n_results * 3 if has_post_filters else n_results
        print(f"chromadb_results",chromadb_results)
       
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=chromadb_results,
                where=where_clause
            )
            
           
            universities = []
            if results and results['metadatas'] and results['metadatas'][0]:
                for metadata, document, distance in zip(
                    results['metadatas'][0], 
                    results['documents'][0],
                    results['distances'][0]
                ):
                 
                    if filters:
                        
                        if filters.get('max_tuition'):
                            if metadata['tuition_fee'] > filters['max_tuition']:
                                logger.debug(f"Filtered out {metadata['name']}: tuition ${metadata['tuition_fee']} > ${filters['max_tuition']}")
                                continue
                        
                        
                        if filters.get('min_gpa'):
                            if metadata['min_gpa'] > filters['min_gpa']:
                                logger.debug(f"Filtered out {metadata['name']}: requires GPA {metadata['min_gpa']} > user's {filters['min_gpa']}")
                                continue
                        
                       
                        if filters.get('major') and filters['major'] != '':
                            majors_str = metadata.get('majors', '').lower()
                            filter_major = filters['major'].lower()
                            if filter_major not in majors_str:
                                logger.debug(f"Filtered out {metadata['name']}: major '{filters['major']}' not in '{metadata.get('majors', '')}'")
                                continue
                    
                    universities.append({
                        "id": metadata['id'],
                        "name": metadata['name'],
                        "country": metadata['country'],
                        "city": metadata['city'],
                        "tuition_fee": metadata['tuition_fee'],
                        "min_gpa": metadata['min_gpa'],
                        "scholarship_available": metadata['scholarship'],
                        "ranking": metadata['ranking'],
                        "relevance_score": 1 - distance,
                        "content": document
                    })
                    
                    
                    if len(universities) >= n_results:
                        break
            
            logger.info(f"Found {len(universities)} universities matching filters from ChromaDB search")
            return universities[:n_results]  
        
        except Exception as e:
            logger.error(f"Error searching universities: {e}")
            return []
    def generate_response(
        self, 
        user_message: str, 
        context_universities: List[Dict],
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
    
        if not self.llm:
            return self._fallback_response(context_universities)
        
        # Build context from retrieved universities
        context = self._build_context(context_universities)
        
        # Build system prompt
        system_prompt = f"""You are a university recommendation assistant helping students find the best universities.

IMPORTANT INSTRUCTIONS:
    
    1. ONLY recommend universities from the list provided below
    2. For EACH university in the list, explain WHY it matches the student's profile
    3. Include specific details: tuition, GPA requirements, scholarships
    4. DO NOT suggest universities not in the provided list
    5. DO NOT give generic advice about "community colleges" or "public universities" unless they are in the list
AVAILABLE UNIVERSITIES:
{context}

When the student asks for recommendations:
- List each university from above
- Explain specifically why it fits their GPA, budget, major, and country preference
- Mention if scholarships are available
- Be specific with numbers (tuition amount, GPA requirement, ranking)

IF NO UNIVERSITIES MATCH:
    - Clearly state that no universities match their criteria
    - Suggest adjusting filters such as GPA, budget, or country."""

      
        messages = [SystemMessage(content=system_prompt)]
        
       
        if conversation_history:
            for msg in conversation_history[-6:]:  
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(SystemMessage(content=f"Assistant previously said: {msg['content']}"))
        
       
        messages.append(HumanMessage(content=user_message))
        
        try:
            response = self.llm.invoke(messages)
            print(f"response generated using LLM :{response}")
            return response.content
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")

            print("unable to call the LLM generate the response")
            return self._fallback_response(context_universities)
    
    def _build_context(self, universities: List[Dict]) -> str:
        if not universities:
            return "No universities found matching your criteria."
        
        context_parts = []
        for i, uni in enumerate(universities, 1):  
            context_parts.append(f"""
{i}. {uni['name']} ({uni['country']})
   - Ranking: #{uni['ranking']}
   - Tuition: ${uni['tuition_fee']}/year
   - Min GPA: {uni['min_gpa']}
   - Scholarship: {'Available' if uni['scholarship_available'] else 'Not available'}
   - Location: {uni['city']}, {uni['country']}
""")
        print(f"total university:{context_parts}")
        return "\n".join(context_parts)
    
    def _fallback_response(self, universities: List[Dict]) -> str:
        """Fallback response when LLM is not available"""
        if not universities:
            return "I couldn't find any universities matching your criteria. Try adjusting your filters or being more specific with your requirements."
        
        response = f"I found {len(universities)} universities that might interest you:\n\n"
        
        for i, uni in enumerate(universities[:5], 1):
            response += f"{i}. **{uni['name']}** ({uni['country']})\n"
            response += f"   - Tuition: ${uni['tuition_fee']}/year\n"
            response += f"   - Min GPA: {uni['min_gpa']}\n"
            response += f"   - Scholarship: {'Available' if uni['scholarship_available'] else 'Not available'}\n\n"
        
        return response
    
    def get_filter_options(self) -> Dict[str, List]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        
        cursor.execute("SELECT DISTINCT country FROM universities WHERE is_active = 1 ORDER BY country")
        countries = [row[0] for row in cursor.fetchall()]
        logger.info("fetch the conteries from DB")
     
        cursor.execute("SELECT DISTINCT name FROM majors ORDER BY name")
        majors = [row[0] for row in cursor.fetchall()]
        print(f"major fetch in the DB")
       
        cursor.execute("SELECT MIN(tuition_fee), MAX(tuition_fee) FROM universities WHERE is_active = 1")
        tuition_range = cursor.fetchone()
        
       
        cursor.execute("SELECT MIN(min_gpa), MAX(min_gpa) FROM universities WHERE is_active = 1")
        gpa_range = cursor.fetchone()
        
        conn.close()
        
        return {
            "countries": countries,
            "majors": majors,
            "tuition_range": {"min": tuition_range[0], "max": tuition_range[1]},
            "gpa_range": {"min": gpa_range[0], "max": gpa_range[1]}
        }
    
    def compare_universities(self, university_ids: List[int]) -> Dict:
        if len(university_ids) < 2 or len(university_ids) > 3:
            raise ValueError("Please provide 2 or 3 university IDs to compare")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        universities = []
        for uni_id in university_ids:
            cursor.execute("""
    SELECT 
        u.id, 
        u.name, 
        u.country, 
        u.city, 
        u.tuition_fee, 
        u.min_gpa,
        u.scholarship_available, 
        u.ranking, 
        u.acceptance_rate, 
        u.duration,
        u.overview, 
        u.accommodation_info, 
        u.website,
        GROUP_CONCAT(um.major_name, ', ') AS majors
    FROM universities u
    LEFT JOIN university_majors um 
        ON u.id = um.university_id
    WHERE u.id = ?
    GROUP BY u.id
""", (uni_id,))
            
            uni = cursor.fetchone()
            print(f"university fetch from the db:{uni}")
            if uni:
                universities.append(dict(uni))
            

        
        conn.close()
        
        return {
            "universities": universities[:4],
            "comparison_criteria": [
                "tuition_fee",
                "min_gpa",
                "scholarship_available",
                "ranking",
                "acceptance_rate",
                "duration"
            ]
        }
    
    def fetch_filtered_universities(self, filters: dict):
        conn = sqlite3.connect(self.db_path)
        print(conn)
        conn.row_factory = sqlite3.Row  
        cursor = conn.cursor()
        
      
        base_query = """
        SELECT DISTINCT u.id, u.name, u.city, u.country, u.tuition_fee,
                        u.min_gpa, u.ranking, u.scholarship_available
        FROM universities u
        LEFT JOIN university_majors m ON u.id = m.university_id
        WHERE u.is_active = 1
    """

        params = []
        
        if filters.get("country") and filters["country"] != "":
            print(repr(filters["country"]))
            base_query += " OR u.country = ?"
            
            params.append(filters["country"])
        
        if filters.get("major") and filters["major"] != "":
            print(repr(filters["major"]))
            base_query += " OR LOWER(TRIM(m.major_name)) = LOWER(TRIM(?))"
            params.append(filters["major"])
        print(f"params are available:{params}")
        
        if filters.get("max_tuition") and filters["max_tuition"] > 0:
            print(repr(filters["max_tuition"]))
            base_query += " OR u.tuition_fee <= ?"
            params.append(filters["max_tuition"])
        
        if filters.get("min_gpa") and filters["min_gpa"] > 0:
            print(repr(filters["min_gpa"]))
            base_query += " OR CAST(u.min_gpa as REAL) <= ?"
            params.append(filters["min_gpa"])
        
        if filters.get("scholarship_track"):
            base_query += " OR u.scholarship_available = 1"
        
        base_query += " ORDER BY u.tuition_fee ASC LIMIT 20"
        
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        conn.close()
        
        
        return [dict(row) for row in rows]



    def query_with_filters(self, query: str, filters: dict, conversation_history: Optional[List[Dict]] = None) -> Dict:
    
        universities = self.fetch_filtered_universities(filters)
        print(universities)
        if not universities:
            return {
                "response": "No universities match the selected filters. Try broadening your criteria.",
                "universities": []
            }
            
        context = self.build_context(universities)
        print(f"context of the :{context}")
        response = self.ask_llm_with_history(query, context, conversation_history)
        print(response)
        
        return {
            "response": response,
            "universities": universities[:2]
        }
    
    def build_context(self, universities):
        if not universities:
            return "No universities found matching your criteria."
        
        lines = []
        for i, uni in enumerate(universities, 1):
            lines.append(
                f"{i}. University: {uni['name']}\n"
                f"   Location: {uni['city']}, {uni['country']}\n"
                f"   Tuition: ${uni['tuition_fee']:,.2f}/year\n"
                f"   Min GPA: {uni['min_gpa']}\n"
                f"   Ranking: {uni['ranking']}\n"
                f"   Scholarship: {'Yes' if uni['scholarship_available'] else 'No'}\n"
            )
        print(f"data fetch and concatenate :{lines[2:]}")
        return "\n".join(lines)
    
    def ask_llm_with_history(self, query: str, context: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Generate LLM response with session awareness."""
        if not self.llm:
            return "LLM not available."
            
        system_prompt = f"""
                You are a university recommendation assistant helping students find universities.

                IMPORTANT INSTRUCTIONS:
                1. ONLY recommend universities from the list provided below
                2. Explain WHY each university matches their criteria
                3. Include specific details: tuition, GPA requirements, location
                4. DO NOT suggest universities not in the provided list

                AVAILABLE UNIVERSITIES:
                {context}

                Answer the student's question using ONLY the universities listed above.
"""
        messages = [SystemMessage(content=system_prompt)]
        
        if conversation_history:
            for msg in conversation_history[-4:]:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(SystemMessage(content=f"Assistant previously said: {msg['content']}"))
        
        messages.append(HumanMessage(content=query))
        
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Error in ask_llm_with_history: {e}")
            return f"Error: {str(e)}"
    

    
    def ask_llm(self, query: str, context: str) -> str:
        if not self.llm:
            return "LLM not available. Please check your Ollama configuration."
        
        system_prompt = f"""
            You are a university recommendation assistant helping students find universities.

            IMPORTANT INSTRUCTIONS:
            1. ONLY recommend universities from the list provided below
            2. Explain WHY each university matches their criteria
            3. Include specific details: tuition, GPA requirements, location
            4. DO NOT suggest universities not in the provided list
            5. Be conversational and helpful.

            AVAILABLE UNIVERSITIES:
            {context}

            Answer the student's question using ONLY the universities listed above.
            If no universities match well, clearly state that and suggest adjusting filters."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]
        
        try:
            response = self.llm.invoke(messages)
            logger.info(f"Generated LLM response for filtered query")
            print(f"response generated with the content:{response.content}")
            return response.content
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return f"Error generating response: {str(e)}"





_rag_service = None

def get_rag_service() -> UniversityRAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = UniversityRAGService()
    return _rag_service


def detect_intent(user_query:str)->str:
    q=user_query.lower().strip()
    greetings=[
        "hi","hello","good morning","good morning","good afternoon","good evening","hii","helo"
    ]
    
    if q in greetings:
        if q == q or q.startswith(q):
            return True
    return False


def normalize(query:str)->str:
    q=query.lower().strip()
    return q





