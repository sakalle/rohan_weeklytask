def api_spec() -> dict:
    schemas = {
        "ChatRequest": {
            "type": "object",
            "required": ["question"],
            "properties": {"question": {"type": "string", "maxLength": 10000}},
        },
        "ClassificationRequest": {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string", "maxLength": 10000}},
        },
        "ClassificationResult": {
            "type": "object",
            "required": ["category", "priority", "sentiment"],
            "properties": {
                "category": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "high"]},
                "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
            },
        },
        "DocumentIngest": {
            "type": "object",
            "required": ["title", "content"],
            "properties": {
                "title": {"type": "string", "maxLength": 200},
                "content": {"type": "string", "maxLength": 100000},
                "source": {"type": "string", "default": "manual"},
            },
        },
        "SummaryRequest": {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string", "maxLength": 10000}},
        },
        "SummaryResult": {
            "type": "object",
            "required": ["summary", "key_points"],
            "properties": {
                "summary": {"type": "string"},
                "key_points": {"type": "array", "items": {"type": "string"}},
            },
        },
        "TicketCreate": {
            "type": "object",
            "required": ["title", "description", "customer_email"],
            "properties": {
                "title": {"type": "string", "maxLength": 200},
                "description": {"type": "string", "maxLength": 10000},
                "customer_email": {"type": "string", "format": "email"},
                "priority": {"type": "string", "enum": ["low", "high"], "default": "low"},
            },
        },
    }
    def json_body(schema: str) -> dict:
        return {
            "required": True,
            "content": {
                "application/json": {"schema": {"$ref": f"#/components/schemas/{schema}"}}
            },
        }
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "SupportDesk API",
            "description": "SupportDesk ticket, AI, knowledge-base, and chat API.",
            "version": "0.2.0",
        },
        "servers": [{"url": "/"}],
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
            },
            "schemas": schemas,
        },
        "security": [{"ApiKeyAuth": []}],
        "paths": {
            "/health": {"get": {"security": [], "responses": {"200": {"description": "Healthy"}}}},
            "/ai/classify": {
                "post": {
                    "summary": "Classify support text",
                    "requestBody": json_body("ClassificationRequest"),
                    "responses": {"200": {"description": "Classification result"}},
                }
            },
            "/ai/summarize": {
                "post": {
                    "summary": "Summarize support text",
                    "requestBody": json_body("SummaryRequest"),
                    "responses": {"200": {"description": "Summary result"}},
                }
            },
            "/docs/ingest": {
                "post": {
                    "summary": "Ingest a knowledge document",
                    "requestBody": json_body("DocumentIngest"),
                    "responses": {"201": {"description": "Document ingested"}},
                }
            },
            "/chat": {
                "post": {
                    "summary": "Answer with citations",
                    "requestBody": json_body("ChatRequest"),
                    "responses": {"200": {"description": "Chat answer"}},
                }
            },
            "/chat/stream": {
                "post": {
                    "summary": "Stream an answer using server-sent events",
                    "requestBody": json_body("ChatRequest"),
                    "responses": {"200": {"description": "SSE stream"}},
                }
            },
            "/tickets": {
                "get": {
                    "summary": "List tickets",
                    "responses": {"200": {"description": "Ticket list"}},
                },
                "post": {
                    "summary": "Create a ticket",
                    "requestBody": json_body("TicketCreate"),
                    "responses": {"201": {"description": "Ticket created"}},
                },
            },
        },
    }
