"""Tests for CLI engine integration."""

from unittest.mock import patch

from ebert.cli import app
from ebert.models import ReviewComment, ReviewResult, Severity
from typer.testing import CliRunner

runner = CliRunner()


def _make_result(severities: list[Severity]) -> ReviewResult:
  """Create a ReviewResult with comments of the given severities."""
  comments = [
    ReviewComment(file="test.py", line=i + 1, severity=sev, message=f"Issue {i}")
    for i, sev in enumerate(severities)
  ]
  return ReviewResult(
    comments=comments, summary="Test", provider="deterministic", model="rules-v1"
  )


class TestEngineValidation:
  def test_provider_implies_llm_engine(self) -> None:
    # --provider alone implies --engine llm (will fail at provider level, not validation)
    result = runner.invoke(app, ["--provider", "anthropic"])

    # Should NOT fail validation - provider implies llm engine
    assert "--provider is only valid with --engine llm" not in result.output
    assert "--engine llm requires --provider" not in result.output

  def test_provider_incompatible_with_explicit_deterministic(self) -> None:
    # --provider with explicit --engine deterministic should fail
    result = runner.invoke(app, ["--engine", "deterministic", "--provider", "anthropic"])

    assert result.exit_code == 1
    assert "--provider is only valid with --engine llm" in result.output

  def test_llm_engine_requires_provider(self) -> None:
    result = runner.invoke(app, ["--engine", "llm"])

    assert result.exit_code == 1
    assert "--engine llm requires --provider" in result.output

  def test_invalid_engine_rejected(self) -> None:
    result = runner.invoke(app, ["--engine", "invalid"])

    assert result.exit_code == 1
    assert "Invalid engine" in result.output

  def test_deterministic_engine_documented_in_help(self) -> None:
    # Help text should mention deterministic as default
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "deterministic" in result.output

  def test_valid_llm_engine_with_provider_accepted(self) -> None:
    # This will fail due to missing API key, but should pass validation
    result = runner.invoke(app, ["--engine", "llm", "--provider", "anthropic"])

    # Should fail with provider error, not validation error
    assert "--provider is only valid" not in result.output
    assert "--engine llm requires" not in result.output


class TestExitCode:
  @patch("ebert.cli.run_review")
  def test_exit_1_when_high_severity_with_flag(self, mock_review: patch) -> None:
    mock_review.return_value = _make_result([Severity.HIGH])
    result = runner.invoke(app, ["--exit-code"])
    assert result.exit_code == 1

  @patch("ebert.cli.run_review")
  def test_exit_1_when_critical_severity_with_flag(self, mock_review: patch) -> None:
    mock_review.return_value = _make_result([Severity.CRITICAL])
    result = runner.invoke(app, ["--exit-code"])
    assert result.exit_code == 1

  @patch("ebert.cli.run_review")
  def test_exit_0_when_no_severe_issues_with_flag(self, mock_review: patch) -> None:
    mock_review.return_value = _make_result([Severity.MEDIUM, Severity.LOW])
    result = runner.invoke(app, ["--exit-code"])
    assert result.exit_code == 0

  @patch("ebert.cli.run_review")
  def test_exit_0_without_flag_ignores_severity(self, mock_review: patch) -> None:
    mock_review.return_value = _make_result([Severity.CRITICAL])
    result = runner.invoke(app, [])
    assert result.exit_code == 0
