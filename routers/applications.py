from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from models import Application,Job,User
from schemas import ApplicationResponse
from security import get_current_user, require_role
from typing import List



router = APIRouter(prefix="/applications",tags=["Applications"])
# SEEKER ONLY - apply to a job
@router.post("/jobs/{job_id}/apply", status_code=status.HTTP_201_CREATED, response_model=ApplicationResponse)
def apply_to_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("seeker"))

):
    #Check job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=404,detail="Job not Found"
        )
    #Check job is open
    if not job.is_open:
        raise HTTPException(
            status_code=400, detail="Job is closed"
        )
    
    # Check if already applied
    existing = db.query(Application).filter(Application.job_id == job_id,Application.seeker_id == current_user.id).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="Already applied"
        )
    # Create application
    application = Application(
        job_id = job_id,
        seeker_id =current_user.id
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application
# SEEKER ONLY — view my applications
@router.get("/mine", response_model=List[ApplicationResponse])
def get_my_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("seeker"))
):
    return db.query(Application).filter(
        Application.seeker_id == current_user.id
    ).all()

# EMPLOYER ONLY — view applications for their job
@router.get("/jobs/{job_id}", response_model=List[ApplicationResponse])
def get_job_applications(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("employer"))
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your job")
    return db.query(Application).filter(
        Application.job_id == job_id
    ).all()

# EMPLOYER ONLY — update application status
@router.patch("/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("employer"))
):
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Check employer owns the job
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if job.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your job")

    if status not in ["pending", "accepted", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    application.status = status
    db.commit()
    db.refresh(application)
    return application