"""Example usage of the Anthropic extractor for receipt data extraction.

This example demonstrates how to use the AnthropicExtractor to extract
structured data from OCR text using Claude's structured outputs feature.
"""

import asyncio
import os

from slipstream.integrations import AnthropicExtractor


async def main():
    """Example of extracting receipt data from OCR text."""
    # Initialize the extractor with your API key
    api_key = os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
    extractor = AnthropicExtractor(api_key=api_key)

    # Sample OCR text from a receipt
    ocr_text = """
    早安美芝城 Breakfast & Brunch
    電子發票證明聯
    114年11-12月
    AA-11111111
    2025-11-02 09:31:43
    隨機碼:4076
    賣方 12345678
    總計:190
    台北市XX區 STORE01 01 00001
    """

    try:
        # Extract structured data
        result = await extractor.extract_receipt_data(ocr_text)

        # Access the parsed receipt
        receipt = result.receipt
        print(f"Merchant: {receipt.merchant_name}")
        print(f"Date: {receipt.date}")
        print(f"Total: {receipt.total_amount} {receipt.currency}")
        print(f"Invoice: {receipt.invoice_number}")
        print(f"Confidence: {receipt.confidence_score:.2f}")

        # Access metadata
        print(f"\nProcessing time: {result.processing_time:.2f}s")
        print(f"Input tokens: {result.input_tokens}")
        print(f"Output tokens: {result.output_tokens}")

        # Access individual items
        print("\nItems:")
        for item in receipt.items:
            print(f"  - {item.description}: {item.amount}")

    except Exception as e:
        print(f"Error during extraction: {e}")


if __name__ == "__main__":
    asyncio.run(main())
