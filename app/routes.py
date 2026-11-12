import logging

from flask import Blueprint, Response, jsonify, redirect, request, stream_with_context

from .ai import ClassificationRequest, SummaryRequest, classify_text, summarize_text
from .auth import require_api_key
from .chat import answer_question, stream_answer
from .extensions import db
from .models import KnowledgeDocument, Ticket
from .notifications import send_ticket_alert
from .openapi import api_spec
from .schemas import ChatRequest, DocumentIngest, TicketCreate, TicketUpdate

api = Blueprint("api", __name__)
logger = logging.getLogger(__name__)


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


@api.get("/")
def root():
    return redirect("/docs")


@api.get("/docs")
def docs():
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>SupportDesk API - Swagger UI</title>"
        '<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">'
        "</head><body><div id=\"swagger-ui\"></div>"
        '<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>'
        "<script>SwaggerUIBundle({url:'/openapi.json',dom_id:'#swagger-ui',"
        "presets:[SwaggerUIBundle.presets.apis,SwaggerUIBundle.SwaggerUIStandalonePreset],"
        "layout:'BaseLayout'});</script></body></html>"
    )


@api.get("/openapi.json")
def openapi():
    return jsonify(api_spec())


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


@api.post("/docs/ingest")
@require_api_key
def ingest_document():
    payload = DocumentIngest.model_validate(request.get_json(silent=True) or {})
    document = KnowledgeDocument(**payload.model_dump())
    db.session.add(document)
    db.session.commit()
    return jsonify(document.to_dict()), 201


@api.post("/chat")
@require_api_key
def chat():
    payload = ChatRequest.model_validate(request.get_json(silent=True) or {})
    return jsonify(
        answer_question(
            payload.question,
            request.headers["X-API-Key"],
            payload.conversation_id,
            payload.history,
        )
    )


@api.post("/chat/stream")
@require_api_key
def chat_stream():
    payload = ChatRequest.model_validate(request.get_json(silent=True) or {})
    return Response(
        stream_with_context(
            stream_answer(payload.question, request.headers["X-API-Key"], payload.conversation_id)
        ),
        mimetype="text/event-stream",
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
