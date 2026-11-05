def ticket_payload():
    return {
        "title": "Login issue",
        "description": "Unable to sign in.",
        "customer_email": "user@example.com",
        "priority": "high",
    }


def test_health_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_root_redirects_to_docs(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/docs"


def test_docs_exposes_openapi_link(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "/openapi.json" in response.text


def test_ticket_requires_api_key(client):
    assert client.get("/tickets").status_code == 401


def test_create_and_get_ticket(client, headers):
    created = client.post("/tickets", json=ticket_payload(), headers=headers)
    assert created.status_code == 201
    ticket_id = created.json["id"]

    fetched = client.get(f"/tickets/{ticket_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json["priority"] == "high"


def test_invalid_ticket_returns_clean_400(client, headers):
    response = client.post(
        "/tickets",
        json={"title": "", "description": "x", "customer_email": "not-an-email"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json["error"] == "validation failed"


def test_missing_ticket_returns_404(client, headers):
    response = client.get("/tickets/999", headers=headers)
    assert response.status_code == 404
    assert response.json["error"] == "resource not found"


def test_patch_ticket(client, headers):
    created = client.post("/tickets", json=ticket_payload(), headers=headers)
    ticket_id = created.json["id"]
    response = client.patch(
        f"/tickets/{ticket_id}", json={"status": "resolved"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json["status"] == "resolved"
