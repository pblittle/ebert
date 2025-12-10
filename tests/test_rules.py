"""Tests for rule engine infrastructure."""

from typing import Sequence

import pytest
from ebert.models import (
  DiffContext,
  FileDiff,
  FocusArea,
  ReviewContext,
  ReviewMode,
  Severity,
)
from ebert.rules.base import Rule, RuleMatch
from ebert.rules.engine import RuleEngine, _extract_content_with_line_map
from ebert.rules.registry import (
  get_all_rules,
  get_rules_for_focus,
  list_rules,
  register_rule,
)


class MockRule:
  """Mock rule for testing."""

  def __init__(
    self,
    rule_id: str = "TEST001",
    name: str = "test-rule",
    focus: FocusArea = FocusArea.BUGS,
    matches: list[RuleMatch] | None = None,
  ):
    self._id = rule_id
    self._name = name
    self._focus = focus
    self._matches = matches or []

  @property
  def id(self) -> str:
    return self._id

  @property
  def name(self) -> str:
    return self._name

  @property
  def focus_area(self) -> FocusArea:
    return self._focus

  def check(self, file_path: str, content: str) -> Sequence[RuleMatch]:
    return self._matches


class TestRuleMatch:
  def test_frozen_dataclass(self) -> None:
    match = RuleMatch(
      line=42,
      severity=Severity.HIGH,
      message="Test message",
      suggestion="Fix it",
    )

    assert match.line == 42
    assert match.severity == Severity.HIGH
    assert match.message == "Test message"
    assert match.suggestion == "Fix it"

  def test_optional_fields(self) -> None:
    match = RuleMatch(
      line=None,
      severity=Severity.INFO,
      message="No line number",
    )

    assert match.line is None
    assert match.suggestion is None


class TestRuleProtocol:
  def test_mock_rule_satisfies_protocol(self) -> None:
    rule: Rule = MockRule()

    assert rule.id == "TEST001"
    assert rule.name == "test-rule"
    assert rule.focus_area == FocusArea.BUGS
    assert rule.check("test.py", "") == []


class TestExtractContentWithLineMap:
  def test_extracts_added_lines(self) -> None:
    diff = """+line 1
+line 2
-removed line
+line 3"""

    content, line_map = _extract_content_with_line_map(diff)

    assert "line 1" in content
    assert "line 2" in content
    assert "line 3" in content
    assert "removed line" not in content

  def test_handles_diff_headers(self) -> None:
    diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
+new line
 existing line"""

    content, line_map = _extract_content_with_line_map(diff)

    assert "new line" in content
    assert "existing line" in content
    assert "---" not in content
    assert "+++" not in content
    assert "@@" not in content

  def test_handles_raw_content(self) -> None:
    raw = """def foo():
    return 42"""

    content, line_map = _extract_content_with_line_map(raw)

    assert "def foo():" in content
    assert "return 42" in content
    # Raw content should have 1:1 line mapping
    assert line_map[1] == 1
    assert line_map[2] == 2

  def test_maps_line_numbers_from_hunk(self) -> None:
    diff = """--- a/file.py
+++ b/file.py
@@ -10,3 +10,4 @@
 context line
+added line"""

    content, line_map = _extract_content_with_line_map(diff)

    # Line 1 in extracted content = line 10 in original file
    assert line_map[1] == 10
    # Line 2 in extracted content = line 11 in original file
    assert line_map[2] == 11


class TestRuleEngine:
  @pytest.fixture
  def sample_context(self) -> ReviewContext:
    return ReviewContext(
      diff=DiffContext(
        files=[
          FileDiff(
            path="test.py",
            content="+print('hello')\n+x = 1",
            is_new=True,
          ),
        ],
      ),
      mode=ReviewMode.QUICK,
      focus=[FocusArea.ALL],
      max_comments=20,
    )

  def test_returns_review_result(self, sample_context: ReviewContext) -> None:
    engine = RuleEngine(rules=[])

    result = engine.review(sample_context)

    assert result.provider == "deterministic"
    assert result.model == "rules-v1"
    assert isinstance(result.summary, str)

  def test_aggregates_rule_matches(self, sample_context: ReviewContext) -> None:
    matches = [
      RuleMatch(line=1, severity=Severity.HIGH, message="Issue 1"),
      RuleMatch(line=2, severity=Severity.LOW, message="Issue 2"),
    ]
    rule = MockRule(matches=matches)
    engine = RuleEngine(rules=[rule])

    result = engine.review(sample_context)

    assert len(result.comments) == 2
    assert "[TEST001]" in result.comments[0].message

  def test_respects_max_comments(self, sample_context: ReviewContext) -> None:
    matches = [
      RuleMatch(line=i, severity=Severity.INFO, message=f"Issue {i}")
      for i in range(30)
    ]
    rule = MockRule(matches=matches)
    context = ReviewContext(
      diff=sample_context.diff,
      mode=ReviewMode.QUICK,
      focus=[FocusArea.ALL],
      max_comments=5,
    )
    engine = RuleEngine(rules=[rule])

    result = engine.review(context)

    assert len(result.comments) == 5
    assert "showing first 5" in result.summary

  def test_skips_deleted_files(self) -> None:
    context = ReviewContext(
      diff=DiffContext(
        files=[
          FileDiff(path="deleted.py", content="-old code", is_deleted=True),
        ],
      ),
    )
    matches = [RuleMatch(line=1, severity=Severity.HIGH, message="Should skip")]
    rule = MockRule(matches=matches)
    engine = RuleEngine(rules=[rule])

    result = engine.review(context)

    assert len(result.comments) == 0

  def test_generates_summary_with_counts(self, sample_context: ReviewContext) -> None:
    matches = [
      RuleMatch(line=1, severity=Severity.CRITICAL, message="Critical"),
      RuleMatch(line=2, severity=Severity.HIGH, message="High"),
      RuleMatch(line=3, severity=Severity.HIGH, message="High 2"),
    ]
    rule = MockRule(matches=matches)
    engine = RuleEngine(rules=[rule])

    result = engine.review(sample_context)

    assert "3 issues" in result.summary
    assert "1 critical" in result.summary
    assert "2 high" in result.summary

  def test_no_issues_summary(self) -> None:
    context = ReviewContext(
      diff=DiffContext(files=[FileDiff(path="clean.py", content="+clean code")]),
    )
    engine = RuleEngine(rules=[])

    result = engine.review(context)

    assert result.summary == "No issues found."


class TestRuleRegistry:
  def test_register_and_list(self) -> None:
    # Note: This modifies global state, so we use a unique ID
    register_rule("REGTEST001", lambda: MockRule(rule_id="REGTEST001"))

    assert "REGTEST001" in list_rules()

  def test_get_all_rules(self) -> None:
    register_rule("REGTEST002", lambda: MockRule(rule_id="REGTEST002"))

    rules = get_all_rules()

    assert any(r.id == "REGTEST002" for r in rules)

  def test_get_rules_for_focus_filters(self) -> None:
    register_rule(
      "REGTEST003",
      lambda: MockRule(rule_id="REGTEST003", focus=FocusArea.SECURITY),
    )
    register_rule(
      "REGTEST004",
      lambda: MockRule(rule_id="REGTEST004", focus=FocusArea.STYLE),
    )

    security_rules = get_rules_for_focus([FocusArea.SECURITY])

    rule_ids = [r.id for r in security_rules]
    assert "REGTEST003" in rule_ids
    assert "REGTEST004" not in rule_ids

  def test_focus_all_returns_all_rules(self) -> None:
    register_rule(
      "REGTEST005",
      lambda: MockRule(rule_id="REGTEST005", focus=FocusArea.BUGS),
    )

    all_rules = get_rules_for_focus([FocusArea.ALL])

    assert any(r.id == "REGTEST005" for r in all_rules)
