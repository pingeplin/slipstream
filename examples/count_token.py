import os
from pathlib import Path

from anthropic import Anthropic
from anthropic.types import MessageParam
from dotenv import load_dotenv

load_dotenv()


def count_tokens():
    # Model specified in the task
    target_model = "claude-haiku-4-5"

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "your-api-key"))

    project_root = Path(__file__).parent.parent
    system_prompt_path = project_root / "prompts" / "extractor_system.jinja2"
    user_prompt_path = project_root / "prompts" / "extractor_user.jinja2"

    try:
        system_content = system_prompt_path.read_text(encoding="utf-8")
        user_content = user_prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # User prompt has {{OCR_TEXT}} placeholder.
    # For counting tokens, we might want to see how much the template itself costs.
    # Or we can put a dummy text.
    user_content_filled = user_content.replace("{{OCR_TEXT}}", "(OCR TEXT PLACEHOLDER)")

    print(f"Counting tokens for model: {target_model}")

    # Count system tokens
    # Note: count_tokens in Anthropic SDK works on messages.
    # To count system prompt tokens, we can include it in the messages if needed,
    # but the SDK often has a way to count specific strings or we can just send it.

    try:
        # System prompt tokens
        messages: list[MessageParam] = [{"role": "user", "content": "Hello"}]
        system_tokens = client.messages.count_tokens(
            model=target_model, system=system_content, messages=messages
        ).input_tokens
        # This counts system + a small user message.

        # Base user prompt tokens (without system)
        user_messages: list[MessageParam] = [
            {"role": "user", "content": user_content_filled}
        ]
        user_tokens = client.messages.count_tokens(
            model=target_model, messages=user_messages
        ).input_tokens

        # Let's also count them separately if possible or just report these.
        # Anthropic's count_tokens returns the total input tokens for the request.

        print("\n--- Results ---")
        print(f"System Prompt ({system_prompt_path.name}):")
        print(f"  Approx. tokens (including small user message): {system_tokens}")

        print(f"\nUser Prompt ({user_prompt_path.name}) with placeholder:")
        print(f"  Approx. tokens: {user_tokens}")

        # If we want just the system prompt tokens, we can try to subtract.
        # But it's better to show message-based count as that's how billed.

    except Exception as e:
        print(f"Error counting tokens: {e}")
        print("\nNote: Make sure ANTHROPIC_API_KEY is set in your environment.")


if __name__ == "__main__":
    count_tokens()
