"""SEC002: Detection of credential patterns."""

import re
from typing import Sequence

from ebert.models import FocusArea, Severity
from ebert.rules.base import RuleMatch
from ebert.rules.registry import register_rule


class CredentialPatternRule:
  """Detects cloud provider credentials and private keys.

  Looks for patterns like:
  - AWS access keys (AKIA...)
  - AWS secret keys
  - Private key blocks (-----BEGIN ... PRIVATE KEY-----)
  - Connection strings with credentials
  """

  # AWS access key ID pattern
  AWS_ACCESS_KEY = re.compile(r"(?<![A-Z0-9])(AKIA[0-9A-Z]{16})(?![A-Z0-9])")

  # AWS secret access key pattern (40 char base64-like)
  AWS_SECRET_KEY = re.compile(
    r"""(?ix)
    (?:aws[_-]?secret|secret[_-]?key)
    \s*[:=]\s*
    ['"]?[A-Za-z0-9/+=]{40}['"]?
    """,
    re.VERBOSE | re.IGNORECASE,
  )

  # Private key block
  PRIVATE_KEY = re.compile(
    r"-----BEGIN\s+(?:RSA\s+)?(?:EC\s+)?(?:DSA\s+)?(?:OPENSSH\s+)?PRIVATE\s+KEY-----"
  )

  # Connection string with password
  CONNECTION_STRING = re.compile(
    r"""(?ix)
    (?:
      (?:mysql|postgres|postgresql|mongodb|redis)://
      [^:]+:[^@]+@                          # user:pass@host
      |
      (?:password|pwd)=[^&\s;]+             # password=... in query string
    )
    """,
    re.VERBOSE | re.IGNORECASE,
  )

  # Google Cloud service account key indicator
  GCP_SERVICE_ACCOUNT = re.compile(
    r'"type"\s*:\s*"service_account"'
  )

  @property
  def id(self) -> str:
    return "SEC002"

  @property
  def name(self) -> str:
    return "credential-pattern"

  @property
  def focus_area(self) -> FocusArea:
    return FocusArea.SECURITY

  def check(self, file_path: str, content: str) -> Sequence[RuleMatch]:
    """Check for credential patterns in content."""
    # Skip likely test files
    if self._is_test_file(file_path):
      return []

    matches: list[RuleMatch] = []

    for i, line in enumerate(content.split("\n"), start=1):
      if self.AWS_ACCESS_KEY.search(line):
        matches.append(RuleMatch(
          line=i,
          severity=Severity.CRITICAL,
          message="AWS access key ID detected",
          suggestion="Use IAM roles or environment variables instead",
        ))
      elif self.AWS_SECRET_KEY.search(line):
        matches.append(RuleMatch(
          line=i,
          severity=Severity.CRITICAL,
          message="Potential AWS secret key detected",
          suggestion="Use IAM roles or AWS Secrets Manager",
        ))
      elif self.PRIVATE_KEY.search(line):
        matches.append(RuleMatch(
          line=i,
          severity=Severity.CRITICAL,
          message="Private key detected in code",
          suggestion="Store private keys in secure key management system",
        ))
      elif self.CONNECTION_STRING.search(line):
        # Skip if it looks like a placeholder
        if not self._is_placeholder(line):
          matches.append(RuleMatch(
            line=i,
            severity=Severity.HIGH,
            message="Connection string with credentials detected",
            suggestion="Use environment variables for connection strings",
          ))

    # Check for GCP service account JSON (file-level check)
    if self.GCP_SERVICE_ACCOUNT.search(content):
      matches.append(RuleMatch(
        line=None,
        severity=Severity.CRITICAL,
        message="GCP service account key file detected",
        suggestion="Use Workload Identity or store in Secret Manager",
      ))

    return matches

  def _is_test_file(self, file_path: str) -> bool:
    """Check if file is a test file."""
    lower_path = file_path.lower()
    return "test" in lower_path or "spec" in lower_path

  def _is_placeholder(self, line: str) -> bool:
    """Check if the line contains placeholder values."""
    placeholders = [
      "example", "placeholder", "your_", "xxx", "changeme",
      "<password>", "${", "{{", "localhost",
    ]
    lower_line = line.lower()
    return any(p in lower_line for p in placeholders)


def _create_credential_pattern() -> CredentialPatternRule:
  return CredentialPatternRule()


register_rule("SEC002", _create_credential_pattern)
