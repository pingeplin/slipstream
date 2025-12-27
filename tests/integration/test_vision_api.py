"""
Integration tests for Google Cloud Vision API OCR functionality.

These tests make real API calls to Google Cloud Vision and require:
1. Google Cloud credentials to be configured
2. Active Google Cloud project with Vision API enabled
3. Test images in tests/dataset/

Run these tests with: uv run pytest tests/integration/test_vision_api.py -m integration

Note: These tests are marked as 'integration' and can be skipped in CI/CD pipelines.
"""

import os
from pathlib import Path

import pytest

from slipstream.integrations.ocr import OCREngine

# Skip all tests in this module if GOOGLE_APPLICATION_CREDENTIALS is not set
pytestmark = pytest.mark.integration


@pytest.fixture
def skip_if_no_credentials():
    """Skip test if Google Cloud credentials are not configured."""
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        pytest.skip(
            "GOOGLE_APPLICATION_CREDENTIALS not set - skipping integration test"
        )


@pytest.fixture
def ocr_engine():
    """Create an OCREngine instance with real Google Vision client."""
    return OCREngine()


@pytest.fixture
def dataset_dir():
    """Return path to test dataset directory."""
    return Path(__file__).parent.parent / "dataset"


class TestRealOCRExtraction:
    """Integration tests using real Google Vision API calls."""

    def test_extract_text_from_english_receipt(
        self, skip_if_no_credentials, ocr_engine, dataset_dir
    ):
        """Test OCR extraction from a real English receipt image."""
        receipt_path = dataset_dir / "receipt_en.png"
        if not receipt_path.exists():
            pytest.skip(f"Test image not found: {receipt_path}")

        result = ocr_engine.extract_text(str(receipt_path))

        # Verify we got some text back
        assert isinstance(result, str)
        assert len(result) > 0
        # Basic sanity check - receipts typically contain numbers
        assert any(char.isdigit() for char in result)

    def test_extract_text_from_chinese_receipt(
        self, skip_if_no_credentials, ocr_engine, dataset_dir
    ):
        """Test OCR extraction from a Chinese/Traditional Chinese receipt."""
        receipt_path = dataset_dir / "receipt_zh_tw.png"
        if not receipt_path.exists():
            pytest.skip(f"Test image not found: {receipt_path}")

        result = ocr_engine.extract_text(str(receipt_path))

        assert isinstance(result, str)
        assert len(result) > 0

    def test_extract_text_from_japanese_receipt(
        self, skip_if_no_credentials, ocr_engine, dataset_dir
    ):
        """Test OCR extraction from a Japanese receipt."""
        receipt_path = dataset_dir / "receipt_jp.png"
        if not receipt_path.exists():
            pytest.skip(f"Test image not found: {receipt_path}")

        result = ocr_engine.extract_text(str(receipt_path))

        assert isinstance(result, str)
        assert len(result) > 0

    def test_extract_text_from_korean_receipt(
        self, skip_if_no_credentials, ocr_engine, dataset_dir
    ):
        """Test OCR extraction from a Korean receipt."""
        receipt_path = dataset_dir / "receipt_kr.png"
        if not receipt_path.exists():
            pytest.skip(f"Test image not found: {receipt_path}")

        result = ocr_engine.extract_text(str(receipt_path))

        assert isinstance(result, str)
        assert len(result) > 0


class TestPerformanceMetrics:
    """Integration tests for performance requirements."""

    def test_ocr_processing_speed(
        self, skip_if_no_credentials, ocr_engine, dataset_dir
    ):
        """Test that OCR processing meets speed requirements (< 5 seconds)."""
        import time

        receipt_path = dataset_dir / "receipt_en.png"
        if not receipt_path.exists():
            pytest.skip(f"Test image not found: {receipt_path}")

        start_time = time.time()
        result = ocr_engine.extract_text(str(receipt_path))
        elapsed_time = time.time() - start_time

        assert isinstance(result, str)
        assert len(result) > 0
        # Performance requirement: < 5 seconds per receipt
        assert elapsed_time < 5.0, (
            f"OCR took {elapsed_time:.2f}s, exceeds 5s requirement"
        )
