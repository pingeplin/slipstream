"""Unit tests for Anthropic extractor integration."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from slipstream.integrations.anthropic_extractor import (
    AnthropicExtractor,
    ExtractionIncompleteError,
    ExtractionRefusedError,
)
from slipstream.models import Receipt, ReceiptItem


@pytest.fixture
def api_key():
    """Provide a test API key."""
    return "sk-test-key-12345"


@pytest.fixture
def sample_ocr_text():
    """Provide sample OCR text for testing."""
    return """
    早安美芝城 Breakfast & Brunch
    電子發票證明聯
    114年11-12月
    AA-11111111
    2025-11-02 09:31:43
    總計:190
    """


@pytest.fixture
def sample_receipt():
    """Provide a sample Receipt for testing."""
    return Receipt(
        merchant_name="早安美芝城 Breakfast & Brunch",
        date="2025-11-02",
        total_amount=190.0,
        currency="TWD",
        items=[
            ReceiptItem(
                description="總計",
                quantity=None,
                unit_price=None,
                amount=190.0,
            )
        ],
        tax=None,
        payment_method=None,
        invoice_number="AA-11111111",
        confidence_score=0.85,
        raw_text="Raw OCR text",
    )


@pytest.fixture
def prompts_dir():
    """Get the prompts directory path."""
    project_root = Path(__file__).parent.parent.parent
    return str(project_root / "prompts")


class TestAnthropicExtractorInit:
    """Test cases for AnthropicExtractor initialization."""

    def test_init_with_defaults(self, api_key, prompts_dir):
        """Test initializing extractor with default parameters."""
        extractor = AnthropicExtractor(api_key=api_key, prompts_dir=prompts_dir)
        assert extractor.model == "claude-haiku-4-5"
        assert extractor.max_tokens == 2048
        assert extractor.temperature == 0.0
        assert extractor.client is not None

    def test_init_with_custom_params(self, api_key, prompts_dir):
        """Test initializing extractor with custom parameters."""
        extractor = AnthropicExtractor(
            api_key=api_key,
            model="claude-sonnet-4-5",
            max_tokens=4096,
            temperature=0.5,
            prompts_dir=prompts_dir,
        )
        assert extractor.model == "claude-sonnet-4-5"
        assert extractor.max_tokens == 4096
        assert extractor.temperature == 0.5

    def test_init_loads_jinja_templates(self, api_key, prompts_dir):
        """Test that Jinja2 templates are loaded correctly."""
        extractor = AnthropicExtractor(api_key=api_key, prompts_dir=prompts_dir)
        # Verify templates can be accessed
        system_template = extractor.jinja_env.get_template("extractor_system.jinja2")
        user_template = extractor.jinja_env.get_template("extractor_user.jinja2")
        assert system_template is not None
        assert user_template is not None


class TestPromptRendering:
    """Test cases for prompt template rendering."""

    def test_render_prompts_system(self, api_key, sample_ocr_text, prompts_dir):
        """Test that system prompt is rendered correctly."""
        extractor = AnthropicExtractor(api_key=api_key, prompts_dir=prompts_dir)
        system_prompt, _ = extractor._render_prompts(sample_ocr_text)

        assert "receipt data extraction" in system_prompt.lower()
        assert "json" in system_prompt.lower()

    def test_render_prompts_user(self, api_key, sample_ocr_text, prompts_dir):
        """Test that user prompt includes OCR text."""
        extractor = AnthropicExtractor(api_key=api_key, prompts_dir=prompts_dir)
        _, user_prompt = extractor._render_prompts(sample_ocr_text)

        assert "早安美芝城" in user_prompt
        assert "AA-11111111" in user_prompt


class TestExtractionSuccess:
    """Test cases for successful extraction."""

    @pytest.mark.asyncio
    async def test_extract_receipt_data_success(
        self, api_key, sample_ocr_text, sample_receipt, prompts_dir, mocker
    ):
        """Test successful receipt data extraction."""
        # Create mock response
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.parsed_output = sample_receipt
        mock_response.usage = MagicMock(
            input_tokens=500,
            output_tokens=300,
            cache_creation_input_tokens=2000,
            cache_read_input_tokens=0,
        )

        # Mock the client's beta.messages.parse method
        extractor = AnthropicExtractor(api_key=api_key, prompts_dir=prompts_dir)
        mock_parse = AsyncMock(return_value=mock_response)
        mocker.patch.object(extractor.client.beta.messages, "parse", mock_parse)

        # Execute extraction
        result = await extractor.extract_receipt_data(sample_ocr_text)

        # Verify result
        assert result.receipt == sample_receipt
        assert result.input_tokens == 500
        assert result.output_tokens == 300
        assert result.cache_creation_input_tokens == 2000
        assert result.cache_read_input_tokens == 0
        assert result.processing_time > 0
        assert result.timestamp is not None

        # Verify API was called with correct parameters
        mock_parse.assert_called_once()
        call_kwargs = mock_parse.call_args.kwargs
        assert call_kwargs["model"] == "claude-haiku-4-5"
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["temperature"] == 0.0
        assert call_kwargs["betas"] == ["structured-outputs-2025-11-13"]
        assert call_kwargs["output_format"] == Receipt

        # Verify system prompt uses cache_control
        system_param = call_kwargs["system"]
        assert isinstance(system_param, list)
        assert len(system_param) == 1
        assert system_param[0]["type"] == "text"
        assert "cache_control" in system_param[0]
        assert system_param[0]["cache_control"] == {"type": "ephemeral"}

    @pytest.mark.asyncio
    async def test_extract_receipt_data_with_custom_max_tokens(
        self, api_key, sample_ocr_text, sample_receipt, prompts_dir, mocker
    ):
        """Test extraction with custom max_tokens override."""
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.parsed_output = sample_receipt
        mock_response.usage = MagicMock(
            input_tokens=500,
            output_tokens=300,
            cache_creation_input_tokens=2000,
            cache_read_input_tokens=0,
        )

        extractor = AnthropicExtractor(api_key=api_key, prompts_dir=prompts_dir)
        mock_parse = AsyncMock(return_value=mock_response)
        mocker.patch.object(extractor.client.beta.messages, "parse", mock_parse)

        # Execute with custom max_tokens
        await extractor.extract_receipt_data(sample_ocr_text, max_tokens=4096)

        # Verify max_tokens override was used
        call_kwargs = mock_parse.call_args.kwargs
        assert call_kwargs["max_tokens"] == 4096


class TestExtractionErrors:
    """Test cases for extraction error handling."""

    @pytest.mark.asyncio
    async def test_extraction_refused_error(
        self, api_key, sample_ocr_text, prompts_dir, mocker
    ):
        """Test handling of model refusal."""
        mock_response = MagicMock()
        mock_response.stop_reason = "refusal"

        extractor = AnthropicExtractor(api_key=api_key, prompts_dir=prompts_dir)
        mock_parse = AsyncMock(return_value=mock_response)
        mocker.patch.object(extractor.client.beta.messages, "parse", mock_parse)

        with pytest.raises(ExtractionRefusedError) as exc_info:
            await extractor.extract_receipt_data(sample_ocr_text)

        assert "refused" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_extraction_max_tokens_error(
        self, api_key, sample_ocr_text, prompts_dir, mocker
    ):
        """Test handling of max_tokens truncation."""
        mock_response = MagicMock()
        mock_response.stop_reason = "max_tokens"

        extractor = AnthropicExtractor(api_key=api_key, prompts_dir=prompts_dir)
        mock_parse = AsyncMock(return_value=mock_response)
        mocker.patch.object(extractor.client.beta.messages, "parse", mock_parse)

        with pytest.raises(ExtractionIncompleteError) as exc_info:
            await extractor.extract_receipt_data(sample_ocr_text)

        assert "truncated" in str(exc_info.value).lower()
        assert "max_tokens" in str(exc_info.value).lower()


class TestRetryLogic:
    """Test cases for retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_api_error(
        self, api_key, sample_ocr_text, sample_receipt, prompts_dir, mocker
    ):
        """Test that API errors trigger retry logic."""
        # Create a mock that fails twice then succeeds
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.parsed_output = sample_receipt
        mock_response.usage = MagicMock(
            input_tokens=500,
            output_tokens=300,
            cache_creation_input_tokens=2000,
            cache_read_input_tokens=0,
        )

        extractor = AnthropicExtractor(api_key=api_key, prompts_dir=prompts_dir)
        mock_parse = AsyncMock(
            side_effect=[
                Exception("API Error 1"),
                Exception("API Error 2"),
                mock_response,
            ]
        )
        mocker.patch.object(extractor.client.beta.messages, "parse", mock_parse)

        # Should succeed after retries
        result = await extractor.extract_receipt_data(sample_ocr_text)
        assert result.receipt == sample_receipt

        # Verify it was called 3 times (2 failures + 1 success)
        assert mock_parse.call_count == 3
