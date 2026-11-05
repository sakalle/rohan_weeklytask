import logging

from flask import Blueprint, jsonify, redirect, request

from .auth import require_api_key
from .extensions import db
from .models import Ticket
from .schemas import TicketCreate, TicketUpdate

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
        "<title>SupportDesk API</title></head>"
        '<body><h1>SupportDesk API</h1>'
        '<p>Interactive documentation is loading. '
        '<a href="/openapi.json">Open the OpenAPI JSON</a>.</p>'
        '<redoc spec-url="/openapi.json"></redoc>'
        '<script src="https://cdn.jsdelivr.net/npm/redoc@latest/'
        'bundles/redoc.standalone.js"></script>'
        "</body></html>"
    )


@api.get("/openapi.json")
def openapi():
    return jsonify(
        {
            "openapi": "3.0.3",
            "info": {"title": "SupportDesk API", "version": "0.1.0"},
            "servers": [{"url": "/"}],
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
                }
            },
            "security": [{"ApiKeyAuth": []}],
            "paths": {
                "/health": {
                    "get": {"security": [], "responses": {"200": {"description": "Healthy"}}}
                },
                "/tickets": {
                    "get": {"responses": {"200": {"description": "Ticket list"}}},
                    "post": {"responses": {"201": {"description": "Ticket created"}}},
                },
                "/tickets/{ticket_id}": {
                    "get": {"responses": {"200": {"description": "Ticket"}}},
                    "patch": {"responses": {"200": {"description": "Ticket updated"}}},
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
