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
import logging

#finding and loading .env file
load_dotenv(find_dotenv(filename="/Users/swarajsolanke/Smart_assistant_chatbot/university_recommander/.env"))



ollama_embed=OllamaEmbeddings(model="nomic-embed-text:latest")

class VectorStore:
    def __init__(self):
        persist_directory =os.path.join("/Users/swarajsolanke/Smart_assistant_chatbot/university_recommander/backend/chroma_db")
        self.vector_store = Chroma(
            embedding_function=ollama_embed,
            persist_directory=persist_directory
        )
    def store_user_embeddings(self, major: str, major_traits: str):
        metadata = {
            "major_name": major,
            "type": "user"
        }
        # Store as a single text document
        try:
            print(self.vector_store)
            self.vector_store.add_texts(
                texts=[major_traits],       
                metadatas=[metadata]      
            )
            #self.vector_store.persist()
            # print("Embeddings stored successfully.")
        except Exception as e:
            raise ValueError(f"Error storing embeddings:->{e}")
    def similarity_search(self,user_traits: str,top_k: int = 5,) -> List[Document]:
        try:
            results: List[Document] = self.vector_store.similarity_search_with_score(
                user_traits,
                k=top_k
            )
            print(results)
            return results
        except Exception as e:

            return []



TAXONOMY_TEXT = """
SKILLS_REQUIRED:
- Programming & Software Development
- Data Analysis & Statistics
- Mathematical Reasoning
- Logical & Algorithmic Thinking
- Research & Experimentation
- System Design & Engineering
- Critical Reading & Writing
- Communication & Presentation
- Creativity & Design
- Problem Solving
- Technical Tool Proficiency
- Domain-Specific Knowledge
- Project & Time Management
- Collaboration & Teamwork
- Ethical & Regulatory Awareness

ACADEMIC_STRENGTHS:
- Mathematics
- Statistics
- Computer Science
- Physics
- Chemistry
- Biology
- Economics
- Psychology
- Social Sciences
- Humanities
- Engineering Fundamentals
- Design & Visual Arts
- Language & Linguistics
- Business & Management
- Law & Policy

THINKING_STYLE (select 1–3):
- Analytical
- Logical
- Abstract
- Systems-Oriented
- Quantitative
- Creative
- Conceptual
- Strategic
- Critical
- Reflective
- Experimental
- Detail-Oriented
- Big-Picture Oriented
- Interdisciplinary

LEARNING_STYLE:
- Theory-Driven
- Practice-Oriented
- Project-Based
- Research-Based
- Experimentation & Trial-and-Error
- Visual Learning
- Text-Based Learning
- Collaborative Learning
- Independent Learning
- Mentorship-Guided
- Case-Study Based

CAREER_INTERESTS:
- Technology & Innovation
- Data & Patterns
- Scientific Discovery
- Human Behavior
- Society & Culture
- Business & Markets
- Design & Creativity
- Problem Solving
- Automation & Efficiency
- Ethics & Policy
- Health & Life Sciences
- Environment & Sustainability
- Education & Knowledge Sharing
- Media & Communication
- Systems & Infrastructure

CAREER_TENDENCIES:
- Research-Oriented
- Engineering-Oriented
- Application-Oriented
- Innovation-Focused
- Operations & Execution-Focused
- Strategy & Planning-Focused
- Creative Production-Focused
- Analytical Decision-Making
- People-Centric Roles
- Independent Contributor
- Team-Based Contributor
- Leadership-Oriented
- Entrepreneurial
- Public-Service Oriented
"""




llm=ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.0
)

# llm = ChatOllama(
#     model="gemma2:2b",
#     temperature=0
# )







def insert_into_db(data: dict):
    conn = sqlite3.connect("/Users/swarajsolanke/Smart_assistant_chatbot/university_recommander/University.db")
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO ai_assessment (
        major,
        academic_strengths,
        thinking_style,
        learning_style,
        skills_required,
        career_interests,
        career_tendencies
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["major"],
        json.dumps(data["academic_strengths"]),
        json.dumps(data["thinking_style"]),
        json.dumps(data["learning_style"]),
        json.dumps(data["skills_required"]),
        json.dumps(data["career_interests"]),
        json.dumps(data["career_tendencies"])
    ))

    conn.commit()
    conn.close()




class MajorProfile(BaseModel):
    academic_strengths: List[str]=Field(..., description="List of academic strengths relevant to the major")

    thinking_style: List[str]= Field(..., description="List of thinking styles associated with the major")
    learning_style: List[str]=Field(..., description="List of learning styles associated with the major")
    skills_required: List[str]=Field(..., description="List of skills required for the major")
    career_interests: List[str]=Field(..., description="List of career interests associated with the major")
    career_tendencies: List[str]=Field(..., description="List of career tendencies associated with the major")


llm_respose=llm.with_structured_output(schema=MajorProfile)
print(llm_respose)
@retry(stop=stop_after_attempt(5) , wait=wait_fixed(5))
def category_classifier(major: str) -> str:
    prompt=ChatPromptTemplate.from_template(
"""
You are an Academic Guidance AI acting as a Curriculum Auditor. 
Context:
We are aligning University Majors with a standardized industry-academic taxonomy to ensure students are meeting specific prerequisite benchmarks. Your goal is to find the "Genetic Signature" of the major—the essential skills that distinguish it from all others.

Your task:
Analyze the input major and map it to the SINGLE MOST RELEVANT profile from the taxonomy below. Output must consist ONLY of verbatim values from the taxonomy.

Selection rules:
- Curriculum Designer Persona: Prioritize the technical and theoretical foundations required for degree completion.
- Identifying "DNA" Competencies: Select only the skills that are unique and mandatory for this major. If a skill applies to 50% of all degrees (like 'problem solving'), exclude it.
- Strict Taxonomy Alignment: You are forbidden from creating new categories. Use the exact strings provided in {TAXONOMY_TEXT}.
- Minimalism: Provide the shortest possible list that still accurately defines the major.


Major: '{major}'
"""
)
    chain=prompt|llm_respose
    result=chain.invoke(input={"major":major,"TAXONOMY_TEXT":TAXONOMY_TEXT})
    return {
        "major": major,
        "academic_strengths": result.academic_strengths,
        "thinking_style": result.thinking_style,
        "learning_style": result.learning_style,
        "skills_required": result.skills_required,
        "career_interests": result.career_interests,
        "career_tendencies": result.career_tendencies
    }





def user_profile_prompt(qa: str) -> str:
    prompt=ChatPromptTemplate.from_template("""
You are an Academic Guidance AI tasked with profiling a student's academic and career inclinations based on their Q&A session. Your goal is to evaluate a candidate's Q&A responses against a specific academic taxonomy to determine the most accurate Major alignment. You are not just matching keywords; you are interpreting intent, technical depth, and conceptual alignment to find the "Genetic Signature" of the user's profile.

TASK:
1. EVALUATE: Analyze the provided  (Question and Answer) session.
2. FILTER: Cross-reference the user's technical interests and competency claims against the.
3. VALIDATE: Eliminate generic overlaps and identify the core academic pillar that matches the user’s specific profile.
4. MAP: Select the SINGLE most relevant Major profile based on the highest density of core competencies.



INPUT DATA:
Taxonomy Reference:
{TAXONOMY_TEXT}

Q&A Session Data:
{qa}


""")

    chain = prompt|llm_respose
    result = chain.invoke (input={"qa": qa, "TAXONOMY_TEXT": TAXONOMY_TEXT})
    print(result)
    return{
        "academic_strengths": result.academic_strengths,
        "thinking_style": result.thinking_style,
        "learning_style": result.learning_style,
        "skills_required": result.skills_required,
        "career_interests": result.career_interests,
        "career_tendencies": result.career_tendencies
    }






result = user_profile_prompt("list_of_QA")
# print(result)





