from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from routers import auth, chat, admin, application, university, assessment, university_chatbot, admin_applications, scholarship, services, payment, admin_system
import logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)
import uvicorn

app = FastAPI(
    title="University Recommendation Platform",

)




app.include_router(auth.router)
app.include_router(university.router)
app.include_router(application.router)
app.include_router(assessment.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(university_chatbot.router)
app.include_router(admin_applications.router)
app.include_router(scholarship.router)
app.include_router(services.router)
app.include_router(payment.router)
app.include_router(admin_system.router)


app.mount(
    "/static",
    StaticFiles(directory="frontend/static"),
    name="static"
)




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("sucessfully created the connection")



@app.get("/", response_class=HTMLResponse)
def root():
    """Serve landing page"""
    return FileResponse(path="frontend/static/templates/landing.html")

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return FileResponse(path="frontend/static/templates/login.html")

@app.get("/register", response_class=HTMLResponse)
def register_page():
    return FileResponse(path="frontend/static/templates/register.html")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return FileResponse(path="frontend/static/templates/dashboard.html")

@app.get("/assessment", response_class=HTMLResponse)
def assessment_page():
    return FileResponse(path="frontend/static/templates/assessment.html")

@app.get("/profile", response_class=HTMLResponse)
def profile_page():
    return FileResponse(path="frontend/static/templates/profile.html")

@app.get("/settings", response_class=HTMLResponse)
def settings_page():
    return FileResponse(path="frontend/static/templates/settings.html")

@app.get("/universities",response_class=HTMLResponse)
def university_page():
    return FileResponse(path="frontend/static/templates/university.html")

@app.get("/university-chatbot", response_class=HTMLResponse)
def university_chatbot_page():
    return FileResponse(path="frontend/static/templates/university-chatbot.html")

@app.get("/Apply_university", response_class=HTMLResponse)
def apply_university():
    return FileResponse("frontend/static/templates/apply.html")

@app.get("/applications", response_class=HTMLResponse)
def applications_page():
    return FileResponse("frontend/static/templates/applications.html")

@app.get("/admin/applications", response_class=HTMLResponse)
def admin_applications_page():
    return FileResponse("frontend/static/templates/admin-applications.html")

@app.get("/scholarships", response_class=HTMLResponse)
def scholarships_page():
    return FileResponse("frontend/static/templates/scholarships.html")

@app.get("/scholarships/apply", response_class=HTMLResponse)
def scholarship_apply_page():
    return FileResponse("frontend/static/templates/scholarship-apply.html")

@app.get("/services", response_class=HTMLResponse)
def services_page():
    return FileResponse("frontend/static/templates/services.html")

@app.get("/premium", response_class=HTMLResponse)
def premium_page():
    return FileResponse("frontend/static/templates/premium.html")

@app.get("/admin/portal", response_class=HTMLResponse)
def admin_portal_page():
    return FileResponse("frontend/static/templates/admin-portal.html")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
