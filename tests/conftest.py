import os
import tempfile

# Must be set before the app is imported: the app reads its settings at import time.
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ADZUNA_APP_ID"] = "test-id"
os.environ["ADZUNA_APP_KEY"] = "SUPERSECRETKEY"
os.environ["CORS_ORIGINS"] = "http://localhost:5173,https://app.example.com/"

import pytest
from fastapi.testclient import TestClient

from database.db import Base, engine
from main import app
from routers import external_jobs


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    external_jobs._cache.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


class Users:
    def __init__(self, client):
        self.client = client

    def make(self, email, role, password="secret1"):
        r = self.client.post("/auth/register", json={"email": email, "password": password, "role": role})
        assert r.status_code == 201, r.text
        token = self.client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}, r.json()["id"]


@pytest.fixture
def users(client):
    return Users(client)


def post_job(client, headers, title="Backend Developer", company="Acme", location="Kochi", description="Build APIs"):
    r = client.post("/jobs/", headers=headers, json={"title": title, "company": company, "location": location, "description": description})
    assert r.status_code == 201, r.text
    return r.json()
