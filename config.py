from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Fail at startup with a clear message instead of a 500 on the first login.
    raise RuntimeError("SECRET_KEY is not set. Add it to your .env file or your host's environment variables.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# --- Adzuna (external jobs) ---
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_COUNTRY = os.getenv("ADZUNA_COUNTRY", "in")  # in, gb, us, ...
ADZUNA_CACHE_TTL_SECONDS = int(os.getenv("ADZUNA_CACHE_TTL_SECONDS", "300"))

# --- CORS ---
# Comma-separated browser origins allowed to call this API, e.g.
# CORS_ORIGINS=http://localhost:5173,https://my-jobboard.vercel.app
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
