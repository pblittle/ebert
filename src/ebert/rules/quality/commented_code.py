"""QUA003: Detection of commented-out code."""

import re
from typing import Sequence

from ebert.models import FocusArea, Severity
from ebert.rules.base import RuleMatch
from ebert.rules.registry import register_rule


class CommentedCodeRule:
  """Detects blocks of commented-out code.

  Commented-out code should be removed rather than committed.
  It adds noise and can become stale quickly.
  """

  # Minimum consecutive commented lines to trigger
  MIN_CONSECUTIVE_LINES = 3

  # Patterns that suggest code rather than documentation
  CODE_PATTERNS = [
    re.compile(r"^\s*#\s*(?:def|class|if|for|while|return|import|from)\s"),  # Python
    re.compile(r"^\s*//\s*(?:function|const|let|var|if|for|while|return|import)\s"),  # JS
    re.compile(r"^\s*//\s*(?:func|type|var|const|if|for|return|import)\s"),  # Go
    re.compile(r"^\s*#\s*\w+\s*="),  # Assignment
    re.compile(r"^\s*//\s*\w+\s*="),  # Assignment
    re.compile(r"^\s*#\s*\w+\("),  # Function call
    re.compile(r"^\s*//\s*\w+\("),  # Function call
  ]

  @property
  def id(self) -> str:
    return "QUA003"

  @property
  def name(self) -> str:
    return "commented-code"

  @property
  def focus_area(self) -> FocusArea:
    return FocusArea.STYLE

  def check(self, file_path: str, content: str) -> Sequence[RuleMatch]:
    """Check for commented-out code blocks."""
    lines = content.split("\n")
    matches: list[RuleMatch] = []

    i = 0
    while i < len(lines):
      # Look for start of potential code comment block
      if self._looks_like_code_comment(lines[i]):
        block_start = i
        block_length = 1

        # Count consecutive commented code lines
        j = i + 1
        while j < len(lines) and self._is_comment_continuation(lines[j]):
          block_length += 1
          j += 1

        # Only flag if block is large enough
        if block_length >= self.MIN_CONSECUTIVE_LINES:
          matches.append(RuleMatch(
            line=block_start + 1,  # 1-indexed
            severity=Severity.LOW,
            message=f"Block of {block_length} commented-out lines",
            suggestion="Remove commented-out code or restore if needed",
          ))
          i = j  # Skip past the block
          continue

      i += 1

    return matches

  def _looks_like_code_comment(self, line: str) -> bool:
    """Check if line looks like commented-out code."""
    return any(pattern.search(line) for pattern in self.CODE_PATTERNS)

  def _is_comment_continuation(self, line: str) -> bool:
    """Check if line continues a comment block."""
    stripped = line.strip()
    # Check if it's a comment (not empty)
    if stripped.startswith("#") and len(stripped) > 1:
      return True
    if stripped.startswith("//") and len(stripped) > 2:
      return True
    return False


def _create_commented_code() -> CommentedCodeRule:
  return CommentedCodeRule()


register_rule("QUA003", _create_commented_code)
