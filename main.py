from fastapi import FastAPI
from database import engine, Base
from routers import auth, jobs, applications

app = FastAPI(
    title="Job Board API",
    description="""
A REST API for connecting employers and job seekers.

## Features
- User registration and login with JWT authentication
- Role-based access control (employer / seeker)
- Employers can post, update, and close jobs
- Seekers can browse, search, and apply to jobs
- Employers can view and manage applications
    """,
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)

@app.get("/", tags=["Root"])
def root():
    return {"message": "Job Board API is running", "docs": "/docs"}