import unittest.mock as mock

import pytest

from slipstream.integrations.gdrive import GDriveClient

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_google_build():
    with mock.patch("slipstream.integrations.gdrive.build") as m:
        yield m


def test_download_files_method_exists(mock_google_build):
    """Test that download_files method exists on GDriveClient."""
    client = GDriveClient()
    assert hasattr(client, "download_files")
    assert callable(client.download_files)


def test_download_files_with_single_file(mock_google_build, tmp_path):
    """Test download_files with a single file (should work like download_file)."""
    with mock.patch(
        "slipstream.integrations.gdrive.MediaIoBaseDownload"
    ) as mock_download:
        mock_instance = mock_download.return_value
        mock_instance.next_chunk.side_effect = [(None, True)]

        client = GDriveClient()
        files = [{"id": "file1", "name": "receipt1.jpg"}]

        results = client.download_files(files, tmp_path)

        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["file_id"] == "file1"
        assert results[0]["dest_path"] == tmp_path / "receipt1.jpg"


def test_download_files_with_multiple_files(mock_google_build, tmp_path):
    """Test download_files with multiple files in parallel."""
    with mock.patch(
        "slipstream.integrations.gdrive.MediaIoBaseDownload"
    ) as mock_download:
        mock_instance = mock_download.return_value
        mock_instance.next_chunk.side_effect = [(None, True)] * 3

        client = GDriveClient()
        files = [
            {"id": "file1", "name": "receipt1.jpg"},
            {"id": "file2", "name": "receipt2.png"},
            {"id": "file3", "name": "receipt3.pdf"},
        ]

        results = client.download_files(files, tmp_path)

        assert len(results) == 3
        assert all(r["success"] for r in results)
        assert {r["file_id"] for r in results} == {"file1", "file2", "file3"}


def test_download_files_with_error_handling(mock_google_build, tmp_path):
    """Test that download_files continues when one file fails (continue-on-error)."""
    mock_service = mock_google_build.return_value
    mock_files = mock_service.files.return_value

    from googleapiclient.errors import HttpError

    # Make the second file fail
    def side_effect_get_media(fileId):
        if fileId == "file2":
            raise HttpError(mock.Mock(status=404), b"File not found")
        return mock.Mock()

    mock_files.get_media.side_effect = side_effect_get_media

    with mock.patch(
        "slipstream.integrations.gdrive.MediaIoBaseDownload"
    ) as mock_download:
        mock_instance = mock_download.return_value
        mock_instance.next_chunk.side_effect = [(None, True)] * 2

        client = GDriveClient()
        files = [
            {"id": "file1", "name": "receipt1.jpg"},
            {"id": "file2", "name": "receipt2.png"},
            {"id": "file3", "name": "receipt3.pdf"},
        ]

        results = client.download_files(files, tmp_path)

        assert len(results) == 3
        # file1 and file3 should succeed, file2 should fail
        success_count = sum(1 for r in results if r["success"])
        failed_count = sum(1 for r in results if not r["success"])

        assert success_count == 2
        assert failed_count == 1

        # Find the failed result
        failed_result = next(r for r in results if not r["success"])
        assert failed_result["file_id"] == "file2"
        assert "error" in failed_result


def test_gdrive_client_accepts_max_workers(mock_google_build):
    """Test that GDriveClient can be initialized with max_workers parameter."""
    client = GDriveClient(max_workers=4)
    assert client.max_workers == 4


def test_gdrive_client_default_max_workers(mock_google_build):
    """Test that GDriveClient has a sensible default for max_workers."""
    client = GDriveClient()
    assert hasattr(client, "max_workers")
    assert isinstance(client.max_workers, int)
    assert client.max_workers > 0


def test_download_files_respects_max_workers(mock_google_build, tmp_path):
    """Test that download_files respects the max_workers parameter."""
    with mock.patch(
        "slipstream.integrations.gdrive.MediaIoBaseDownload"
    ) as mock_download:
        mock_instance = mock_download.return_value
        mock_instance.next_chunk.side_effect = [(None, True)]

        # Test with different max_workers values
        client_2 = GDriveClient(max_workers=2)
        assert client_2.max_workers == 2

        client_8 = GDriveClient(max_workers=8)
        assert client_8.max_workers == 8

        # Verify download_files can be called successfully
        files = [{"id": "file1", "name": "receipt1.jpg"}]
        results = client_2.download_files(files, tmp_path)
        assert len(results) == 1
        assert results[0]["success"] is True
