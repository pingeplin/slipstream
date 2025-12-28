"""Unit tests for GSheetsClient error handling and resilience."""

import unittest.mock as mock

import pytest
from googleapiclient.errors import HttpError

from slipstream.integrations.gsheets import GSheetsClient

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_google_build():
    """Mock the build function and return a mock service."""
    with mock.patch("slipstream.integrations.gsheets.build") as m:
        mock_service = mock.Mock()
        m.return_value = mock_service
        yield mock_service


def test_append_row_rate_limit_retry(mock_google_build):
    """Test that HTTP 429 (rate limit) errors trigger retry logic."""
    # Create mock HTTP 429 error
    mock_response = mock.Mock(status=429)
    rate_limit_error = HttpError(mock_response, b"Rate limit exceeded")

    # Create mock that fails twice with 429, then succeeds
    mock_append = mock.Mock()
    success_response = {"updates": {"updatedRows": 1}}
    mock_append.execute.side_effect = [
        rate_limit_error,
        rate_limit_error,
        success_response,
    ]

    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="test-sheet-123")
    result = client.append_row(["data"])

    # Verify it was called 3 times (2 failures + 1 success)
    assert mock_append.execute.call_count == 3
    assert result == success_response


def test_append_rows_rate_limit_retry(mock_google_build):
    """Test that append_rows also retries on rate limit."""
    mock_response = mock.Mock(status=429)
    rate_limit_error = HttpError(mock_response, b"Rate limit exceeded")

    mock_append = mock.Mock()
    success_response = {"updates": {"updatedRows": 2}}
    mock_append.execute.side_effect = [rate_limit_error, success_response]

    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="test-sheet-123")
    result = client.append_rows([["data1"], ["data2"]])

    # Verify it was called 2 times (1 failure + 1 success)
    assert mock_append.execute.call_count == 2
    assert result == success_response


def test_append_row_max_retries_exceeded(mock_google_build):
    """Test that after max retries, the error is raised."""
    mock_response = mock.Mock(status=429)
    rate_limit_error = HttpError(mock_response, b"Rate limit exceeded")

    mock_append = mock.Mock()
    # Fail all attempts
    mock_append.execute.side_effect = rate_limit_error

    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="test-sheet-123")

    # Should raise HttpError after all retries exhausted
    with pytest.raises(HttpError) as exc_info:
        client.append_row(["data"])

    assert exc_info.value.resp.status == 429


def test_append_row_invalid_spreadsheet_id(mock_google_build):
    """Test handling of 404 errors for invalid spreadsheet ID."""
    mock_response = mock.Mock(status=404)
    not_found_error = HttpError(mock_response, b"Requested entity was not found")

    mock_append = mock.Mock()
    mock_append.execute.side_effect = not_found_error

    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="invalid-id")

    # Should raise HttpError without retry (404 is not retryable)
    with pytest.raises(HttpError) as exc_info:
        client.append_row(["data"])

    assert exc_info.value.resp.status == 404
    # 404 should only be attempted once (not retryable)
    assert mock_append.execute.call_count == 1


def test_append_row_permission_denied(mock_google_build):
    """Test handling of 403 errors for permission denied."""
    mock_response = mock.Mock(status=403)
    permission_error = HttpError(mock_response, b"Permission denied")

    mock_append = mock.Mock()
    mock_append.execute.side_effect = permission_error

    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="test-sheet-123")

    # Should raise HttpError without retry (403 is not retryable)
    with pytest.raises(HttpError) as exc_info:
        client.append_row(["data"])

    assert exc_info.value.resp.status == 403
    # 403 should only be attempted once (not retryable)
    assert mock_append.execute.call_count == 1


def test_append_row_service_unavailable_retry(mock_google_build):
    """Test that HTTP 503 (service unavailable) errors trigger retry."""
    mock_response = mock.Mock(status=503)
    service_error = HttpError(mock_response, b"Service unavailable")

    mock_append = mock.Mock()
    success_response = {"updates": {"updatedRows": 1}}
    mock_append.execute.side_effect = [service_error, success_response]

    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="test-sheet-123")
    result = client.append_row(["data"])

    # Should retry once and succeed
    assert mock_append.execute.call_count == 2
    assert result == success_response


def test_append_row_network_error_retry(mock_google_build):
    """Test that network errors (e.g., ConnectionError) trigger retry."""
    mock_append = mock.Mock()
    success_response = {"updates": {"updatedRows": 1}}
    mock_append.execute.side_effect = [
        ConnectionError("Network error"),
        success_response,
    ]

    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="test-sheet-123")
    result = client.append_row(["data"])

    # Should retry once and succeed
    assert mock_append.execute.call_count == 2
    assert result == success_response


def test_append_row_invalid_range(mock_google_build):
    """Test handling of 400 errors for invalid range."""
    mock_response = mock.Mock(status=400)
    invalid_error = HttpError(mock_response, b"Invalid range")

    mock_append = mock.Mock()
    mock_append.execute.side_effect = invalid_error

    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="test-sheet-123")

    # Should raise HttpError without retry (400 is not retryable)
    with pytest.raises(HttpError) as exc_info:
        client.append_row(["data"], range_name="InvalidRange!")

    assert exc_info.value.resp.status == 400
    # 400 should only be attempted once (not retryable)
    assert mock_append.execute.call_count == 1
