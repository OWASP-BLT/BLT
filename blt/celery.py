from celery import Celery

celery_app = Celery("blt", namespace="CELERY")
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.autodiscover_tasks()


@celery_app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
