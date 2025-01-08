from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command


def MonitorJob():
    call_command("check_keywords")


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(MonitorJob, "interval", seconds=10)
    scheduler.start()
