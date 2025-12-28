import asyncio
import os
import tempfile
from collections.abc import Callable, Generator
from pathlib import Path

import typer
from dotenv import load_dotenv

# Disable gRPC fork support warnings
# These warnings occur when gRPC clients (Google APIs, Anthropic SDK) are used
# with thread pools. Setting this env var disables the warnings.
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "0")

from slipstream.integrations.anthropic_extractor import (
    AnthropicExtractor,
    ExtractionError,
    ExtractionIncompleteError,
    ExtractionRefusedError,
)
from slipstream.integrations.gdrive import DownloadResult, GDriveClient
from slipstream.integrations.gsheets import GSheetsClient, receipt_to_sheet_row
from slipstream.integrations.ocr import OCREngine
from slipstream.models import ProcessingResult
from slipstream.utils.url_parser import URLParserError, parse_google_id

load_dotenv()

app = typer.Typer(no_args_is_help=True)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Slipstream CLI tool."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


async def process_downloaded_file(
    download_result: DownloadResult,
    ocr_engine: OCREngine,
    extractor: AnthropicExtractor | None,
    on_progress: Callable[[str, str], None] | None = None,
) -> ProcessingResult:
    """Process a single downloaded file through OCR and LLM extraction.

    Args:
        download_result: Download result with success, dest_path, etc.
        ocr_engine: OCR engine for text extraction
        extractor: Anthropic extractor for structured data extraction (optional)
        on_progress: Optional callback for progress updates (event_type, message)

    Returns:
        ProcessingResult with OCR text, extraction results, and any errors
    """
    dest_path = download_result.dest_path
    file_name = dest_path.name
    file_id = download_result.file_id

    # Initialize result
    result = ProcessingResult(
        file_id=file_id,
        file_name=file_name,
        download_success=download_result.success,
        download_error=download_result.error if not download_result.success else None,
    )

    # Skip processing if download failed
    if not download_result.success:
        return result

    # Step 1: OCR extraction
    try:
        # OCR is synchronous, so we run it in an executor for true parallelism
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, ocr_engine.extract_text, str(dest_path))
        result.ocr_text = text

        message = f"Extracted text from {file_name}: {len(text)} characters"
        if on_progress:
            on_progress("ocr_success", message)

    except Exception as e:
        # Catch-all for OCR errors
        result.ocr_error = str(e)
        message = f"Failed to process {file_name}: {e}"
        if on_progress:
            on_progress("ocr_error", message)
        return result  # Don't attempt LLM if OCR failed

    # Step 2: LLM extraction (already async)
    if extractor:
        try:
            extraction_result = await extractor.extract_receipt_data(text)
            result.extraction_result = extraction_result

            message = (
                f"Structured data extracted for {file_name}: "
                f"{extraction_result.receipt.merchant_name}, "
                f"{extraction_result.receipt.date}, "
                f"${extraction_result.receipt.total_amount:.2f} "
                f"{extraction_result.receipt.currency}"
            )
            if on_progress:
                on_progress("llm_success", message)

        except (
            ExtractionRefusedError,
            ExtractionIncompleteError,
            ExtractionError,
            Exception,
        ) as e:
            result.extraction_error = str(e)
            message = f"Failed to extract structured data from {file_name}: {e}"
            if on_progress:
                on_progress("llm_error", message)

    return result


async def run_pipeline(
    download_results: Generator[DownloadResult, None, None],
    ocr_engine: OCREngine,
    extractor: AnthropicExtractor | None = None,
    gsheets_client: GSheetsClient | None = None,
    on_progress: Callable[[str, str], None] | None = None,
) -> list[ProcessingResult]:
    """Run the streaming pipeline: process files as they download.

    Args:
        download_results: Generator yielding DownloadResult objects as
            downloads complete
        ocr_engine: OCR engine for text extraction
        extractor: Optional Anthropic extractor for structured data extraction
        gsheets_client: Optional Google Sheets client for writing results
        on_progress: Optional callback for progress updates (event_type, message)

    Returns:
        List of ProcessingResult objects containing OCR text, LLM extractions,
        and errors
    """
    # Stream: Start processing each file as soon as it downloads
    tasks = []
    for download_result in download_results:
        # Report download status immediately
        if download_result.success:
            message = f"Downloaded {download_result.dest_path.name}"
            if on_progress:
                on_progress("download_success", message)
        else:
            file_name = download_result.dest_path.name
            message = f"Failed to download {file_name}: {download_result.error}"
            if on_progress:
                on_progress("download_error", message)

        # Start processing this file immediately
        # (don't wait for other downloads)
        task = asyncio.create_task(
            process_downloaded_file(download_result, ocr_engine, extractor, on_progress)
        )
        tasks.append(task)

    # Wait for all processing tasks to complete
    results = await asyncio.gather(*tasks)

    # If Google Sheets client is provided, append successful extractions
    if gsheets_client:
        successful_receipts = []
        for result in results:
            if result.extraction_result:
                receipt = result.extraction_result.receipt
                row = receipt_to_sheet_row(receipt)
                successful_receipts.append(row)

        if successful_receipts:
            try:
                # Append all rows in a single batch operation
                gsheets_client.append_rows(successful_receipts)
                count = len(successful_receipts)
                message = f"Successfully appended {count} receipts to spreadsheet"
                if on_progress:
                    on_progress("sheets_success", message)
            except Exception as e:
                message = f"Failed to append receipts to spreadsheet: {e}"
                if on_progress:
                    on_progress("sheets_error", message)

    return list(results)


@app.command()
def process(
    folder: str = typer.Option(
        ..., "--folder", "-f", help="Google Drive folder ID or URL"
    ),
    workers: int = typer.Option(
        4, "--workers", "-w", help="Number of parallel download workers"
    ),
    sheet: str | None = typer.Option(
        None,
        "--sheet",
        "-s",
        help="Google Sheets spreadsheet ID or URL to write results to",
    ),
):
    """Process files from a Google Drive folder."""
    try:
        folder_id = parse_google_id(folder)
    except URLParserError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    typer.echo(f"Processing folder: {folder_id}")

    try:
        client = GDriveClient(max_workers=workers)
        files = client.list_files(
            folder_id, mime_types=["image/jpeg", "image/png", "application/pdf"]
        )
    except Exception as e:
        typer.echo(f"Error communicating with Google Drive: {e}", err=True)
        raise typer.Exit(code=1) from e

    if not files:
        typer.echo("No supported files found in folder.")
        return

    # Initialize OCR engine
    try:
        ocr_engine = OCREngine()
        # Eagerly initialize the Vision API client in the main thread
        # to avoid gRPC initialization warnings when running in executor
        _ = ocr_engine.client
    except Exception as e:
        typer.echo(f"Failed to initialize OCR engine: {e}", err=True)
        raise typer.Exit(code=1) from e

    # Initialize Anthropic extractor
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        typer.echo(
            "Warning: ANTHROPIC_API_KEY not found. Skipping LLM extraction.",
            err=True,
        )
        extractor = None
    else:
        try:
            extractor = AnthropicExtractor(api_key=anthropic_api_key)
        except Exception as e:
            typer.echo(f"Failed to initialize Anthropic extractor: {e}", err=True)
            raise typer.Exit(code=1) from e

    # Initialize Google Sheets client if --sheet option is provided
    gsheets_client = None
    if sheet:
        try:
            spreadsheet_id = parse_google_id(sheet)
            gsheets_client = GSheetsClient(spreadsheet_id=spreadsheet_id)
            typer.echo(f"Will write results to spreadsheet: {spreadsheet_id}")
        except URLParserError as e:
            typer.echo(f"Error parsing spreadsheet ID: {e}", err=True)
            raise typer.Exit(code=1) from e
        except Exception as e:
            typer.echo(f"Failed to initialize Google Sheets client: {e}", err=True)
            raise typer.Exit(code=1) from e

    # Create progress callback for CLI output
    def cli_progress(event_type: str, message: str):
        """Callback to handle progress events and output to CLI."""
        if "error" in event_type:
            typer.echo(message, err=True)
        else:
            typer.echo(message)

    # Execute the async pipeline
    async def execute_pipeline():
        """Execute the pipeline with temporary directory management."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest_dir = Path(tmp_dir)
            download_results = client.download_files(files, dest_dir)
            await run_pipeline(
                download_results=download_results,
                ocr_engine=ocr_engine,
                extractor=extractor,
                gsheets_client=gsheets_client,
                on_progress=cli_progress,
            )

    asyncio.run(execute_pipeline())


def main():
    app()


if __name__ == "__main__":
    main()
