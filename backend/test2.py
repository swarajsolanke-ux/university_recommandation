from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.documents import Document
import os
from langchain_chroma import Chroma
from dotenv import load_dotenv,find_dotenv
from typing import List
from langchain_groq import ChatGroq
from tenacity import retry , stop_after_attempt , wait_fixed
from pydantic import BaseModel, Field
from typing import List, Optional,Dict
from langchain_core.prompts import ChatPromptTemplate
import sqlite3, json
import re  
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3
import uuid
from dotenv import load_dotenv
load_dotenv(find_dotenv(filename="/Users/swarajsolanke/Smart_assistant_chatbot/university_recommander/.env"))


# Focuses on computation, software systems, data, algorithms, and information processing to design and optimize digital technologies.

Main_CATEGORIES_LIST="""
1) Computing & Information Sciences:
   Focuses on computation and information systems, including software, algorithms, data, artificial intelligence, and information processing. All computer-related disciplines—whether awarded as science, engineering, or technology degrees

2) Engineering & Technology:
 Applies scientific and mathematical principles to design, build, and maintain machines, systems, structures, and technological solutions.

3) Business, Management & Commerce:
 Studies the planning, organization, finance, marketing, and operation of businesses and commercial enterprises.

4) Natural & Physical Sciences:
 Investigates the fundamental laws of nature through the study of matter, energy, space, and physical phenomena.

5) Health & Medical Sciences:
 Concentrates on diagnosing, treating, and preventing diseases while improving human health and healthcare systems.


6) Life Sciences & Biotechnology:
 Examines living organisms and biological systems, applying biological knowledge to innovation in medicine, agriculture, and industry.

7) Social Sciences:
 Analyzes human behavior, societies, institutions, and social relationships to understand and address societal challenges.

8) Arts, Humanities & Languages:
 Explores human culture, creativity, history, philosophy, and language to interpret and express human experience.

9) Law & Legal Studies:
 Studies legal systems, regulations, and principles governing justice, rights, and societal order.

10) Education & Teaching:
 Focuses on learning theories, teaching methodologies, curriculum development, and educational leadership.

11) Media, Communication & Design:
 Examines the creation and distribution of information, visual communication, digital media, and storytelling across platforms.

12) Architecture, Planning & Construction:
 Involves the design, planning, and construction of buildings and spaces that shape the built environment.

13) Agriculture, Food & Veterinary Sciences:
  Addresses food production, animal health, natural resource management, and sustainable agricultural systems.

14) Hospitality, Tourism & Services:
 Studies service-oriented industries focused on travel, accommodation, events, and customer experience management.

15) Interdisciplinary & Emerging Fields:
 ntegrates multiple disciplines to address complex problems and develop innovative fields driven by technological and societal change.

"""


# llm = ChatOllama(
#     model="gemma2:2b",
#     temperature=0
# )


llm=ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0)


class MajorCatgory(BaseModel):
    recommanded_category:str=Field(..., description="The most suitable major category from the provided categories list that aligns with the characteristics of the major")
    reason:str=Field(..., description="A brief explanation of why this category fits the major")

llm_respose=llm.with_structured_output(schema=MajorCatgory)


def get_category_id(category_name):
    conn = sqlite3.connect(database="/Users/swarajsolanke/Smart_assistant_chatbot/university_recommander/University.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category_id FROM main_catgeory 
        WHERE category_Name = ? 
        LIMIT 1
    """, (category_name,))
    
    result = cursor.fetchone()
    return result[0] if result else None




@retry(stop=stop_after_attempt(5) , wait=wait_fixed(5))
def main_category_prompt(major: str) -> str:
    prompt=ChatPromptTemplate.from_template(
"""
You are an expert academic advisor with deep knowledge of university majors, academic disciplines, and career pathways. Your task is to analyze a specific major provided by the user and recommend the single most suitable Main Category from our predefined academic category list.
Instructions:
1. Deep Analysis First
-Understand the core academic discipline and primary focus of the major.
-Consider the curriculum content, research areas, and career outcomes.
-Analyze the academic department where this major typically resides.
-Don't rely on superficial keyword matching. do not ramdomly match the major.
Major: {major}

Categories List:
{Main_CATEGORIES_LIST}

"""
)
    

    
    #Entertainment Push notification(inn-progress)

    chain=prompt|llm_respose
    result=chain.invoke(input={"major":major,"Main_CATEGORIES_LIST":Main_CATEGORIES_LIST})
    return {
        "recommanded_category": result.recommanded_category,
        # "reason": result.reason
        }





class CategoryScore(BaseModel):
    name: str = Field(
        ...,
        description="Name of the recommended major category"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score indicating suitability of the category (0 to 1)"
    )
class UserCategoryResponse(BaseModel):
    categories: List[CategoryScore] = Field(
        ...,
        description="Top recommended major categories with confidence scores"
    )

user_llm_respose=llm.with_structured_output(schema=UserCategoryResponse)
Q_A_LIST="""
Q. How would you describe yourself in social situations?
A."I'm outgoing and energetic" – I love hackathons, team brainstorming sessions, and explaining tech concepts to friends over coffee.

Q.What subjects or areas do you excel in academically?
A.I crushed circuits, programming, data structures, and machine learning projects; hardware-software integration is my sweet spot.

Q.How do you approach problem-solving?
A. I debug code line-by-line, simulate systems mathematically, and prototype until the solution scales efficiently.

Q.How do you learn best?
A.Hands-on labs, building Arduino projects, and tinkering with simulations beats lectures any day..

Q.What topics or activities interest you most?
A.AI/ML algorithms, robotics, embedded systems, and sustainable tech innovations keep me up at night.

Q.What kind of career environment appeals to you?
A.Think R&D labs, startups, or engineering teams at companies like Tesla or Google, where I can iterate prototypes and deploy real impact.
"""






def user_profile_prompt(Q_A_LIST: str) -> str:
    prompt=ChatPromptTemplate.from_template("""
You are an academic classification engine.
Your task is to analyze student answers and classify them into predefined academic categories.

IMPORTANT RULES:
- You MUST only use the categories provided below.
- You MUST NOT invent new categories.
- You may return up to 3 best-matching categories.
- If answers are unclear, return lower confidence. 
                                               
Student_Q&A:\n {Q_A_LIST}
Academic_categories:
                                            
{Main_CATEGORIES_LIST}
""")

    chain = prompt|user_llm_respose
    result = chain.invoke (input={"Q_A_LIST": Q_A_LIST, "Main_CATEGORIES_LIST": Main_CATEGORIES_LIST})
    print(result)


    response=UserCategoryResponse.model_validate(result) 
   
    return response.model_dump()



def insert_category(category_name):
        conn = sqlite3.connect(database="/Users/swarajsolanke/Smart_assistant_chatbot/university_recommander/University.db")
        cursor = conn.cursor()
        category_uuid=str(uuid.uuid4())
        cursor.execute("""
        INSERT INTO main_catgeory (category_id, category_Name) 
            VALUES (?, ?)
        """, (category_uuid,category_name))
        conn.commit()
        conn.close()
        return cursor.lastrowid





# def insert_categories(cursor, conn, category_list):
#     inserted_count = 0
#     for category_name in category_list:
#         category_uuid = str(uuid.uuid4())
#         try:
#             cursor.execute("""
#                 INSERT OR IGNORE INTO main_catgeory (category_id, category_Name) 
#                 VALUES (?, ?)
#             """, (category_uuid, category_name))
#             if cursor.rowcount > 0:  
#                 inserted_count += 1
#                 print(f"Inserted: {category_name}")
#             else:
#                 print(f"Already exists: {category_name}")
#         except sqlite3.IntegrityError as e:
#             print(f"Skip duplicate: {category_name} ({e})")
    
#     conn.commit()  # Commit once at end
#     conn.close()
#     print(f" Total new categories inserted: {inserted_count}")
#     return inserted_count

# Usage

# result_inserted=insert_categories(cursor,conn,category_list)
# print(result_inserted)


# result=user_profile_prompt(Q_A_LIST)
# print(result)



# #pydantic model for the profile dimensions
# class UserProfileDimension(BaseModel):
#     personality_traits: str = Field(..., description="Extracted personality traits of the user")
#     academic_strengths: str = Field(..., description="Extracted academic strengths of the user")
#     thinking_style: str = Field(..., description="Extracted thinking style of the user")
#     learning_style: str = Field(..., description="Extracted learning style of the user")
#     interests: str = Field(..., description="Extracted interests of the user")
#     career_paths: str = Field(..., description="Extracted career paths of the user")

# class ResponseResoning(BaseModel):
#     top_match:List[str]=Field(..., description="List of top reasons for the match")
#     match_markdown:Dict[str,float]=Field(..., description="Breakdown of match scores by dimension")

# user_profile_llm = llm.with_structured_output(schema=UserProfileDimension)

# def parse_user_qa(Q_A_LIST:str)->Dict:
#     prompt = ChatPromptTemplate.from_template("""
# Extract the user's responses into these exact dimensions from the Q&A. Map each answer to the closest dimension:
# - personality_traits: From social situations or self-description.
# - academic_strengths: From subjects excelled in.
# - thinking_style: From problem-solving approach.
# - learning_style: From how they learn best.
# - interests: From topics/activities that interest them.
# - career_paths: From career environment appeals (or tendencies).

# If a dimension doesn't match perfectly, use the most relevant excerpt or leave as empty string if no match.

# Q&A: {Q_A_LIST}

# Output ONLY valid JSON in this exact format, no extra text: {{"personality_traits": "extracted text", "academic_strengths": "extracted text", "thinking_style": "extracted text", "learning_style": "extracted text", "interests": "extracted text", "career_paths": "extracted text"}}
#     """)
#     chain=prompt|user_profile_llm
#     result = chain.invoke(input={"Q_A_LIST":Q_A_LIST})
#     print(f"parse llm response:{result}")
    
 
#     return result.model_dump()


# llm_for_resoning=llm.with_structured_output(schema=ResponseResoning)

# model = OllamaEmbeddings(model='nomic-embed-text:latest')

# def extract_keywords(text):
#     return set(re.findall(r'\w+', text.lower()))  

# def calculate_similarity_keywords(user_answer, profile_traits, keywords):
#     user_keywords = extract_keywords(user_answer)
#     strong = set(keywords['strong_indicators'])
#     moderate = set(keywords['moderate_indicators'])
#     profile_keywords = strong.union(moderate)
#     matches = len(user_keywords.intersection(profile_keywords))
#     score = (matches / max(len(profile_keywords), 1)) * 100
#     return min(score, 100)

# def calculate_similarity_semantic(user_answer, profile_traits):
#     if not user_answer or not profile_traits:
#         return 0
#     user_embedding = model.embed_documents([user_answer])
#     print(user_embedding)
#     profile_text = " ".join(profile_traits)
#     profile_embedding = model.embed_documents([profile_text])
#     similarity = cosine_similarity(user_embedding, profile_embedding)[0][0]
#     print(f"similarity:{similarity}")
#     return similarity * 100


# def hybrid_similarity(user_answer, profile_traits, keywords):
#     keyword_score = calculate_similarity_keywords(user_answer, profile_traits, keywords)
#     if keyword_score < 20:
#         return 0
#     return calculate_similarity_semantic(user_answer, profile_traits)



# def calculate_submajor_score(user_qa, submajor_profile):
#     weights = {
#         'personality_traits': 0.15,
#         'academic_strengths': 0.20,
#         'thinking_style': 0.15,
#         'learning_style': 0.10,
#         'interests': 0.25,  
#         'career_paths': 0.15
#     }
#     keywords = submajor_profile['keywords']
#     all_user_text = " ".join(user_qa.values())
#     global_keyword_score = calculate_similarity_keywords(all_user_text, [], keywords)
#     if global_keyword_score<20:
#         return 0
#     total_score = 0
#     for dimension, weight in weights.items():
#         user_answer = user_qa.get(dimension, "")
#         profile_traits = submajor_profile['profile'].get(dimension, [])
#         dimension_score = calculate_similarity_semantic(user_answer, profile_traits)
#         print(f"dimension_score:{dimension_score}")
#         total_score += dimension_score * weight
#         print(f"total_score:{total_score}")
#     return total_score  




# def generate_reasoning(user_qa, submajor_profile):
#     prompt = ChatPromptTemplate.from_template("""
# Generate reasoning for why this submajor matches the user.
# User QA: {user_qa}
# Submajor Profile: {profile}

# Output JSON: {{"top_matches": ["reason1", "reason2"], "match_breakdown": {{"dim1": score, ...}}}}
#     """)
#     chain = prompt | llm_for_resoning
#     result = chain.invoke({"user_qa": json.dumps(user_qa), "profile": json.dumps(submajor_profile['profile'])})
#     print(f"output of the generate reasoning: {result}")
#     return result.model_dump() 



# def recommend_submajors(user_qa, top_3_main_categories):
#     all_submajor_scores = []

#     categories = top_3_main_categories["categories"]
#     print(categories)

#     for item in categories:
#         category = item["name"]
#         category_confidence = item["confidence"]

#         submajors = get_submajors_for_category(category)

#         for submajor in submajors:
#             submajor_profile = load_submajor_profile(submajor, category)

#             match_score = calculate_submajor_score(user_qa, submajor_profile)
        
#             if match_score < 30:
#                 continue

#             print(f"match score for submajor{submajor}:{match_score}")

#             final_score = match_score * category_confidence
#             print(f"final score for submajor:{final_score}")
#             reasoning = generate_reasoning(user_qa, submajor_profile)

#             all_submajor_scores.append({
#                 "submajor": submajor,
#                 "main_category": category,
#                 "match_score": match_score,
#                 "category_confidence": category_confidence,
#                 "final_score": final_score,
#                 "reasoning": reasoning
#             })
#         print(f"profile match score :{match_score}")

#     ranked = sorted(
#         all_submajor_scores,
#         key=lambda x: x["final_score"],
#         reverse=True
#     )[:5]

#     return {
#         "recommendations": [
#             {**item, "rank": i + 1}
#             for i, item in enumerate(ranked)
#         ]
#     }






