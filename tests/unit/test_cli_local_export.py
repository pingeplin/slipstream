"""Unit tests for CLI integration of local export functionality."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from slipstream.integrations.gdrive import DownloadResult
from slipstream.main import app
from tests.utils import clean_cli_output

pytestmark = pytest.mark.unit

runner = CliRunner()


@pytest.fixture
def mock_gdrive_client():
    """Mock GDrive client for testing."""
    with patch("slipstream.main.GDriveClient") as mock:
        yield mock


@pytest.fixture
def mock_ocr_engine():
    """Mock OCR engine for testing."""
    with patch("slipstream.main.OCREngine") as mock:
        mock_instance = mock.return_value
        mock_instance.extract_text.return_value = "Sample receipt text"
        yield mock


@pytest.fixture
def mock_run_pipeline():
    """Mock run_pipeline function for testing."""
    with patch("slipstream.main.run_pipeline") as mock:
        # Mock as async function
        mock.return_value = AsyncMock(return_value=[])
        yield mock


def test_cli_accepts_save_local_option(mock_gdrive_client):
    """Verify process command accepts --save-local with a path."""
    # Test that the command doesn't fail with --save-local option
    result = runner.invoke(
        app,
        [
            "process",
            "--folder",
            "https://drive.google.com/drive/folders/XYZ123",
            "--save-local",
            "/tmp/receipts.csv",
        ],
    )

    # Should not fail due to unexpected argument
    # (It may fail for other reasons like missing API keys, but not arg parsing)
    assert "unexpected" not in result.stdout.lower()
    assert "unexpected" not in result.stderr.lower()


def test_cli_accepts_save_local_without_value_fails():
    """Verify --save-local requires a value."""
    result = runner.invoke(
        app,
        [
            "process",
            "--folder",
            "https://drive.google.com/drive/folders/XYZ123",
            "--save-local",
        ],
    )

    # Should fail when --save-local has no value
    assert result.exit_code != 0
    # Combine output and remove formatting/newlines to handle potential wrapping
    full_output = result.stdout + result.stderr
    clean_output = clean_cli_output(full_output)
    assert "save-local" in clean_output or "Missingoption" in clean_output


@patch("slipstream.main.run_pipeline")
def test_cli_passes_local_path_to_pipeline(
    mock_run_pipeline,
    mock_gdrive_client,
    mock_ocr_engine,
    tmp_path: Path,
):
    """Verify the path provided in CLI is correctly passed to run_pipeline."""

    # Mock run_pipeline as async coroutine
    async def mock_pipeline_coro(*args, **kwargs):
        return []

    mock_run_pipeline.return_value = mock_pipeline_coro()

    # Setup mocks
    mock_instance = mock_gdrive_client.return_value
    files = [{"id": "f1", "name": "r1.jpg", "mimeType": "image/jpeg"}]
    mock_instance.list_files.return_value = files

    def mock_download_generator():
        yield DownloadResult(success=True, file_id="f1", dest_path=tmp_path / "r1.jpg")

    mock_instance.download_files.return_value = mock_download_generator()

    # Expected local path
    local_path = tmp_path / "receipts.csv"

    # Invoke CLI with --save-local
    result = runner.invoke(
        app,
        [
            "process",
            "--folder",
            "https://drive.google.com/drive/folders/XYZ123",
            "--save-local",
            str(local_path),
        ],
    )

    # Verify run_pipeline was called with local_path
    assert mock_run_pipeline.called
    call_kwargs = mock_run_pipeline.call_args[1]
    assert "local_path" in call_kwargs

    # The path should be a Path object pointing to our specified location
    passed_path = call_kwargs["local_path"]
    assert passed_path == local_path


@patch("slipstream.main.run_pipeline")
def test_cli_local_path_is_none_when_not_provided(
    mock_run_pipeline,
    mock_gdrive_client,
    mock_ocr_engine,
    tmp_path: Path,
):
    """Verify local_path is None when --save-local is not provided."""

    # Mock run_pipeline as async coroutine
    async def mock_pipeline_coro(*args, **kwargs):
        return []

    mock_run_pipeline.return_value = mock_pipeline_coro()

    # Setup mocks
    mock_instance = mock_gdrive_client.return_value
    files = [{"id": "f1", "name": "r1.jpg", "mimeType": "image/jpeg"}]
    mock_instance.list_files.return_value = files

    def mock_download_generator():
        yield DownloadResult(success=True, file_id="f1", dest_path=tmp_path / "r1.jpg")

    mock_instance.download_files.return_value = mock_download_generator()

    # Invoke CLI WITHOUT --save-local
    result = runner.invoke(
        app,
        [
            "process",
            "--folder",
            "https://drive.google.com/drive/folders/XYZ123",
        ],
    )

    # Verify run_pipeline was called
    assert mock_run_pipeline.called
    call_kwargs = mock_run_pipeline.call_args[1]

    # local_path should be None when not provided
    assert "local_path" in call_kwargs
    assert call_kwargs["local_path"] is None
