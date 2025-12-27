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

# Test data from environment variables (no defaults - must be set by developer)
TEST_FOLDER_URL = os.getenv("TEST_GDRIVE_FOLDER_URL")
TEST_FOLDER_ID = os.getenv("TEST_GDRIVE_FOLDER_ID")
EXPECTED_FILE_COUNT = int(os.getenv("TEST_GDRIVE_FILE_COUNT", "3"))
EMPTY_FOLDER_ID = os.getenv("TEST_GDRIVE_EMPTY_FOLDER_ID")

runner = CliRunner()


def check_env_vars():
    """Check if required environment variables are set."""
    missing = []
    if not TEST_FOLDER_URL:
        missing.append("TEST_GDRIVE_FOLDER_URL")
    if not TEST_FOLDER_ID:
        missing.append("TEST_GDRIVE_FOLDER_ID")
    if not EMPTY_FOLDER_ID:
        missing.append("TEST_GDRIVE_EMPTY_FOLDER_ID")

    if missing:
        pytest.skip(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and set your test folder IDs."
        )


@pytest.fixture
def integration_env():
    """Fixture to set up integration test environment.

    This can be expanded to verify ADC is configured, set environment variables,
    or perform other setup tasks.
    """
    # Future: Add ADC validation here if needed
    return
    # Future: Add cleanup if needed


@pytest.mark.integration
def test_process_folder_via_url(integration_env):
    """Scenario 1: Process Folder via URL (Happy Path).

    Verifies that providing a valid Google Drive folder URL correctly triggers
    the download of all supported files.
    """
    check_env_vars()
    result = runner.invoke(app, ["--folder", TEST_FOLDER_URL])

    # Verify exit code is 0
    assert result.exit_code == 0, (
        f"Expected exit code 0, got {result.exit_code}\nOutput: {result.stdout}\nError: {result.stderr}"
    )

    # Verify folder ID is being processed
    assert f"Processing folder: {TEST_FOLDER_ID}" in result.stdout

    # Verify all 3 files are reported as downloaded
    # Count "Downloaded" messages
    download_count = result.stdout.count("Downloaded")
    assert download_count == EXPECTED_FILE_COUNT, (
        f"Expected {EXPECTED_FILE_COUNT} files to be downloaded, found {download_count}"
    )


@pytest.mark.integration
def test_process_folder_via_id(integration_env):
    """Scenario 2: Process Folder via Folder ID.

    Verifies that providing a raw Google Drive folder ID works identically to the URL.
    """
    check_env_vars()
    result = runner.invoke(app, ["--folder", TEST_FOLDER_ID])

    # Verify exit code is 0
    assert result.exit_code == 0, (
        f"Expected exit code 0, got {result.exit_code}\nOutput: {result.stdout}\nError: {result.stderr}"
    )

    # Verify folder ID is being processed
    assert f"Processing folder: {TEST_FOLDER_ID}" in result.stdout

    # Verify all 3 files are reported as downloaded
    download_count = result.stdout.count("Downloaded")
    assert download_count == EXPECTED_FILE_COUNT, (
        f"Expected {EXPECTED_FILE_COUNT} files to be downloaded, found {download_count}"
    )


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
def test_process_empty_folder(integration_env):
    """Scenario 4: Process Empty Folder (or folder with no supported files).

    Verifies behavior when no files match the required MIME types.
    """
    check_env_vars()
    result = runner.invoke(app, ["--folder", EMPTY_FOLDER_ID])

    # Verify exit code is 0 (graceful handling)
    assert result.exit_code == 0, (
        f"Expected exit code 0, got {result.exit_code}\nOutput: {result.stdout}\nError: {result.stderr}"
    )

    # Verify the "no files found" message
    assert "No supported files found in folder." in result.stdout, (
        f"Expected 'No supported files found' message\nOutput: {result.stdout}"
    )
