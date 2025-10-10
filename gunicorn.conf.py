import multiprocessing
import os

# Reduce workers for memory efficiency, especially with large JSON files
workers = 1  # Use single worker for debugging
worker_class = "sync"  # Use sync worker instead of threaded
# threads = int(os.getenv('GUNICORN_THREADS', 4))  # Disabled for sync worker
timeout = 180
graceful_timeout = 180
keepalive = 5
bind = "0.0.0.0:8000"
forwarded_allow_ips = "*"
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Memory management settings
max_requests = 1000  # Restart workers after 1000 requests to prevent memory leaks
max_requests_jitter = 100  # Add randomness to prevent all workers restarting at once
preload_app = False  # Don't preload to save memory during startup


