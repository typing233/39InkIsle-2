import pytest


@pytest.mark.asyncio
async def test_admin_list_users(client, admin_user):
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "adminpass123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_user_cannot_list_users(client, test_user):
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "password123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_user_cannot_access_import(client, test_user):
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "password123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/v1/import/folders", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_user_cannot_access_audit_logs(client, test_user):
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "password123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access(client):
    resp = await client.get("/api/v1/books")
    assert resp.status_code == 401

    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401
