import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app

from .extensions import db
from .models import AutomationRun

logger = logging.getLogger(__name__)


def send_ticket_alert(ticket: dict) -> None:
    webhook_url = current_app.config.get("N8N_WEBHOOK_URL")
    if not webhook_url:
        db.session.add(AutomationRun(ticket_id=ticket["id"], status="skipped"))
        db.session.commit()
        logger.info("n8n alert skipped: N8N_WEBHOOK_URL is not configured")
        return

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SupportDesk/1.0",
    }
    webhook_secret = current_app.config.get("N8N_WEBHOOK_SECRET")
    if webhook_secret:
        headers["X-N8N-Webhook-Secret"] = webhook_secret

    request = Request(
        webhook_url,
        data=json.dumps(ticket).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"n8n webhook returned HTTP {response.status}")
        db.session.add(AutomationRun(ticket_id=ticket["id"], status="success"))
        db.session.commit()
        logger.info("Sent ticket id=%s to n8n for alert routing", ticket["id"])
    except HTTPError as error:
        db.session.add(AutomationRun(ticket_id=ticket["id"], status="failed"))
        db.session.commit()
        response_body = error.read().decode("utf-8", errors="replace")
        logger.error(
            "n8n webhook rejected ticket id=%s with HTTP %s: %s",
            ticket["id"],
            error.code,
            response_body,
        )
    except (OSError, URLError, RuntimeError):
        db.session.add(AutomationRun(ticket_id=ticket["id"], status="failed"))
        db.session.commit()
        logger.exception("Could not send ticket id=%s to n8n", ticket["id"])
