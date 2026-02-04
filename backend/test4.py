from ast import Dict
import json
from langchain_ollama import ChatOllama,OllamaEmbeddings
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
import os
from langchain_groq import ChatGroq
from typing import Dict, List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3
from langchain_core.output_parsers import StrOutputParser


SCORE_TEMPLATE = {
    "academic_strengths": {
        "mathematics": 0.0,
        "physical_sciences": 0.0,
        "life_sciences": 0.0,
        "computer_science": 0.0,
        "business_economics": 0.0,
        "social_sciences": 0.0,
        "language_literature": 0.0,
        "law_public_policy": 0.0,
        "education_pedagogy": 0.0,
        "design_creative_studies": 0.0,
        "health_medical_sciences": 0.0,
        "agriculture_environment": 0.0
    },

    "thinking_style": {
        "logical_reasoning": 0.0,
        "analytical_thinking": 0.0,
        "critical_thinking": 0.0,
        "systems_thinking": 0.0,
        "creative_thinking": 0.0,
        "strategic_thinking": 0.0,
        "ethical_judgment": 0.0,
        "human_centered_thinking": 0.0
    },

    "learning_style": {
        "visual_learning": 0.0,
        "auditory_learning": 0.0,
        "reading_writing": 0.0,
        "hands_on_practical": 0.0,
        "research_oriented": 0.0,
        "collaborative_learning": 0.0,
        "independent_learning": 0.0
    },

    "interests": {
        "technology_innovation": 0.0,
        "scientific_discovery": 0.0,
        "business_enterprise": 0.0,
        "public_service_society": 0.0,
        "health_wellbeing": 0.0,
        "law_governance": 0.0,
        "arts_culture": 0.0,
        "media_communication": 0.0,
        "environment_sustainability": 0.0,
        "travel_hospitality": 0.0,
        "education_training": 0.0
    }}



# llm = ChatOllama(
#     model="gemma2:2b",
#     temperature=0
# )


llm=ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2)


class ScoreFinder(BaseModel):
    academic_strengths: Dict[str, float] = Field(
        ..., description="Scores between 0 and 1"
    )
    thinking_style: Dict[str, float] = Field(
        ..., description="Scores between 0 and 1"
    )
    learning_style: Dict[str, float] = Field(
        ..., description="Scores between 0 and 1"
    )
    interests: Dict[str, float] = Field(
        ..., description="Scores between 0 and 1"
    )

llm_response=llm.with_structured_output(schema=ScoreFinder)



def build_prompt_with_score(major: str) -> dict:
    prompt = ChatPromptTemplate.from_template("""
You are an expert educational consultant.
assign relevance scores between 0 and 1
for EACH key in the provided scoring template.

Rules:
- Every key must be present
- Values must be floats between 0 and 1
- Higher score = stronger relevance


MAJOR:
{major}

SCORING TEMPLATE:
{template}

Return ONLY valid JSON matching the schema.
""")

    chain = prompt | llm_response|StrOutputParser()

    response = chain.invoke({
        "major": major,
        "template": SCORE_TEMPLATE
    })

    return {
        "major": major,
        "academic_strengths": response.academic_strengths,
        "thinking_style": response.thinking_style,
        "learning_style": response.learning_style,
        "interests": response.interests
    }





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

class UserQARequest(BaseModel):
    academic_strengths: Dict[str, float] = Field(
        ..., description="Scores between 0 and 1"
    )
    thinking_style: Dict[str, float] = Field(
        ..., description="Scores between 0 and 1"
    )
    learning_style: Dict[str, float] = Field(
        ..., description="Scores between 0 and 1"
    )
    interests: Dict[str, float] = Field(
        ..., description="Scores between 0 and 1"
    )


llm_response_user=llm.with_structured_output(schema=UserQARequest)
def User_built_prompt(Q_A_LIST: str) -> dict:
    prompt = ChatPromptTemplate.from_template("""
You are an expert educational consultant. based on the following QA pair of the list provided
assign relevance scores between 0 and 1

Rules:
- Every key must be present
- Values must be floats between 0 and 1
- Higher score = stronger relevance


Q_A_LIST:
{Q_A_LIST}

SCORING TEMPLATE:
{template}

Return ONLY valid JSON matching the schema.
""")

    chain = prompt | llm_response_user

    response = chain.invoke({
        "Q_A_LIST": Q_A_LIST,
        "template": SCORE_TEMPLATE
    })
    print(response)
    return {
        "academic_strengths": response.academic_strengths,
        "thinking_style": response.thinking_style,
        "learning_style": response.learning_style,
        "interests": response.interests
    }








# def trait_similarity(user_scores: dict, major_scores: dict) -> float:
#     score = 0.0
#     for trait, user_value in user_scores.items():
#         print(trait)
#         print(user_value)
#         major_value = major_scores.get(trait, 0.0)
#         score += user_value * major_value
#     return score


def trait_similarity(user_scores: dict, major_scores: dict) -> float:
    numerator = 0.0
    denominator = 0.0

    for trait, user_value in user_scores.items():
        print(trait)
        print(user_value)
        numerator += user_value * major_scores.get(trait, 0.0)
        denominator += user_value
        print(numerator)
        print(denominator)

    if denominator == 0:
        return 0.0

    return numerator / denominator   



Trait_Weights ={
    "academic_strengths": 0.30,
    "thinking_style": 0.25,
    "learning_style": 0.20,
    "interests": 0.15
}



#score one major



def score_major(user_traits: dict, major_row: dict) -> float:
    academic = trait_similarity(
        user_traits["academic_strengths"],
        json.loads(major_row["academic_strengths_scores"])
    )

    thinking = trait_similarity(
        user_traits["thinking_style"],
        json.loads(major_row["thinking_style_scores"])
    )

    learning = trait_similarity(
        user_traits["learning_style"],
        json.loads(major_row["learning_style_scores"])
    )

    interests = trait_similarity(
        user_traits["interests"],
        json.loads(major_row["interests_scores"])

    )

    final_score = (
       Trait_Weights["academic_strengths"] * academic +
        Trait_Weights["thinking_style"] * thinking +
        Trait_Weights["learning_style"] * learning +
        Trait_Weights["interests"] * interests
    )
    print(final_score)

    return round(final_score, 2)





#fetch major from DB

def fetch_majors(conn):
    conn = sqlite3.connect("/Users/swarajsolanke/Smart_assistant_chatbot/university_recommander/University.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            m.major,
            m.academic_strengths_scores,
            m.thinking_style_scores,
            m.learning_style_scores,
            m.interests_scores,
            c.category_Name
        FROM Major_data m
        LEFT JOIN main_catgeory c ON m.category_id = c.id
    """)
    columns = [desc[0] for desc in cursor.description]
    print(f"columns of the database:{columns}")
    return [dict(zip(columns, row)) for row in cursor.fetchall()]




#rank and recommanded the major 

def recommend_majors(user_traits, majors, top_k=5):
    recommendations = []

    for major in majors:
        score = score_major(user_traits, major)
        recommendations.append({
            "major": major["major"],
            #"category": major["category_Name"],
            "score": score
        })

    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations[:top_k]












def insert_into_db_score(data:dict ,category_id:str):
    conn = sqlite3.connect("/Users/swarajsolanke/Smart_assistant_chatbot/university_recommander/University.db")
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO Major_data (
        major,
        academic_strengths_scores,
        thinking_style_scores,
        learning_style_scores,
        interests_scores,
        category_id
    ) VALUES (?, ?, ?, ?, ?,?)
    """, (
        data["major"],
        json.dumps(data["academic_strengths"]),
        json.dumps(data["thinking_style"]),
        json.dumps(data["learning_style"]),
        json.dumps(data["interests"]),
        category_id
    ))

    conn.commit()
    conn.close()



class Questiongenrate(BaseModel):
    personality_question:str=Field(...,description=" generate a question about  personality")
    Academic_Strengths_question:str=Field(...,description="generate a question about  acadamic strength")
    thinking_style_question:str=Field(...,description="generate a question about thinking style")
    Learning_Style_question:str=Field(...,description="generate a question about Learning style")
    Interests_question:str=Field(...,description="generate a question about Interests")
    carrer_tendencies_question:str=Field(...,description="generate a  question about career tendencies")


list_category="""
1) Personality 
2) Academic_Strengths
3) Thinking_Style
4) Learning_Style
5) Interests 
6) Career_Tendencies

"""


llm_question=llm.with_structured_output(schema=Questiongenrate)

def question_genrate_prompt(list_category:str)->dict:

    prompt=ChatPromptTemplate.from_template(
        """

You are an AI assessment assistant designed to generate career-guidance questions for students.

Task:
Generate exactly 6 short questions — one question for each category listed below.

list_category:
{list_category}

Rules:
- Generate exactly one question per category.
- Everytime generate a new and random question for every category.
- Each question must clearly reflect its category.
- Keep all questions short, simple, and student-friendly.
- Do not repeat ideas across questions.
- Do not add explanations, numbering, or extra text.

"""
)
    chain=prompt|llm_question
    final_response=chain.invoke(input={'list_category':list_category})
    return {
        "personality":final_response.personality_question,
        "Academic_Strengths":final_response.Academic_Strengths_question,
        "thinking_style":final_response.thinking_style_question,
        "Learning_Style":final_response.Learning_Style_question,
        "Interests":final_response.Interests_question,
        "carrer_tendencies":final_response.carrer_tendencies_question
    }
# result=question_genrate_prompt(list_category)

# print(result)
