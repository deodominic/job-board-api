from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from database.db import engine, Base
from routers import auth, jobs, applications, external_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await external_jobs.close_client()


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
- External jobs from Adzuna, proxied and cached
    """,
    version="2.1.0",
    lifespan=lifespan,
)

# Lets the React app (a different origin) call this API from the browser.
# We authenticate with an Authorization header, not cookies, so credentials stay off.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(external_jobs.router)


@app.get("/", tags=["Root"])
def root():
    return {"message": "Job Board API is running", "docs": "/docs"}
