"""Integration tests for Google Drive folder processing.

These tests require:
- Google Cloud Application Default Credentials (ADC) to be configured
  Run: gcloud auth application-default login
- Environment variables for test folders (see .env.example)
  Copy .env.example to .env and update with your own test folder IDs
- Execute with: pytest -m integration
"""

import os

import pytest
from typer.testing import CliRunner

from slipstream.main import app
from tests.integration.utils import skip_if_missing_env_vars

# Test data from environment variables (no defaults - must be set by developer)
TEST_FOLDER_URL = os.getenv("TEST_GDRIVE_FOLDER_URL")
TEST_FOLDER_ID = os.getenv("TEST_GDRIVE_FOLDER_ID")
EXPECTED_FILE_COUNT = int(os.getenv("TEST_GDRIVE_FILE_COUNT", "3"))
EMPTY_FOLDER_ID = os.getenv("TEST_GDRIVE_EMPTY_FOLDER_ID")

runner = CliRunner()


GDRIVE_REQUIRED_VARS = [
    "TEST_GDRIVE_FOLDER_URL",
    "TEST_GDRIVE_FOLDER_ID",
    "TEST_GDRIVE_EMPTY_FOLDER_ID",
]


@pytest.fixture
def integration_env():
    """Fixture to set up integration test environment.

    This can be expanded to verify ADC is configured, set environment variables,
    or perform other setup tasks.
    """
    # Future: Add ADC validation here if needed
    return
    # Future: Add cleanup if needed


def run_app_and_verify_success(args, expected_folder_id):
    """Helper to run the app and verify common success criteria."""
    result = runner.invoke(app, args)

    # Verify exit code is 0
    assert result.exit_code == 0, (
        f"Expected exit code 0, got {result.exit_code}\nOutput: {result.stdout}\nError: {result.stderr}"
    )

    # Verify folder ID is being processed
    assert f"Processing folder: {expected_folder_id}" in result.stdout

    # Verify all files are reported as downloaded
    download_count = result.stdout.count("Downloaded")
    assert download_count == EXPECTED_FILE_COUNT, (
        f"Expected {EXPECTED_FILE_COUNT} files to be downloaded, found {download_count}"
    )
    return result


@pytest.mark.integration
@skip_if_missing_env_vars(GDRIVE_REQUIRED_VARS)
def test_process_folder_via_url(integration_env):
    """Scenario 1: Process Folder via URL (Happy Path).

    Verifies that providing a valid Google Drive folder URL correctly triggers
    the download of all supported files.
    """
    run_app_and_verify_success(["--folder", TEST_FOLDER_URL], TEST_FOLDER_ID)


@pytest.mark.integration
@skip_if_missing_env_vars(GDRIVE_REQUIRED_VARS)
def test_process_folder_via_id(integration_env):
    """Scenario 2: Process Folder via Folder ID.

    Verifies that providing a raw Google Drive folder ID works identically to the URL.
    """
    run_app_and_verify_success(["--folder", TEST_FOLDER_ID], TEST_FOLDER_ID)


@pytest.mark.integration
def test_process_invalid_folder_id(integration_env):
    """Scenario 3: Process Invalid Folder ID.

    Verifies the system's behavior when a non-existent or inaccessible folder ID is provided.
    """
    # This test doesn't require env vars since it uses a fake ID
    invalid_folder_id = "non_existent_id_12345"
    result = runner.invoke(app, ["--folder", invalid_folder_id])

    # Verify exit code is non-zero
    assert result.exit_code == 1, (
        f"Expected exit code 1, got {result.exit_code}\nOutput: {result.stdout}\nError: {result.stderr}"
    )

    # Verify error message is shown
    # The error should mention Google Drive communication issue
    assert "Error communicating with Google Drive" in result.stderr, (
        f"Expected error message about Google Drive communication\nStderr: {result.stderr}"
    )


@pytest.mark.integration
@skip_if_missing_env_vars(GDRIVE_REQUIRED_VARS)
def test_process_empty_folder(integration_env):
    """Scenario 4: Process Empty Folder (or folder with no supported files).

    Verifies behavior when no files match the required MIME types.
    """
    result = runner.invoke(app, ["--folder", EMPTY_FOLDER_ID])

    # Verify exit code is 0 (graceful handling)
    assert result.exit_code == 0, (
        f"Expected exit code 0, got {result.exit_code}\nOutput: {result.stdout}\nError: {result.stderr}"
    )

    # Verify the "no files found" message
    assert "No supported files found in folder." in result.stdout, (
        f"Expected 'No supported files found' message\nOutput: {result.stdout}"
    )
