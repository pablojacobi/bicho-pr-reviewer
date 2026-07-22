"""Small helper for running user-provided commands and expressions."""

import subprocess


def run_command(user_input: str) -> None:
    """Run a shell command supplied by the user."""
    subprocess.run(user_input, shell=True)


def compute(expression: str) -> object:
    """Evaluate a math expression provided by the user."""
    return eval(expression)
