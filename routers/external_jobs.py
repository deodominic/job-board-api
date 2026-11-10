import logging
import time
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

from config import (
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    ADZUNA_CACHE_TTL_SECONDS,
    ADZUNA_COUNTRY,
)
from schemas import ExternalJob, ExternalJobResponse

logger = logging.getLogger(__name__)

# SECURITY: httpx logs every request URL at INFO, and Adzuna requires app_key in the query
# string, so this would write your key into the logs. Keep httpx at WARNING or higher.
logging.getLogger("httpx").setLevel(logging.WARNING)

router = APIRouter(prefix="/external-jobs", tags=["External Jobs"])

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
RESULTS_PER_PAGE = 20
CACHE_MAX_ENTRIES = 500

# ---------------------------------------------------------------- HTTP client
# One shared client = connection reuse (faster than a new client per request).
_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
    return _client


async def close_client() -> None:
    """Call from the app's shutdown/lifespan hook."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


# ---------------------------------------------------------------- tiny TTL cache
# In-memory, per process. Fine for one Render instance; move to Redis if you scale out.
_cache: dict = {}


def _cache_get(key):
    entry = _cache.get(key)
    if entry and entry[0] > time.monotonic():
        return entry[1]
    _cache.pop(key, None)
    return None


def _cache_set(key, value) -> None:
    if len(_cache) >= CACHE_MAX_ENTRIES:
        now = time.monotonic()
        for k in [k for k, (exp, _) in _cache.items() if exp <= now]:
            _cache.pop(k, None)
        if len(_cache) >= CACHE_MAX_ENTRIES:       # still full: drop oldest-expiring
            _cache.pop(min(_cache, key=lambda k: _cache[k][0]), None)
    _cache[key] = (time.monotonic() + ADZUNA_CACHE_TTL_SECONDS, value)


# ---------------------------------------------------------------- transform
def transform_job(job: dict) -> Optional[dict]:
    """Map one Adzuna result to our shape. Returns None if it is unusable."""
    job_id, title, url = job.get("id"), job.get("title"), job.get("redirect_url")
    if not job_id or not title or not url:
        return None
    if not str(url).startswith(("https://", "http://")):   # never pass odd schemes to <a href>
        return None
    return {
        "id": str(job_id),
        "title": title,
        "company": (job.get("company") or {}).get("display_name"),
        "location": (job.get("location") or {}).get("display_name"),
        "description": job.get("description"),
        "contract_time": job.get("contract_time"),
        "contract_type": job.get("contract_type"),
        "category": (job.get("category") or {}).get("label"),
        "created": job.get("created"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "salary_is_predicted": str(job.get("salary_is_predicted", "0")) == "1",
        "redirect_url": url,
    }


# ---------------------------------------------------------------- endpoint
@router.get("/", response_model=ExternalJobResponse)
async def external_jobs(
    search: Optional[str] = Query(None, min_length=2, max_length=100),
    location: Optional[str] = Query(None, max_length=100),
    category: Optional[str] = Query(None, max_length=60),      # Adzuna category tag, e.g. "it-jobs"
    job_type: Optional[Literal["full_time", "part_time"]] = None,
    salary_min: Optional[int] = Query(None, ge=0),
    sort_by: Optional[Literal["date", "salary", "relevance"]] = None,
    page: int = Query(1, ge=1, le=50),
):
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        logger.error("Adzuna credentials are not configured")
        raise HTTPException(status_code=503, detail="External jobs are temporarily unavailable")

    # Build only the params the caller actually set.
    query = {"results_per_page": RESULTS_PER_PAGE}
    if search:
        query["what"] = search.strip()
    if location:
        query["where"] = location.strip()
    if category:
        query["category"] = category
    if job_type:
        query[job_type] = 1                    # full_time=1 or part_time=1
    if salary_min:
        query["salary_min"] = salary_min
    if sort_by:
        query["sort_by"] = sort_by

    cache_key = (ADZUNA_COUNTRY, page, tuple(sorted(query.items())))   # credentials NOT in key
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{ADZUNA_BASE_URL}/{ADZUNA_COUNTRY}/search/{page}"
    params = {"app_id": ADZUNA_APP_ID, "app_key": ADZUNA_APP_KEY, **query}

    try:
        response = await get_client().get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        logger.warning("Adzuna request timed out")
        raise HTTPException(status_code=504, detail="External jobs provider timed out") from None
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.error("Adzuna returned HTTP %s", code)          # log status only, never the URL (it has the key)
        if code == 429:
            raise HTTPException(status_code=429, detail="Too many requests, try again shortly") from None
        raise HTTPException(status_code=502, detail="External jobs provider error") from None
    except (httpx.RequestError, ValueError):
        logger.error("Adzuna request failed")
        raise HTTPException(status_code=502, detail="Could not reach external jobs provider") from None

    jobs = [j for j in (transform_job(r) for r in data.get("results", [])) if j]
    count = int(data.get("count", 0))
    result = {
        "count": count,
        "page": page,
        "has_more": page * RESULTS_PER_PAGE < count,
        "jobs": jobs,
    }
    _cache_set(cache_key, result)
    return result
