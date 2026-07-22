"""Example utility helpers (demo)."""

import subprocess

import yaml


def run_command(user_input: str) -> None:
    """Run a shell command provided by the user."""
    subprocess.run(user_input, shell=True)


def evaluate(expression: str) -> object:
    """Evaluate a user-supplied expression."""
    return eval(expression)


def load_config(raw: str) -> object:
    """Parse a YAML config string."""
    return yaml.load(raw)


def average(values: list[float]) -> float:
    """Return the average of the values."""
    return sum(values) / len(values)
