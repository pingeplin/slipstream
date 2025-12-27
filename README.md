# Slipstream

Slipstream is a CLI tool designed to automate the process of handling receipts. It reads receipt images from a Google Drive folder, identifies and structures the information using AI, and exports the data to Google Sheets for easy expense tracking and reimbursement.

## Features

- **Google Drive Integration**: Automatically lists and downloads receipt images (JPG, PNG, PDF) from a specified folder.
- **AI-Powered Extraction**: (Planned) Uses Google Vision OCR and Anthropic Claude Haiku to extract merchant names, dates, amounts, and line items.
- **Google Sheets Export**: (Planned) Seamlessly appends structured receipt data to your spreadsheets.
- **Smart URL Parsing**: Supports both Google Drive Folder IDs and full sharing URLs.

## Getting Started

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) (recommended Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/slipstream.git
   cd slipstream
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

### Configuration

Slipstream requires access to Google Cloud and Anthropic APIs.

1. **Google Cloud**: Set up a project in the Google Cloud Console and enable the Google Drive and Google Sheets APIs.
2. **Authentication**: Authenticate using Application Default Credentials (ADC):
   ```bash
   gcloud auth application-default login
   ```
3. **Environment Variables**: Create a `.env` file (see `.env.example` if available) with your configuration.

## Usage

You can run Slipstream using `uv run`.

### Processing a Folder

To process all receipts in a Google Drive folder:

```bash
uv run slipstream process --folder "https://drive.google.com/drive/folders/YOUR_FOLDER_ID"
```

Or using the folder ID directly:

```bash
uv run slipstream process -f YOUR_FOLDER_ID
```

## Development

### Running Tests

This project follows Test-Driven Development (TDD) principles.

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov
```

### Code Style

We use `ruff` for linting and formatting:

```bash
uv run ruff check .
uv run ruff format .
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
