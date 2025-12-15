"""Tests for output formatters."""

import json

import pytest
from ebert.models import ReviewComment, ReviewResult, Severity
from ebert.output.formatter import (
  GitHubFormatter,
  JsonFormatter,
  MarkdownFormatter,
  get_formatter,
)


class TestJsonFormatter:
  def test_format_empty_result(self) -> None:
    result = ReviewResult(
      comments=[],
      summary="No issues",
      provider="test",
      model="test-model",
    )
    formatter = JsonFormatter()
    output = formatter.format(result)
    data = json.loads(output)

    assert data["summary"] == "No issues"
    assert data["provider"] == "test"
    assert data["model"] == "test-model"
    assert data["comments"] == []

  def test_format_with_comments(self, sample_review_result: ReviewResult) -> None:
    formatter = JsonFormatter()
    output = formatter.format(sample_review_result)
    data = json.loads(output)

    assert len(data["comments"]) == 1
    assert data["comments"][0]["file"] == "test.py"
    assert data["comments"][0]["severity"] == "low"


class TestMarkdownFormatter:
  def test_format_empty_result(self) -> None:
    result = ReviewResult(
      comments=[],
      summary="All good",
      provider="test",
      model="test-model",
    )
    formatter = MarkdownFormatter()
    output = formatter.format(result)

    assert "# Code Review" in output
    assert "All good" in output
    assert "No issues found" in output

  def test_format_with_comments(self, sample_review_result: ReviewResult) -> None:
    formatter = MarkdownFormatter()
    output = formatter.format(sample_review_result)

    assert "# Code Review" in output
    assert "[LOW]" in output
    assert "test.py" in output
    assert "Consider adding a docstring" in output


class TestGitHubFormatter:
  def test_format_empty_result(self) -> None:
    result = ReviewResult(
      comments=[], summary="No issues", provider="test", model="test-model"
    )
    formatter = GitHubFormatter()
    output = formatter.format(result)
    assert output == ""

  def test_format_high_severity_as_error(self) -> None:
    result = ReviewResult(
      comments=[ReviewComment(file="test.py", line=10, severity=Severity.HIGH, message="Bug")],
      summary="Issues", provider="test", model="test-model"
    )
    formatter = GitHubFormatter()
    output = formatter.format(result)
    assert output == "::error file=test.py,line=10::Bug"

  def test_format_medium_severity_as_warning(self) -> None:
    result = ReviewResult(
      comments=[ReviewComment(file="test.py", line=5, severity=Severity.MEDIUM, message="Smell")],
      summary="Issues", provider="test", model="test-model"
    )
    formatter = GitHubFormatter()
    output = formatter.format(result)
    assert output == "::warning file=test.py,line=5::Smell"

  def test_format_low_severity_as_notice(self) -> None:
    result = ReviewResult(
      comments=[ReviewComment(file="test.py", line=1, severity=Severity.LOW, message="Info")],
      summary="Issues", provider="test", model="test-model"
    )
    formatter = GitHubFormatter()
    output = formatter.format(result)
    assert output == "::notice file=test.py,line=1::Info"

  def test_format_encodes_special_chars(self) -> None:
    result = ReviewResult(
      comments=[ReviewComment(
        file="test.py", line=1, severity=Severity.HIGH, message="Error with %\nSee details."
      )],
      summary="Issues", provider="test", model="test-model"
    )
    formatter = GitHubFormatter()
    output = formatter.format(result)
    assert output == "::error file=test.py,line=1::Error with %25%0ASee details."


class TestGetFormatter:
  def test_get_terminal_formatter(self) -> None:
    formatter = get_formatter("terminal")
    assert formatter is not None

  def test_get_json_formatter(self) -> None:
    formatter = get_formatter("json")
    assert isinstance(formatter, JsonFormatter)

  def test_get_markdown_formatter(self) -> None:
    formatter = get_formatter("markdown")
    assert isinstance(formatter, MarkdownFormatter)

  def test_get_github_formatter(self) -> None:
    formatter = get_formatter("github")
    assert isinstance(formatter, GitHubFormatter)

  def test_unknown_formatter(self) -> None:
    with pytest.raises(ValueError, match="Unknown format"):
      get_formatter("unknown")
