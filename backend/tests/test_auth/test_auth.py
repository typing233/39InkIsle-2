import pytest


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "newuser",
        "email": "new@test.com",
        "password": "securepass123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_register_duplicate(client, test_user):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "another@test.com",
        "password": "securepass123",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login(client, test_user):
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "password123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client, test_user):
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "password123",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_refresh_token(client, test_user):
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "password123",
    })
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_list_sessions(client, test_user):
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "password123",
        "device_name": "Test Device",
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/v1/auth/sessions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) >= 1
