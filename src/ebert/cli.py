"""CLI interface using Typer."""

import os
import traceback
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ebert import __version__
from ebert.diff import FileError
from ebert.models import FocusArea, ReviewMode
from ebert.output import get_formatter
from ebert.providers.registry import ProviderNotFoundError, ProviderUnavailableError
from ebert.review import run_review

app = typer.Typer(
  name="ebert",
  help="Uncompromising AI code review CLI",
  no_args_is_help=False,
)

console = Console()


def _is_debug() -> bool:
  return os.environ.get("EBERT_DEBUG", "").lower() in ("1", "true", "yes")


def version_callback(value: bool) -> None:
  if value:
    console.print(f"ebert {__version__}")
    raise typer.Exit()


@app.command()
def main(
  files: Optional[list[str]] = typer.Argument(
    None,
    help="Files or glob patterns to review (e.g., src/*.py)",
  ),
  branch: str = typer.Option(None, "--branch", "-b", help="Branch to review against base"),
  base: str = typer.Option("main", "--base", help="Base branch for comparison"),
  provider: str = typer.Option(
    None, "--provider", "-p", help="LLM provider (gemini, openai, anthropic, ollama)"
  ),
  model: str = typer.Option(None, "--model", "-m", help="Model to use"),
  full: bool = typer.Option(False, "--full", "-f", help="Full review (default: quick review)"),
  focus: str = typer.Option(None, "--focus", help="Focus areas: security,bugs,style,performance"),
  format_type: str = typer.Option(
    "terminal", "--format", help="Output format: terminal, json, markdown"
  ),
  config: Path = typer.Option(None, "--config", "-c", help="Config file path"),
  debug: bool = typer.Option(False, "--debug", "-d", help="Show full traceback on errors"),
  version: bool = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True),
) -> None:
  """Review code changes using AI.

  With no arguments, reviews staged git changes.
  With file arguments, reviews the specified files directly.
  """
  mode = ReviewMode.FULL if full else ReviewMode.QUICK
  focus_areas = _parse_focus(focus) if focus else None
  show_traceback = debug or _is_debug()

  try:
    result = run_review(
      branch=branch,
      base=base,
      provider=provider,
      model=model,
      mode=mode,
      focus=focus_areas,
      config_path=config,
      files=files,
    )

    formatter = get_formatter(format_type)
    output = formatter.format(result)
    if output:
      console.print(output)

  except ProviderNotFoundError as e:
    console.print(f"[red]Error:[/red] {e}")
    raise typer.Exit(1) from None
  except ProviderUnavailableError as e:
    console.print(f"[red]Error:[/red] {e}")
    raise typer.Exit(1) from None
  except FileError as e:
    console.print(f"[red]Error:[/red] {e}")
    raise typer.Exit(1) from None
  except Exception as e:
    console.print(f"[red]Error:[/red] {e}")
    if show_traceback:
      console.print("\n[dim]Traceback:[/dim]")
      console.print(traceback.format_exc())
    raise typer.Exit(1) from None


def _parse_focus(focus_str: str) -> list[FocusArea]:
  """Parse focus string into list of FocusArea."""
  areas = []
  for part in focus_str.split(","):
    part = part.strip().lower()
    try:
      areas.append(FocusArea(part))
    except ValueError:
      console.print(f"[yellow]Warning:[/yellow] Unknown focus area '{part}', ignoring")
  return areas or [FocusArea.ALL]


if __name__ == "__main__":
  app()
