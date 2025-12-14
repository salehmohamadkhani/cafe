# تنظیمات Gunicorn برای production
bind = "127.0.0.1:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
preload_app = True
accesslog = "/var/log/cafe/access.log"
errorlog = "/var/log/cafe/error.log"
loglevel = "info"
proc_name = "cafe_app"

