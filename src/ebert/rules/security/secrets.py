"""SEC001: Detection of hardcoded secrets."""

import re
from typing import Sequence

from ebert.models import FocusArea, Severity
from ebert.rules.base import RuleMatch
from ebert.rules.registry import register_rule


class HardcodedSecretRule:
  """Detects common patterns of hardcoded secrets.

  Looks for patterns like:
  - api_key = "sk-..."
  - password: "secret123"
  - token = "ghp_..."
  """

  # Pattern to match key-value secret assignments
  ASSIGNMENT_PATTERN = re.compile(
    r"""(?ix)                           # Case insensitive, verbose
    (?:api[_-]?key|apikey|secret|password|passwd|pwd|token|auth[_-]?token)
    \s*[:=]\s*                          # Assignment operator
    ['"][^'"]{8,}['"]                   # Quoted value, 8+ chars
    """,
    re.VERBOSE | re.IGNORECASE,
  )

  # Pattern to match known secret prefixes
  PREFIX_PATTERN = re.compile(
    r"""(?x)
    ['"]
    (?:
      sk-[a-zA-Z0-9]{20,}               # OpenAI API key
      |pk-[a-zA-Z0-9]{20,}              # Public key prefix
      |ghp_[a-zA-Z0-9]{36,}             # GitHub personal access token
      |gho_[a-zA-Z0-9]{36,}             # GitHub OAuth token
      |xox[baprs]-[a-zA-Z0-9-]{10,}     # Slack tokens
    )
    ['"]
    """,
    re.VERBOSE,
  )

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
    """Check for hardcoded secrets in content."""
    # Skip likely test/example files
    if self._is_test_or_example(file_path):
      return []

    matches: list[RuleMatch] = []

    for i, line in enumerate(content.split("\n"), start=1):
      # Skip comments
      stripped = line.strip()
      if stripped.startswith("#") or stripped.startswith("//"):
        continue

      if self.ASSIGNMENT_PATTERN.search(line):
        matches.append(RuleMatch(
          line=i,
          severity=Severity.CRITICAL,
          message="Potential hardcoded secret detected",
          suggestion="Use environment variables or a secrets manager",
        ))
      elif self.PREFIX_PATTERN.search(line):
        matches.append(RuleMatch(
          line=i,
          severity=Severity.CRITICAL,
          message="API key or token detected in code",
          suggestion="Move to environment variable or .env file (not committed)",
        ))

    return matches

  def _is_test_or_example(self, file_path: str) -> bool:
    """Check if file is likely a test or example."""
    lower_path = file_path.lower()
    return any(
      pattern in lower_path
      for pattern in ["test", "example", "mock", "fixture", "fake"]
    )


def _create_hardcoded_secret() -> HardcodedSecretRule:
  return HardcodedSecretRule()


register_rule("SEC001", _create_hardcoded_secret)
