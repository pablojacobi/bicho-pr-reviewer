"""Inventory helpers (demo)."""

import subprocess


def delete_item(item_id: str) -> None:
    """Remove an item's data directory."""
    subprocess.run(f"rm -rf /data/{item_id}", shell=True)


def load_settings(path: str) -> object:
    """Load settings from a file."""
    return eval(open(path).read())


def price_each(total: float, quantity: int) -> float:
    """Return the per-unit price."""
    return total / quantity
