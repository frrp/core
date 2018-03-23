from __future__ import absolute_import, unicode_literals
import os
import logging

from celery import Celery, signals
from celery.schedules import crontab
from celery.signals import worker_ready

from settings import INFO_BOT_CACHE_TELEGRAM_BOT_SECONDS, SHORT, MEDIUM, LONG



# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

app = Celery('core')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# app.conf.update(
#     CELERY_BROKER_POOL_LIMIT=1,
# )

# Load task modules from all registered Django app configs.
# Celery auto-discover modules in tasks.py files
app.autodiscover_tasks()


## CELERY Periodic Tasks/Scheduler
##   http://docs.celeryproject.org/en/v4.1.0/userguide/periodic-tasks.html
##   http://docs.celeryproject.org/en/v4.1.0/reference/celery.schedules.html#celery.schedules.crontab
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    from taskapp import tasks

    # Pull poloniex data every minute
    EVERY_MINUTE = 60
    sender.add_periodic_task(EVERY_MINUTE, tasks.pull_poloniex_data.s(), name='every %is' % EVERY_MINUTE)

    # Process data and send signals
    # calculate SHORT period at the start of the hour
    sender.add_periodic_task(
        crontab(minute=0),
        tasks.compute_and_save_indicators.s({'period': SHORT}),
        name='at the beginning of every hour',
        )

    # calculate MEDIUM period at the start of every 4 hours
    sender.add_periodic_task(
        crontab(minute=0, hour='*/4'),
        tasks.compute_and_save_indicators.s({'period': MEDIUM}),
        name='at the beginning of every 4 hours',
        )

    # calculate LONG period daily at midnight.
    sender.add_periodic_task(
        crontab(minute=0, hour=0),
        tasks.compute_and_save_indicators.s({'period': LONG}),
        name='daily at midnight',
        )

    # Precache info_bot every 4 hours
    sender.add_periodic_task(INFO_BOT_CACHE_TELEGRAM_BOT_SECONDS, tasks.precache_info_bot.s(), name='every %is' % INFO_BOT_CACHE_TELEGRAM_BOT_SECONDS)


## Non periodic tasks
## Runs tasks, that should start, when worker is ready. Like precaching.
@worker_ready.connect
def at_start(sender, **kwarg):
    with sender.app.connection() as conn:
        sender.app.send_task('taskapp.tasks.precache_info_bot', args=None, connection=conn)

## Debug, demo tasks
@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

@app.task
def demo(x):
    print("Hi, "+x)

# Periodic Tasks
# @app.task
# def pull_poloniex_data():
#     from taskapp.helpers import _pull_poloniex_data
#     _pull_poloniex_data()