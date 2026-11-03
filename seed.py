from app import create_app
from app.extensions import db
from app.models import Ticket

app = create_app()
with app.app_context():
    if not db.session.execute(db.select(Ticket)).first():
        db.session.add_all(
            [
                Ticket(
                    title="Cannot reset password",
                    description="The reset link returns an expired-token error.",
                    customer_email="demo@example.com",
                    priority="high",
                ),
                Ticket(
                    title="How do I export reports?",
                    description="Please share the report export steps.",
                    customer_email="demo@example.com",
                    priority="low",
                ),
            ]
        )
        db.session.commit()
        print("Seeded 2 tickets.")
    else:
        print("Tickets already exist; nothing to seed.")
