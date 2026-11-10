# Backend update: connect the API to the React frontend

Copy these files over your repo (same folders), commit, push. Render redeploys automatically.
**No database migration is needed** (no new columns).

## Before you push: set these on Render (Environment tab)
| Variable | Value |
|---|---|
| `SECRET_KEY`, `DATABASE_URL` | already set |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | from your Adzuna dashboard |
| `CORS_ORIGINS` | your frontend's exact URL, e.g. `https://my-jobboard.vercel.app` (several allowed, comma-separated). `http://localhost:5173` is allowed by default. |

## What changed and why
| File | Change |
|---|---|
| `main.py` | **CORS middleware** (without it the browser blocks every call from the React app); closes the shared HTTP client on shutdown |
| `requirements.txt` | **adds `httpx`**. Your pushed Adzuna router imports it, so Render crashes on start without it |
| `config.py` | Adzuna and CORS settings; fails fast with a clear message if `SECRET_KEY` is missing |
| `routers/external_jobs.py` | Hardened Adzuna proxy at **`/external-jobs/`** (was `/External_jobs/`): optional keyword, filters, 5-minute cache, proper 429/502/504, never logs your API key |
| `routers/jobs.py` | Newest first; search matches title, company and description (and treats `%` and `_` literally); **new `GET /jobs/mine`** (all my jobs incl. closed); deleting a job **that has applications now returns a clear 409** instead of a 500 |
| `routers/applications.py` | Responses include job title/company and (for employers) the applicant's email; no N+1 queries |
| `routers/auth.py` | Emails are case-insensitive (`A@x.com` and `a@x.com` are one account) |
| `schemas.py`, `database/models.py` | `created_at` on jobs and applications; the extra application fields (read-only properties, not columns) |
| `security.py` | `datetime.utcnow()` replaced (deprecated) |
| `tests/` | 38 tests. Run: `pip install -r requirements-dev.txt` then `pytest` |

## Behaviour changes to know about
- The Adzuna URL changed to `/external-jobs/` with `?search=` (was `/External_jobs/?Job_title=`). The new frontend uses the new one; deploy the backend first.
- Employer emails are now exposed to the employer who owns the job, only for people who applied to it.

## Not included (needs a migration tool such as Alembic)
Pagination with totals, job type/salary/category/experience columns, a unique constraint on (job, seeker), saved jobs, refresh tokens.
