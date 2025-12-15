"""Output formatting for review results."""

import json
from abc import ABC, abstractmethod
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ebert.models import ReviewResult, Severity


class OutputFormatter(ABC):
  """Base output formatter."""

  @abstractmethod
  def format(self, result: ReviewResult) -> str:
    """Format review result for output."""
    ...


class TerminalFormatter(OutputFormatter):
  """Rich terminal output formatter."""

  SEVERITY_STYLES = {
    Severity.CRITICAL: "bold red",
    Severity.HIGH: "red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "blue",
    Severity.INFO: "dim",
  }

  def __init__(self, console: Console | None = None):
    self.console = console or Console()

  def format(self, result: ReviewResult) -> str:
    self._print_summary(result)
    self._print_comments(result)
    return ""

  def _print_summary(self, result: ReviewResult) -> None:
    self.console.print()
    self.console.print(Panel(
      result.summary,
      title=f"[bold]Code Review[/bold] ({result.provider}/{result.model})",
      border_style="blue",
    ))

  def _print_comments(self, result: ReviewResult) -> None:
    if not result.comments:
      self.console.print("\n[green]No issues found.[/green]")
      return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Severity", width=10)
    table.add_column("File", width=30)
    table.add_column("Line", width=6, justify="right")
    table.add_column("Issue", min_width=40)

    for comment in result.comments:
      style = self.SEVERITY_STYLES.get(comment.severity, "")
      severity_text = Text(comment.severity.value.upper(), style=style)

      message = comment.message
      if comment.suggestion:
        message += f"\n[dim]Suggestion: {comment.suggestion}[/dim]"

      file_link = self._make_file_link(comment.file, comment.line)
      table.add_row(
        severity_text,
        file_link,
        str(comment.line) if comment.line else "-",
        message,
      )

    self.console.print()
    self.console.print(table)
    self.console.print(f"\n[dim]{len(result.comments)} issue(s) found[/dim]")

  def _make_file_link(self, file_path: str, line: int | None) -> str:
    """Create a clickable file link for terminals that support hyperlinks."""
    url = Path(file_path).resolve().as_uri()
    if line:
      url += f":{line}"
    return f"[link={url}]{file_path}[/link]"


class JsonFormatter(OutputFormatter):
  """JSON output formatter."""

  def format(self, result: ReviewResult) -> str:
    data = {
      "summary": result.summary,
      "provider": result.provider,
      "model": result.model,
      "comments": [
        {
          "file": c.file,
          "line": c.line,
          "severity": c.severity.value,
          "message": c.message,
          "suggestion": c.suggestion,
        }
        for c in result.comments
      ],
    }
    return json.dumps(data, indent=2)


class MarkdownFormatter(OutputFormatter):
  """Markdown output formatter."""

  def format(self, result: ReviewResult) -> str:
    lines = [
      "# Code Review",
      "",
      f"**Provider:** {result.provider}/{result.model}",
      "",
      "## Summary",
      "",
      result.summary,
      "",
    ]

    if result.comments:
      lines.extend(["## Issues", ""])
      for comment in result.comments:
        severity = comment.severity.value.upper()
        location = f"{comment.file}"
        if comment.line:
          location += f":{comment.line}"

        lines.append(f"### [{severity}] {location}")
        lines.append("")
        lines.append(comment.message)
        if comment.suggestion:
          lines.append("")
          lines.append(f"**Suggestion:** {comment.suggestion}")
        lines.append("")
    else:
      lines.extend(["## Issues", "", "No issues found.", ""])

    return "\n".join(lines)


class GitHubFormatter(OutputFormatter):
  """GitHub Actions workflow command formatter for PR annotations."""

  def format(self, result: ReviewResult) -> str:
    lines = []
    for comment in result.comments:
      level = self._severity_to_level(comment.severity)
      location = f"file={comment.file}"
      if comment.line:
        location += f",line={comment.line}"
      message = comment.message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
      lines.append(f"::{level} {location}::{message}")
    return "\n".join(lines)

  def _severity_to_level(self, severity: Severity) -> str:
    if severity in (Severity.CRITICAL, Severity.HIGH):
      return "error"
    if severity == Severity.MEDIUM:
      return "warning"
    return "notice"


def get_formatter(format_type: str) -> OutputFormatter:
  """Get formatter by type name."""
  formatters = {
    "terminal": TerminalFormatter,
    "json": JsonFormatter,
    "markdown": MarkdownFormatter,
    "github": GitHubFormatter,
  }
  formatter_class = formatters.get(format_type)
  if not formatter_class:
    raise ValueError(f"Unknown format: {format_type}")
  return formatter_class()
