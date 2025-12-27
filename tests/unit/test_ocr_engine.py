"""Unit tests for OCR Engine using Google Vision API."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from slipstream.integrations.ocr import OCREngine


class TestOCREngineInitialization:
    """Test OCREngine initialization and client setup."""

    def test_ocr_engine_creates_with_default_client(self):
        """Test that OCREngine initializes with a default Vision API client."""
        with patch("slipstream.integrations.ocr.vision.ImageAnnotatorClient"):
            engine = OCREngine()
            assert engine is not None
            assert engine.client is not None

    def test_ocr_engine_accepts_custom_client(self):
        """Test that OCREngine can be initialized with a custom client."""
        mock_client = Mock()
        engine = OCREngine(client=mock_client)
        assert engine.client is mock_client


class TestTextExtraction:
    """Test basic text extraction functionality."""

    def test_extract_text_returns_string_from_clear_image(self):
        """Test that extract_text returns recognized text from a clear image."""
        mock_client = Mock()
        mock_response = Mock()
        mock_annotation = Mock()
        mock_annotation.description = "RECEIPT\nStore Name\nTotal: $25.00"
        mock_response.text_annotations = [mock_annotation]
        mock_client.text_detection.return_value = mock_response

        engine = OCREngine(client=mock_client)
        result = engine.extract_text("tests/dataset/receipt_en.jpg")

        assert isinstance(result, str)
        assert len(result) > 0
        assert "RECEIPT" in result or "Store Name" in result

    @patch("slipstream.integrations.ocr.Path")
    def test_extract_text_calls_vision_api_with_image(self, mock_path_class):
        """Test that extract_text properly calls the Vision API."""
        # Mock file system
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"fake image data"
        mock_path.open.return_value.__enter__.return_value = mock_file
        mock_path_class.return_value = mock_path

        mock_client = Mock()
        mock_response = Mock()
        mock_annotation = Mock()
        mock_annotation.description = "Test text"
        mock_response.text_annotations = [mock_annotation]
        mock_client.text_detection.return_value = mock_response

        engine = OCREngine(client=mock_client)
        result = engine.extract_text("tests/dataset/test.png")

        mock_client.text_detection.assert_called_once()
        assert result == "Test text"


class TestErrorHandling:
    """Test error handling for various failure scenarios."""

    def test_extract_text_raises_error_for_invalid_path(self):
        """Test that extract_text raises appropriate error for non-existent file."""
        mock_client = Mock()
        engine = OCREngine(client=mock_client)

        with pytest.raises(FileNotFoundError):
            engine.extract_text("/invalid/path/to/image.png")

    @patch("slipstream.integrations.ocr.Path")
    def test_extract_text_handles_empty_response(self, mock_path_class):
        """Test that extract_text returns empty string when no text is found."""
        # Mock file system
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"fake image data"
        mock_path.open.return_value.__enter__.return_value = mock_file
        mock_path_class.return_value = mock_path

        mock_client = Mock()
        mock_response = Mock()
        mock_response.text_annotations = []
        mock_client.text_detection.return_value = mock_response

        engine = OCREngine(client=mock_client)
        result = engine.extract_text("tests/dataset/blank.jpg")

        assert result == ""

    def test_extract_text_handles_api_errors_gracefully(self):
        """Test that extract_text handles Google API errors gracefully."""
        from google.api_core.exceptions import GoogleAPIError

        mock_client = Mock()
        mock_client.text_detection.side_effect = GoogleAPIError("Quota exceeded")

        engine = OCREngine(client=mock_client)

        with pytest.raises(GoogleAPIError):
            engine.extract_text("tests/dataset/receipt_en.jpg")


class TestAdvancedScenarios:
    """Test advanced scenarios including validation and edge cases."""

    def test_extract_text_handles_directory_path(self):
        """Test that extract_text raises error when given a directory path."""
        mock_client = Mock()
        engine = OCREngine(client=mock_client)

        with pytest.raises(FileNotFoundError):
            engine.extract_text("tests/dataset/")

    @patch("slipstream.integrations.ocr.Path")
    def test_extract_text_with_multilingual_content(self, mock_path_class):
        """Test that extract_text handles multilingual text (CJK characters)."""
        # Mock file system
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"fake image data"
        mock_path.open.return_value.__enter__.return_value = mock_file
        mock_path_class.return_value = mock_path

        mock_client = Mock()
        mock_response = Mock()
        mock_annotation = Mock()
        # Simulating multilingual receipt with Japanese, Chinese, and Korean text
        mock_annotation.description = "レシート\n商店名\n合計: ¥2500\n谢谢光临"
        mock_response.text_annotations = [mock_annotation]
        mock_client.text_detection.return_value = mock_response

        engine = OCREngine(client=mock_client)
        result = engine.extract_text("tests/dataset/receipt_multilang.png")

        assert isinstance(result, str)
        assert "レシート" in result or "谢谢" in result

    @patch("slipstream.integrations.ocr.Path")
    def test_extract_text_handles_partial_text_recognition(self, mock_path_class):
        """Test handling of low-quality images with partial text recognition."""
        # Mock file system
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"fake blurry image data"
        mock_path.open.return_value.__enter__.return_value = mock_file
        mock_path_class.return_value = mock_path

        mock_client = Mock()
        mock_response = Mock()
        mock_annotation = Mock()
        # Simulating partial recognition from blurry image
        mock_annotation.description = "R--EIPT\nT-tal: $--5.00"
        mock_response.text_annotations = [mock_annotation]
        mock_client.text_detection.return_value = mock_response

        engine = OCREngine(client=mock_client)
        result = engine.extract_text("tests/dataset/blurry_receipt.png")

        # Should return whatever it could recognize without crashing
        assert isinstance(result, str)
        assert len(result) > 0
