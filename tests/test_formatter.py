"""Tests for output formatters."""

import json

import pytest

from ebert.models import ReviewResult, ReviewComment, Severity
from ebert.output.formatter import JsonFormatter, MarkdownFormatter, get_formatter


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

  def test_unknown_formatter(self) -> None:
    with pytest.raises(ValueError, match="Unknown format"):
      get_formatter("unknown")
