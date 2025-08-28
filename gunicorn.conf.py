import multiprocessing

workers = int((multiprocessing.cpu_count() * 2) + 1)
worker_class = "gthread"
threads = 8
timeout = 180
graceful_timeout = 180
keepalive = 5
bind = "0.0.0.0:8000"
forwarded_allow_ips = "*"
accesslog = "-"
errorlog = "-"
loglevel = "info"


