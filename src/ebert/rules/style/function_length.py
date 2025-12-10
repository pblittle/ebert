"""STY002: Detection of overly long functions."""

import os
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
  # JS/TS pattern: function declarations, arrow functions, class methods, object methods
  _JS_FUNC_PATTERN = (
    r"^\s*(?:async\s+)?(?:"
    r"function\s+(\w+)|"  # function name()
    r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>|"  # const name = () =>
    r"(\w+)\s*\([^)]*\)\s*\{"  # method() { - class methods and object methods
    r")"
  )
  # Java pattern: modifiers + return type + name()
  # Return type can include generics (List<String>) or arrays (int[])
  _JAVA_FUNC_PATTERN = (
    r"^\s*(?:public|private|protected)?\s*"
    r"(?:static\s+)?(?:[\w.<>\[\]]+\s+)?(\w+)\s*\([^)]*\)\s*\{?"
  )

  FUNCTION_PATTERNS: dict[str, re.Pattern[str]] = {
    ".py": re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\("),
    ".js": re.compile(_JS_FUNC_PATTERN),
    ".ts": re.compile(_JS_FUNC_PATTERN),
    ".go": re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?(\w+)\s*\("),
    ".rb": re.compile(r"^\s*def\s+(\w+)"),
    ".java": re.compile(_JAVA_FUNC_PATTERN),
  }

  # Extensions that use brace-based syntax
  _BRACE_LANGUAGES = frozenset([".js", ".ts", ".go", ".java"])

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
    _, ext = os.path.splitext(file_path)
    return self.FUNCTION_PATTERNS.get(ext)

  def _measure_function(self, lines: list[str], start: int, file_path: str) -> int:
    """Measure the length of a function starting at the given line."""
    _, ext = os.path.splitext(file_path)

    # Special handling for Python (indentation-based)
    if ext == ".py":
      return self._measure_python_function(lines, start)

    # Special handling for Ruby (def/end blocks)
    if ext == ".rb":
      return self._measure_ruby_function(lines, start)

    # Check if this is a brace-based language
    if ext not in self._BRACE_LANGUAGES:
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

    # No brace found (e.g., single-line arrow function: const fn = () => 1;)
    if not started:
      return 1

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

  # Ruby block keywords that pair with 'end'
  _RUBY_BLOCK_KEYWORDS = re.compile(
    r"^(?:def|class|module|if|unless|case|while|until|for|begin|do)\b"
  )

  def _measure_ruby_function(self, lines: list[str], start: int) -> int:
    """Measure Ruby function length using def/end blocks."""
    if start >= len(lines):
      return 1

    # Count all block keywords that pair with 'end'
    depth = 1  # Start at 1 for the opening def

    for i in range(start + 1, len(lines)):
      line = lines[i].strip()

      # Check for block-starting keywords (increases depth)
      if self._RUBY_BLOCK_KEYWORDS.match(line):
        depth += 1

      # Check for end keyword (decreases depth)
      if re.match(r"end\b", line):
        depth -= 1
        if depth == 0:
          return i - start + 1

    return len(lines) - start


def _create_function_length() -> FunctionLengthRule:
  return FunctionLengthRule()


register_rule("STY002", _create_function_length)
