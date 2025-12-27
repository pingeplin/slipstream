"""Unit tests for data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from slipstream.models import ExtractionResult, Receipt, ReceiptItem


class TestReceiptItem:
    """Test cases for ReceiptItem model."""

    def test_create_receipt_item_minimal(self):
        """Test creating a receipt item with only required fields."""
        item = ReceiptItem(description="Coffee")
        assert item.description == "Coffee"
        assert item.quantity is None
        assert item.unit_price is None
        assert item.amount is None

    def test_create_receipt_item_complete(self):
        """Test creating a receipt item with all fields."""
        item = ReceiptItem(
            description="Cappuccino",
            quantity=2.0,
            unit_price=120.0,
            amount=240.0,
        )
        assert item.description == "Cappuccino"
        assert item.quantity == 2.0
        assert item.unit_price == 120.0
        assert item.amount == 240.0


class TestReceipt:
    """Test cases for Receipt model."""

    def test_create_receipt_minimal(self):
        """Test creating a receipt with only required fields."""
        receipt = Receipt(
            merchant_name="Coffee Shop",
            date="2025-12-27",
            total_amount=240.0,
            confidence_score=0.95,
            raw_text="Raw OCR text here",
        )
        assert receipt.merchant_name == "Coffee Shop"
        assert receipt.date == "2025-12-27"
        assert receipt.total_amount == 240.0
        assert receipt.currency == "TWD"  # default
        assert receipt.items == []  # default empty list
        assert receipt.confidence_score == 0.95
        assert receipt.raw_text == "Raw OCR text here"

    def test_create_receipt_complete(self):
        """Test creating a receipt with all fields."""
        items = [
            ReceiptItem(description="Cappuccino", quantity=2.0, amount=240.0),
            ReceiptItem(description="Cookie", quantity=1.0, amount=50.0),
        ]
        receipt = Receipt(
            merchant_name="Coffee Shop",
            date="2025-12-27",
            total_amount=290.0,
            currency="USD",
            items=items,
            tax=15.0,
            payment_method="Credit Card",
            invoice_number="INV-123456",
            confidence_score=0.92,
            raw_text="Raw OCR text here",
        )
        assert receipt.merchant_name == "Coffee Shop"
        assert receipt.currency == "USD"
        assert len(receipt.items) == 2
        assert receipt.tax == 15.0
        assert receipt.payment_method == "Credit Card"
        assert receipt.invoice_number == "INV-123456"

    def test_confidence_score_validation_valid(self):
        """Test that confidence score accepts valid values (0.0 to 1.0)."""
        for score in [0.0, 0.5, 1.0]:
            receipt = Receipt(
                merchant_name="Test",
                date="2025-12-27",
                total_amount=100.0,
                confidence_score=score,
                raw_text="test",
            )
            assert receipt.confidence_score == score

    def test_confidence_score_validation_invalid_high(self):
        """Test that confidence score rejects values > 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            Receipt(
                merchant_name="Test",
                date="2025-12-27",
                total_amount=100.0,
                confidence_score=1.5,
                raw_text="test",
            )
        assert "confidence_score" in str(exc_info.value)

    def test_confidence_score_validation_invalid_low(self):
        """Test that confidence score rejects values < 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            Receipt(
                merchant_name="Test",
                date="2025-12-27",
                total_amount=100.0,
                confidence_score=-0.1,
                raw_text="test",
            )
        assert "confidence_score" in str(exc_info.value)


class TestExtractionResult:
    """Test cases for ExtractionResult model."""

    def test_create_extraction_result(self):
        """Test creating an extraction result with metadata."""
        receipt = Receipt(
            merchant_name="Coffee Shop",
            date="2025-12-27",
            total_amount=240.0,
            confidence_score=0.95,
            raw_text="Raw OCR text",
        )
        result = ExtractionResult(
            receipt=receipt,
            input_tokens=500,
            output_tokens=300,
            processing_time=2.5,
        )
        assert result.receipt == receipt
        assert result.input_tokens == 500
        assert result.output_tokens == 300
        assert result.processing_time == 2.5
        assert isinstance(result.timestamp, datetime)

    def test_extraction_result_timestamp_auto_generated(self):
        """Test that timestamp is automatically generated if not provided."""
        receipt = Receipt(
            merchant_name="Test",
            date="2025-12-27",
            total_amount=100.0,
            confidence_score=0.9,
            raw_text="test",
        )
        result1 = ExtractionResult(
            receipt=receipt,
            input_tokens=100,
            output_tokens=50,
            processing_time=1.0,
        )
        result2 = ExtractionResult(
            receipt=receipt,
            input_tokens=100,
            output_tokens=50,
            processing_time=1.0,
        )
        # Timestamps should be close but potentially different
        assert isinstance(result1.timestamp, datetime)
        assert isinstance(result2.timestamp, datetime)
