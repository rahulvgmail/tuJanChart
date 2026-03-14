import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://stockpulse:stockpulse@localhost:5432/stockpulse"
    )
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    DATA_ADAPTER = os.getenv("DATA_ADAPTER", "yfinance")

    # Technical analysis config
    GAP_THRESHOLD = float(os.getenv("GAP_THRESHOLD", "3.0"))
    VOLUME_MAX_PERIOD = int(os.getenv("VOLUME_MAX_PERIOD", "21"))
    VOLUME_AVG_SHORT_PERIOD = int(os.getenv("VOLUME_AVG_SHORT_PERIOD", "140"))
    VOLUME_AVG_LONG_PERIOD = int(os.getenv("VOLUME_AVG_LONG_PERIOD", "280"))
    RESULT_WINDOW_SHORT = int(os.getenv("RESULT_WINDOW_SHORT", "7"))
    RESULT_WINDOW_MEDIUM = int(os.getenv("RESULT_WINDOW_MEDIUM", "10"))
    RESULT_WINDOW_LONG = int(os.getenv("RESULT_WINDOW_LONG", "15"))
    RESULT_DECLARED_WINDOW = int(os.getenv("RESULT_DECLARED_WINDOW", "10"))

    # tuJanalyst integration
    TUJANALYST_BASE_URL = os.getenv("TUJANALYST_BASE_URL", "")
    TUJANALYST_TIMEOUT = int(os.getenv("TUJANALYST_TIMEOUT", "5"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://stockpulse:stockpulse@localhost:5432/stockpulse_test",
    )


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
