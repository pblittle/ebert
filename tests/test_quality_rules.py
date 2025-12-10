"""Tests for quality rules."""

import pytest
from ebert.models import FocusArea, Severity
from ebert.rules.quality.commented_code import CommentedCodeRule
from ebert.rules.quality.debug import DebugStatementRule
from ebert.rules.quality.todos import TodoCommentRule


class TestDebugStatementRule:
  @pytest.fixture
  def rule(self) -> DebugStatementRule:
    return DebugStatementRule()

  def test_properties(self, rule: DebugStatementRule) -> None:
    assert rule.id == "QUA001"
    assert rule.name == "debug-statement"
    assert rule.focus_area == FocusArea.BUGS

  def test_detects_python_print(self, rule: DebugStatementRule) -> None:
    content = "def foo():\n  print(x)"
    matches = rule.check("test.py", content)

    assert len(matches) == 1
    assert matches[0].line == 2
    assert matches[0].severity == Severity.MEDIUM

  def test_detects_python_breakpoint(self, rule: DebugStatementRule) -> None:
    content = "breakpoint()"
    matches = rule.check("debug.py", content)

    assert len(matches) == 1

  def test_detects_pdb_import(self, rule: DebugStatementRule) -> None:
    content = "import pdb"
    matches = rule.check("test.py", content)

    assert len(matches) == 1

  def test_detects_js_console_log(self, rule: DebugStatementRule) -> None:
    content = "function foo() {\n  console.log(x);\n}"
    matches = rule.check("test.js", content)

    assert len(matches) == 1

  def test_detects_js_debugger(self, rule: DebugStatementRule) -> None:
    content = "debugger"
    matches = rule.check("app.js", content)

    assert len(matches) == 1

  def test_detects_ts_console_debug(self, rule: DebugStatementRule) -> None:
    content = "console.debug(data);"
    matches = rule.check("app.ts", content)

    assert len(matches) == 1

  def test_detects_go_fmt_print(self, rule: DebugStatementRule) -> None:
    content = "fmt.Println(x)"
    matches = rule.check("main.go", content)

    assert len(matches) == 1

  def test_detects_ruby_puts(self, rule: DebugStatementRule) -> None:
    content = "puts x"
    matches = rule.check("app.rb", content)

    assert len(matches) == 1

  def test_ignores_unsupported_extensions(self, rule: DebugStatementRule) -> None:
    content = "print(x)"
    matches = rule.check("README.md", content)

    assert len(matches) == 0

  def test_ignores_comments(self, rule: DebugStatementRule) -> None:
    content = "# print(x)"
    matches = rule.check("test.py", content)

    assert len(matches) == 0


class TestTodoCommentRule:
  @pytest.fixture
  def rule(self) -> TodoCommentRule:
    return TodoCommentRule()

  def test_properties(self, rule: TodoCommentRule) -> None:
    assert rule.id == "QUA002"
    assert rule.name == "todo-comment"
    assert rule.focus_area == FocusArea.BUGS

  def test_detects_todo(self, rule: TodoCommentRule) -> None:
    content = "# TODO: implement this"
    matches = rule.check("test.py", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.INFO
    assert "TODO" in matches[0].message

  def test_detects_fixme(self, rule: TodoCommentRule) -> None:
    content = "// FIXME: broken code"
    matches = rule.check("test.js", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.MEDIUM

  def test_detects_hack(self, rule: TodoCommentRule) -> None:
    content = "# HACK: workaround for bug"
    matches = rule.check("test.py", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.MEDIUM

  def test_detects_xxx(self, rule: TodoCommentRule) -> None:
    content = "// XXX: needs review"
    matches = rule.check("test.ts", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.MEDIUM

  def test_detects_bug(self, rule: TodoCommentRule) -> None:
    content = "# BUG: known issue"
    matches = rule.check("test.py", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.HIGH

  def test_case_insensitive(self, rule: TodoCommentRule) -> None:
    content = "# todo: lowercase"
    matches = rule.check("test.py", content)

    assert len(matches) == 1

  def test_requires_separator(self, rule: TodoCommentRule) -> None:
    content = "# TODOLIST is not a todo"
    matches = rule.check("test.py", content)

    assert len(matches) == 0


class TestCommentedCodeRule:
  @pytest.fixture
  def rule(self) -> CommentedCodeRule:
    return CommentedCodeRule()

  def test_properties(self, rule: CommentedCodeRule) -> None:
    assert rule.id == "QUA003"
    assert rule.name == "commented-code"
    assert rule.focus_area == FocusArea.STYLE

  def test_detects_python_commented_block(self, rule: CommentedCodeRule) -> None:
    content = """# def old_function():
#   x = 1
#   return x
"""
    matches = rule.check("test.py", content)

    assert len(matches) == 1
    assert matches[0].severity == Severity.LOW
    assert "3" in matches[0].message

  def test_detects_js_commented_block(self, rule: CommentedCodeRule) -> None:
    content = """// function oldFunc() {
//   const x = 1;
//   return x;
// }"""
    matches = rule.check("test.js", content)

    assert len(matches) == 1

  def test_ignores_short_blocks(self, rule: CommentedCodeRule) -> None:
    content = """# x = 1
# y = 2"""
    matches = rule.check("test.py", content)

    # Only 2 lines, below threshold
    assert len(matches) == 0

  def test_ignores_documentation(self, rule: CommentedCodeRule) -> None:
    content = """# This is a description
# of what this module does
# and how to use it"""
    matches = rule.check("test.py", content)

    # Regular comments don't look like code
    assert len(matches) == 0

  def test_detects_assignment_pattern(self, rule: CommentedCodeRule) -> None:
    content = """# old_value = 42
# another_var = "test"
# third_var = []"""
    matches = rule.check("test.py", content)

    assert len(matches) == 1
