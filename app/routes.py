import logging

from flask import Blueprint, Response, jsonify, request, stream_with_context

from .ai import ClassificationRequest, SummaryRequest, classify_text, summarize_text
from .auth import require_api_key
from .chat import answer_question, stream_answer
from .extensions import db
from .models import KnowledgeDocument, Ticket
from .notifications import send_ticket_alert
from .schemas import DocumentIngest, TicketCreate, TicketUpdate

api = Blueprint("api", __name__)
logger = logging.getLogger(__name__)


@api.post("/docs/ingest")
@require_api_key
def ingest_document():
    payload = DocumentIngest.model_validate(request.get_json(silent=True) or {})
    document = KnowledgeDocument(**payload.model_dump())
    db.session.add(document)
    db.session.commit()
    return jsonify(document.to_dict()), 201


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


@api.post("/ai/classify")
@require_api_key
def classify():
    payload = ClassificationRequest.model_validate(request.get_json(silent=True) or {})
    return jsonify(classify_text(payload.text).model_dump())


@api.post("/ai/summarize")
@require_api_key
def summarize():
    payload = SummaryRequest.model_validate(request.get_json(silent=True) or {})
    return jsonify(summarize_text(payload.text).model_dump())


@api.post("/chat")
@require_api_key
def chat():
    body = request.get_json(silent=True) or {}
    question = body.get("question")
    if not isinstance(question, str) or not question.strip() or len(question) > 10_000:
        raise ValueError("question must be a non-empty string")
    return jsonify(answer_question(question, request.headers["X-API-Key"]))


@api.post("/chat/stream")
@require_api_key
def chat_stream():
    body = request.get_json(silent=True) or {}
    question = body.get("question")
    if not isinstance(question, str) or not question.strip() or len(question) > 10_000:
        raise ValueError("question must be a non-empty string")
    return Response(
        stream_with_context(stream_answer(question, request.headers["X-API-Key"])),
        mimetype="text/event-stream",
    )


@api.get("/docs")
def docs():
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>SupportDesk API — Swagger UI</title>"
        '<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">'
        "</head><body><div id=\"swagger-ui\"></div>"
        '<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>'
        "<script>"
        "window.ui = SwaggerUIBundle({url:'/openapi.json',dom_id:'#swagger-ui',"
        "deepLinking:true,presets:[SwaggerUIBundle.presets.apis,"
        "SwaggerUIBundle.SwaggerUIStandalonePreset],layout:'BaseLayout'});"
        "</script>"
        "</body></html>"
    )


@api.get("/openapi.json")
def openapi():
    return jsonify(
        {
            "openapi": "3.0.3",
            "info": {
                "title": "SupportDesk API",
                "description": "SupportDesk ticket and AI classification API.",
                "version": "0.2.0",
            },
            "servers": [{"url": "/"}],
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
                },
                "schemas": {
                    "TicketCreate": {
                        "type": "object",
                        "required": ["title", "description", "customer_email"],
                        "properties": {
                            "title": {"type": "string", "maxLength": 200},
                            "description": {"type": "string", "maxLength": 10000},
                            "customer_email": {"type": "string", "format": "email"},
                            "priority": {
                                "type": "string",
                                "enum": ["low", "high"],
                                "default": "low",
                            },
                        },
                    },
                    "TicketUpdate": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "maxLength": 200},
                            "description": {"type": "string", "maxLength": 10000},
                            "customer_email": {"type": "string", "format": "email"},
                            "priority": {"type": "string", "enum": ["low", "high"]},
                            "status": {
                                "type": "string",
                                "enum": ["open", "in_progress", "resolved"],
                            },
                        },
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
                            "sentiment": {
                                "type": "string",
                                "enum": ["positive", "neutral", "negative"],
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
                    },
                },
            },
            "security": [{"ApiKeyAuth": []}],
            "paths": {
                "/health": {
                    "get": {"security": [], "responses": {"200": {"description": "Healthy"}}}
                },
                "/ai/classify": {
                    "post": {
                        "summary": "Classify a support message",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ClassificationRequest"}
                                }
                            },
                            "/ai/summarize": {
                                "post": {
                                    "summary": "Summarize a support message",
                                    "requestBody": {
                                        "required": True,
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "$ref": "#/components/schemas/SummaryRequest"
                                                }
                                            }
                                        },
                                        "/docs/ingest": {
                                            "post": {
                                                "summary": "Ingest a knowledge-base document",
                                                "requestBody": {
                                                    "required": True,
                                                    "content": {
                                                        "application/json": {
                                                            "schema": {
                                                                "type": "object",
                                                                "required": ["title", "content"],
                                                                "properties": {
                                                                    "title": {"type": "string"},
                                                                    "content": {"type": "string"},
                                                                    "source": {
                                                                        "type": "string",
                                                                        "default": "manual",
                                                                    },
                                                                },
                                                            }
                                                        }
                                                    },
                                                },
                                                "responses": {
                                                    "201": {"description": "Document ingested"}
                                                },
                                            }
                                        },
                                    },
                                    "responses": {
                                        "200": {
                                            "description": "Summary result",
                                            "content": {
                                                "application/json": {
                                                    "schema": {
                                                        "$ref": "#/components/schemas/SummaryResult"
                                                    }
                                                }
                                            },
                                        },
                                        "400": {"description": "Invalid request"},
                                        "503": {"description": "AI service unavailable"},
                                    },
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Classification result",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/ClassificationResult"
                                        }
                                    }
                                },
                            },
                            "400": {"description": "Invalid request"},
                            "503": {"description": "AI service unavailable"},
                        }
                    }
                },
                "/tickets": {
                    "get": {
                        "summary": "List tickets",
                        "responses": {"200": {"description": "Ticket list"}},
                    },
                    "post": {
                        "summary": "Create a ticket",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TicketCreate"}
                                }
                            },
                        },
                        "responses": {"201": {"description": "Ticket created"}},
                    },
                },
                "/tickets/{ticket_id}": {
                    "parameters": [
                        {
                            "name": "ticket_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "get": {
                        "summary": "Get a ticket",
                        "responses": {"200": {"description": "Ticket"}},
                    },
                    "patch": {
                        "summary": "Update a ticket",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TicketUpdate"}
                                }
                            },
                        },
                        "responses": {"200": {"description": "Ticket updated"}},
                    },
                },
            },
        }
    )


@api.route("/tickets", methods=["GET", "POST"])
@require_api_key
def tickets():
    if request.method == "GET":
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
        pagination = db.paginate(
            db.select(Ticket).order_by(Ticket.created_at.desc()),
            page=page,
            per_page=per_page,
            error_out=False,
        )
        return jsonify(
            {
                "items": [ticket.to_dict() for ticket in pagination.items],
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
            }
        )

    payload = TicketCreate.model_validate(request.get_json(silent=True) or {})
    ticket = Ticket(**payload.model_dump())
    db.session.add(ticket)
    db.session.commit()
    send_ticket_alert(ticket.to_dict())
    logger.info("Created ticket id=%s priority=%s", ticket.id, ticket.priority)
    return jsonify(ticket.to_dict()), 201


@api.route("/tickets/<int:ticket_id>", methods=["GET", "PATCH"])
@require_api_key
def ticket_detail(ticket_id: int):
    ticket = db.get_or_404(Ticket, ticket_id)
    if request.method == "GET":
        return jsonify(ticket.to_dict())

    payload = TicketUpdate.model_validate(request.get_json(silent=True) or {})
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    db.session.commit()
    logger.info("Updated ticket id=%s", ticket.id)
    return jsonify(ticket.to_dict())
