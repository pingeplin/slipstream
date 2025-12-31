import re


def clean_cli_output(output: str) -> str:
    """
    Remove ANSI escape codes, Rich formatting characters, whitespace, and newlines
    from CLI output to make assertions robust against terminal wrapping.
    """
    # 1. Remove ANSI escape codes
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    output = ansi_escape.sub("", output)

    # 2. Remove:
    # \s - all whitespace (space, tab, newline, etc.)
    # │, ╭, ╮, ╰, ╯, ─ - Rich box characters
    return re.sub(r"[\s│╭╮╰╯─]", "", output)
