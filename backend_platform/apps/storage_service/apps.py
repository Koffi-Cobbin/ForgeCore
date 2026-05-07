from django.apps import AppConfig


class StorageServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.storage_service'
    label = 'storage_service'

    def ready(self):
        """Register periodic tasks when the app starts up.

        The cleanup schedule is only registered when TASK_MODE='django_q'.
        In sync mode it is a no-op — use `manage.py cleanup_temp` instead.
        """
        from django.conf import settings

        if not getattr(settings, 'REGISTER_PERIODIC_TASKS', True):
            return

        self._register_cleanup_schedule()

    def _register_cleanup_schedule(self):
        from django.conf import settings
        from apps.common.tasks import TaskDispatcher
        from apps.storage_service.tasks import cleanup_temp_files

        schedule_cfg = getattr(settings, 'TEMP_CLEANUP_SCHEDULE', {})

        TaskDispatcher.schedule(
            cleanup_temp_files,
            name=schedule_cfg.get('name', 'storage.cleanup_temp_files'),
            schedule_type=schedule_cfg.get('schedule_type', 'D'),
            hours=schedule_cfg.get('hours', 3),
            repeats=schedule_cfg.get('repeats', -1),
            replace_existing=schedule_cfg.get('replace_existing', True),
        )
