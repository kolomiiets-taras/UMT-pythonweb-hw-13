"""Integration tests for auth routes."""

from src.services.auth import auth_service


async def test_signup_created(client):
    resp = await client.post(
        "/api/auth/signup",
        json={"username": "neo", "email": "neo@example.com", "password": "secret123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "neo@example.com"
    assert data["role"] == "user"
    assert "password" not in data


async def test_signup_duplicate_conflict(client, user):
    resp = await client.post(
        "/api/auth/signup",
        json={"username": "xx", "email": user.email, "password": "secret123"},
    )
    assert resp.status_code == 409


async def test_login_success(client, user):
    resp = await client.post(
        "/api/auth/login",
        data={"username": user.email, "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]


async def test_login_bad_password(client, user):
    resp = await client.post(
        "/api/auth/login", data={"username": user.email, "password": "wrong"}
    )
    assert resp.status_code == 401


async def test_login_unconfirmed(client, db_session):
    from src.entity.models import User

    u = User(
        username="u", email="unconf@example.com",
        password=auth_service.get_password_hash("secret123"), confirmed=False,
    )
    db_session.add(u)
    await db_session.commit()
    resp = await client.post(
        "/api/auth/login", data={"username": "unconf@example.com", "password": "secret123"}
    )
    assert resp.status_code == 401


async def test_refresh_token_flow(client, user, db_session):
    login = await client.post(
        "/api/auth/login", data={"username": user.email, "password": "secret123"}
    )
    refresh = login.json()["refresh_token"]
    resp = await client.get(
        "/api/auth/refresh_token", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_confirmed_email(client, db_session):
    from src.entity.models import User

    u = User(
        username="c", email="conf@example.com",
        password=auth_service.get_password_hash("secret123"), confirmed=False,
    )
    db_session.add(u)
    await db_session.commit()
    token = auth_service.create_email_token({"sub": "conf@example.com"})
    resp = await client.get(f"/api/auth/confirmed_email/{token}")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Email confirmed"


async def test_forgot_and_reset_password(client, user):
    forgot = await client.post("/api/auth/forgot_password", json={"email": user.email})
    assert forgot.status_code == 200

    token = auth_service.create_reset_token({"sub": user.email})
    resp = await client.post(
        "/api/auth/reset_password",
        json={"token": token, "new_password": "brandnew1"},
    )
    assert resp.status_code == 200

    login = await client.post(
        "/api/auth/login", data={"username": user.email, "password": "brandnew1"}
    )
    assert login.status_code == 200
