import os
from celery import Celery
from celery.signals import worker_ready
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Create Celery app
celery_app = Celery(
    'audio_video_processor',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'tasks.video_tasks',
        'tasks.audio_tasks', 
        'tasks.ai_tasks',
        'tasks.storage_tasks'
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'tasks.video_tasks.*': {'queue': 'video_processing'},
        'tasks.audio_tasks.*': {'queue': 'audio_processing'},
        'tasks.ai_tasks.*': {'queue': 'ai_processing'},
        'tasks.storage_tasks.*': {'queue': 'storage'},
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },
    
    # Task execution settings
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    task_reject_on_worker_lost=True,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handler for when worker is ready"""
    logger.info(f"Celery worker {sender} is ready")

if __name__ == '__main__':
    celery_app.start()

