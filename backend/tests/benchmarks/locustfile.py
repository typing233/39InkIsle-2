"""
Performance benchmark suite for InkIsle.

Run: locust -f backend/tests/benchmarks/locustfile.py --host http://localhost:8000
"""
from locust import HttpUser, task, between


class InkIsleUser(HttpUser):
    wait_time = between(0.5, 2)
    token = None

    def on_start(self):
        resp = self.client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "password123",
        })
        if resp.status_code == 200:
            self.token = resp.json()["access_token"]

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(5)
    def browse_library(self):
        self.client.get("/api/v1/books?page=1&page_size=24&sort_by=created_at&sort_order=desc", headers=self._headers())

    @task(4)
    def search_fulltext(self):
        self.client.get("/api/v1/books?q=fantasy&page=1&page_size=24", headers=self._headers())

    @task(2)
    def search_fuzzy(self):
        self.client.get("/api/v1/books?q=fantasi&q_fuzzy=true&page=1", headers=self._headers())

    @task(3)
    def search_filtered(self):
        self.client.get("/api/v1/books?format=epub&rating_min=3&sort_by=avg_rating&sort_order=desc", headers=self._headers())

    @task(2)
    def list_collections(self):
        self.client.get("/api/v1/collections", headers=self._headers())

    @task(2)
    def get_reviews(self):
        self.client.get("/api/v1/books?page=1&page_size=1", headers=self._headers())

    @task(1)
    def opds_recent(self):
        self.client.get("/opds/v1/catalog/recent?page=1", auth=("testuser", "password123"))

    @task(1)
    def opds2_publications(self):
        self.client.get("/opds/v2/publications.json?page=1", auth=("testuser", "password123"))

    @task(1)
    def health_check(self):
        self.client.get("/api/v1/health")
