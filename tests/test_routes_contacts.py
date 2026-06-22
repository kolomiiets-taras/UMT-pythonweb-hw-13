"""Integration tests for contacts routes."""

from datetime import date, timedelta


def _payload(**over):
    base = {
        "first_name": "Bob",
        "last_name": "Hill",
        "email": "bob@x.com",
        "phone": "+1000000",
        "birthday": "1990-01-01",
    }
    base.update(over)
    return base


async def test_contacts_require_auth(client):
    resp = await client.get("/api/contacts/")
    assert resp.status_code == 401


async def test_create_and_get_contact(client, auth_headers):
    create = await client.post("/api/contacts/", json=_payload(), headers=auth_headers)
    assert create.status_code == 201
    cid = create.json()["id"]

    got = await client.get(f"/api/contacts/{cid}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["email"] == "bob@x.com"


async def test_list_and_search(client, auth_headers):
    await client.post("/api/contacts/", json=_payload(first_name="Zoe", email="zoe@x.com"), headers=auth_headers)
    resp = await client.get("/api/contacts/?first_name=zoe", headers=auth_headers)
    assert resp.status_code == 200
    assert all("zoe" in c["first_name"].lower() for c in resp.json())


async def test_update_contact(client, auth_headers):
    create = await client.post("/api/contacts/", json=_payload(), headers=auth_headers)
    cid = create.json()["id"]
    upd = await client.put(
        f"/api/contacts/{cid}", json=_payload(first_name="Robert"), headers=auth_headers
    )
    assert upd.status_code == 200
    assert upd.json()["first_name"] == "Robert"


async def test_update_missing_contact(client, auth_headers):
    resp = await client.put("/api/contacts/9999", json=_payload(), headers=auth_headers)
    assert resp.status_code == 404


async def test_delete_contact(client, auth_headers):
    create = await client.post("/api/contacts/", json=_payload(), headers=auth_headers)
    cid = create.json()["id"]
    delete = await client.delete(f"/api/contacts/{cid}", headers=auth_headers)
    assert delete.status_code == 204
    got = await client.get(f"/api/contacts/{cid}", headers=auth_headers)
    assert got.status_code == 404


async def test_upcoming_birthdays(client, auth_headers):
    soon = (date.today() + timedelta(days=3)).replace(year=1995).isoformat()
    await client.post("/api/contacts/", json=_payload(email="soon@x.com", birthday=soon), headers=auth_headers)
    resp = await client.get("/api/contacts/birthdays", headers=auth_headers)
    assert resp.status_code == 200
    assert any(c["email"] == "soon@x.com" for c in resp.json())
