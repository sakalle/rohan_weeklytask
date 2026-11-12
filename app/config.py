import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///supportdesk.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_KEY = os.getenv("TICKET_API_KEY", "dev-key-change-me")
    N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
    N8N_WEBHOOK_SECRET = os.getenv("N8N_WEBHOOK_SECRET")
    LLM_API_URL = os.getenv("LLM_API_URL")
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL", "supportdesk-classifier")
    CHAT_DAILY_QUOTA = int(os.getenv("CHAT_DAILY_QUOTA", "20"))
