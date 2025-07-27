from celery import Celery

celery_app = Celery("tasks", broker="redis://localhost")

from post_popularity_rate_celery import popularity_rate