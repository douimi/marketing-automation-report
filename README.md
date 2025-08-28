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

## Memory Optimization

The application uses a lazy loading configuration service to handle large JSON files (countries.json, products.json) without loading them entirely into memory at startup. This prevents "Cannot allocate memory" errors in containers.

Features:
- **Lazy Loading**: Configuration data is loaded on-demand
- **Caching**: Frequently accessed data is cached with LRU cache
- **Memory Limits**: Docker containers have 2GB memory limit with 512MB reservation
- **Optimized Workers**: Reduced Gunicorn workers (2) and threads (4) for memory efficiency
- **Search APIs**: AJAX endpoints for efficient dropdown searching

Gunicorn runs with gevent workers for concurrency; Redis-backed sessions enable multiple users across workers/containers.
