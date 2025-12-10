"""Tests for CLI engine integration."""

from ebert.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestEngineValidation:
  def test_provider_requires_llm_engine(self) -> None:
    result = runner.invoke(app, ["--provider", "anthropic"])

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

  def test_deterministic_is_default(self) -> None:
    # This should not require --provider
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "deterministic (default" in result.output

  def test_valid_llm_engine_with_provider_accepted(self) -> None:
    # This will fail due to missing API key, but should pass validation
    result = runner.invoke(app, ["--engine", "llm", "--provider", "anthropic"])

    # Should fail with provider error, not validation error
    assert "--provider is only valid" not in result.output
    assert "--engine llm requires" not in result.output
