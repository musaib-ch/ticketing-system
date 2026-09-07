import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    'fetch-emails-every-2-minutes': {
        'task': 'tickets.tasks.fetch_inbound_emails',
        'schedule': crontab(minute='*/2'),
    },
    'enforce-business-rules-every-hour': {
        'task': 'tickets.tasks.enforce_business_rules',
        'schedule': crontab(minute='0'),  # run every hour on the hour
    },
}
