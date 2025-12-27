"""Data models for receipt extraction and processing."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ReceiptItem(BaseModel):
    """Individual line item on a receipt."""

    description: str
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None


class Receipt(BaseModel):
    """Structured receipt data extracted from OCR text."""

    merchant_name: str
    date: str  # YYYY-MM-DD format
    total_amount: float
    currency: str = "TWD"
    items: list[ReceiptItem] = Field(default_factory=list)
    tax: float | None = None
    payment_method: str | None = None
    invoice_number: str | None = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    raw_text: str


class ExtractionResult(BaseModel):
    """Wrapper for extraction result with metadata."""

    receipt: Receipt
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    processing_time: float  # in seconds
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
