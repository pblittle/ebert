"""QUA001: Detection of debug statements."""

import re
from typing import Sequence

from ebert.models import FocusArea, Severity
from ebert.rules.base import RuleMatch
from ebert.rules.registry import register_rule


class DebugStatementRule:
  """Detects debug statements that should not be committed.

  Supports multiple languages:
  - Python: print(), breakpoint(), pdb
  - JavaScript/TypeScript: console.log/debug/warn/error, debugger
  - Go: fmt.Print*, log.Print*
  - Ruby: puts, p, pp, binding.pry
  """

  # Shared pattern for JS/TS files (DRY)
  _JS_TS_PATTERN = re.compile(
    r"^\s*(?:console\.(?:log|debug|warn|error|trace|info)\s*\(|debugger\b)"
  )

  PATTERNS: dict[str, re.Pattern[str]] = {
    ".py": re.compile(
      r"^\s*(?:print\s*\(|breakpoint\s*\(|import\s+pdb|pdb\.set_trace\s*\()"
    ),
    ".js": _JS_TS_PATTERN,
    ".ts": _JS_TS_PATTERN,
    ".tsx": _JS_TS_PATTERN,
    ".jsx": _JS_TS_PATTERN,
    ".go": re.compile(
      r"^\s*(?:fmt\.Print|log\.Print)"
    ),
    ".rb": re.compile(
      r"^\s*(?:puts\s|p\s+[^=]|pp\s|binding\.pry)"
    ),
  }

  @property
  def id(self) -> str:
    return "QUA001"

  @property
  def name(self) -> str:
    return "debug-statement"

  @property
  def focus_area(self) -> FocusArea:
    return FocusArea.BUGS

  def check(self, file_path: str, content: str) -> Sequence[RuleMatch]:
    """Check for debug statements in content."""
    pattern = self._get_pattern(file_path)
    if pattern is None:
      return []

    matches: list[RuleMatch] = []

    for i, line in enumerate(content.split("\n"), start=1):
      # Skip comments
      stripped = line.strip()
      if stripped.startswith("#") or stripped.startswith("//"):
        continue

      if pattern.search(line):
        matches.append(RuleMatch(
          line=i,
          severity=Severity.MEDIUM,
          message="Debug statement found",
          suggestion="Remove debug statements before committing",
        ))

    return matches

  def _get_pattern(self, file_path: str) -> re.Pattern[str] | None:
    """Get the appropriate pattern for the file extension."""
    for ext, pattern in self.PATTERNS.items():
      if file_path.endswith(ext):
        return pattern
    return None


def _create_debug_statement() -> DebugStatementRule:
  return DebugStatementRule()


register_rule("QUA001", _create_debug_statement)
