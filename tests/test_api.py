import time

from tests.conftest import post_job


# ---------------------------------------------------------------- CORS
class TestCors:
    def test_allowed_origin_gets_headers_on_preflight(self, client):
        r = client.options("/jobs/", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        })
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_trailing_slash_in_env_is_ignored(self, client):
        r = client.get("/jobs/", headers={"Origin": "https://app.example.com"})
        assert r.headers["access-control-allow-origin"] == "https://app.example.com"

    def test_unknown_origin_is_not_allowed(self, client):
        r = client.get("/jobs/", headers={"Origin": "https://evil.example.net"})
        assert "access-control-allow-origin" not in r.headers

    def test_every_method_the_frontend_uses_is_allowed(self, client):
        for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
            r = client.options("/jobs/1", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": method})
            assert r.status_code == 200, method


# ---------------------------------------------------------------- auth
class TestAuth:
    def test_emails_are_case_insensitive(self, client, users):
        users.make("Kevin@Example.com", "seeker")
        r = client.post("/auth/register", json={"email": "kevin@example.com", "password": "secret1", "role": "seeker"})
        assert r.status_code == 400 and "already registered" in r.json()["detail"]
        ok = client.post("/auth/login", json={"email": "KEVIN@example.COM", "password": "secret1"})
        assert ok.status_code == 200

    def test_register_stores_lowercase_email(self, client, users):
        _, _ = users.make("MiXed@Example.com", "employer")
        headers, _ = users.make("other@example.com", "seeker")
        apps = client.get("/applications/mine", headers=headers)
        assert apps.status_code == 200

    def test_wrong_password_is_401(self, client, users):
        users.make("a@example.com", "seeker")
        assert client.post("/auth/login", json={"email": "a@example.com", "password": "nope"}).status_code == 401

    def test_role_cannot_be_chosen_freely(self, client):
        r = client.post("/auth/register", json={"email": "x@example.com", "password": "secret1", "role": "admin"})
        assert r.status_code == 422


# ---------------------------------------------------------------- jobs
class TestJobs:
    def test_list_is_newest_first_and_includes_created_at(self, client, users):
        h, _ = users.make("boss@example.com", "employer")
        first = post_job(client, h, title="First")
        second = post_job(client, h, title="Second")
        jobs = client.get("/jobs/").json()
        assert [j["id"] for j in jobs] == [second["id"], first["id"]]
        assert jobs[0]["created_at"]

    def test_search_matches_title_company_and_description(self, client, users):
        h, _ = users.make("boss@example.com", "employer")
        post_job(client, h, title="Python Dev", company="Alpha", description="x")
        post_job(client, h, title="Designer", company="Pythonic Co", description="x")
        post_job(client, h, title="Tester", company="Beta", description="needs python skills")
        post_job(client, h, title="Chef", company="Gamma", description="food")
        titles = {j["title"] for j in client.get("/jobs/", params={"search": "python"}).json()}
        assert titles == {"Python Dev", "Designer", "Tester"}

    def test_search_treats_percent_and_underscore_literally(self, client, users):
        h, _ = users.make("boss@example.com", "employer")
        post_job(client, h, title="Plain job")
        post_job(client, h, title="100% remote")
        assert [j["title"] for j in client.get("/jobs/", params={"search": "%"}).json()] == ["100% remote"]
        assert client.get("/jobs/", params={"search": "_"}).json() == []

    def test_location_and_company_filters(self, client, users):
        h, _ = users.make("boss@example.com", "employer")
        post_job(client, h, location="Kochi", company="Acme")
        post_job(client, h, location="Delhi", company="Other")
        assert len(client.get("/jobs/", params={"location": "koch"}).json()) == 1
        assert len(client.get("/jobs/", params={"company": "other"}).json()) == 1

    def test_closed_jobs_leave_the_public_list(self, client, users):
        h, _ = users.make("boss@example.com", "employer")
        job = post_job(client, h)
        assert client.patch(f"/jobs/{job['id']}/close", headers=h).status_code == 200
        assert client.get("/jobs/").json() == []
        assert client.get(f"/jobs/{job['id']}").json()["is_open"] is False

    def test_mine_returns_only_my_jobs_including_closed(self, client, users):
        a, _ = users.make("a@example.com", "employer")
        b, _ = users.make("b@example.com", "employer")
        mine_open = post_job(client, a, title="Mine open")
        mine_closed = post_job(client, a, title="Mine closed")
        post_job(client, b, title="Theirs")
        client.patch(f"/jobs/{mine_closed['id']}/close", headers=a)
        got = client.get("/jobs/mine", headers=a).json()
        assert {j["title"] for j in got} == {"Mine open", "Mine closed"}
        assert {j["is_open"] for j in got} == {True, False}
        assert mine_open["id"] in [j["id"] for j in got]

    def test_mine_is_employer_only_and_not_swallowed_by_job_id_route(self, client, users):
        s, _ = users.make("s@example.com", "seeker")
        assert client.get("/jobs/mine", headers=s).status_code == 403
        assert client.get("/jobs/mine").status_code in (401, 403)  # no token
        # if "mine" were parsed as {job_id} this would be a 422 int-parsing error
        e, _ = users.make("e@example.com", "employer")
        assert client.get("/jobs/mine", headers=e).status_code == 200

    def test_only_the_owner_can_edit_close_or_delete(self, client, users):
        a, _ = users.make("a@example.com", "employer")
        b, _ = users.make("b@example.com", "employer")
        job = post_job(client, a)
        body = {"title": "Hacked", "company": "x", "location": "x", "description": "x"}
        assert client.put(f"/jobs/{job['id']}", headers=b, json=body).status_code == 403
        assert client.patch(f"/jobs/{job['id']}/close", headers=b).status_code == 403
        assert client.delete(f"/jobs/{job['id']}", headers=b).status_code == 403
        assert client.get(f"/jobs/{job['id']}").json()["title"] == job["title"]

    def test_seekers_cannot_post(self, client, users):
        s, _ = users.make("s@example.com", "seeker")
        r = client.post("/jobs/", headers=s, json={"title": "t", "company": "c", "location": "l", "description": "d"})
        assert r.status_code == 403

    def test_delete_without_applications_works(self, client, users):
        h, _ = users.make("boss@example.com", "employer")
        job = post_job(client, h)
        assert client.delete(f"/jobs/{job['id']}", headers=h).status_code == 200
        assert client.get(f"/jobs/{job['id']}").status_code == 404

    def test_delete_with_applications_is_a_clear_409_not_a_500(self, client, users):
        h, _ = users.make("boss@example.com", "employer")
        s, _ = users.make("s@example.com", "seeker")
        job = post_job(client, h)
        client.post(f"/applications/jobs/{job['id']}/apply", headers=s)
        r = client.delete(f"/jobs/{job['id']}", headers=h)
        assert r.status_code == 409
        assert "Close it instead" in r.json()["detail"]
        assert client.get(f"/jobs/{job['id']}").status_code == 200  # still there
        assert len(client.get(f"/applications/jobs/{job['id']}", headers=h).json()) == 1  # applicants intact

    def test_blank_fields_are_rejected(self, client, users):
        h, _ = users.make("boss@example.com", "employer")
        r = client.post("/jobs/", headers=h, json={"title": "  ", "company": "c", "location": "l", "description": "d"})
        assert r.status_code == 422


# ---------------------------------------------------------------- applications
class TestApplications:
    def _setup(self, client, users):
        boss, boss_id = users.make("boss@example.com", "employer")
        seeker, seeker_id = users.make("seeker@example.com", "seeker")
        job = post_job(client, boss, title="Data Analyst", company="Acme")
        return boss, boss_id, seeker, seeker_id, job

    def test_my_applications_include_job_title_and_company(self, client, users):
        boss, _, seeker, _, job = self._setup(client, users)
        client.post(f"/applications/jobs/{job['id']}/apply", headers=seeker)
        mine = client.get("/applications/mine", headers=seeker).json()
        assert len(mine) == 1
        assert mine[0]["job_title"] == "Data Analyst" and mine[0]["job_company"] == "Acme"
        assert mine[0]["status"] == "pending" and mine[0]["created_at"]

    def test_employer_sees_applicant_email(self, client, users):
        boss, _, seeker, seeker_id, job = self._setup(client, users)
        client.post(f"/applications/jobs/{job['id']}/apply", headers=seeker)
        got = client.get(f"/applications/jobs/{job['id']}", headers=boss).json()
        assert got[0]["seeker_email"] == "seeker@example.com" and got[0]["seeker_id"] == seeker_id

    def test_other_employers_cannot_see_applicants(self, client, users):
        boss, _, seeker, _, job = self._setup(client, users)
        other, _ = users.make("other@example.com", "employer")
        client.post(f"/applications/jobs/{job['id']}/apply", headers=seeker)
        assert client.get(f"/applications/jobs/{job['id']}", headers=other).status_code == 403

    def test_seekers_only_see_their_own_applications(self, client, users):
        boss, _, seeker, _, job = self._setup(client, users)
        other, _ = users.make("other@example.com", "seeker")
        client.post(f"/applications/jobs/{job['id']}/apply", headers=seeker)
        assert client.get("/applications/mine", headers=other).json() == []

    def test_cannot_apply_twice_to_closed_or_missing_jobs(self, client, users):
        boss, _, seeker, _, job = self._setup(client, users)
        assert client.post(f"/applications/jobs/{job['id']}/apply", headers=seeker).status_code == 201
        assert client.post(f"/applications/jobs/{job['id']}/apply", headers=seeker).json()["detail"] == "Already applied"
        assert client.post("/applications/jobs/9999/apply", headers=seeker).status_code == 404
        client.patch(f"/jobs/{job['id']}/close", headers=boss)
        other, _ = users.make("other@example.com", "seeker")
        assert client.post(f"/applications/jobs/{job['id']}/apply", headers=other).json()["detail"] == "Job is closed"

    def test_employers_cannot_apply(self, client, users):
        boss, _, _, _, job = self._setup(client, users)
        assert client.post(f"/applications/jobs/{job['id']}/apply", headers=boss).status_code == 403

    def test_status_update_by_owner_only(self, client, users):
        boss, _, seeker, _, job = self._setup(client, users)
        other, _ = users.make("other@example.com", "employer")
        app_id = client.post(f"/applications/jobs/{job['id']}/apply", headers=seeker).json()["id"]
        assert client.patch(f"/applications/{app_id}/status", headers=other, params={"status": "accepted"}).status_code == 403
        assert client.patch(f"/applications/{app_id}/status", headers=boss, params={"status": "bogus"}).status_code == 400
        r = client.patch(f"/applications/{app_id}/status", headers=boss, params={"status": "accepted"})
        assert r.status_code == 200 and r.json()["status"] == "accepted" and r.json()["job_title"] == "Data Analyst"

    def test_unauthenticated_requests_are_rejected(self, client):
        assert client.get("/applications/mine").status_code in (401, 403)
        assert client.post("/applications/jobs/1/apply").status_code in (401, 403)

    def test_tampered_token_is_rejected(self, client):
        r = client.get("/applications/mine", headers={"Authorization": "Bearer not.a.token"})
        assert r.status_code == 401


# ---------------------------------------------------------------- external jobs (Adzuna)
import logging
import httpx
from routers import external_jobs as ej


def adzuna(handler):
    ej._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))


def sample(count=45):
    return {"count": count, "results": [
        {"id": 123, "title": "Python Dev", "company": None, "location": {"display_name": "Kochi"}, "description": "snippet",
         "redirect_url": "https://adzuna.in/x", "category": {"label": "IT Jobs"}, "salary_min": 500000, "salary_max": 800000,
         "salary_is_predicted": "1", "contract_time": "full_time"},
        {"id": 2, "title": "Bad link", "redirect_url": "javascript:alert(1)"},
        {"title": "No id", "redirect_url": "https://x"},
    ]}


class TestExternalJobs:
    def test_shapes_the_response_and_drops_unusable_results(self, client):
        sent = []
        adzuna(lambda req: (sent.append(req), httpx.Response(200, json=sample()))[1])
        r = client.get("/external-jobs/", params={"search": "python", "job_type": "full_time", "page": 2})
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 45 and body["page"] == 2 and body["has_more"] is True
        assert body["attribution"] == "Jobs by Adzuna"
        assert len(body["jobs"]) == 1
        job = body["jobs"][0]
        assert job["id"] == "123" and job["company"] is None and job["salary_is_predicted"] is True
        assert job["category"] == "IT Jobs" and job["salary_min"] == 500000
        params = dict(sent[0].url.params)
        assert params["what"] == "python" and params["full_time"] == "1" and params["app_key"] == "SUPERSECRETKEY"
        assert "/jobs/in/search/2" in str(sent[0].url)

    def test_keyword_is_optional(self, client):
        sent = []
        adzuna(lambda req: (sent.append(req), httpx.Response(200, json=sample()))[1])
        assert client.get("/external-jobs/").status_code == 200
        assert "what" not in dict(sent[0].url.params)

    def test_repeat_searches_are_served_from_cache(self, client):
        calls = []
        adzuna(lambda req: (calls.append(1), httpx.Response(200, json=sample()))[1])
        for _ in range(3):
            client.get("/external-jobs/", params={"search": "python"})
        assert len(calls) == 1
        client.get("/external-jobs/", params={"search": "java"})
        assert len(calls) == 2

    def test_upstream_failures_map_to_clear_statuses(self, client):
        adzuna(lambda req: httpx.Response(500, json={}))
        assert client.get("/external-jobs/", params={"search": "a1"}).status_code == 502
        adzuna(lambda req: httpx.Response(429, json={}))
        assert client.get("/external-jobs/", params={"search": "a2"}).status_code == 429
        def timeout(req): raise httpx.ReadTimeout("slow")
        adzuna(timeout)
        assert client.get("/external-jobs/", params={"search": "a3"}).status_code == 504
        adzuna(lambda req: httpx.Response(200, text="<html>not json</html>"))
        assert client.get("/external-jobs/", params={"search": "a4"}).status_code == 502

    def test_failures_are_not_cached(self, client):
        calls = []
        def handler(req):
            calls.append(1)
            return httpx.Response(500, json={}) if len(calls) == 1 else httpx.Response(200, json=sample())
        adzuna(handler)
        assert client.get("/external-jobs/", params={"search": "retry"}).status_code == 502
        assert client.get("/external-jobs/", params={"search": "retry"}).status_code == 200

    def test_the_api_key_never_reaches_logs_or_responses(self, client, caplog):
        adzuna(lambda req: httpx.Response(200, json=sample()))
        with caplog.at_level(logging.DEBUG):
            r = client.get("/external-jobs/", params={"search": "python"})
        assert "SUPERSECRETKEY" not in r.text
        assert "SUPERSECRETKEY" not in caplog.text

    def test_bad_input_is_rejected(self, client):
        assert client.get("/external-jobs/", params={"job_type": "x"}).status_code == 422
        assert client.get("/external-jobs/", params={"page": 0}).status_code == 422
        assert client.get("/external-jobs/", params={"page": 999}).status_code == 422
        assert client.get("/external-jobs/", params={"search": "a"}).status_code == 422

    def test_missing_credentials_give_503_without_leaking_details(self, client, monkeypatch):
        monkeypatch.setattr(ej, "ADZUNA_APP_KEY", None)
        r = client.get("/external-jobs/", params={"search": "python"})
        assert r.status_code == 503 and "credential" not in r.text.lower()

    def test_cache_stays_bounded(self, client):
        adzuna(lambda req: httpx.Response(200, json=sample()))
        for i in range(ej.CACHE_MAX_ENTRIES + 25):
            client.get("/external-jobs/", params={"search": f"q{i:04d}"})
        assert len(ej._cache) <= ej.CACHE_MAX_ENTRIES
