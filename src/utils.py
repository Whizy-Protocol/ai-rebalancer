import os


def get_env_variable(env_key, default=None):
    if os.environ.get(env_key):
        return os.environ[env_key]
    return default
