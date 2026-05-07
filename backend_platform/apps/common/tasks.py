import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class TaskDispatcher:
    """
    Central task dispatcher abstraction.
    Routes tasks to sync execution or Django-Q2 based on TASK_MODE setting.
    This abstraction allows future migration to Celery, Redis, SQS, etc.
    """

    @classmethod
    def dispatch(cls, func, *args, **kwargs):
        mode = getattr(settings, 'TASK_MODE', 'sync')
        task_name = f"{func.__module__}.{func.__name__}"

        if mode == 'django_q':
            try:
                from django_q.tasks import async_task
                async_task(task_name, *args, **kwargs)
                logger.info(f"Task dispatched async: {task_name}")
            except Exception as e:
                logger.error(f"Failed to dispatch async task {task_name}: {e}. Falling back to sync.")
                cls._run_sync(func, *args, **kwargs)
        else:
            cls._run_sync(func, *args, **kwargs)

    @classmethod
    def _run_sync(cls, func, *args, **kwargs):
        task_name = f"{func.__module__}.{func.__name__}"
        try:
            func(*args, **kwargs)
            logger.info(f"Task executed sync: {task_name}")
        except Exception as e:
            logger.error(f"Sync task {task_name} failed: {e}")
            raise

    @classmethod
    def dispatch_with_hook(cls, func, hook, *args, **kwargs):
        mode = getattr(settings, 'TASK_MODE', 'sync')
        task_name = f"{func.__module__}.{func.__name__}"
        hook_name = f"{hook.__module__}.{hook.__name__}"

        if mode == 'django_q':
            try:
                from django_q.tasks import async_task
                async_task(task_name, *args, hook=hook_name, **kwargs)
            except Exception as e:
                logger.error(f"Failed to dispatch async task with hook: {e}. Falling back to sync.")
                cls._run_sync(func, *args, **kwargs)
        else:
            cls._run_sync(func, *args, **kwargs)
