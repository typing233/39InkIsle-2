import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_search_books_empty(client, test_user):
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "password123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/v1/books", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []
