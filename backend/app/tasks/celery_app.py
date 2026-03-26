"""
Celery Application Configuration
"""
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta
import os

from app.config import settings

# Celery configuration
celery_app = Celery(
    'ontology_tasks',
    broker=os.getenv('CELERY_BROKER_URL', settings.REDIS_URL),
    backend=os.getenv('CELERY_RESULT_BACKEND', settings.REDIS_URL),
    include=['app.tasks.ingestion', 'app.tasks.nlp', 'app.tasks.graph']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=100,
)

# Celery Beat Schedule
celery_app.conf.beat_schedule = {
    # News ingestion every 2-5 minutes (clamped by settings validator)
    'ingest-news-realtime-polling': {
        'task': 'app.tasks.ingestion.ingest_news',
        'schedule': timedelta(minutes=settings.INGESTION_INTERVAL_MINUTES),
    },
    # Entity linking every hour
    'entity-linking-hourly': {
        'task': 'app.tasks.nlp.entity_linking',
        'schedule': crontab(minute=0),
    },
    # Risk analysis update every hour
    'risk-analysis-hourly': {
        'task': 'app.tasks.graph.update_risk_analysis',
        'schedule': crontab(minute=15),
    },
    # Graph statistics update every 15 minutes
    'graph-stats-every-15-minutes': {
        'task': 'app.tasks.graph.update_statistics',
        'schedule': crontab(minute='*/15'),
    },
}

if __name__ == '__main__':
    celery_app.start()
