"""Anthropic API integration for receipt data extraction using structured outputs."""

import time
from pathlib import Path

from anthropic import AsyncAnthropic
from anthropic.types.beta import (
    BetaCacheControlEphemeralParam,
    BetaMessageParam,
    BetaTextBlockParam,
)
from jinja2 import Environment, FileSystemLoader, select_autoescape
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
)

from slipstream.models import ExtractionResult, Receipt


class ExtractionError(Exception):
    """Base exception for extraction errors."""


class ExtractionRefusedError(ExtractionError):
    """Raised when the model refuses to process the request."""


class ExtractionIncompleteError(ExtractionError):
    """Raised when the response is truncated due to token limits."""


class AnthropicExtractor:
    """
    Anthropic-powered receipt data extractor using structured outputs.

    This class uses Claude's structured outputs feature (beta) to extract
    structured receipt data from OCR text with automatic Pydantic validation.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5",
        max_tokens: int = 2048,
        temperature: float = 0.0,
        prompts_dir: str | None = None,
    ) -> None:
        """
        Initialize the Anthropic extractor.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-haiku-4-5)
            max_tokens: Maximum tokens for response (default: 2048)
            temperature: Sampling temperature (default: 0.0 for deterministic)
            prompts_dir: Directory containing Jinja2 templates (default: ./prompts)
        """
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Set up Jinja2 environment for prompt templates
        if prompts_dir is None:
            # Default to prompts/ directory in project root
            project_root = Path(__file__).parent.parent.parent.parent
            prompts_dir = str(project_root / "prompts")

        self.jinja_env = Environment(
            loader=FileSystemLoader(prompts_dir),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _render_prompts(self, ocr_text: str) -> tuple[str, str]:
        """
        Render system and user prompts from Jinja2 templates.

        Args:
            ocr_text: Raw OCR text to include in user prompt

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system_template = self.jinja_env.get_template("extractor_system.jinja2")
        user_template = self.jinja_env.get_template("extractor_user.jinja2")

        system_prompt = system_template.render()
        user_prompt = user_template.render(OCR_TEXT=ocr_text)

        return system_prompt, user_prompt

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def extract_receipt_data(
        self, ocr_text: str, max_tokens: int | None = None
    ) -> ExtractionResult:
        """
        Extract structured receipt data from OCR text using structured outputs.

        This method uses Anthropic's structured outputs beta feature to ensure
        the response matches the Receipt Pydantic model schema.

        Args:
            ocr_text: Raw OCR text from receipt image
            max_tokens: Override default max_tokens if specified

        Returns:
            ExtractionResult containing the validated Receipt and metadata

        Raises:
            ExtractionRefusedError: If the model refuses the request
            ExtractionIncompleteError: If response is truncated
            Exception: For other API errors (with retry)
        """
        start_time = time.time()

        # Render prompts
        system_prompt, user_prompt = self._render_prompts(ocr_text)

        # Construct properly typed message
        messages: list[BetaMessageParam] = [{"role": "user", "content": user_prompt}]

        # Call Anthropic API with structured outputs and prompt caching
        response = await self.client.beta.messages.parse(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=self.temperature,
            betas=["structured-outputs-2025-11-13"],
            system=[
                BetaTextBlockParam(
                    type="text",
                    text=system_prompt,
                    cache_control=BetaCacheControlEphemeralParam(type="ephemeral"),
                )
            ],
            messages=messages,
            output_format=Receipt,
        )

        # Handle edge cases based on stop_reason
        if response.stop_reason == "refusal":
            raise ExtractionRefusedError("Model refused to process the request")

        if response.stop_reason == "max_tokens":
            raise ExtractionIncompleteError(
                "Response truncated due to token limit. Try increasing max_tokens."
            )

        # Extract validated Receipt from parsed_output
        receipt: Receipt = response.parsed_output  # type: ignore

        # Calculate processing time
        processing_time = time.time() - start_time

        # Create result with metadata
        result = ExtractionResult(
            receipt=receipt,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_input_tokens=response.usage.cache_creation_input_tokens,
            cache_read_input_tokens=response.usage.cache_read_input_tokens,
            processing_time=processing_time,
        )

        return result
