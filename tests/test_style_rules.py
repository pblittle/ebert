"""Tests for style rules."""

import pytest
from ebert.models import FocusArea, Severity
from ebert.rules.style.function_length import FunctionLengthRule
from ebert.rules.style.line_length import LineLengthRule


class TestLineLengthRule:
  @pytest.fixture
  def rule(self) -> LineLengthRule:
    return LineLengthRule()

  def test_properties(self, rule: LineLengthRule) -> None:
    assert rule.id == "STY001"
    assert rule.name == "long-line"
    assert rule.focus_area == FocusArea.STYLE

  def test_detects_warning_length(self, rule: LineLengthRule) -> None:
    # 125 characters
    content = "x" * 125
    matches = rule.check("test.py", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.LOW
    assert "125" in matches[0].message

  def test_detects_error_length(self, rule: LineLengthRule) -> None:
    # 155 characters
    content = "x" * 155
    matches = rule.check("test.py", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.MEDIUM
    assert "155" in matches[0].message

  def test_ignores_acceptable_length(self, rule: LineLengthRule) -> None:
    content = "x" * 100
    matches = rule.check("test.py", content)

    assert len(matches) == 0

  def test_skips_markdown_files(self, rule: LineLengthRule) -> None:
    content = "x" * 200
    matches = rule.check("README.md", content)

    assert len(matches) == 0

  def test_skips_json_files(self, rule: LineLengthRule) -> None:
    content = "x" * 200
    matches = rule.check("package.json", content)

    assert len(matches) == 0

  def test_skips_lock_files(self, rule: LineLengthRule) -> None:
    content = "x" * 200
    matches = rule.check("poetry.lock", content)

    assert len(matches) == 0

  def test_custom_thresholds(self) -> None:
    rule = LineLengthRule(warning_length=80, error_length=100)

    content = "x" * 90
    matches = rule.check("test.py", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.LOW

  def test_multiple_long_lines(self, rule: LineLengthRule) -> None:
    content = "x" * 125 + "\n" + "y" * 160 + "\nshort line"
    matches = rule.check("test.py", content)

    assert len(matches) == 2


class TestFunctionLengthRule:
  @pytest.fixture
  def rule(self) -> FunctionLengthRule:
    return FunctionLengthRule(max_lines=5)  # Low threshold for testing

  def test_properties(self, rule: FunctionLengthRule) -> None:
    assert rule.id == "STY002"
    assert rule.name == "long-function"
    assert rule.focus_area == FocusArea.STYLE

  def test_detects_long_python_function(self, rule: FunctionLengthRule) -> None:
    content = """def long_function():
    line1 = 1
    line2 = 2
    line3 = 3
    line4 = 4
    line5 = 5
    line6 = 6
    return line6

def next_func():
    pass"""
    matches = rule.check("test.py", content)

    assert len(matches) == 1
    assert "long_function" in matches[0].message
    assert matches[0].severity == Severity.MEDIUM

  def test_ignores_short_python_function(self, rule: FunctionLengthRule) -> None:
    content = """def short_function():
    return 1"""
    matches = rule.check("test.py", content)

    assert len(matches) == 0

  def test_detects_long_js_function(self, rule: FunctionLengthRule) -> None:
    content = """function longFunction() {
  const a = 1;
  const b = 2;
  const c = 3;
  const d = 4;
  const e = 5;
  return e;
}"""
    matches = rule.check("test.js", content)

    assert len(matches) == 1

  def test_detects_arrow_function(self, rule: FunctionLengthRule) -> None:
    content = """const longFunc = () => {
  const a = 1;
  const b = 2;
  const c = 3;
  const d = 4;
  const e = 5;
  return e;
};"""
    matches = rule.check("test.js", content)

    assert len(matches) == 1

  def test_detects_long_go_function(self, rule: FunctionLengthRule) -> None:
    content = """func longFunction() int {
    a := 1
    b := 2
    c := 3
    d := 4
    e := 5
    return e
}"""
    matches = rule.check("main.go", content)

    assert len(matches) == 1

  def test_ignores_unsupported_extensions(self, rule: FunctionLengthRule) -> None:
    content = "long content " * 100
    matches = rule.check("test.txt", content)

    assert len(matches) == 0

  def test_default_threshold(self) -> None:
    rule = FunctionLengthRule()  # Default 50 lines

    # Create a 60-line function
    lines = ["def long_function():"]
    lines.extend(["    x = 1"] * 60)
    lines.append("def next_func():")
    lines.append("    pass")
    content = "\n".join(lines)

    matches = rule.check("test.py", content)

    assert len(matches) == 1

  def test_handles_single_line_functions(self, rule: FunctionLengthRule) -> None:
    """Test that single-line brace functions don't break subsequent detection."""
    content = """function one() { return 1; }
function two() {
  const a = 1;
  const b = 2;
  const c = 3;
  const d = 4;
  const e = 5;
  return e;
}
function three() { return 3; }"""
    matches = rule.check("test.js", content)

    # Only 'two' should be detected as long (7 lines > 5 threshold)
    assert len(matches) == 1
    assert "two" in matches[0].message
