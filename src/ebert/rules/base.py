"""Rule abstractions for deterministic review."""

from dataclasses import dataclass
from typing import Protocol, Sequence

from ebert.models import FocusArea, Severity


@dataclass(frozen=True)
class RuleMatch:
  """A single rule match found during analysis.

  This is an intermediate representation that gets converted to
  ReviewComment by the RuleEngine. Keeping it separate allows rules
  to remain decoupled from the output model.
  """

  line: int | None
  severity: Severity
  message: str
  suggestion: str | None = None


class Rule(Protocol):
  """Protocol for deterministic review rules.

  Each rule is responsible for detecting a single category of issues.
  Rules are stateless and operate on file content only.

  Example:
    class MyRule:
      @property
      def id(self) -> str:
        return "SEC001"

      @property
      def name(self) -> str:
        return "hardcoded-secret"

      @property
      def focus_area(self) -> FocusArea:
        return FocusArea.SECURITY

      def check(self, file_path: str, content: str) -> Sequence[RuleMatch]:
        # Analyze content, return matches
        return []
  """

  @property
  def id(self) -> str:
    """Unique identifier for this rule (e.g., 'SEC001')."""
    ...

  @property
  def name(self) -> str:
    """Human-readable rule name (e.g., 'hardcoded-secret')."""
    ...

  @property
  def focus_area(self) -> FocusArea:
    """The focus area this rule belongs to."""
    ...

  def check(self, file_path: str, content: str) -> Sequence[RuleMatch]:
    """Check content for issues.

    Args:
      file_path: Relative path to file (for file-type detection).
      content: Raw file content (not diff format).

    Returns:
      Sequence of RuleMatch objects. Empty if no issues found.
    """
    ...
