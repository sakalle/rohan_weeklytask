from unittest.mock import patch


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


def test_docs_uses_swagger_ui(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui.css" in response.text
    assert "swagger-ui-bundle.js" in response.text


def test_openapi_describes_interactive_request_schemas(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json["components"]["schemas"]["TicketCreate"]["required"]
    assert "/ai/classify" in response.json["paths"]


def test_classify_requires_api_key(client):
    response = client.post("/ai/classify", json={"text": "I cannot sign in"})
    assert response.status_code == 401


def test_classify_returns_validated_result(client, headers):
    client.application.config.update(
        LLM_API_URL="https://llm.example.test/v1/chat/completions",
        LLM_API_KEY="test-key",
    )
    with patch(
        "app.ai._request_classification",
        return_value={
            "category": "authentication",
            "priority": "high",
            "sentiment": "negative",
        },
    ):
        response = client.post(
            "/ai/classify", json={"text": "I cannot sign in"}, headers=headers
        )
    assert response.status_code == 200
    assert response.json["priority"] == "high"


def test_classify_retries_invalid_result(client, headers):
    client.application.config.update(
        LLM_API_URL="https://llm.example.test/v1/chat/completions",
        LLM_API_KEY="test-key",
    )
    with patch(
        "app.ai._request_classification",
        side_effect=[
            {"category": "authentication", "priority": "urgent", "sentiment": "negative"},
            {"category": "authentication", "priority": "high", "sentiment": "negative"},
        ],
    ) as request:
        response = client.post(
            "/ai/classify", json={"text": "I cannot sign in"}, headers=headers
        )
    assert response.status_code == 200
    assert request.call_count == 2


def test_classify_returns_friendly_error_when_unconfigured(client, headers):
    response = client.post("/ai/classify", json={"text": "Help"}, headers=headers)
    assert response.status_code == 503
    assert response.json["error"] == "AI classification unavailable"


def test_ticket_requires_api_key(client):
    assert client.get("/tickets").status_code == 401


def test_create_and_get_ticket(client, headers):
    with patch("app.routes.send_ticket_alert") as send_alert:
        created = client.post("/tickets", json=ticket_payload(), headers=headers)
    send_alert.assert_called_once()
    assert created.status_code == 201
    ticket_id = created.json["id"]

    fetched = client.get(f"/tickets/{ticket_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json["priority"] == "high"


def test_ticket_is_stored_when_n8n_is_not_configured(client, headers):
    with patch("app.routes.send_ticket_alert") as send_alert:
        response = client.post("/tickets", json=ticket_payload(), headers=headers)
    assert response.status_code == 201
    send_alert.assert_called_once_with(response.json)


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
