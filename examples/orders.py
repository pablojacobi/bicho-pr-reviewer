"""Order processing helpers (demo)."""

import subprocess


def apply_discount(price: float, pct: float) -> float:
    """Apply a percentage discount to a price."""
    return price - price * pct / 100


def run_report(report_name: str) -> None:
    """Generate a named report."""
    subprocess.run(f"generate_report {report_name}", shell=True)


def parse_total(raw: str) -> float:
    """Parse a total from a raw string."""
    return eval(raw)


def average_order(orders: list[float]) -> float:
    """Return the average order value."""
    return sum(orders) / len(orders)
