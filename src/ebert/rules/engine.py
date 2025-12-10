"""Rule engine that composes and executes rules."""

import re

from ebert.models import ReviewComment, ReviewContext, ReviewResult, Severity
from ebert.rules.base import Rule
from ebert.rules.registry import RuleRegistry, get_rules_for_focus

# Pattern to parse diff hunk headers: @@ -start,count +start,count @@
_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _extract_content_with_line_map(
  diff_content: str,
) -> tuple[str, dict[int, int]]:
  """Extract content from diff format with line number mapping.

  For new files or file scanning, extracts the actual content with
  1:1 line mapping. For diffs, parses hunk headers to track original
  line numbers.

  Args:
    diff_content: Content in diff format or raw file content.

  Returns:
    Tuple of (extracted_content, line_map) where line_map maps
    1-indexed line numbers in extracted_content to original file
    line numbers.
  """
  lines: list[str] = []
  line_map: dict[int, int] = {}
  current_file_line = 1
  is_diff_format = False

  for line in diff_content.split("\n"):
    # Check for diff headers
    if line.startswith("---") or line.startswith("+++"):
      is_diff_format = True
      continue

    # Parse hunk header to get starting line number
    hunk_match = _HUNK_HEADER.match(line)
    if hunk_match:
      is_diff_format = True
      current_file_line = int(hunk_match.group(1))
      continue

    # Skip removed lines (don't increment file line counter)
    if line.startswith("-"):
      continue

    # Handle added lines
    if line.startswith("+"):
      extracted_line_num = len(lines) + 1
      lines.append(line[1:])
      line_map[extracted_line_num] = current_file_line
      current_file_line += 1
    else:
      # Context lines or raw content (non-diff format)
      extracted_line_num = len(lines) + 1
      lines.append(line)
      line_map[extracted_line_num] = current_file_line
      current_file_line += 1

  # For non-diff format, line numbers are 1:1
  if not is_diff_format:
    line_map = {i: i for i in range(1, len(lines) + 1)}

  return "\n".join(lines), line_map


class RuleEngine:
  """Orchestrates rule execution and result aggregation.

  This is the main entry point for deterministic review. It composes
  rules based on focus areas and produces a ReviewResult compatible
  with LLM provider output.

  Example:
    engine = RuleEngine()
    result = engine.review(context)
  """

  VERSION = "rules-v1"

  def __init__(self, rules: list[Rule] | None = None):
    """Initialize the rule engine.

    Args:
      rules: Optional list of rules to use. If None, rules are loaded
             from the registry based on the context's focus areas.
    """
    self._rules = rules

  def review(self, context: ReviewContext) -> ReviewResult:
    """Execute all applicable rules and return results.

    Args:
      context: Review context containing diff and settings.

    Returns:
      ReviewResult with comments from all rules.
    """
    # Lazy load rules if not provided
    if self._rules is None:
      RuleRegistry.load_all()
      self._rules = get_rules_for_focus(list(context.focus))

    all_comments: list[ReviewComment] = []

    for file_diff in context.diff.files:
      if file_diff.is_deleted:
        continue  # Skip deleted files

      content, line_map = _extract_content_with_line_map(file_diff.content)

      for rule in self._rules:
        matches = rule.check(file_diff.path, content)

        for match in matches:
          # Map extracted line number to original file line number
          original_line = None
          if match.line is not None:
            original_line = line_map.get(match.line, match.line)

          all_comments.append(ReviewComment(
            file=file_diff.path,
            line=original_line,
            severity=match.severity,
            message=f"[{rule.id}] {match.message}",
            suggestion=match.suggestion,
          ))

    # Respect max_comments limit
    comments = all_comments[:context.max_comments]

    # Generate summary
    summary = self._generate_summary(all_comments, context.max_comments)

    return ReviewResult(
      comments=comments,
      summary=summary,
      provider="deterministic",
      model=self.VERSION,
    )

  def _generate_summary(
    self,
    comments: list[ReviewComment],
    max_shown: int,
  ) -> str:
    """Generate a summary of the review.

    Args:
      comments: All comments found (before truncation).
      max_shown: Maximum comments that will be shown.

    Returns:
      Human-readable summary string.
    """
    if not comments:
      return "No issues found."

    # Count by severity
    by_severity: dict[str, int] = {}
    for comment in comments:
      sev = comment.severity.value
      by_severity[sev] = by_severity.get(sev, 0) + 1

    # Build summary with severity counts (iterate over enum for maintainability)
    parts = []
    for sev_enum in Severity:
      sev = sev_enum.value
      if sev in by_severity:
        parts.append(f"{by_severity[sev]} {sev}")

    summary = f"Found {len(comments)} issue{'s' if len(comments) != 1 else ''}"
    if parts:
      summary += f": {', '.join(parts)}"
    summary += "."

    if len(comments) > max_shown:
      summary += f" (showing first {max_shown})"

    return summary
