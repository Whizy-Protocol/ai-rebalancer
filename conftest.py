"""
Pytest configuration file to load environment variables from .env file.
"""

from dotenv import load_dotenv


def pytest_configure(config):
    """Load environment variables before running tests"""
    load_dotenv()
