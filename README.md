# marketing-automation-report

## Deployment with Docker

1. Create a `.env` file with secrets:
```
SECRET_KEY=change-me
OPENAI_API_KEY=sk-...
SESSION_REDIS_URL=redis://redis:6379/0
```

2. Build and run:
```
docker compose up -d --build
```

The app will be available on `http://localhost:8000`.

Gunicorn runs with gevent workers for concurrency; Redis-backed sessions enable multiple users across workers/containers.
