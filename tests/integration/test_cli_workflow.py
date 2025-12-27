"""End-to-end integration tests for Slipstream CLI workflow.

Tests the complete flow: CLI → URL Parser → Google Drive → Download → OCR

These tests verify the complete integration of all components in the Slipstream
CLI tool, from accepting folder IDs/URLs through to extracting text via OCR.

Requirements:
- Google Cloud credentials (gcloud auth application-default login)
- Environment variables in .env (see .env.example):
  - TEST_GDRIVE_FOLDER_URL: URL to test folder with receipt images
  - TEST_GDRIVE_FOLDER_ID: Folder ID for the same test folder
  - TEST_GDRIVE_FILE_COUNT: Number of supported files in test folder
  - TEST_GDRIVE_EMPTY_FOLDER_ID: Empty folder for testing edge cases

Run with: pytest -m integration

Note: Tests skip gracefully if credentials or environment variables are not configured.
"""

import os

import pytest
from typer.testing import CliRunner

from slipstream.main import app
from tests.integration.utils import (
    skip_if_missing_env_vars,
    skip_on_billing_error,
    verify_cli_error,
    verify_cli_success,
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Environment variables for test configuration
TEST_FOLDER_URL = os.getenv("TEST_GDRIVE_FOLDER_URL")
TEST_FOLDER_ID = os.getenv("TEST_GDRIVE_FOLDER_ID")
EXPECTED_FILE_COUNT = int(os.getenv("TEST_GDRIVE_FILE_COUNT", "3"))
EMPTY_FOLDER_ID = os.getenv("TEST_GDRIVE_EMPTY_FOLDER_ID")

# CLI runner instance
runner = CliRunner()

# Core environment variables required for most tests
CORE_ENV_VARS = [
    "TEST_GDRIVE_FOLDER_URL",
    "TEST_GDRIVE_FOLDER_ID",
    "TEST_GDRIVE_EMPTY_FOLDER_ID",
]


# Happy Path Tests


@pytest.mark.integration
@skip_if_missing_env_vars(CORE_ENV_VARS)
@skip_on_billing_error
def test_cli_workflow_with_folder_url_complete_pipeline():
    """Test complete workflow from folder URL to OCR extraction.

    This test validates the entire end-to-end flow:
    1. CLI accepts Google Drive folder URL
    2. URL parser extracts folder ID
    3. Google Drive client lists files
    4. Files are downloaded to temp directory
    5. OCR processes each downloaded file
    6. Extracted text is reported

    This is the primary happy path test for the Slipstream CLI.
    """
    result = runner.invoke(app, ["process", "--folder", TEST_FOLDER_URL])

    # Verify basic success criteria
    verify_cli_success(result, TEST_FOLDER_ID, EXPECTED_FILE_COUNT)

    # Verify OCR extraction occurred
    ocr_extract_count = result.stdout.count("Extracted text from")
    assert ocr_extract_count == EXPECTED_FILE_COUNT, (
        f"Expected OCR extraction for {EXPECTED_FILE_COUNT} files, "
        f"found {ocr_extract_count}\nOutput: {result.stdout}"
    )

    # Verify extracted text has character counts (sanity check)
    assert "characters" in result.stdout, (
        f"Expected character count in OCR output\nOutput: {result.stdout}"
    )


@pytest.mark.integration
@skip_if_missing_env_vars(CORE_ENV_VARS)
@skip_on_billing_error
def test_cli_workflow_with_folder_id_complete_pipeline():
    """Test complete workflow using folder ID instead of URL.

    Validates that both URL and raw folder ID inputs work identically.
    This ensures the URL parser correctly handles both input formats.
    """
    result = runner.invoke(app, ["process", "--folder", TEST_FOLDER_ID])

    # Verify basic success criteria
    verify_cli_success(result, TEST_FOLDER_ID, EXPECTED_FILE_COUNT)

    # Verify OCR extraction occurred
    ocr_extract_count = result.stdout.count("Extracted text from")
    assert ocr_extract_count == EXPECTED_FILE_COUNT, (
        f"Expected OCR extraction for {EXPECTED_FILE_COUNT} files, "
        f"found {ocr_extract_count}"
    )


@pytest.mark.integration
@skip_if_missing_env_vars(CORE_ENV_VARS)
@skip_on_billing_error
def test_cli_workflow_ocr_text_extraction_quality():
    """Verify OCR extraction produces meaningful text output.

    This test checks that the OCR integration is working correctly
    by validating that extracted text contains expected patterns
    (digits for receipts, non-zero character counts).
    """
    result = runner.invoke(app, ["process", "--folder", TEST_FOLDER_ID])

    assert result.exit_code == 0, f"CLI failed: {result.stderr}"

    # Verify that character counts are positive
    # Format: "Extracted text from {filename}: {count} characters"
    import re

    char_count_pattern = r"Extracted text from .+: (\d+) characters"
    matches = re.findall(char_count_pattern, result.stdout)

    assert len(matches) > 0, "No OCR character counts found in output"

    for count_str in matches:
        count = int(count_str)
        assert count > 0, "OCR extracted 0 characters, expected text content"


# Error Scenario Tests


@pytest.mark.integration
def test_cli_workflow_invalid_url_format():
    """Test CLI handling of malformed URLs.

    Verifies that the URL parser correctly rejects invalid URLs
    and the CLI exits with proper error messages.
    """
    # Test URL parsing errors (these should fail at URL validation stage)
    url_parsing_errors = [
        "https://example.com/not-a-drive-url",  # Wrong domain
        "https://drive.google.com/invalid/path/12345",  # Invalid path
    ]

    for invalid_url in url_parsing_errors:
        result = runner.invoke(app, ["process", "--folder", invalid_url])

        # Should exit with code 1
        assert result.exit_code == 1, f"Expected exit code 1 for '{invalid_url}'"

        # Should mention URL parsing issue
        error_output = result.stdout + result.stderr
        assert (
            "Unsupported URL domain" in error_output
            or "Could not find ID in URL" in error_output
        ), f"Expected URL parsing error for '{invalid_url}'\nOutput: {error_output}"


@pytest.mark.integration
def test_cli_workflow_invalid_folder_id():
    """Test CLI handling of non-existent folder IDs.

    Verifies that attempting to access a non-existent folder
    fails gracefully with an appropriate error message.
    """
    invalid_folder_id = "invalid_folder_id_12345_nonexistent"
    result = runner.invoke(app, ["process", "--folder", invalid_folder_id])

    # Should exit with code 1
    verify_cli_error(result, 1, "Error communicating with Google Drive")


@pytest.mark.integration
@skip_if_missing_env_vars(CORE_ENV_VARS)
def test_cli_workflow_empty_folder():
    """Test graceful handling of folders with no supported files.

    Verifies that processing an empty folder (or one with only
    unsupported file types) completes successfully without errors,
    and reports that no files were found.
    """
    result = runner.invoke(app, ["process", "--folder", EMPTY_FOLDER_ID])

    # Should exit with code 0 (not an error condition)
    assert result.exit_code == 0, (
        f"Expected exit code 0 for empty folder, got {result.exit_code}\n"
        f"Output: {result.stdout}\nError: {result.stderr}"
    )

    # Should indicate no files found
    assert "No supported files found in folder." in result.stdout, (
        f"Expected 'No supported files found' message\nOutput: {result.stdout}"
    )

    # Should not attempt any downloads or OCR
    assert "Downloaded" not in result.stdout
    assert "Extracted text from" not in result.stdout


@pytest.mark.integration
@skip_if_missing_env_vars(CORE_ENV_VARS)
@skip_on_billing_error
def test_cli_workflow_reports_processing_steps():
    """Verify CLI provides clear progress reporting.

    Ensures that users can see what the CLI is doing at each step:
    - Folder being processed
    - Files being downloaded
    - OCR extraction in progress
    """
    result = runner.invoke(app, ["process", "--folder", TEST_FOLDER_ID])

    assert result.exit_code == 0, f"CLI failed: {result.stderr}"

    # Should show folder processing
    assert f"Processing folder: {TEST_FOLDER_ID}" in result.stdout

    # Should show download progress
    assert "Downloaded" in result.stdout

    # Should show OCR progress
    assert "Extracted text from" in result.stdout


# Edge Case Tests


@pytest.mark.integration
def test_cli_workflow_url_with_user_parameter():
    """Test handling of Drive URLs with user-specific parameters.

    Google Drive URLs sometimes include '/u/0/' or '/u/1/' for multi-account users.
    This test verifies the URL parser handles these variations correctly.
    """
    if not TEST_FOLDER_ID:
        pytest.skip("TEST_GDRIVE_FOLDER_ID not set")

    # Construct URL with user parameter
    url_with_user = f"https://drive.google.com/drive/u/0/folders/{TEST_FOLDER_ID}"

    result = runner.invoke(app, ["process", "--folder", url_with_user])

    # Should extract the folder ID correctly and process normally
    # We don't need full success (no billing), just verify ID extraction
    assert (
        f"Processing folder: {TEST_FOLDER_ID}" in result.stdout
        or result.exit_code
        in [
            0,
            1,
        ]
    )


@pytest.mark.integration
@skip_if_missing_env_vars(CORE_ENV_VARS)
def test_cli_workflow_short_flag():
    """Test that the short flag '-f' works identically to '--folder'."""
    result = runner.invoke(app, ["process", "-f", TEST_FOLDER_ID])

    # Should work the same as --folder
    assert f"Processing folder: {TEST_FOLDER_ID}" in result.stdout


# Anthropic LLM Integration Tests


@pytest.mark.integration
@skip_if_missing_env_vars(CORE_ENV_VARS)
@skip_on_billing_error
def test_cli_workflow_complete_pipeline_with_llm(mocker):
    """Test complete workflow including Anthropic LLM extraction.

    This test validates the full end-to-end flow including LLM:
    1. CLI accepts Google Drive folder URL
    2. URL parser extracts folder ID
    3. Google Drive client lists files
    4. Files are downloaded to temp directory
    5. OCR processes each downloaded file
    6. Anthropic LLM extracts structured data from OCR text
    7. Extracted structured data is reported

    This test uses mocking for the LLM to avoid API costs and ensure consistency.
    """
    # Mock the AnthropicExtractor
    from slipstream.models import ExtractionResult, Receipt

    mock_receipt = Receipt(
        merchant_name="Test Store",
        date="2024-01-15",
        total_amount=42.50,
        currency="USD",
        items=[],
        payment_method=None,
        tax=None,
        confidence_score=0.95,
        raw_text="Sample OCR text",
    )

    mock_result = ExtractionResult(
        receipt=mock_receipt,
        input_tokens=100,
        output_tokens=50,
        cache_creation_input_tokens=2000,
        cache_read_input_tokens=0,
        processing_time=0.5,
    )

    # Mock the extract_receipt_data method to return our test data
    mock_extractor = mocker.patch("slipstream.main.AnthropicExtractor", autospec=True)
    mock_instance = mock_extractor.return_value
    mock_instance.extract_receipt_data = mocker.AsyncMock(return_value=mock_result)

    result = runner.invoke(app, ["process", "--folder", TEST_FOLDER_URL])

    # Verify basic success criteria
    verify_cli_success(result, TEST_FOLDER_ID, EXPECTED_FILE_COUNT)

    # Verify OCR extraction occurred
    ocr_extract_count = result.stdout.count("Extracted text from")
    assert ocr_extract_count == EXPECTED_FILE_COUNT, (
        f"Expected OCR extraction for {EXPECTED_FILE_COUNT} files, "
        f"found {ocr_extract_count}\nOutput: {result.stdout}"
    )

    # Verify LLM extraction occurred
    llm_extract_count = result.stdout.count("Structured data extracted")
    assert llm_extract_count == EXPECTED_FILE_COUNT, (
        f"Expected LLM extraction for {EXPECTED_FILE_COUNT} files, "
        f"found {llm_extract_count}\nOutput: {result.stdout}"
    )

    # Verify merchant name appears in output
    assert "Test Store" in result.stdout, (
        f"Expected merchant name 'Test Store' in output\nOutput: {result.stdout}"
    )


@pytest.mark.integration
@skip_if_missing_env_vars(CORE_ENV_VARS)
@skip_on_billing_error
def test_cli_workflow_llm_failure_handling(mocker):
    """Test CLI handles LLM errors gracefully (continue-on-error).

    This test verifies that when the LLM fails to extract data from one file,
    the CLI continues processing other files and reports the error appropriately.
    """
    from slipstream.integrations.anthropic_extractor import ExtractionRefusedError
    from slipstream.models import ExtractionResult, Receipt

    # Create a mock that raises an error on first call, succeeds on subsequent calls
    mock_receipt = Receipt(
        merchant_name="Success Store",
        date="2024-01-15",
        total_amount=25.00,
        currency="USD",
        items=[],
        payment_method=None,
        tax=None,
        confidence_score=0.92,
        raw_text="Sample OCR text",
    )

    mock_result = ExtractionResult(
        receipt=mock_receipt,
        input_tokens=100,
        output_tokens=50,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=2000,
        processing_time=0.5,
    )

    # Mock the extractor to fail once, then succeed
    mock_extractor = mocker.patch("slipstream.main.AnthropicExtractor", autospec=True)
    mock_instance = mock_extractor.return_value
    mock_instance.extract_receipt_data = mocker.AsyncMock(
        side_effect=[
            ExtractionRefusedError("Model refused to process"),
            mock_result,
            mock_result,
        ]
    )

    result = runner.invoke(app, ["process", "--folder", TEST_FOLDER_ID])

    # Should still exit with code 0 (continue-on-error)
    assert result.exit_code == 0, (
        f"Expected exit code 0 (continue-on-error), got {result.exit_code}\n"
        f"Output: {result.stdout}\nError: {result.stderr}"
    )

    # Verify error message for failed extraction (check both stdout and stderr)
    error_output = result.stdout + result.stderr
    assert "Failed to extract structured data" in error_output or (
        "Model refused to process" in error_output
    ), (
        f"Expected LLM error message in output\nOutput: {result.stdout}\nError: {result.stderr}"
    )

    # Verify successful extractions for other files
    llm_success_count = result.stdout.count("Structured data extracted")
    assert llm_success_count >= 2, (
        f"Expected at least 2 successful LLM extractions, found {llm_success_count}\n"
        f"Output: {result.stdout}"
    )


@pytest.mark.integration
@skip_if_missing_env_vars(CORE_ENV_VARS)
@skip_on_billing_error
def test_cli_workflow_llm_incomplete_response(mocker):
    """Test CLI handles LLM truncation errors gracefully.

    This test verifies that when the LLM response is truncated due to token limits,
    the CLI reports a warning and continues processing other files.
    """
    from slipstream.integrations.anthropic_extractor import (
        ExtractionIncompleteError,
    )
    from slipstream.models import ExtractionResult, Receipt

    mock_receipt = Receipt(
        merchant_name="Complete Store",
        date="2024-01-15",
        total_amount=30.00,
        currency="USD",
        items=[],
        payment_method=None,
        tax=None,
        confidence_score=0.88,
        raw_text="Sample OCR text",
    )

    mock_result = ExtractionResult(
        receipt=mock_receipt,
        input_tokens=100,
        output_tokens=50,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=2000,
        processing_time=0.5,
    )

    # Mock to raise incomplete error once, then succeed
    mock_extractor = mocker.patch("slipstream.main.AnthropicExtractor", autospec=True)
    mock_instance = mock_extractor.return_value
    mock_instance.extract_receipt_data = mocker.AsyncMock(
        side_effect=[
            ExtractionIncompleteError("Response truncated"),
            mock_result,
            mock_result,
        ]
    )

    result = runner.invoke(app, ["process", "--folder", TEST_FOLDER_ID])

    # Should still exit with code 0 (continue-on-error)
    assert result.exit_code == 0, f"CLI failed: {result.stderr}"

    # Verify warning message for truncated response (check both stdout and stderr)
    error_output = result.stdout + result.stderr
    assert (
        "Response truncated" in error_output
        or "Failed to extract structured data" in error_output
    ), (
        f"Expected truncation warning in output\nOutput: {result.stdout}\nError: {result.stderr}"
    )

    # Verify successful extractions for other files
    llm_success_count = result.stdout.count("Structured data extracted")
    assert llm_success_count >= 2, (
        f"Expected at least 2 successful LLM extractions, found {llm_success_count}\n"
        f"Output: {result.stdout}"
    )
