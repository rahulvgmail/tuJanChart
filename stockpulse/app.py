import os

from flask import Flask

from config import config_by_name
from stockpulse.extensions import init_celery, init_db, init_redis, login_manager


def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(
        __name__,
        template_folder="web/templates",
        static_folder="web/static",
    )
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    init_db(app.config["SQLALCHEMY_DATABASE_URI"])
    init_redis(app.config["REDIS_URL"])
    init_celery(app)
    login_manager.init_app(app)

    # Register blueprints
    from stockpulse.api import api_bp
    from stockpulse.web import web_bp, dashboard_bp, web_auth_bp, admin_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(web_auth_bp)
    app.register_blueprint(admin_bp)

    # Health check
    @app.route("/healthz")
    def healthz():
        from stockpulse.extensions import db_engine, redis_client

        health = {"status": "ok", "db": "ok", "redis": "ok"}
        try:
            with db_engine.connect() as conn:
                conn.execute(
                    __import__("sqlalchemy").text("SELECT 1")
                )
        except Exception as e:
            health["db"] = f"error: {e}"
            health["status"] = "degraded"
        try:
            redis_client.ping()
        except Exception as e:
            health["redis"] = f"error: {e}"
            health["status"] = "degraded"

        status_code = 200 if health["status"] == "ok" else 503
        return health, status_code

    return app
