"""Unit tests for local export integration in the pipeline."""

import csv
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from slipstream.integrations.anthropic_extractor import AnthropicExtractor
from slipstream.integrations.gdrive import DownloadResult
from slipstream.integrations.gsheets import GSheetsClient
from slipstream.integrations.ocr import OCREngine
from slipstream.main import run_pipeline
from slipstream.models import ExtractionResult, Receipt


@pytest.fixture
def mock_ocr_engine():
    """Create a mock OCR engine."""
    engine = MagicMock(spec=OCREngine)
    engine.extract_text.return_value = "Test receipt text"
    return engine


@pytest.fixture
def mock_extractor():
    """Create a mock Anthropic extractor."""
    extractor = MagicMock(spec=AnthropicExtractor)

    # Create a sample receipt
    receipt = Receipt(
        merchant_name="Test Store",
        date="2024-12-28",
        total_amount=150.50,
        currency="TWD",
        confidence_score=0.95,
        raw_text="Test receipt text",
    )

    # Create extraction result
    extraction_result = ExtractionResult(
        receipt=receipt,
        input_tokens=100,
        output_tokens=50,
        processing_time=0.5,
    )

    # Mock the async extract method
    async def mock_extract(_text):
        return extraction_result

    extractor.extract_receipt_data = mock_extract
    return extractor


@pytest.fixture
def download_results_generator(tmp_path: Path):
    """Create a generator of download results."""

    def generator():
        file_path = tmp_path / "test_receipt.jpg"
        file_path.write_text("dummy file")

        yield DownloadResult(
            file_id="test_file_id",
            dest_path=file_path,
            success=True,
            error=None,
        )

    return generator()


@pytest.mark.asyncio
async def test_run_pipeline_triggers_local_export(
    tmp_path: Path,
    download_results_generator,
    mock_ocr_engine,
    mock_extractor,
):
    """Verify run_pipeline calls LocalExporter.export when local_path is provided."""
    local_path = tmp_path / "receipts.csv"

    # Run pipeline with local_path
    await run_pipeline(
        download_results=download_results_generator,
        ocr_engine=mock_ocr_engine,
        extractor=mock_extractor,
        local_path=local_path,
    )

    # Verify CSV file was created
    assert local_path.exists()

    # Verify content
    with open(local_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert len(rows) == 2  # Header + 1 data row
    assert rows[0] == ["商家", "日期", "幣別", "總計"]
    assert rows[1][0] == "Test Store"


@pytest.mark.asyncio
async def test_run_pipeline_local_export_execution(
    tmp_path: Path,
    download_results_generator,
    mock_ocr_engine,
    mock_extractor,
):
    """Verify that local export is executed as part of the pipeline."""
    local_path = tmp_path / "exports" / "receipts.csv"

    # Ensure parent directory doesn't exist yet
    assert not local_path.parent.exists()

    # Run pipeline
    results = await run_pipeline(
        download_results=download_results_generator,
        ocr_engine=mock_ocr_engine,
        extractor=mock_extractor,
        local_path=local_path,
    )

    # Verify pipeline completed successfully
    assert len(results) == 1
    assert results[0].extraction_result is not None

    # Verify local export was executed
    assert local_path.exists()
    assert local_path.parent.exists()


@pytest.mark.asyncio
async def test_run_pipeline_local_export_without_gsheets(
    tmp_path: Path,
    download_results_generator,
    mock_ocr_engine,
    mock_extractor,
):
    """Verify data is saved locally even if GSheets client is not provided."""
    local_path = tmp_path / "receipts.csv"

    # Run pipeline WITHOUT gsheets_client
    await run_pipeline(
        download_results=download_results_generator,
        ocr_engine=mock_ocr_engine,
        extractor=mock_extractor,
        gsheets_client=None,  # Explicitly no GSheets
        local_path=local_path,
    )

    # Verify local file exists
    assert local_path.exists()

    # Verify data was saved
    with open(local_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert len(rows) == 2  # Header + 1 data row
    assert rows[1][0] == "Test Store"


@pytest.mark.asyncio
async def test_run_pipeline_local_export_persists_on_gsheets_failure(
    tmp_path: Path,
    download_results_generator,
    mock_ocr_engine,
    mock_extractor,
):
    """Verify data remains saved locally even if GSheets call fails."""
    local_path = tmp_path / "receipts.csv"

    # Create a mock GSheets client that raises an error
    mock_gsheets = MagicMock(spec=GSheetsClient)
    mock_gsheets.append_rows.side_effect = Exception("GSheets API error")

    # Run pipeline - should not raise exception
    results = await run_pipeline(
        download_results=download_results_generator,
        ocr_engine=mock_ocr_engine,
        extractor=mock_extractor,
        gsheets_client=mock_gsheets,
        local_path=local_path,
    )

    # Verify pipeline completed
    assert len(results) == 1
    assert results[0].extraction_result is not None

    # Verify GSheets was attempted
    mock_gsheets.append_rows.assert_called_once()

    # Verify local export still succeeded despite GSheets failure
    assert local_path.exists()

    # Verify data was saved locally
    with open(local_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert len(rows) == 2  # Header + 1 data row
    assert rows[1][0] == "Test Store"


@pytest.mark.asyncio
async def test_run_pipeline_no_local_export_when_path_not_provided(
    tmp_path: Path,
    download_results_generator,
    mock_ocr_engine,
    mock_extractor,
):
    """Verify no local file is created when local_path is not provided."""
    # Run pipeline without local_path
    await run_pipeline(
        download_results=download_results_generator,
        ocr_engine=mock_ocr_engine,
        extractor=mock_extractor,
        local_path=None,  # No local export
    )

    # Verify no CSV files were created in tmp_path
    csv_files = list(tmp_path.glob("*.csv"))
    assert len(csv_files) == 0
