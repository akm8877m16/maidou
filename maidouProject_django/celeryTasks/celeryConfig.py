# -*- coding:utf-8 -*-
from celery import platforms
from celery.schedules import crontab
from datetime import timedelta

CELERY_RESULT_BACKEND = 'redis://localhost'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_DISABLE_RATE_LIMITS = True
platforms.C_FORCE_ROOT = True

# schedules

CELERYBEAT_SCHEDULE = {
    #'check open status': {
    #     'task': 'celeryTasks.tasks.getOpenStatus',
    #     'schedule': timedelta(seconds=15)       # 每 15 秒执行一次   # 任务函数参数
    #},
    #'check online status': {
    #    'task': 'celeryTasks.tasks.getOnLineStatus',
    #    'schedule': timedelta(seconds=20)  # 每 20 秒执行一次   # 任务函数参数
    #},
    'hour history': {
        'task': 'celeryTasks.tasks.getHourHistory',
        'schedule': crontab(minute=1)  #
    },
    'bill month history':{
        'task': 'celeryTasks.tasks.getBillMonth',
        'schedule': crontab(day_of_month=1)  #
    }
    #'multiply-at-some-time': {
    #    'task': 'celery_app.task2.multiply',
    #    'schedule': crontab(hour=9, minute=50),   # 每天早上 9 点 50 分执行一次
    #    'args': (3, 7)                            # 任务函数参数
    #}getHourHistory
}

