"""Gunicorn configuration for production deployment."""

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000  # Restart worker after N requests (prevent memory leaks)
max_requests_jitter = 50  # Add randomness to prevent all workers restarting at once
timeout = 30  # Worker timeout
keepalive = 5  # Keep-alive connections

# Process naming
proc_name = "epicservice"

# Server mechanics
daemon = False  # Run in foreground (systemd will manage)
pidfile = "/var/run/epicservice/epicservice.pid"
user = "epicservice"
group = "epicservice"
tmp_upload_dir = None

# Logging
accesslog = "/var/log/epicservice/access.log"
errorlog = "/var/log/epicservice/error.log"
loglevel = "info"  # debug, info, warning, error, critical
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Enable structured logging
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}

# Graceful shutdown
graceful_timeout = 30  # Time to wait for workers to finish requests

# Preload app for better performance
preload_app = True


def on_starting(server):
    """Called just before the master process is initialized."""
    print("[Gunicorn] Starting EpicService...")


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("[Gunicorn] Reloading workers...")


def when_ready(server):
    """Called just after the server is started."""
    print(f"[Gunicorn] Server is ready. Listening on {bind}")
    print(f"[Gunicorn] Workers: {workers}")


def on_exit(server):
    """Called just before exiting Gunicorn."""
    print("[Gunicorn] Shutting down...")


def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal."""
    print(f"[Gunicorn] Worker {worker.pid} interrupted")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    print(f"[Gunicorn] Worker spawned (pid: {worker.pid})")


def worker_abort(worker):
    """Called when a worker times out."""
    print(f"[Gunicorn] Worker {worker.pid} aborted (timeout)")
