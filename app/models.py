from datetime import UTC, datetime

from .extensions import db


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    customer_email = db.Column(db.String(320), nullable=False)
    priority = db.Column(db.String(10), nullable=False, default="low")
    status = db.Column(db.String(20), nullable=False, default="open")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "customer_email": self.customer_email,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class KnowledgeDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(500), nullable=False, default="manual")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
        }


class AIUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_key = db.Column(db.String(200), nullable=False)
    operation = db.Column(db.String(40), nullable=False)
    input_tokens = db.Column(db.Integer, nullable=False, default=0)
    output_tokens = db.Column(db.Integer, nullable=False, default=0)
    cost = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )


class ConversationMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(100), nullable=False, index=True)
    user_key = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
