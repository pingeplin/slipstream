from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from slipstream.integrations.gdrive import DownloadResult
from slipstream.main import app

pytestmark = pytest.mark.unit

runner = CliRunner()


@pytest.fixture
def mock_gdrive_client():
    with patch("slipstream.main.GDriveClient") as mock:
        yield mock


@pytest.fixture
def mock_ocr_engine():
    with patch("slipstream.main.OCREngine") as mock:
        mock_instance = mock.return_value
        # Default: return simple text for any image
        mock_instance.extract_text.return_value = "Sample receipt text"
        yield mock


def test_process_command_exists():
    """Verify that the 'process' command exists in the CLI."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "process" in result.stdout.lower()


def test_process_folder_required():
    """Verify that --folder is a required argument for the process command."""
    # In Typer, if an option is required and not provided, it should fail
    result = runner.invoke(app, ["process", "--folder"])
    assert result.exit_code != 0
    assert (
        "Missing option" in result.stdout
        or "--folder" in result.stdout
        or "Missing option" in result.stderr
        or "--folder" in result.stderr
    )


def test_folder_id_parsing(mock_gdrive_client):
    """Verify that both raw IDs and URLs are correctly parsed by the CLI."""
    # Use a URL
    url = "https://drive.google.com/drive/folders/XYZ123"
    result = runner.invoke(app, ["process", "--folder", url])
    assert result.exit_code == 0
    assert "Processing folder: XYZ123" in result.stdout


def test_folder_id_parsing_alias(mock_gdrive_client):
    """Verify that the -f alias for --folder works."""
    url = "https://drive.google.com/drive/folders/XYZ123"
    result = runner.invoke(app, ["process", "-f", url])
    assert result.exit_code == 0
    assert "Processing folder: XYZ123" in result.stdout


def test_invalid_folder_url():
    """Verify the CLI reports a clear error when an invalid URL is provided."""
    result = runner.invoke(app, ["process", "--folder", "https://wrong.com/abc"])
    assert result.exit_code != 0
    assert (
        "Unsupported URL domain" in result.stdout
        or "Unsupported URL domain" in result.stderr
    )


def test_process_flow_success(mock_gdrive_client, mock_ocr_engine, tmp_path):
    """Verify the end-to-end flow: parse URL -> list files -> download files."""
    mock_instance = mock_gdrive_client.return_value
    files = [
        {"id": "f1", "name": "r1.jpg", "mimeType": "image/jpeg"},
        {"id": "f2", "name": "r2.png", "mimeType": "image/png"},
    ]
    mock_instance.list_files.return_value = files

    # Mock download_files to yield successful results (it's now a generator)
    def mock_download_generator():
        yield DownloadResult(success=True, file_id="f1", dest_path=tmp_path / "r1.jpg")
        yield DownloadResult(success=True, file_id="f2", dest_path=tmp_path / "r2.png")

    mock_instance.download_files.return_value = mock_download_generator()

    url = "https://drive.google.com/drive/folders/XYZ123"
    result = runner.invoke(app, ["process", "--folder", url])

    assert result.exit_code == 0
    assert "Downloaded r1.jpg" in result.stdout
    assert "Downloaded r2.png" in result.stdout
    assert mock_instance.list_files.called
    assert mock_instance.download_files.called


def test_process_empty_folder(mock_gdrive_client):
    """Handle cases where the folder contains no supported files."""
    mock_instance = mock_gdrive_client.return_value
    mock_instance.list_files.return_value = []

    result = runner.invoke(app, ["process", "--folder", "empty_folder"])

    assert result.exit_code == 0
    assert "No supported files found in folder." in result.stdout


def test_gdrive_api_error(mock_gdrive_client):
    """Verify the CLI handles Google Drive API errors gracefully."""
    mock_instance = mock_gdrive_client.return_value
    # Use a generic Exception for now, as HttpError needs more setup
    mock_instance.list_files.side_effect = Exception("API Error")

    result = runner.invoke(app, ["process", "--folder", "error_folder"])

    assert result.exit_code != 0
    assert "Error communicating with Google Drive" in result.stderr


def test_process_partial_download_failure(
    mock_gdrive_client, mock_ocr_engine, tmp_path
):
    """Verify that the CLI continues if one file fails to download."""
    mock_instance = mock_gdrive_client.return_value
    files = [
        {"id": "f1", "name": "r1.jpg", "mimeType": "image/jpeg"},
        {"id": "f2", "name": "r2.png", "mimeType": "image/png"},
    ]
    mock_instance.list_files.return_value = files

    # Mock download_files to yield one success and one failure (it's now a generator)
    def mock_download_generator():
        yield DownloadResult(success=True, file_id="f1", dest_path=tmp_path / "r1.jpg")
        yield DownloadResult(
            success=False,
            file_id="f2",
            dest_path=tmp_path / "r2.png",
            error="Download Failed",
        )

    mock_instance.download_files.return_value = mock_download_generator()

    result = runner.invoke(app, ["process", "--folder", "some_folder"])

    assert result.exit_code == 0
    assert "Downloaded r1.jpg" in result.stdout
    assert "Failed to download r2.png: Download Failed" in result.stderr
