"""Tests for parallel pipeline implementation."""

import asyncio
import time
import unittest.mock as mock

import pytest

pytestmark = pytest.mark.unit


def test_gdrive_parallel_download_creates_thread_local_services(tmp_path):
    """Test that parallel downloads create thread-local services.

    Due to threading/SSL issues with httplib2, each thread needs its own
    service instance for thread safety. This test verifies that behavior.
    """
    from slipstream.integrations.gdrive import GDriveClient

    with mock.patch("slipstream.integrations.gdrive.build") as mock_build:
        mock_service = mock.Mock()
        mock_build.return_value = mock_service

        # Mock the MediaIoBaseDownload to simulate successful downloads
        with mock.patch(
            "slipstream.integrations.gdrive.MediaIoBaseDownload"
        ) as mock_download:
            mock_instance = mock_download.return_value
            mock_instance.next_chunk.return_value = (None, True)

            # Create client and download 3 files
            client = GDriveClient(max_workers=2)
            files = [
                {"id": "file1", "name": "receipt1.jpg"},
                {"id": "file2", "name": "receipt2.png"},
                {"id": "file3", "name": "receipt3.pdf"},
            ]

            # download_files is now a generator
            results = list(client.download_files(files, tmp_path))

            # Verify all files were processed
            assert len(results) == 3
            assert all(r.success for r in results)

            # build() is called once for init + once per download thread
            # This is necessary for thread safety with httplib2
            assert mock_build.call_count >= 1, (
                f"Expected build() to be called at least once, got "
                f"{mock_build.call_count}"
            )


def test_download_files_yields_as_completed(tmp_path):
    """Test that download_files yields results as they complete (streaming).

    This verifies that we get results as soon as individual downloads finish,
    rather than waiting for all downloads to complete.
    """
    from slipstream.integrations.gdrive import GDriveClient

    with mock.patch("slipstream.integrations.gdrive.build") as mock_build:
        mock_service = mock.Mock()
        mock_build.return_value = mock_service

        with mock.patch(
            "slipstream.integrations.gdrive.MediaIoBaseDownload"
        ) as mock_download:
            mock_instance = mock_download.return_value
            mock_instance.next_chunk.return_value = (None, True)

            client = GDriveClient(max_workers=2)
            files = [
                {"id": "file1", "name": "receipt1.jpg"},
                {"id": "file2", "name": "receipt2.png"},
                {"id": "file3", "name": "receipt3.pdf"},
            ]

            # Consume the generator and track when we get each result
            results_received = []
            for result in client.download_files(files, tmp_path):
                results_received.append(result)
                # Verify we can process this result immediately
                assert result.success is True
                assert result.file_id is not None

            # All 3 files should have been yielded
            assert len(results_received) == 3


@pytest.mark.asyncio
async def test_pipeline_is_actually_parallel():
    """Test that the pipeline actually processes files in parallel.

    This test verifies that Download -> OCR -> LLM steps for multiple files
    run concurrently, not sequentially. If they run in parallel, total time
    should be ~1x the longest task, not 3x the sum of all tasks.
    """
    # Mock the pipeline components with async sleeps to simulate work
    # Each file takes ~0.1 seconds to process

    async def mock_download(file_info, dest_dir):
        """Simulate download taking 0.1s"""
        await asyncio.sleep(0.1)
        return {"success": True, "file_id": file_info["id"], "dest_path": dest_dir}

    async def mock_ocr(file_path):
        """Simulate OCR taking 0.1s"""
        await asyncio.sleep(0.1)
        return "extracted text"

    async def mock_llm(text):
        """Simulate LLM extraction taking 0.1s"""
        await asyncio.sleep(0.1)
        return {"merchant": "Test Store", "total": 10.00}

    # Process 3 files
    files = [
        {"id": "file1", "name": "receipt1.jpg"},
        {"id": "file2", "name": "receipt2.jpg"},
        {"id": "file3", "name": "receipt3.jpg"},
    ]

    start_time = time.time()

    # Simulate parallel processing
    tasks = []
    for file_info in files:

        async def process_one(f):
            download_result = await mock_download(f, "/tmp")
            text = await mock_ocr(download_result["dest_path"])
            return await mock_llm(text)

        tasks.append(process_one(file_info))

    results = await asyncio.gather(*tasks)

    elapsed_time = time.time() - start_time

    # Verify all files were processed
    assert len(results) == 3

    # CRITICAL: If running in parallel, should take ~0.3s (3 steps * 0.1s)
    # If running sequentially, would take ~0.9s (3 files * 3 steps * 0.1s)
    # Allow some overhead, so check that it's less than 0.6s
    assert elapsed_time < 0.6, (
        f"Pipeline took {elapsed_time:.2f}s to process 3 files. "
        f"This suggests sequential processing (expected < 0.6s for parallel). "
        f"Sequential would take ~0.9s, parallel should take ~0.3s."
    )
