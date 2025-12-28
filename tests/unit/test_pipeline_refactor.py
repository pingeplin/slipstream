"""Tests for refactored pipeline functions (TDD approach).

This test module drives the refactoring of:
- process_downloaded_file: Refactored to return ProcessingResult
- run_pipeline: Extracted from nested function to module-level

Following Test-Driven Development:
1. Write tests first (RED - tests fail)
2. Implement to make tests pass (GREEN)
3. Refactor for clarity (REFACTOR)
"""

import asyncio
import time
from collections.abc import Generator
from unittest.mock import AsyncMock, Mock

import pytest

from slipstream.integrations.anthropic_extractor import (
    AnthropicExtractor,
    ExtractionRefusedError,
)
from slipstream.integrations.gdrive import DownloadResult
from slipstream.integrations.ocr import OCREngine
from slipstream.main import process_downloaded_file, run_pipeline
from slipstream.models import ExtractionResult, ProcessingResult, Receipt


@pytest.mark.unit
class TestProcessDownloadedFileRefactor:
    """Tests for refactored process_downloaded_file function."""

    @pytest.mark.asyncio
    async def test_process_downloaded_file_skips_failed_download(self, tmp_path):
        """Test that failed downloads are skipped without processing."""
        # Setup
        download_result = DownloadResult(
            success=False,
            file_id="f1",
            dest_path=tmp_path / "receipt.jpg",
            error="Download failed",
        )
        mock_ocr = Mock(spec=OCREngine)

        # Execute
        result = await process_downloaded_file(download_result, mock_ocr, None)

        # Verify
        assert isinstance(result, ProcessingResult)
        assert result.file_id == "f1"
        assert result.file_name == "receipt.jpg"
        assert result.download_success is False
        assert result.download_error == "Download failed"
        assert result.ocr_text is None
        mock_ocr.extract_text.assert_not_called()  # Should skip OCR

    @pytest.mark.asyncio
    async def test_process_downloaded_file_success(self, tmp_path):
        """Test successful processing of a downloaded file returns structured result."""
        # Setup - create a real file for the test
        dest_file = tmp_path / "receipt.jpg"
        dest_file.write_text("fake image data")

        download_result = DownloadResult(
            success=True, file_id="f1", dest_path=dest_file
        )
        mock_ocr = Mock(spec=OCREngine)
        mock_ocr.extract_text.return_value = "Sample OCR text with merchant info"

        mock_extractor = Mock(spec=AnthropicExtractor)
        mock_receipt = Receipt(
            merchant_name="Test Store",
            date="2024-01-15",
            total_amount=42.50,
            currency="TWD",
            confidence_score=0.95,
            raw_text="Sample OCR text with merchant info",
        )
        mock_extraction = ExtractionResult(
            receipt=mock_receipt,
            input_tokens=100,
            output_tokens=50,
            processing_time=1.5,
        )
        # Make extract_receipt_data async
        mock_extractor.extract_receipt_data = AsyncMock(return_value=mock_extraction)

        # Execute
        result = await process_downloaded_file(
            download_result, mock_ocr, mock_extractor
        )

        # Verify
        assert isinstance(result, ProcessingResult)
        assert result.file_id == "f1"
        assert result.file_name == "receipt.jpg"
        assert result.download_success is True
        assert result.download_error is None
        assert result.ocr_text == "Sample OCR text with merchant info"
        assert result.ocr_error is None
        assert result.extraction_result == mock_extraction
        assert result.extraction_error is None

    @pytest.mark.asyncio
    async def test_process_downloaded_file_handles_ocr_error(self, tmp_path):
        """Test that OCR errors are captured in result without raising."""
        # Setup
        dest_file = tmp_path / "receipt.jpg"
        dest_file.write_text("fake image data")

        download_result = DownloadResult(
            success=True, file_id="f2", dest_path=dest_file
        )
        mock_ocr = Mock(spec=OCREngine)
        mock_ocr.extract_text.side_effect = Exception("OCR processing failed")

        mock_extractor = Mock(spec=AnthropicExtractor)

        # Execute
        result = await process_downloaded_file(
            download_result, mock_ocr, mock_extractor
        )

        # Verify
        assert isinstance(result, ProcessingResult)
        assert result.download_success is True
        assert result.ocr_text is None
        assert "OCR processing failed" in result.ocr_error
        assert result.extraction_result is None  # Should not attempt LLM
        # Extractor should not be called
        if hasattr(mock_extractor, "extract_receipt_data"):
            mock_extractor.extract_receipt_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_downloaded_file_with_progress_callback(self, tmp_path):
        """Test that progress callback is invoked for each stage."""
        # Setup
        dest_file = tmp_path / "receipt.jpg"
        dest_file.write_text("fake image data")

        download_result = DownloadResult(
            success=True, file_id="f3", dest_path=dest_file
        )
        mock_ocr = Mock(spec=OCREngine)
        mock_ocr.extract_text.return_value = "OCR text"

        progress_calls = []

        def capture_progress(event_type: str, message: str):
            progress_calls.append((event_type, message))

        # Execute
        result = await process_downloaded_file(
            download_result, mock_ocr, None, on_progress=capture_progress
        )

        # Verify
        assert isinstance(result, ProcessingResult)
        assert result.ocr_text == "OCR text"
        assert len(progress_calls) >= 1
        # Verify we got an OCR success event
        event_types = [call[0] for call in progress_calls]
        assert "ocr_success" in event_types

    @pytest.mark.asyncio
    async def test_process_downloaded_file_handles_llm_errors(self, tmp_path):
        """Test that LLM extraction errors are captured without stopping."""
        # Setup
        dest_file = tmp_path / "receipt.jpg"
        dest_file.write_text("fake image data")

        download_result = DownloadResult(
            success=True, file_id="f4", dest_path=dest_file
        )
        mock_ocr = Mock(spec=OCREngine)
        mock_ocr.extract_text.return_value = "OCR text"

        mock_extractor = Mock(spec=AnthropicExtractor)
        mock_extractor.extract_receipt_data = AsyncMock(
            side_effect=ExtractionRefusedError("Model refused")
        )

        # Execute
        result = await process_downloaded_file(
            download_result, mock_ocr, mock_extractor
        )

        # Verify
        assert isinstance(result, ProcessingResult)
        assert result.ocr_text == "OCR text"
        assert result.extraction_result is None
        assert "Model refused" in result.extraction_error


@pytest.mark.unit
class TestRunPipelineRefactor:
    """Tests for refactored run_pipeline function."""

    @pytest.mark.asyncio
    async def test_run_pipeline_processes_streaming_downloads(self, tmp_path):
        """Test that run_pipeline processes files as they complete downloading."""

        # Setup
        def mock_download_generator() -> Generator[DownloadResult, None, None]:
            dest1 = tmp_path / "r1.jpg"
            dest1.write_text("fake data 1")
            yield DownloadResult(success=True, file_id="f1", dest_path=dest1)

            dest2 = tmp_path / "r2.jpg"
            dest2.write_text("fake data 2")
            yield DownloadResult(success=True, file_id="f2", dest_path=dest2)

        mock_ocr = Mock(spec=OCREngine)
        mock_ocr.extract_text.return_value = "OCR text"

        # Execute
        results = await run_pipeline(
            download_results=mock_download_generator(),
            ocr_engine=mock_ocr,
            extractor=None,
        )

        # Verify
        assert len(results) == 2
        assert all(isinstance(r, ProcessingResult) for r in results)
        assert results[0].file_id == "f1"
        assert results[1].file_id == "f2"
        assert all(r.download_success for r in results)
        assert all(r.ocr_text == "OCR text" for r in results)

    @pytest.mark.asyncio
    async def test_run_pipeline_error_isolation(self, tmp_path):
        """Test that one file's error doesn't stop processing of other files."""

        # Setup
        def mock_download_generator() -> Generator[DownloadResult, None, None]:
            # Success
            dest1 = tmp_path / "r1.jpg"
            dest1.write_text("fake data 1")
            yield DownloadResult(success=True, file_id="f1", dest_path=dest1)

            # Download failed
            dest2 = tmp_path / "r2.jpg"
            yield DownloadResult(
                success=False, file_id="f2", dest_path=dest2, error="Download failed"
            )

            # Success
            dest3 = tmp_path / "r3.jpg"
            dest3.write_text("fake data 3")
            yield DownloadResult(success=True, file_id="f3", dest_path=dest3)

        call_count = 0

        def faulty_ocr(path):
            nonlocal call_count
            call_count += 1
            if "r1" in str(path):
                raise Exception("OCR error on r1")
            return "OCR text"

        mock_ocr = Mock(spec=OCREngine)
        mock_ocr.extract_text.side_effect = faulty_ocr

        # Execute
        results = await run_pipeline(
            download_results=mock_download_generator(),
            ocr_engine=mock_ocr,
            extractor=None,
        )

        # Verify
        assert len(results) == 3
        # f1 had OCR error
        assert results[0].file_id == "f1"
        assert results[0].ocr_error is not None
        assert "OCR error on r1" in results[0].ocr_error

        # f2 download failed
        assert results[1].file_id == "f2"
        assert results[1].download_success is False

        # f3 succeeded
        assert results[2].file_id == "f3"
        assert results[2].ocr_text == "OCR text"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_run_pipeline_parallel_execution_timing(self, tmp_path):
        """Test that multiple files are processed in parallel, not sequentially."""

        # Setup
        def mock_download_generator() -> Generator[DownloadResult, None, None]:
            for i in range(3):
                dest = tmp_path / f"r{i}.jpg"
                dest.write_text(f"fake data {i}")
                yield DownloadResult(success=True, file_id=f"f{i}", dest_path=dest)

        # Mock OCR to simulate async work
        async def slow_extract_wrapper(path):
            # Simulate OCR work
            await asyncio.sleep(0.1)
            return "OCR text"

        mock_ocr = Mock(spec=OCREngine)

        # OCR extract_text is synchronous, but run_pipeline runs it in executor
        # For this test, we'll simulate timing by making the mock synchronous but sleep
        def blocking_ocr(path):
            # This will block, but when run in executor it allows parallelism
            time.sleep(0.1)
            return "OCR text"

        mock_ocr.extract_text.side_effect = blocking_ocr

        # Execute and time
        start = time.time()
        results = await run_pipeline(
            download_results=mock_download_generator(),
            ocr_engine=mock_ocr,
            extractor=None,
        )
        elapsed = time.time() - start

        # Verify - should take ~0.1s (parallel), not ~0.3s (sequential)
        assert len(results) == 3
        assert all(r.ocr_text == "OCR text" for r in results)
        # Allow some overhead, but should be much less than 0.3s for sequential
        assert elapsed < 0.25, (
            f"Took {elapsed:.2f}s, expected <0.25s for parallel execution"
        )

    @pytest.mark.asyncio
    async def test_run_pipeline_with_progress_callback(self, tmp_path):
        """Test that progress callback is invoked for pipeline events."""

        # Setup
        def mock_download_generator() -> Generator[DownloadResult, None, None]:
            dest = tmp_path / "r1.jpg"
            dest.write_text("fake data")
            yield DownloadResult(success=True, file_id="f1", dest_path=dest)

        mock_ocr = Mock(spec=OCREngine)
        mock_ocr.extract_text.return_value = "OCR text"

        progress_events = []

        def capture_progress(event_type: str, message: str):
            progress_events.append((event_type, message))

        # Execute
        results = await run_pipeline(
            download_results=mock_download_generator(),
            ocr_engine=mock_ocr,
            extractor=None,
            on_progress=capture_progress,
        )

        # Verify
        assert len(results) == 1
        assert len(progress_events) >= 1
        # Should have events for OCR success at minimum
        event_types = [e[0] for e in progress_events]
        assert "ocr_success" in event_types
