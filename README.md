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
- Set `N8N_WEBHOOK_URL` to the office n8n alert webhook URL to enable alert routing.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Public health check |
| GET | `/tickets` | Paginated ticket list |
| POST | `/tickets` | Create a validated ticket |
| GET | `/tickets/<id>` | Get a ticket |
| PATCH | `/tickets/<id>` | Update a ticket |

Example:

```powershell
curl.exe -H "X-API-Key: local-secret" -H "Content-Type: application/json" `
  -d '{\"title\":\"Login issue\",\"description\":\"Cannot sign in\",\"customer_email\":\"user@example.com\",\"priority\":\"high\"}' `
  http://localhost:5000/tickets
```

## Docker and n8n

`docker compose up --build` starts Flask on port 5000 and n8n on port 5678.
Import `n8n/ticket-routing.json` and `n8n/daily-summary.json` into n8n, then
configure Slack credentials. Flask is the system of record: it validates and
saves tickets to SQLite, then sends the saved ticket event to n8n. n8n only
branches high priority tickets to an alert and low priority tickets to a log node.

## Quality

```powershell
ruff check .
pytest
```

<<<<<<< Updated upstream
=======
## Week 1 demo checklist

1. Start Flask and verify `GET /health` returns `{"status": "ok"}`.
2. Send a high-priority ticket with `X-API-Key` and confirm it is stored.
3. List tickets with `GET /tickets` to show database persistence.
4. Configure `N8N_WEBHOOK_URL` with the office n8n alert webhook URL.
5. Import the n8n workflows and create a ticket through Flask.
6. Confirm high-priority tickets alert support and low-priority tickets are logged.
7. Send invalid input and show the clean `400 validation failed` response.

>>>>>>> Stashed changes
Commits should use Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`).
Open changes through a pull request and use `.env.example` for local settings;
never commit secrets.
