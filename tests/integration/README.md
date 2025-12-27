# Integration Tests

This directory contains integration tests that make real API calls to Google Cloud services.

## Google Vision API OCR Tests

The OCR integration tests (`test_vision_api.py`) verify the Google Cloud Vision API integration with real receipt images.

### Prerequisites

1. **Google Cloud Project** with Vision API enabled
2. **Billing enabled** on your project
3. **Credentials configured** using one of these methods:

   **Option A: Application Default Credentials (Recommended for local development)**
   ```bash
   gcloud auth application-default login
   ```

   **Option B: Service Account Key**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   ```

### Running Integration Tests

```bash
# Run all integration tests
uv run pytest tests/integration/ -m integration -v

# Run only OCR integration tests
uv run pytest tests/integration/test_vision_api.py -m integration -v

# Skip integration tests (useful for CI/CD)
uv run pytest -m "not integration"
```

### Test Behavior

- **If credentials are not configured**: Tests will be skipped with a helpful message
- **If billing is not enabled**: Tests will be skipped gracefully
- **If everything is configured**: Tests will make real API calls and verify OCR functionality

### Test Images

Integration tests use sample receipt images from `tests/dataset/`:
- `receipt_en.png` - English receipt
- `receipt_zh_tw.png` - Traditional Chinese receipt
- `receipt_jp.png` - Japanese receipt
- `receipt_kr.png` - Korean receipt

### Cost Considerations

These tests make real API calls to Google Cloud Vision, which may incur charges:
- Vision API pricing: ~$1.50 per 1000 images
- Each test run processes 5 images (one per test)
- Estimated cost per test run: ~$0.01

For cost-effective testing, run integration tests selectively rather than on every commit.
