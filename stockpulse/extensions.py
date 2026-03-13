from celery import Celery
from flask_login import LoginManager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from redis import Redis

db_engine = None
DbSession: sessionmaker[Session] | None = None

login_manager = LoginManager()
login_manager.login_view = "web_auth.login"

import os
from dotenv import load_dotenv

load_dotenv()

_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_database_url = os.getenv("DATABASE_URL", "postgresql://stockpulse:stockpulse@localhost:5432/stockpulse")

celery_app = Celery(
    "stockpulse",
    broker=_redis_url,
    backend=_redis_url,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "Asia/Kolkata"
celery_app.conf.enable_utc = True
celery_app.autodiscover_tasks(["stockpulse.ingestion", "stockpulse.engine", "stockpulse.webhooks"])

redis_client: Redis | None = None


def init_db(database_url: str) -> None:
    global db_engine, DbSession
    db_engine = create_engine(database_url, pool_size=20, max_overflow=40, pool_pre_ping=True)
    DbSession = sessionmaker(bind=db_engine)


def get_db() -> Session:
    """Get a new database session. Caller must close it."""
    if DbSession is None:
        # Auto-init from env var (for Celery workers)
        init_db(_database_url)
    return DbSession()


def init_redis(redis_url: str) -> None:
    global redis_client
    redis_client = Redis.from_url(redis_url, decode_responses=True)


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login session management."""
    if DbSession is None:
        return None
    session = DbSession()
    try:
        from stockpulse.models.user import User
        return session.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None


def init_celery(app=None) -> Celery:
    if app:
        celery_app.conf.broker_url = app.config["REDIS_URL"]
        celery_app.conf.result_backend = app.config["REDIS_URL"]
        celery_app.conf.task_serializer = "json"
        celery_app.conf.result_serializer = "json"
        celery_app.conf.accept_content = ["json"]
        celery_app.conf.timezone = "Asia/Kolkata"
        celery_app.conf.enable_utc = True

        # Register beat schedule
        from stockpulse.ingestion.scheduler import CELERY_BEAT_SCHEDULE

        celery_app.conf.beat_schedule = CELERY_BEAT_SCHEDULE

        # Auto-discover tasks
        celery_app.autodiscover_tasks(["stockpulse.ingestion", "stockpulse.engine", "stockpulse.webhooks"])

    return celery_app
