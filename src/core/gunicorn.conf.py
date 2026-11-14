import os

from src.core.settings import Settings
from src.core.version import __version__

settings = Settings()

# Базовые настройки
bind = f"{settings.api_host}:{settings.api_port}"
workers = 1
worker_class = "src.core.worker.BotWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# Логирование
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Настройки процесса
preload_app = True
timeout = 300  # Увеличено для бота
keepalive = 2
graceful_timeout = 120

# Настройки для работы с ботом
worker_tmp_dir = "/dev/shm"

raw_env = [f"PYTHONPATH={os.getcwd()}", "PYTHONUNBUFFERED=1"]
raw_env.append(f"APP_VERSION={__version__}")


def post_worker_init(worker):
    from src.core.logging import setup_logging

    setup_logging(settings.log_level, debug=settings.debug)


app_env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", ""))
if app_env in {"dev", "development"}:
    workers = 1
    loglevel = "debug"
    reload = True
    timeout = 600  # Увеличено для разработки
    preload_app = False  # Отключаем для разработки
