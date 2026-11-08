from fastapi import APIRouter,HTTPException,status,Query,Depends
from schemas import ExternalJob,ExternalJobResponse
from dotenv import load_dotenv
import httpx
import os

load_dotenv()

router = APIRouter(prefix="/External_jobs",tags=["ExtrenalJobs"])

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")


def transform_job(job: dict) -> dict:
    return {
        "id": job["id"],
        "title": job["title"],
        "company": job.get("company", {}).get("display_name"),
        "location": job.get("location", {}).get("display_name"),
        "description": job.get("description"),
        "contract_time": job.get("contract_time"),
        "created": job.get("created"),
        "redirect_url": job.get("redirect_url"),
        "category": job.get("category", {}).get("label"),
        "salary_is_predicted": job.get("salary_is_predicted") }

@router.get("/",response_model=ExternalJobResponse)

async def external_job(Job_title: str = Query(...,min_length=2),
                       location: str = Query("India"),
                       page: int = Query(1,ge=1)):

    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        raise HTTPException(status_code=500,detail="Adzuna credentials are expired or not verified")

    
    url = (
        f"https://api.adzuna.com/v1/api/jobs/in/search/{page}"
    )

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": Job_title,
        "where": location,
        "results_per_page": 20
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url,params=params)

        response.raise_for_status()

        data = response.json()

        cleaned_jobs = [transform_job(job) for job in data.get("results",[])]
    

        return {
            "count": data.get("count", 0),
            "jobs": cleaned_jobs
        }

    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502,detail="Adzuna API returned an error")

    except httpx.RequestError:
        raise HTTPException(status_code=502,detail="Could not connect to Adzuna API")
    
                       




