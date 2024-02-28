"""
Logging utils
"""
from typing import Any

from rich.console import Console

console = Console()


def print(text):  # noqa
    """Basic console print"""
    console.print(text)


def debug(text: str) -> None:
    """Debug log"""
    return
    console.print(f"[bright_black][bold]DEBUG[/bold]\t {text}[/bright_black]")


def success(text: str) -> None:
    """Success log"""
    console.print(f"[green][bold]SUCCESS[/bold]\t {text}[/green]")


def info(text: str) -> None:
    """Info log"""
    console.print(f"[blue][bold]INFO[/bold]\t {text}[/blue]")


def warn(text: str) -> None:
    """Warn log"""
    console.print(f"[yellow][bold]WARNING[/bold]\t {text}[/yellow]")


def error(text: str) -> None:
    """Error log"""
    console.print(f"[red][bold]ERROR[/bold]\t {text}[/red]")


def exception():
    """Print an exception"""
    console.print_exception()


def print_json(entries: Any):
    """Print JSON output"""
    console.print_json(data=entries)
