import re
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
    # Use robust cleaning to handle terminal wrapping/formatting
    clean_stdout = re.sub(r"[\s│╭╮╰╯─]", "", result.stdout.lower())
    assert "process" in clean_stdout


def test_process_folder_required():
    """Verify that --folder is a required argument for the process command."""
    # In Typer, if an option is required and not provided, it should fail
    result = runner.invoke(app, ["process", "--folder"])
    assert result.exit_code != 0
    # Use robust cleaning to handle terminal wrapping/formatting
    full_output = result.stdout + result.stderr
    clean_output = re.sub(r"[\s│╭╮╰╯─]", "", full_output)
    assert "folder" in clean_output or "Missingoption" in clean_output


def test_folder_id_parsing(mock_gdrive_client):
    """Verify that both raw IDs and URLs are correctly parsed by the CLI."""
    # Use a URL
    url = "https://drive.google.com/drive/folders/XYZ123"
    result = runner.invoke(app, ["process", "--folder", url])
    assert result.exit_code == 0
    clean_stdout = re.sub(r"[\s│╭╮╰╯─]", "", result.stdout)
    assert "Processingfolder:XYZ123" in clean_stdout


def test_folder_id_parsing_alias(mock_gdrive_client):
    """Verify that the -f alias for --folder works."""
    url = "https://drive.google.com/drive/folders/XYZ123"
    result = runner.invoke(app, ["process", "-f", url])
    assert result.exit_code == 0
    clean_stdout = re.sub(r"[\s│╭╮╰╯─]", "", result.stdout)
    assert "Processingfolder:XYZ123" in clean_stdout


def test_invalid_folder_url():
    """Verify the CLI reports a clear error when an invalid URL is provided."""
    result = runner.invoke(app, ["process", "--folder", "https://wrong.com/abc"])
    assert result.exit_code != 0
    # Use robust cleaning to handle terminal wrapping/formatting
    full_output = result.stdout + result.stderr
    clean_output = re.sub(r"[\s│╭╮╰╯─]", "", full_output)
    assert "UnsupportedURLdomain" in clean_output


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
    clean_stdout = re.sub(r"[\s│╭╮╰╯─]", "", result.stdout)
    assert "Downloadedr1.jpg" in clean_stdout
    assert "Downloadedr2.png" in clean_stdout
    assert mock_instance.list_files.called
    assert mock_instance.download_files.called


def test_process_empty_folder(mock_gdrive_client):
    """Handle cases where the folder contains no supported files."""
    mock_instance = mock_gdrive_client.return_value
    mock_instance.list_files.return_value = []

    result = runner.invoke(app, ["process", "--folder", "empty_folder"])

    assert result.exit_code == 0
    clean_stdout = re.sub(r"[\s│╭╮╰╯─]", "", result.stdout)
    assert "Nosupportedfilesfoundinfolder." in clean_stdout


def test_gdrive_api_error(mock_gdrive_client):
    """Verify the CLI handles Google Drive API errors gracefully."""
    mock_instance = mock_gdrive_client.return_value
    # Use a generic Exception for now, as HttpError needs more setup
    mock_instance.list_files.side_effect = Exception("API Error")

    result = runner.invoke(app, ["process", "--folder", "error_folder"])

    assert result.exit_code != 0
    clean_stderr = re.sub(r"[\s│╭╮╰╯─]", "", result.stderr)
    assert "ErrorcommunicatingwithGoogleDrive" in clean_stderr


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
    clean_stdout = re.sub(r"[\s│╭╮╰╯─]", "", result.stdout)
    clean_stderr = re.sub(r"[\s│╭╮╰╯─]", "", result.stderr)
    assert "Downloadedr1.jpg" in clean_stdout
    assert "Failedtodownloadr2.png:DownloadFailed" in clean_stderr
