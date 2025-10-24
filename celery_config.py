from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'delete-nameless-entities': {
        'task': 'api.tasks.delete_nameless_entities',
        'schedule': crontab(hour=0, minute=30),
        'args': (),
        'options': {'queue': 'maintenance_queue'}
    },


    'update-all-group-performance-records': {
        'task': 'api.tasks.update_all_group_performance_records',
        'schedule': crontab(hour=6, minute=0),
        'args': (),
        'options': {'queue': 'analytics_queue'}
    },

    'calculate-daily-luckiest-roller': {
        'task': 'api.tasks.calculate_luckiest_roller_of_the_day',
        'schedule': crontab(hour=0, minute=0),
        'args': (),
        'options': {'queue': 'analytics_queue'}
    },
}

CELERY_TASK_QUEUES = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'analytics_queue': {
        'exchange': 'analytics_queue',
        'routing_key': 'analytics_queue',
    },
    'maintenance_queue': {
        'exchange': 'maintenance_queue',
        'routing_key': 'maintenance_queue',
    },
}
