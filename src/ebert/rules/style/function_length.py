"""STY002: Detection of overly long functions."""

import re
from typing import Sequence

from ebert.models import FocusArea, Severity
from ebert.rules.base import RuleMatch
from ebert.rules.registry import register_rule


class FunctionLengthRule:
  """Detects functions that exceed recommended length.

  Long functions are harder to understand, test, and maintain.
  Consider breaking them into smaller, focused functions.

  Default threshold: 50 lines
  """

  DEFAULT_MAX_LINES = 50

  # Patterns to detect function starts
  # JS/TS pattern: function name() or const/let/var name = () =>
  _JS_FUNC_PATTERN = (
    r"^\s*(?:async\s+)?(?:function\s+(\w+)|"
    r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>)"
  )
  # Java pattern: modifiers + return type + name()
  # Return type can include generics (List<String>) or arrays (int[])
  _JAVA_FUNC_PATTERN = (
    r"^\s*(?:public|private|protected)?\s*"
    r"(?:static\s+)?(?:[\w.<>\[\]]+\s+)?(\w+)\s*\([^)]*\)\s*\{?"
  )

  FUNCTION_PATTERNS: dict[str, re.Pattern[str]] = {
    ".py": re.compile(r"^\s*(async\s+)?def\s+(\w+)\s*\("),
    ".js": re.compile(_JS_FUNC_PATTERN),
    ".ts": re.compile(_JS_FUNC_PATTERN),
    ".go": re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?(\w+)\s*\("),
    ".rb": re.compile(r"^\s*def\s+(\w+)"),
    ".java": re.compile(_JAVA_FUNC_PATTERN),
  }

  # Patterns to detect function/block ends
  END_PATTERNS: dict[str, re.Pattern[str]] = {
    ".py": re.compile(r"^(?!\s)"),  # Python: unindented line (dedent)
    ".js": re.compile(r"^\s*\}"),
    ".ts": re.compile(r"^\s*\}"),
    ".go": re.compile(r"^\s*\}"),
    ".rb": re.compile(r"^\s*end\b"),
    ".java": re.compile(r"^\s*\}"),
  }

  def __init__(self, max_lines: int = DEFAULT_MAX_LINES):
    self._max_lines = max_lines

  @property
  def id(self) -> str:
    return "STY002"

  @property
  def name(self) -> str:
    return "long-function"

  @property
  def focus_area(self) -> FocusArea:
    return FocusArea.STYLE

  def check(self, file_path: str, content: str) -> Sequence[RuleMatch]:
    """Check for long functions in content."""
    func_pattern = self._get_function_pattern(file_path)
    if func_pattern is None:
      return []

    matches: list[RuleMatch] = []
    lines = content.split("\n")

    i = 0
    while i < len(lines):
      match = func_pattern.search(lines[i])
      if match:
        # Extract function name from first non-None group
        func_name = next((g for g in match.groups() if g), "function")
        func_start = i
        func_length = self._measure_function(lines, i, file_path)

        if func_length > self._max_lines:
          matches.append(RuleMatch(
            line=func_start + 1,  # 1-indexed
            severity=Severity.MEDIUM,
            message=f"Function '{func_name}' is {func_length} lines (max {self._max_lines})",
            suggestion="Consider breaking into smaller functions",
          ))
          i += func_length  # Skip past this function
          continue

      i += 1

    return matches

  def _get_function_pattern(self, file_path: str) -> re.Pattern[str] | None:
    """Get function pattern for file extension."""
    for ext, pattern in self.FUNCTION_PATTERNS.items():
      if file_path.endswith(ext):
        return pattern
    return None

  def _measure_function(self, lines: list[str], start: int, file_path: str) -> int:
    """Measure the length of a function starting at the given line."""
    # Special handling for Python (indentation-based)
    if file_path.endswith(".py"):
      return self._measure_python_function(lines, start)

    # Special handling for Ruby (def/end blocks)
    if file_path.endswith(".rb"):
      return self._measure_ruby_function(lines, start)

    # Brace-based languages
    end_pattern = None
    for ext, pattern in self.END_PATTERNS.items():
      if file_path.endswith(ext):
        end_pattern = pattern
        break

    if end_pattern is None:
      return 1  # Can't measure, assume single line

    # Count braces for proper nesting
    brace_count = 0
    started = False

    for i in range(start, len(lines)):
      line = lines[i]

      # Function body starts when we see an opening brace
      if not started and "{" in line:
        started = True

      if started:
        brace_count += line.count("{") - line.count("}")
        # Function ends when brace count returns to 0 or less
        if brace_count <= 0:
          return i - start + 1

    return len(lines) - start

  def _measure_python_function(self, lines: list[str], start: int) -> int:
    """Measure Python function length using indentation."""
    if start >= len(lines):
      return 1

    # Get the indentation of the def line
    def_line = lines[start]
    base_indent = len(def_line) - len(def_line.lstrip())

    # Find where the function ends (next line at same or less indentation)
    for i in range(start + 1, len(lines)):
      line = lines[i]

      # Skip empty lines and comments
      stripped = line.strip()
      if not stripped or stripped.startswith("#"):
        continue

      current_indent = len(line) - len(line.lstrip())
      if current_indent <= base_indent:
        return i - start

    return len(lines) - start

  def _measure_ruby_function(self, lines: list[str], start: int) -> int:
    """Measure Ruby function length using def/end blocks."""
    if start >= len(lines):
      return 1

    # Count nested def/end blocks
    depth = 1  # Start at 1 for the opening def

    for i in range(start + 1, len(lines)):
      line = lines[i].strip()

      # Check for nested def (increases depth)
      if re.match(r"^def\s+\w+", line):
        depth += 1

      # Check for end keyword (decreases depth)
      if line == "end" or line.startswith("end "):
        depth -= 1
        if depth == 0:
          return i - start + 1

    return len(lines) - start


def _create_function_length() -> FunctionLengthRule:
  return FunctionLengthRule()


register_rule("STY002", _create_function_length)
