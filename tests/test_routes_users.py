"""Integration tests for user routes (me + avatar role guard)."""

from unittest.mock import MagicMock, patch


async def test_read_me(client, auth_headers, user):
    resp = await client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == user.email


async def test_me_requires_auth(client):
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


async def test_avatar_forbidden_for_user(client, auth_headers):
    files = {"file": ("a.png", b"data", "image/png")}
    resp = await client.patch("/api/users/avatar", files=files, headers=auth_headers)
    assert resp.status_code == 403


async def test_avatar_allowed_for_admin(client, admin_token):
    with patch("src.routes.users.cloudinary.uploader.upload", return_value={"version": 1}), \
         patch("src.routes.users.cloudinary.CloudinaryImage") as ci:
        ci.return_value.build_url.return_value = "http://cdn/avatar.png"
        files = {"file": ("a.png", b"data", "image/png")}
        resp = await client.patch(
            "/api/users/avatar", files=files,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["avatar"] == "http://cdn/avatar.png"
