from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import Job, User
from schemas import JobCreate, JobResponse
from security import get_current_user, require_role
from typing import List,Optional

router = APIRouter(prefix="/jobs", tags=["Jobs"])

# PUBLIC — anyone can browse open jobs
@router.get("/", response_model=List[JobResponse])
def get_jobs(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    location: Optional[str] = None,
    company: Optional[str] = None
):
    query = db.query(Job).filter(Job.is_open == True)

    if search:
        query = query.filter(Job.title.ilike(f"%{search}%"))

    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))

    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))

    return query.all()
# PUBLIC — get single job
@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# EMPLOYER ONLY — post a new job
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=JobResponse)
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("employer"))
):
    new_job = Job(
        title=job.title,
        description=job.description,
        company=job.company,
        location=job.location,
        employer_id=current_user.id
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

# EMPLOYER ONLY — update their own job
@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("employer"))
):
    db_job = db.query(Job).filter(Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    if db_job.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your job")
    db_job.title = job.title
    db_job.description = job.description
    db_job.company = job.company
    db_job.location = job.location
    db.commit()
    db.refresh(db_job)
    return db_job

# EMPLOYER ONLY — close a job
@router.patch("/{job_id}/close", response_model=JobResponse)
def close_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("employer"))
):
    db_job = db.query(Job).filter(Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    if db_job.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your job")
    db_job.is_open = False
    db.commit()
    db.refresh(db_job)
    return db_job

# EMPLOYER ONLY — delete their own job
@router.delete("/{job_id}", status_code=200)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("employer"))
):
    db_job = db.query(Job).filter(Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    if db_job.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your job")
    db.delete(db_job)
    db.commit()
    return {"message": "Job deleted"}