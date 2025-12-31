# Slipstream

Slipstream is a CLI tool designed to automate the process of handling receipts. It reads receipt images from a Google Drive folder, identifies and structures the information using AI, and exports the data to Google Sheets for easy expense tracking and reimbursement.

## Features

- **Google Drive Integration**: Automatically lists and downloads receipt images (JPG, PNG, PDF) from a specified folder in parallel.
- **AI-Powered Extraction**: Uses Google Vision OCR and Anthropic Claude 3.5 Haiku with structured outputs to extract merchant names, dates, amounts, and line items.
- **Google Sheets Export**: Seamlessly appends structured receipt data to your spreadsheets in batch.
- **Local CSV Export**: Export processed receipt data to a local CSV file for offline use.
- **Smart URL Parsing**: Supports both Google Drive Folder IDs and full sharing URLs, as well as Google Sheets URLs.
- **Streaming Pipeline**: Processes files as soon as they are downloaded for maximum efficiency.

## Getting Started

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) (recommended Python package manager)

### Installation

#### As a Command-Line Tool (Recommended)

If you have `uv` installed, you can install Slipstream directly from GitHub as a global tool:

```bash
uv tool install git+https://github.com/pingeplin/slipstream.git
```

Now you can run it directly:

```bash
slipstream --help
```

#### For Development

1. Clone the repository:
   ```bash
   git clone https://github.com/pingeplin/slipstream.git
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

If installed as a tool, you can run `slipstream` directly. Otherwise, use `uv run slipstream`.

### Processing a Folder

To process all receipts in a Google Drive folder and export to Google Sheets or a local CSV file:

```bash
slipstream process --folder "FOLDER_URL" --sheet "SHEET_URL"
```

Or using IDs and short flags:

```bash
slipstream process -f YOUR_FOLDER_ID -s YOUR_SHEET_ID
```

You can also control parallelism with the `--workers` option:

```bash
slipstream process -f YOUR_FOLDER_ID -w 8
```

To save the results to a local CSV file:

```bash
slipstream process -f YOUR_FOLDER_ID --save-local receipts.csv
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
