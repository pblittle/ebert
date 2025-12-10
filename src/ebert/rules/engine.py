"""Rule engine that composes and executes rules."""

from ebert.models import ReviewComment, ReviewContext, ReviewResult
from ebert.rules.base import Rule
from ebert.rules.registry import RuleRegistry, get_rules_for_focus


def _extract_content_from_diff(diff_content: str) -> str:
  """Extract raw file content from diff format.

  For new files or file scanning, extracts the actual content.
  For modifications, extracts added lines for analysis.

  Args:
    diff_content: Content in diff format or raw file content.

  Returns:
    Extracted content suitable for rule analysis.
  """
  lines = []
  for line in diff_content.split("\n"):
    # Skip diff headers
    if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
      continue
    # Skip removed lines
    if line.startswith("-"):
      continue
    # Handle added lines: extract content after the +
    if line.startswith("+"):
      lines.append(line[1:])
    else:
      # Context lines (unchanged) or raw content
      lines.append(line)
  return "\n".join(lines)


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

      content = _extract_content_from_diff(file_diff.content)

      for rule in self._rules:
        matches = rule.check(file_diff.path, content)

        for match in matches:
          all_comments.append(ReviewComment(
            file=file_diff.path,
            line=match.line,
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

    # Build summary with severity counts
    parts = []
    for sev in ["critical", "high", "medium", "low", "info"]:
      if sev in by_severity:
        parts.append(f"{by_severity[sev]} {sev}")

    summary = f"Found {len(comments)} issue{'s' if len(comments) != 1 else ''}"
    if parts:
      summary += f": {', '.join(parts)}"
    summary += "."

    if len(comments) > max_shown:
      summary += f" (showing first {max_shown})"

    return summary
