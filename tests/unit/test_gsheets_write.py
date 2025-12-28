"""Unit tests for GSheetsClient write operations."""

import unittest.mock as mock

import pytest

from slipstream.integrations.gsheets import GSheetsClient

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_google_build():
    """Mock the build function and return a mock service."""
    with mock.patch("slipstream.integrations.gsheets.build") as m:
        mock_service = mock.Mock()
        m.return_value = mock_service
        yield mock_service


def test_append_row_success(mock_google_build):
    """Test successfully appending a single row to a spreadsheet."""
    # Setup mock response chain
    mock_append = mock.Mock()
    mock_append.execute.return_value = {
        "updates": {
            "updatedRows": 1,
            "updatedColumns": 4,
            "updatedCells": 4,
        }
    }
    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    # Create client and append a row
    client = GSheetsClient(spreadsheet_id="test-sheet-123")
    values = ["Merchant A", "2024-01-15", "USD", 123.45]
    result = client.append_row(values)

    # Verify the API was called correctly
    mock_spreadsheets.values.assert_called_once()
    mock_values.append.assert_called_once_with(
        spreadsheetId="test-sheet-123",
        range="Sheet1!A1",
        valueInputOption="RAW",
        body={"values": [values]},
    )
    mock_append.execute.assert_called_once()

    # Verify result
    assert result["updates"]["updatedRows"] == 1


def test_append_row_with_custom_range(mock_google_build):
    """Test appending a row to a custom range."""
    mock_append = mock.Mock()
    mock_append.execute.return_value = {"updates": {"updatedRows": 1}}
    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="test-sheet-123")
    values = ["Data1", "Data2"]
    client.append_row(values, range_name="MySheet!B5")

    mock_values.append.assert_called_once_with(
        spreadsheetId="test-sheet-123",
        range="MySheet!B5",
        valueInputOption="RAW",
        body={"values": [values]},
    )


def test_append_rows_batch_success(mock_google_build):
    """Test successfully appending multiple rows in batch."""
    mock_append = mock.Mock()
    mock_append.execute.return_value = {
        "updates": {
            "updatedRows": 3,
            "updatedColumns": 4,
            "updatedCells": 12,
        }
    }
    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="test-sheet-123")
    rows = [
        ["Merchant A", "2024-01-15", "USD", 123.45],
        ["Merchant B", "2024-01-16", "EUR", 234.56],
        ["Merchant C", "2024-01-17", "JPY", 345.67],
    ]
    result = client.append_rows(rows)

    # Verify the API was called correctly
    mock_values.append.assert_called_once_with(
        spreadsheetId="test-sheet-123",
        range="Sheet1!A1",
        valueInputOption="RAW",
        body={"values": rows},
    )

    # Verify result
    assert result["updates"]["updatedRows"] == 3


def test_append_rows_with_custom_range(mock_google_build):
    """Test appending multiple rows to a custom range."""
    mock_append = mock.Mock()
    mock_append.execute.return_value = {"updates": {"updatedRows": 2}}
    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="test-sheet-123")
    rows = [["A", "B"], ["C", "D"]]
    client.append_rows(rows, range_name="Data!C10")

    mock_values.append.assert_called_once_with(
        spreadsheetId="test-sheet-123",
        range="Data!C10",
        valueInputOption="RAW",
        body={"values": rows},
    )


def test_append_row_requires_spreadsheet_id(mock_google_build):
    """Test that append_row raises error if spreadsheet_id is not set."""
    client = GSheetsClient()  # No spreadsheet_id

    with pytest.raises(ValueError, match="spreadsheet_id must be set"):
        client.append_row(["data"])


def test_append_rows_requires_spreadsheet_id(mock_google_build):
    """Test that append_rows raises error if spreadsheet_id is not set."""
    client = GSheetsClient()  # No spreadsheet_id

    with pytest.raises(ValueError, match="spreadsheet_id must be set"):
        client.append_rows([["data"]])


def test_append_row_with_empty_values(mock_google_build):
    """Test appending an empty row."""
    mock_append = mock.Mock()
    mock_append.execute.return_value = {"updates": {"updatedRows": 1}}
    mock_values = mock.Mock()
    mock_values.append.return_value = mock_append
    mock_spreadsheets = mock.Mock()
    mock_spreadsheets.values.return_value = mock_values
    mock_google_build.spreadsheets.return_value = mock_spreadsheets

    client = GSheetsClient(spreadsheet_id="test-sheet-123")
    client.append_row([])

    mock_values.append.assert_called_once_with(
        spreadsheetId="test-sheet-123",
        range="Sheet1!A1",
        valueInputOption="RAW",
        body={"values": [[]]},
    )
