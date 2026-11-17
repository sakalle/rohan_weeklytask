import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DOCUMENTS = [
    (
        "Account security",
        "Users can reset their password and manage account security in account settings.",
    ),
    ("Login help", "If login fails, check sign in credentials and the dashboard access policy."),
    ("Reports", "Users can export and download reports from the reports page."),
    ("Tickets", "Create a support ticket and check ticket status from the support portal."),
    ("Profile", "Update your profile and contact support from the profile page."),
    ("Notifications", "Configure notification settings for your team."),
]


def main() -> int:
    from app import create_app
    from app.extensions import db
    from app.models import KnowledgeDocument
    from app.rag import retrieve_documents

    questions = json.loads(
        (Path(__file__).parent / "golden_questions.json").read_text(encoding="utf-8")
    )
    app = create_app(
        type(
            "EvalConfig",
            (),
            {
                "TESTING": True,
                "API_KEY": "eval-key",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            },
        )
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add_all(
            [
                KnowledgeDocument(title=title, content=content, source="eval")
                for title, content in DOCUMENTS
            ]
        )
        db.session.commit()
        hits = 0
        for item in questions:
            sources = retrieve_documents(item["question"])
            haystack = " ".join(
                f"{source['title']} {source['snippet']}".lower() for source in sources
            )
            hit = all(term.lower() in haystack for term in item["expected_terms"])
            hits += int(hit)
            print(f"{'PASS' if hit else 'FAIL'}: {item['question']}")
    hit_rate = hits / len(questions)
    print(f"Retrieval hit rate: {hits}/{len(questions)} ({hit_rate:.1%})")
    threshold = 0.80
    if hit_rate < threshold:
        print(f"FAIL: hit rate is below the {threshold:.0%} threshold.")
        return 1
    print(f"PASS: hit rate meets the {threshold:.0%} threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
