from uvicorn.workers import UvicornWorker


class BotWorker(UvicornWorker):
    """Uvicorn под gunicorn с обязательным lifespan."""

    CONFIG_KWARGS = {"loop": "auto", "http": "auto", "lifespan": "on"}
