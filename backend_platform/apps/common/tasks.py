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

    @classmethod
    def schedule(
        cls,
        func,
        *,
        name: str,
        schedule_type: str = "D",
        minutes: int | None = None,
        hours: int | None = None,
        cron: str | None = None,
        repeats: int = -1,
        replace_existing: bool = True,
    ) -> bool:
        """Register a recurring schedule with Django-Q2.

        Only active when TASK_MODE='django_q'. In sync mode this is a no-op
        (use the `cleanup_temp` management command instead).

        Args:
            func:            Callable whose dotted path will be scheduled.
            name:            Human-readable schedule name (used as a unique key).
            schedule_type:   Django-Q2 schedule type constant:
                               'I' = minutes interval
                               'H' = hourly
                               'D' = daily   (default)
                               'W' = weekly
                               'M' = monthly
                               'C' = cron
            minutes:         Interval in minutes (used when schedule_type='I').
            hours:           Hour-of-day offset for daily/weekly schedules (0-23).
            cron:            Cron expression string (used when schedule_type='C').
            repeats:         -1 = infinite, 0 = once, N = N times.
            replace_existing: If True, update the schedule if it already exists.

        Returns:
            True if the schedule was created/updated, False if skipped.
        """
        mode = getattr(settings, 'TASK_MODE', 'sync')
        if mode != 'django_q':
            logger.info(
                "TaskDispatcher.schedule: TASK_MODE=%r — schedule '%s' not registered. "
                "Run `manage.py cleanup_temp` manually or switch to TASK_MODE=django_q.",
                mode, name,
            )
            return False

        task_name = f"{func.__module__}.{func.__name__}"

        try:
            from django_q.models import Schedule
        except ImportError:
            logger.error("TaskDispatcher.schedule: django_q not installed — cannot create schedule '%s'.", name)
            return False

        kwargs_q: dict = {
            "func": task_name,
            "name": name,
            "schedule_type": schedule_type,
            "repeats": repeats,
        }
        if minutes is not None:
            kwargs_q["minutes"] = minutes
        if hours is not None:
            kwargs_q["hours"] = hours
        if cron is not None:
            kwargs_q["cron"] = cron

        try:
            existing = Schedule.objects.filter(name=name).first()
            if existing:
                if replace_existing:
                    for attr, val in kwargs_q.items():
                        setattr(existing, attr, val)
                    existing.save()
                    logger.info("TaskDispatcher.schedule: updated existing schedule '%s'.", name)
                    return True
                logger.info("TaskDispatcher.schedule: schedule '%s' already exists, skipping.", name)
                return False

            Schedule.objects.create(**kwargs_q)
            logger.info("TaskDispatcher.schedule: registered new schedule '%s' → %s.", name, task_name)
            return True

        except Exception as exc:
            logger.error("TaskDispatcher.schedule: failed to register '%s': %s", name, exc)
            return False
