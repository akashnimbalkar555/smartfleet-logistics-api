import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("smartfleet")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "flag-overdue-shipments-every-30-mins": {
        "task": "logistics.tasks.flag_overdue_shipments",
        "schedule": crontab(minute="*/30"),
    },
}
