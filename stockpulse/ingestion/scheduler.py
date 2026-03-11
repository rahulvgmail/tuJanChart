"""Celery Beat schedule configuration for data ingestion tasks."""

from celery.schedules import crontab

# All times are in Asia/Kolkata (IST) as configured in celery_app.conf.timezone

CELERY_BEAT_SCHEDULE = {
    # EOD data pull: 4:00 PM IST on weekdays
    "eod-data-pull": {
        "task": "ingestion.pull_eod_data",
        "schedule": crontab(hour=16, minute=0, day_of_week="1-5"),
    },
    # Intraday quotes: every 3 minutes during market hours (9:15 AM - 3:30 PM IST)
    "intraday-quotes": {
        "task": "ingestion.pull_intraday_quotes",
        "schedule": crontab(minute="*/3", hour="9-15", day_of_week="1-5"),
    },
    # Corporate actions (board meetings, result dates): 6:00 PM IST daily
    "corporate-actions": {
        "task": "ingestion.pull_corporate_actions",
        "schedule": crontab(hour=18, minute=0, day_of_week="1-5"),
    },
    # Retry failed webhook deliveries: every 5 minutes on weekdays
    "webhook-retries": {
        "task": "webhooks.retry_deliveries",
        "schedule": crontab(minute="*/5", day_of_week="1-5"),
    },
}
