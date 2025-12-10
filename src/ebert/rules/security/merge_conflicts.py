"""SEC003: Detection of unresolved merge conflicts."""

import re
from typing import Sequence

from ebert.models import FocusArea, Severity
from ebert.rules.base import RuleMatch
from ebert.rules.registry import register_rule


class MergeConflictRule:
  """Detects unresolved git merge conflict markers.

  Looks for:
  - <<<<<<< (conflict start)
  - ======= (conflict separator)
  - >>>>>>> (conflict end)

  These markers indicate the code has unresolved conflicts and
  should never be committed.
  """

  CONFLICT_START = re.compile(r"^<{7}\s")
  CONFLICT_SEPARATOR = re.compile(r"^={7}$")
  CONFLICT_END = re.compile(r"^>{7}\s")

  @property
  def id(self) -> str:
    return "SEC003"

  @property
  def name(self) -> str:
    return "merge-conflict"

  @property
  def focus_area(self) -> FocusArea:
    return FocusArea.SECURITY

  def check(self, file_path: str, content: str) -> Sequence[RuleMatch]:
    """Check for unresolved merge conflict markers."""
    matches: list[RuleMatch] = []

    for i, line in enumerate(content.split("\n"), start=1):
      if self.CONFLICT_START.match(line):
        matches.append(RuleMatch(
          line=i,
          severity=Severity.CRITICAL,
          message="Unresolved merge conflict marker (start)",
          suggestion="Resolve the merge conflict before committing",
        ))
      elif self.CONFLICT_SEPARATOR.match(line):
        matches.append(RuleMatch(
          line=i,
          severity=Severity.CRITICAL,
          message="Unresolved merge conflict marker (separator)",
          suggestion="Resolve the merge conflict before committing",
        ))
      elif self.CONFLICT_END.match(line):
        matches.append(RuleMatch(
          line=i,
          severity=Severity.CRITICAL,
          message="Unresolved merge conflict marker (end)",
          suggestion="Resolve the merge conflict before committing",
        ))

    return matches


def _create_merge_conflict() -> MergeConflictRule:
  return MergeConflictRule()


register_rule("SEC003", _create_merge_conflict)
