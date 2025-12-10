"""QUA002: Detection of TODO/FIXME comments."""

import re
from typing import Sequence

from ebert.models import FocusArea, Severity
from ebert.rules.base import RuleMatch
from ebert.rules.registry import register_rule


class TodoCommentRule:
  """Detects TODO, FIXME, HACK, and XXX comments.

  These comments indicate incomplete or problematic code that
  should be addressed before or after merging.
  """

  # Pattern to match TODO-style comments
  PATTERN = re.compile(
    r"(?:^|\s)(?:#|//|/\*|\*|<!--|--)\s*"  # Comment prefix
    r"(TODO|FIXME|HACK|XXX|BUG|OPTIMIZE)"  # Keyword
    r"[\s:(\[]",  # Separator
    re.IGNORECASE,
  )

  # Severity mapping based on keyword
  SEVERITY_MAP = {
    "TODO": Severity.INFO,
    "FIXME": Severity.MEDIUM,
    "HACK": Severity.MEDIUM,
    "XXX": Severity.MEDIUM,
    "BUG": Severity.HIGH,
    "OPTIMIZE": Severity.LOW,
  }

  @property
  def id(self) -> str:
    return "QUA002"

  @property
  def name(self) -> str:
    return "todo-comment"

  @property
  def focus_area(self) -> FocusArea:
    return FocusArea.BUGS

  def check(self, file_path: str, content: str) -> Sequence[RuleMatch]:
    """Check for TODO-style comments in content."""
    matches: list[RuleMatch] = []

    for i, line in enumerate(content.split("\n"), start=1):
      match = self.PATTERN.search(line)
      if match:
        keyword = match.group(1).upper()
        severity = self.SEVERITY_MAP.get(keyword, Severity.INFO)

        matches.append(RuleMatch(
          line=i,
          severity=severity,
          message=f"{keyword} comment found",
          suggestion=f"Address the {keyword} before merging or create a tracking issue",
        ))

    return matches


def _create_todo_comment() -> TodoCommentRule:
  return TodoCommentRule()


register_rule("QUA002", _create_todo_comment)
