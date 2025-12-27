import functools
import os

import pytest
from google.api_core.exceptions import PermissionDenied


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


def skip_on_billing_error(func):
    """
    Decorator to skip tests if Google Cloud billing is not enabled.

    Useful for Google Cloud Vision API and other GCP services that require billing.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PermissionDenied as e:
            if "billing" in str(e).lower():
                pytest.skip(
                    "Google Cloud Vision API requires billing to be enabled. "
                    "Enable billing on your project or skip integration tests."
                )
            raise

    return wrapper


def verify_cli_success(result, expected_folder_id, expected_file_count):
    """
    Verify common CLI success criteria for workflow tests.

    Args:
        result: CliRunner result object from typer.testing
        expected_folder_id: Expected folder ID in output
        expected_file_count: Expected number of downloaded files
    """
    assert result.exit_code == 0, (
        f"Expected exit code 0, got {result.exit_code}\n"
        f"Output: {result.stdout}\nError: {result.stderr}"
    )

    assert f"Processing folder: {expected_folder_id}" in result.stdout, (
        f"Expected folder ID {expected_folder_id} in output\nOutput: {result.stdout}"
    )

    download_count = result.stdout.count("Downloaded")
    assert download_count == expected_file_count, (
        f"Expected {expected_file_count} files downloaded, found {download_count}\n"
        f"Output: {result.stdout}"
    )


def verify_cli_error(result, expected_exit_code, expected_error_substring):
    """
    Verify CLI error handling criteria for workflow tests.

    Args:
        result: CliRunner result object from typer.testing
        expected_exit_code: Expected non-zero exit code
        expected_error_substring: Expected error message substring
    """
    assert result.exit_code == expected_exit_code, (
        f"Expected exit code {expected_exit_code}, got {result.exit_code}\n"
        f"Output: {result.stdout}\nError: {result.stderr}"
    )

    # Check both stdout and stderr for error message
    error_output = result.stdout + result.stderr
    assert expected_error_substring in error_output, (
        f"Expected error message '{expected_error_substring}' not found\n"
        f"Output: {result.stdout}\nError: {result.stderr}"
    )
