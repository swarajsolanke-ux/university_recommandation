
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from services.university_rag_service import detect_intent, get_rag_service, normalize
from middleware.auth_middleware import get_current_active_user, get_optional_user
import sqlite3
import uuid
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbot/university", tags=["University Chatbot"])


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    #universities: List[Dict]
    session_id: str


class ComparisonRequest(BaseModel):
    university_ids: List[int]



chat_sessions = {}


@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(
    request: ChatMessage,
    current_user: Optional[dict] = Depends(get_optional_user)
):
   
   
    try:
        session_id = request.session_id or str(uuid.uuid4())
        print(f"session_id:{session_id}")
        
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                "messages": [],
                "created_at": datetime.now(),
                "user_id": current_user.get("user_id") if current_user else None
            }
        
       
        rag_service = get_rag_service()
        print(f"rag servicee is being called")
        
       
        filters = request.filters or {}
        
        intent=detect_intent(request.message)
        print(intent)
        if intent:
            ai_response=(
                "Hello! I can help you find universities based on your GPA, "
                "budget, major, and country preference. Tell me what you're looking for."
            )
            
            chat_sessions[session_id]["messages"].append({
                "role": "user",
                "content": request.message,
                "timestamp": datetime.now().isoformat()
            })

            chat_sessions[session_id]["messages"].append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.now().isoformat()
            })

            return ChatResponse(
                response=ai_response,
                universities=[],
                session_id=session_id
            )

            
        normalize_query=normalize(request.message)
        print(f"normalize query:{normalize_query}")
        
        universities = rag_service.search_universities(
            query=normalize_query,
            filters=filters,
            n_results=2
        )
        print(f"universities :{universities}")
        
       
        conversation_history = chat_sessions[session_id]["messages"]
        
       
        ai_response = rag_service.generate_response(
            user_message=normalize_query,
            context_universities=universities,
            conversation_history=conversation_history
        )
        
        
        chat_sessions[session_id]["messages"].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        })
        
        chat_sessions[session_id]["messages"].append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        
        return ChatResponse(
            response=ai_response,
            universities=universities[:3],  
            session_id=session_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@router.post("/compare")
async def compare_universities(request: ComparisonRequest):
    try:
        rag_service = get_rag_service()
        comparison = rag_service.compare_universities(request.university_ids)
        return comparison
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing universities: {str(e)}")


@router.get("/filters")
async def get_filter_options():
    try:
        rag_service = get_rag_service()
        print(F"rag_service callled:{rag_service}")
        return rag_service.get_filter_options()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching filters: {str(e)}")
    

@router.post("/query", response_model=ChatResponse)
async def query_universities(
    request: ChatMessage,
    current_user: Optional[dict] = Depends(get_optional_user)
):
    
    try:
        session_id = request.session_id or str(uuid.uuid4())
        print(f"session_id:{session_id}")
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                "messages": [],
                "created_at": datetime.now(),
                "user_id": current_user.get("user_id") if current_user else None
            }
        
        rag_service = get_rag_service()
        filters = request.filters or {}
        intent=detect_intent(request.message)
        print(intent)
        if intent:
            ai_response=(
                "Hello! I can help you find universities based on your GPA, "
                "budget, major, and country preference. Tell me what you're looking for."
            )
            
            chat_sessions[session_id]["messages"].append({
                "role": "user",
                "content": request.message,
                "timestamp": datetime.now().isoformat()
            })

            chat_sessions[session_id]["messages"].append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.now().isoformat()
            })

            return ChatResponse(
                response=ai_response,
                universities=[],
                session_id=session_id
            )


        normalize_query = normalize(request.message)
        conversation_history = chat_sessions[session_id]["messages"]
        print(f"conversation_his")

        
        # Process filtered query
        result = rag_service.query_with_filters(normalize_query, filters, conversation_history)
        
        # Update session
        chat_sessions[session_id]["messages"].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        })
        
        chat_sessions[session_id]["messages"].append({
            "role": "assistant",
            "content": result["response"],
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(
            response=result["response"],
            #universities=result["universities"],
            session_id=session_id
        )
    except Exception as e:
        import traceback
        print(f"Error in query_universities: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    

    
@router.post("/session")
async def create_session(current_user: Optional[dict] = Depends(get_optional_user)):
    session_id = str(uuid.uuid4())
    chat_sessions[session_id] = {
        "messages": [],
        "created_at": datetime.now(),
        "user_id": current_user.get("user_id") if current_user else None
    }
    
    return {
        "session_id": session_id,
        "message": "Session created successfully"
    }


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return chat_sessions[session_id]


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"message": "Session cleared successfully"}
    
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/reingest")
async def reingest_universities():
    try:
        rag_service = get_rag_service()
        # Delete existing collection and recreate
        rag_service.chroma_client.delete_collection(name=rag_service.collection_name)
        rag_service.collection = rag_service.chroma_client.create_collection(
            name=rag_service.collection_name,
            metadata={"description": "University information for RAG"}
        )
        rag_service._ingest_universities()
        
        return {"message": "Universities re-ingested successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error re-ingesting universities: {str(e)}")
