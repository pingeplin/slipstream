import re


def clean_cli_output(output: str) -> str:
    """
    Remove Rich formatting characters, whitespace, and newlines from CLI output
    to make assertions robust against terminal wrapping.
    """
    # Remove:
    # \s - all whitespace (space, tab, newline, etc.)
    # │, ╭, ╮, ╰, ╯, ─ - Rich box characters
    return re.sub(r"[\s│╭╮╰╯─]", "", output)
