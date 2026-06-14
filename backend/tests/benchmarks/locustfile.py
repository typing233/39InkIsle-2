from locust import HttpUser, task, between


class InkIsleUser(HttpUser):
    wait_time = between(1, 3)
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
        self.client.get("/api/v1/books?page=1&page_size=20", headers=self._headers())

    @task(3)
    def search_books(self):
        self.client.get("/api/v1/books?q=python&page=1", headers=self._headers())

    @task(2)
    def get_me(self):
        self.client.get("/api/v1/users/me", headers=self._headers())

    @task(1)
    def health_check(self):
        self.client.get("/api/v1/health")
