"""Tests for security rules."""

import pytest
from ebert.models import FocusArea, Severity
from ebert.rules.security.credentials import CredentialPatternRule
from ebert.rules.security.merge_conflicts import MergeConflictRule
from ebert.rules.security.secrets import HardcodedSecretRule


class TestHardcodedSecretRule:
  @pytest.fixture
  def rule(self) -> HardcodedSecretRule:
    return HardcodedSecretRule()

  def test_properties(self, rule: HardcodedSecretRule) -> None:
    assert rule.id == "SEC001"
    assert rule.name == "hardcoded-secret"
    assert rule.focus_area == FocusArea.SECURITY

  def test_detects_api_key_assignment(self, rule: HardcodedSecretRule) -> None:
    content = 'api_key = "sk-1234567890abcdefghij"'
    matches = rule.check("config.py", content)

    # May match both ASSIGNMENT_PATTERN and PREFIX_PATTERN
    assert len(matches) >= 1
    assert all(m.severity == Severity.CRITICAL for m in matches)
    assert all(m.line == 1 for m in matches)

  def test_detects_password_pattern(self, rule: HardcodedSecretRule) -> None:
    content = 'password: "supersecret123"'
    matches = rule.check("config.yaml", content)

    assert len(matches) == 1
    assert "secret" in matches[0].message.lower()

  def test_detects_github_token(self, rule: HardcodedSecretRule) -> None:
    content = 'token = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"'
    matches = rule.check("deploy.py", content)

    # May match both ASSIGNMENT_PATTERN and PREFIX_PATTERN
    assert len(matches) >= 1
    assert all(m.severity == Severity.CRITICAL for m in matches)

  def test_detects_slack_token(self, rule: HardcodedSecretRule) -> None:
    content = 'SLACK_TOKEN = "xoxb-1234567890-abcdefghij"'
    matches = rule.check("bot.py", content)

    assert len(matches) >= 1

  def test_ignores_environment_variable_usage(self, rule: HardcodedSecretRule) -> None:
    content = 'api_key = os.environ.get("API_KEY")'
    matches = rule.check("config.py", content)

    assert len(matches) == 0

  def test_ignores_short_values(self, rule: HardcodedSecretRule) -> None:
    content = 'api_key = "short"'  # Less than 8 chars
    matches = rule.check("config.py", content)

    assert len(matches) == 0

  def test_ignores_test_files(self, rule: HardcodedSecretRule) -> None:
    content = 'api_key = "sk-1234567890abcdefghij"'
    matches = rule.check("test_config.py", content)

    assert len(matches) == 0

  def test_ignores_comments(self, rule: HardcodedSecretRule) -> None:
    content = '# api_key = "sk-1234567890abcdefghij"'
    matches = rule.check("config.py", content)

    assert len(matches) == 0


class TestCredentialPatternRule:
  @pytest.fixture
  def rule(self) -> CredentialPatternRule:
    return CredentialPatternRule()

  def test_properties(self, rule: CredentialPatternRule) -> None:
    assert rule.id == "SEC002"
    assert rule.name == "credential-pattern"
    assert rule.focus_area == FocusArea.SECURITY

  def test_detects_aws_access_key(self, rule: CredentialPatternRule) -> None:
    content = 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"'
    matches = rule.check("config.py", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.CRITICAL
    assert "AWS" in matches[0].message

  def test_detects_aws_secret_key(self, rule: CredentialPatternRule) -> None:
    content = 'aws_secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'
    matches = rule.check("config.py", content)

    assert len(matches) == 1

  def test_detects_private_key_block(self, rule: CredentialPatternRule) -> None:
    content = '-----BEGIN RSA PRIVATE KEY-----'
    matches = rule.check("key.pem", content)

    assert len(matches) == 1
    assert "private key" in matches[0].message.lower()

  def test_detects_openssh_private_key(self, rule: CredentialPatternRule) -> None:
    content = '-----BEGIN OPENSSH PRIVATE KEY-----'
    matches = rule.check("id_rsa", content)

    assert len(matches) == 1

  def test_detects_connection_string(self, rule: CredentialPatternRule) -> None:
    content = 'DATABASE_URL = "postgres://user:realpassword@host.com/db"'
    matches = rule.check("config.py", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.HIGH

  def test_ignores_placeholder_connection_string(self, rule: CredentialPatternRule) -> None:
    content = 'DATABASE_URL = "postgres://user:your_password@localhost/db"'
    matches = rule.check("config.py", content)

    # Should be ignored due to placeholder
    conn_matches = [m for m in matches if "connection string" in m.message.lower()]
    assert len(conn_matches) == 0

  def test_detects_gcp_service_account(self, rule: CredentialPatternRule) -> None:
    content = '{"type": "service_account", "project_id": "my-project"}'
    matches = rule.check("service-account.json", content)

    assert len(matches) == 1
    assert "GCP" in matches[0].message

  def test_ignores_test_files(self, rule: CredentialPatternRule) -> None:
    content = 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"'
    matches = rule.check("test_aws.py", content)

    assert len(matches) == 0


class TestMergeConflictRule:
  @pytest.fixture
  def rule(self) -> MergeConflictRule:
    return MergeConflictRule()

  def test_properties(self, rule: MergeConflictRule) -> None:
    assert rule.id == "SEC003"
    assert rule.name == "merge-conflict"
    assert rule.focus_area == FocusArea.SECURITY

  def test_detects_conflict_start(self, rule: MergeConflictRule) -> None:
    content = '<<<<<<< HEAD'
    matches = rule.check("file.py", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.CRITICAL
    assert "start" in matches[0].message.lower()

  def test_detects_conflict_separator(self, rule: MergeConflictRule) -> None:
    content = '======='
    matches = rule.check("file.py", content)

    assert len(matches) == 1
    assert "separator" in matches[0].message.lower()

  def test_detects_conflict_end(self, rule: MergeConflictRule) -> None:
    content = '>>>>>>> feature-branch'
    matches = rule.check("file.py", content)

    assert len(matches) == 1
    assert "end" in matches[0].message.lower()

  def test_detects_full_conflict_block(self, rule: MergeConflictRule) -> None:
    content = """def foo():
<<<<<<< HEAD
    return 1
=======
    return 2
>>>>>>> feature
"""
    matches = rule.check("file.py", content)

    assert len(matches) == 3  # start, separator, end

  def test_ignores_similar_strings(self, rule: MergeConflictRule) -> None:
    content = 'message = "Use <<< for input"'
    matches = rule.check("file.py", content)

    assert len(matches) == 0

  def test_ignores_equals_in_code(self, rule: MergeConflictRule) -> None:
    content = 'x = y == z'
    matches = rule.check("file.py", content)

    assert len(matches) == 0
