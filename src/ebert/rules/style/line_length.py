"""STY001: Detection of overly long lines."""

from typing import Sequence

from ebert.models import FocusArea, Severity
from ebert.rules.base import RuleMatch
from ebert.rules.registry import register_rule


class LineLengthRule:
  """Detects lines exceeding recommended length limits.

  Default thresholds:
  - 120 characters: LOW severity
  - 150 characters: MEDIUM severity

  Long lines reduce readability and can cause horizontal
  scrolling in code reviews.
  """

  DEFAULT_WARNING_LENGTH = 120
  DEFAULT_ERROR_LENGTH = 150

  def __init__(
    self,
    warning_length: int = DEFAULT_WARNING_LENGTH,
    error_length: int = DEFAULT_ERROR_LENGTH,
  ):
    self._warning_length = warning_length
    self._error_length = error_length

  @property
  def id(self) -> str:
    return "STY001"

  @property
  def name(self) -> str:
    return "long-line"

  @property
  def focus_area(self) -> FocusArea:
    return FocusArea.STYLE

  def check(self, file_path: str, content: str) -> Sequence[RuleMatch]:
    """Check for long lines in content."""
    # Skip certain file types where long lines are common/acceptable
    if self._should_skip(file_path):
      return []

    matches: list[RuleMatch] = []

    for i, line in enumerate(content.split("\n"), start=1):
      length = len(line)

      if length > self._error_length:
        matches.append(RuleMatch(
          line=i,
          severity=Severity.MEDIUM,
          message=f"Line exceeds {self._error_length} characters ({length})",
          suggestion="Break this line for better readability",
        ))
      elif length > self._warning_length:
        matches.append(RuleMatch(
          line=i,
          severity=Severity.LOW,
          message=f"Line exceeds {self._warning_length} characters ({length})",
          suggestion=None,
        ))

    return matches

  def _should_skip(self, file_path: str) -> bool:
    """Check if file should be skipped."""
    skip_extensions = (
      ".md",    # Markdown often has long URLs
      ".json",  # JSON formatting is often on one line
      ".svg",   # SVG files have long paths
      ".lock",  # Lock files
    )
    return file_path.endswith(skip_extensions)


def _create_line_length() -> LineLengthRule:
  return LineLengthRule()


register_rule("STY001", _create_line_length)
