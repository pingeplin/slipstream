import unittest.mock as mock

import pytest

from slipstream.integrations.gdrive import GDriveClient

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_google_build():
    with mock.patch("slipstream.integrations.gdrive.build") as m:
        yield m


def test_init_client_success(mock_google_build):
    """Scenario 1.1: Initialize the Google Drive service using ADC."""
    client = GDriveClient()
    assert client.service is not None
    mock_google_build.assert_called_once_with("drive", "v3")


def test_list_files_in_folder(mock_google_build):
    """Scenario 2.1: List files in a valid folder ID."""
    mock_service = mock_google_build.return_value
    mock_files = mock_service.files.return_value
    mock_list = mock_files.list.return_value
    mock_execute = mock_list.execute

    mock_execute.return_value = {
        "files": [
            {"id": "file1", "name": "receipt1.jpg", "mimeType": "image/jpeg"},
            {"id": "file2", "name": "receipt2.pdf", "mimeType": "application/pdf"},
        ]
    }

    client = GDriveClient()
    files = client.list_files("folder_id_123")

    assert len(files) == 2
    assert files[0]["id"] == "file1"
    assert "folder_id_123" in mock_files.list.call_args[1]["q"]


def test_list_files_filtering(mock_google_build):
    """Scenario 2.3: Filter files by MIME type (JPG, PNG, PDF)."""
    mock_service = mock_google_build.return_value
    mock_files = mock_service.files.return_value

    client = GDriveClient()
    mime_types = ["image/jpeg", "image/png", "application/pdf"]
    client.list_files("folder_id_123", mime_types=mime_types)

    q = mock_files.list.call_args[1]["q"]
    assert "image/jpeg" in q
    assert "image/png" in q
    assert "application/pdf" in q


def test_download_file_success(mock_google_build, tmp_path):
    """Scenario 3.1: Download a specific file by ID to a local path."""
    mock_service = mock_google_build.return_value
    mock_files = mock_service.files.return_value

    # Mocking MediaIoBaseDownload is a bit more involved
    with mock.patch(
        "slipstream.integrations.gdrive.MediaIoBaseDownload"
    ) as mock_download:
        mock_instance = mock_download.return_value
        mock_instance.next_chunk.side_effect = [(None, True)]  # Finished in one go

        client = GDriveClient()
        dest_path = tmp_path / "receipt.jpg"
        client.download_file("file_id_123", str(dest_path))

        mock_download.assert_called_once()
        # Verify it was called with some io object and the request
        assert mock_files.get_media.called


def test_download_file_not_found(mock_google_build, tmp_path):
    """Scenario 3.2: Handle download failures."""
    mock_service = mock_google_build.return_value
    mock_files = mock_service.files.return_value

    # Simulate HttpError
    from googleapiclient.errors import HttpError

    mock_files.get_media.side_effect = HttpError(
        mock.Mock(status=404), b"File not found"
    )

    client = GDriveClient()
    dest_path = tmp_path / "missing.jpg"

    with pytest.raises(HttpError):
        client.download_file("invalid_id", str(dest_path))
