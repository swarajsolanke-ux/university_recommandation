from fastapi import FastAPI,Request
from pydantic import BaseModel,Field
from typing import List, Optional, Dict
from test import llm_respose, TAXONOMY_TEXT, category_classifier,insert_into_db,VectorStore,user_profile_prompt
from test4 import User_built_prompt, build_prompt_with_score, fetch_majors,recommend_majors
import requests
import uvicorn
# from schemas import AssessmentRequest
import logging
from test2 import get_category_id, main_category_prompt,insert_category
import sqlite3

from test4 import insert_into_db_score,question_genrate_prompt,list_category
app=FastAPI()

vector=VectorStore()
class UserQARequest(BaseModel):
    qa:list

class majorRequest(BaseModel):
    major:List[str]

class CategoriesRequest(BaseModel):
    categories:List[str]

class QuestionGenerateRequest(BaseModel):
    list_category: List[str] = Field(
        default=list_category,
        description="List of categories to generate questions for"
    )


# @app.get("/user_major")
# def major_recomandatio(request: UserQARequest):
#     profile=user_profile_prompt(request.qa)
#     return profile

@app.post("/add_major")
def major_add(request: majorRequest):
    major_name=request.major
    for major in major_name:
        data=category_classifier(major)

        logging.info("data  return ",data)
        insert_into_db(data)
        parts=[]
        for key, value in data.items():
            if key=="major":
                continue
            if isinstance(value, list):
                value_str = ", ".join(value) if value else "None"
            else:
                value_str = str(value)

            parts.append(f"{value_str}")

        data_str = " | ".join(parts)

        print(data_str)
        logging.info("Data inserted into database")
        vector.store_user_embeddings(major=major, major_traits=data_str)
    return data



@app.post("/db_scoring")
def db_scoring(request: majorRequest):
    major_name=request.major
    for major in major_name:
        classify_category=main_category_prompt(major)
        category_name = classify_category["recommanded_category"]
        catgeory_id=get_category_id(category_name)
        data=build_prompt_with_score(major)
        logging.info("data  return ",data)
        result=insert_into_db_score(data,catgeory_id)
        print(result)
    return f"sucessfully inserted"

    





@app.post("/add-category")
def category_add(request:CategoriesRequest):
    categories_list=request.categories
    for category in categories_list:
        category_inserted=insert_category(category_name=category)
        print(category_inserted)
    
    return f"category_inserted sucessfully"



@app.post("/assessment/evaluate")
async def recommanded_major(request: Request):
    payload = await request.json()


    user_data = "\n".join(
        f"Q: {item['question']}\nA: {item['answer']}"
        for item in payload["user_data"]
    )
    print(user_data)
    
    user_traits = User_built_prompt(user_data)

    
    major_data = fetch_majors()

   
    recommendations = recommend_majors(user_traits, major_data)

  
    formatted = []
    for rec in recommendations:
        formatted.append({
            "major_name": rec["major"],
            "match_percentage": int(rec["score"] * 100),
            "difficulty_level": "Medium",
            "estimated_cost": "$2500",
            "study_duration": "3–4 years",
            "roadmap": [
                "Build strong fundamentals",
                "Develop core skills",
                "Work on projects",
                "Gain industry experience"
            ]
        })

    return {
        "recommendations": formatted
    }





@app.post("/genearte-question")
def genarate_question(request:QuestionGenerateRequest):
    result=question_genrate_prompt(request.list_category)
    return result











    



# @app.post("/evaluate")
# async def evaluate_assessment(payload: AssessmentRequest):
#     """
#     Receives question-answer pairs from frontend
#     """

#     # Example: Combine answers for AI / embedding
#     combined_text = "\n".join(
#         f"Q: {item.question}\nA: {item.answer}"
#         for item in payload.user_data
#     )
#     user_traits=user_profile_prompt(combined_text)

#     parts=[]
#     for key, value in user_traits.items():
#         if key=="major":
#             continue
#         if isinstance(value, list):
#             value_str = ", ".join(value) if value else "None"
#         else:
#             value_str = str(value)

#         parts.append(f"{value_str}")

#     data_str = " | ".join(parts)
#     results=vector.similarity_search(user_traits=data_str)
#     print(results)
#     return results

if __name__=="__main__":    
    uvicorn.run(app, host="0.0.0.0", port=5000)


