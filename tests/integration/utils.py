import functools
import os

import pytest


def skip_if_missing_env_vars(required_vars):
    """
    Decorator to skip tests if required environment variables are not set.

    Args:
        required_vars (list): List of environment variable names to check.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            missing = [var for var in required_vars if not os.getenv(var)]
            if missing:
                pytest.skip(
                    f"Missing required environment variables: {', '.join(missing)}. "
                    "Ensure they are set in your environment or .env file."
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator
