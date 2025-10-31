import os


def get_env_variable(env_key, default=None):
    if env_key in os.environ and os.environ[env_key]:
        return os.environ[env_key]
    return default
