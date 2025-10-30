"""
Pytest configuration file for setting up the Django environment.

This module initializes Django settings and the application context
before tests run, ensuring that models and configuration are correctly
loaded for database and logic testing.
"""

import os
import sys
from pathlib import Path

import django
from django.conf import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kobold_keeper.settings')


def pytest_configure(config):
    """
    Pytest hook that runs once at the start of the test session.
    It performs the full Django setup.
    """
    try:
        if not settings.configured:
            django.setup()
    except Exception as e:
        print(f"Error during Django setup: {e}")


def pytest_unconfigure(config):
    """
    Optional cleanup hook.
    """
    pass
