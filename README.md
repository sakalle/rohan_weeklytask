# SupportDesk AI — Week 1

Flask + SQLite backend and n8n automation foundation for the SupportDesk AI capstone.

## Run locally

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:TICKET_API_KEY = "local-secret"
python seed.py
flask --app wsgi run --debug
```

- Health: `GET http://localhost:5000/health`
- Swagger-style docs: `http://localhost:5000/docs`
- Tickets require `X-API-Key: local-secret`.
- Set `LLM_API_URL`, `LLM_API_KEY`, and `LLM_MODEL` to enable `/ai/classify`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Public health check |
| GET | `/tickets` | Paginated ticket list |
| POST | `/tickets` | Create a validated ticket |
| GET | `/tickets/<id>` | Get a ticket |
| PATCH | `/tickets/<id>` | Update a ticket |
| POST | `/ai/classify` | Classify text with the configured LLM |

Example:

```powershell
curl.exe -H "X-API-Key: local-secret" -H "Content-Type: application/json" `
  -d '{\"title\":\"Login issue\",\"description\":\"Cannot sign in\",\"customer_email\":\"user@example.com\",\"priority\":\"high\"}' `
  http://localhost:5000/tickets
```

## Docker and n8n

`docker compose up --build` starts Flask on port 5000 and n8n on port 5678.
Import `n8n/ticket-routing.json` and `n8n/daily-summary.json` into n8n, then
configure Slack credentials. The routing workflow branches high priority tickets
to an alert and low priority tickets to a log node.

## Quality

```powershell
ruff check .
pytest
```

## Week 2 AI classification

`POST /ai/classify` accepts `{"text": "..."}` and returns validated
`category`, `priority`, and `sentiment` fields. `POST /ai/summarize` accepts the
same input and returns a validated `summary` plus `key_points`. Both endpoints
require the API key and call an OpenAI-compatible chat-completions endpoint
configured through environment variables. Invalid model output is retried once
before returning a friendly `503` response.

`POST /chat` answers from ingested knowledge documents and includes source
citation metadata. `POST /chat/stream` returns the same answer as
server-sent events. When retrieval finds no relevant document, the bot says it
does not know instead of inventing an answer.

## Week 1 demo checklist

1. Start Flask and verify `GET /health` returns `{"status": "ok"}`.
2. Send a high-priority ticket with `X-API-Key` and confirm it is stored.
3. List tickets with `GET /tickets` to show database persistence.
4. Import the n8n workflows and trigger the webhook.
5. Confirm high-priority tickets alert support and low-priority tickets are logged.
6. Send invalid input and show the clean `400 validation failed` response.

Commits should use Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`).
Open changes through a pull request and use `.env.example` for local settings;
never commit secrets.
