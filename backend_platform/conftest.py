"""Pytest configuration for ForgeCore test suite."""
import django
from django.conf import settings


def pytest_configure(config):
    """Ensure Django is set up before tests run."""
    # pytest.ini already sets DJANGO_SETTINGS_MODULE via addopts/env,
    # but this hook provides a safety net.
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')