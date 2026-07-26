# Job Board API

A RESTful API for connecting employers and job seekers, built with FastAPI and PostgreSQL.

## Features

- User registration and login with JWT authentication
- Role-based access control (employer / seeker)
- Employers can post, update, close, and delete jobs
- Seekers can browse, search, and apply to jobs
- Search jobs by title, company, or location
- Employers can view and manage applications
- Input validation with Pydantic
- Auto-generated Swagger documentation

## Tech Stack

- **Python** — core language
- **FastAPI** — web framework
- **PostgreSQL** — database
- **SQLAlchemy** — ORM
- **JWT** — authentication
- **bcrypt** — password hashing
- **pg8000** — PostgreSQL driver

## Project Structure

# Job Board API

A RESTful API for connecting employers and job seekers, built with FastAPI and PostgreSQL.

## Features

- User registration and login with JWT authentication
- Role-based access control (employer / seeker)
- Employers can post, update, close, and delete jobs
- Seekers can browse, search, and apply to jobs
- Search jobs by title, company, or location
- Employers can view and manage applications
- Input validation with Pydantic
- Auto-generated Swagger documentation

## Tech Stack

- **Python** — core language
- **FastAPI** — web framework
- **PostgreSQL** — database
- **SQLAlchemy** — ORM
- **JWT** — authentication
- **bcrypt** — password hashing
- **pg8000** — PostgreSQL driver

## Project Structure

job_board_api/
├── main.py # FastAPI app entry point
├── database.py # Database connection and session
├── models.py # SQLAlchemy database models
├── schemas.py # Pydantic request/response schemas
├── security.py # JWT and password hashing utilities
├── config.py # Configuration settings
└── routers/
├── auth.py # Register and login endpoints
├── jobs.py # Job CRUD endpoints
└── applications.py # Application endpoints

## Database Design

Three tables with relationships:

- **users** — stores employers and seekers with roles
- **jobs** — job listings linked to employers
- **applications** — applications linking seekers to jobs

## API Endpoints

### Auth
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/auth/register` | Public | Register as employer or seeker |
| POST | `/auth/login` | Public | Login and get JWT token |

### Jobs
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/jobs` | Public | Browse all open jobs |
| GET | `/jobs?search=` | Public | Search jobs by title |
| GET | `/jobs?location=` | Public | Filter jobs by location |
| GET | `/jobs/{id}` | Public | Get single job |
| POST | `/jobs` | Employer | Post a new job |
| PUT | `/jobs/{id}` | Employer | Update a job |
| PATCH | `/jobs/{id}/close` | Employer | Close a job |
| DELETE | `/jobs/{id}` | Employer | Delete a job |

### Applications
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/applications/jobs/{id}/apply` | Seeker | Apply to a job |
| GET | `/applications/mine` | Seeker | View my applications |
| GET | `/applications/jobs/{id}` | Employer | View job applicants |
| PATCH | `/applications/{id}/status` | Employer | Accept or reject application |

## How to Run Locally

**1. Clone the repository:**
```bash
git clone https://github.com/YOUR-USERNAME/job-board-api.git
cd job-board-api
```

**2. Install dependencies:**
```bash
pip install fastapi uvicorn sqlalchemy pg8000 passlib bcrypt python-jose
```

**3. Set up PostgreSQL:**
- Install PostgreSQL
- Create a database called `job_board_db`
- Update `database.py` with your credentials

**4. Run the server:**
```bash
uvicorn main:app --reload
```

**5. Open Swagger UI:**

http://localhost:8000/docs

## How to Test the API

1. Register as employer: `POST /auth/register` with `role: "employer"`
2. Register as seeker: `POST /auth/register` with `role: "seeker"`
3. Login to get JWT token: `POST /auth/login`
4. Click Authorize in Swagger UI and paste the token
5. Employer posts a job: `POST /jobs`
6. Seeker applies: `POST /applications/jobs/{id}/apply`
7. Employer views applicants: `GET /applications/jobs/{id}`
8. Employer accepts: `PATCH /applications/{id}/status` with `status: accepted`