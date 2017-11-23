# -*- coding: utf-8 -*-

import pytz

broker_url = 'redis://127.0.0.1:6379/11'

timezone = pytz.timezone('Asia/Shanghai')

imports = ['task.poll_publisher']

beat_schedule = {
    'poll_publisher': {
        'task': 'poll_instagram',
        'schedule': 15
    }
}
