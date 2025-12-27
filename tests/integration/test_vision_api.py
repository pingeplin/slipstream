"""
Integration tests for Google Cloud Vision API OCR functionality.

These tests make real API calls to Google Cloud Vision and require:
1. Google Cloud credentials configured via Application Default Credentials (ADC)
   - Run: gcloud auth application-default login
   - Or set GOOGLE_APPLICATION_CREDENTIALS to a service account key
2. Active Google Cloud project with Vision API enabled and billing enabled
3. Test images in tests/dataset/

Run these tests with: uv run pytest tests/integration/test_vision_api.py -m integration

Note: These tests are marked as 'integration' and can be skipped in CI/CD pipelines.
"""

import functools
from pathlib import Path

import pytest
from google.api_core.exceptions import PermissionDenied

from slipstream.integrations.ocr import OCREngine


def skip_on_billing_error(func):
    """Decorator to skip tests if billing is not enabled on the GCP project."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PermissionDenied as e:
            if "billing" in str(e).lower():
                pytest.skip(
                    "Google Cloud Vision API requires billing to be enabled. "
                    "Enable billing on your project or skip integration tests."
                )
            raise

    return wrapper


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def ocr_engine():
    """
    Create an OCREngine instance with real Google Vision client using ADC.

    Skips all tests if credentials are not available.
    """
    try:
        engine = OCREngine()
        # Test that we can actually create a client (this validates credentials)
        _ = engine.client
        return engine
    except Exception as e:
        pytest.skip(
            f"Google Cloud credentials not configured. "
            f"Run 'gcloud auth application-default login' or set GOOGLE_APPLICATION_CREDENTIALS. "
            f"Error: {e}"
        )


@pytest.fixture
def dataset_dir():
    """Return path to test dataset directory."""
    return Path(__file__).parent.parent / "dataset"


@skip_on_billing_error
def test_extract_text_from_english_receipt(ocr_engine, dataset_dir):
    """Test OCR extraction from a real English receipt image."""
    receipt_path = dataset_dir / "receipt_en.jpg"
    if not receipt_path.exists():
        pytest.skip(f"Test image not found: {receipt_path}")

    result = ocr_engine.extract_text(str(receipt_path))

    # Verify we got some text back
    assert isinstance(result, str)
    assert len(result) > 0
    # Basic sanity check - receipts typically contain numbers
    assert any(char.isdigit() for char in result)


@skip_on_billing_error
def test_extract_text_from_chinese_receipt(ocr_engine, dataset_dir):
    """Test OCR extraction from a Chinese/Traditional Chinese receipt."""
    receipt_path = dataset_dir / "receipt_zh_tw.jpg"
    if not receipt_path.exists():
        pytest.skip(f"Test image not found: {receipt_path}")

    result = ocr_engine.extract_text(str(receipt_path))

    assert isinstance(result, str)
    assert len(result) > 0


@skip_on_billing_error
def test_extract_text_from_japanese_receipt(ocr_engine, dataset_dir):
    """Test OCR extraction from a Japanese receipt."""
    receipt_path = dataset_dir / "receipt_jp.jpg"
    if not receipt_path.exists():
        pytest.skip(f"Test image not found: {receipt_path}")

    result = ocr_engine.extract_text(str(receipt_path))

    assert isinstance(result, str)
    assert len(result) > 0


@skip_on_billing_error
def test_extract_text_from_korean_receipt(ocr_engine, dataset_dir):
    """Test OCR extraction from a Korean receipt."""
    receipt_path = dataset_dir / "receipt_kr.jpg"
    if not receipt_path.exists():
        pytest.skip(f"Test image not found: {receipt_path}")

    result = ocr_engine.extract_text(str(receipt_path))

    assert isinstance(result, str)
    assert len(result) > 0


@skip_on_billing_error
def test_ocr_processing_speed(ocr_engine, dataset_dir):
    """Test that OCR processing meets speed requirements (< 5 seconds)."""
    import time

    receipt_path = dataset_dir / "receipt_en.jpg"
    if not receipt_path.exists():
        pytest.skip(f"Test image not found: {receipt_path}")

    start_time = time.time()
    result = ocr_engine.extract_text(str(receipt_path))
    elapsed_time = time.time() - start_time

    assert isinstance(result, str)
    assert len(result) > 0
    # Performance requirement: < 5 seconds per receipt
    assert elapsed_time < 5.0, f"OCR took {elapsed_time:.2f}s, exceeds 5s requirement"
