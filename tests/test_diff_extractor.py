"""Tests for diff extraction."""

from pathlib import Path

import pytest

from ebert.diff.extractor import (
  extract_files_as_context,
  FileError,
  parse_diff_output,
  _format_as_diff,
  _resolve_patterns,
)


class TestParseDiffOutput:
  def test_empty_diff(self) -> None:
    result = parse_diff_output("")
    assert result == []

  def test_whitespace_diff(self) -> None:
    result = parse_diff_output("   \n\n  ")
    assert result == []

  def test_single_file_diff(self, sample_diff: str) -> None:
    result = parse_diff_output(sample_diff)
    assert len(result) == 1
    assert result[0].path == "test.py"
    assert not result[0].is_new
    assert not result[0].is_deleted

  def test_new_file_diff(self) -> None:
    diff = """diff --git a/new_file.py b/new_file.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,3 @@
+def new_func():
+    pass
"""
    result = parse_diff_output(diff)
    assert len(result) == 1
    assert result[0].path == "new_file.py"
    assert result[0].is_new
    assert not result[0].is_deleted

  def test_deleted_file_diff(self) -> None:
    diff = """diff --git a/old_file.py b/old_file.py
deleted file mode 100644
index 1234567..0000000
--- a/old_file.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def old_func():
-    pass
"""
    result = parse_diff_output(diff)
    assert len(result) == 1
    assert result[0].path == "old_file.py"
    assert not result[0].is_new
    assert result[0].is_deleted

  def test_multiple_files_diff(self) -> None:
    diff = """diff --git a/file1.py b/file1.py
index 1234567..abcdefg 100644
--- a/file1.py
+++ b/file1.py
@@ -1 +1 @@
-old
+new
diff --git a/file2.py b/file2.py
index 1234567..abcdefg 100644
--- a/file2.py
+++ b/file2.py
@@ -1 +1 @@
-old2
+new2
"""
    result = parse_diff_output(diff)
    assert len(result) == 2
    assert result[0].path == "file1.py"
    assert result[1].path == "file2.py"


class TestFormatAsDiff:
  def test_formats_content_as_unified_diff(self) -> None:
    content = "line1\nline2"
    result = _format_as_diff("test.py", content)

    assert "diff --git a/test.py b/test.py" in result
    assert "new file mode 100644" in result
    assert "--- /dev/null" in result
    assert "+++ b/test.py" in result
    assert "@@ -0,0 +1,2 @@" in result
    assert "+line1" in result
    assert "+line2" in result

  def test_single_line_file(self) -> None:
    result = _format_as_diff("single.txt", "only line")
    assert "@@ -0,0 +1,1 @@" in result


class TestResolvePatterns:
  def test_resolves_explicit_file(self, tmp_path: Path) -> None:
    test_file = tmp_path / "test.py"
    test_file.write_text("content")

    result = _resolve_patterns(["test.py"], tmp_path)

    assert len(result) == 1
    assert result[0] == test_file

  def test_resolves_glob_pattern(self, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("a")
    (tmp_path / "b.py").write_text("b")
    (tmp_path / "c.txt").write_text("c")

    result = _resolve_patterns(["*.py"], tmp_path)

    assert len(result) == 2
    paths = {p.name for p in result}
    assert paths == {"a.py", "b.py"}

  def test_skips_directories(self, tmp_path: Path) -> None:
    (tmp_path / "subdir").mkdir()
    (tmp_path / "file.py").write_text("content")

    result = _resolve_patterns(["*"], tmp_path)

    assert len(result) == 1
    assert result[0].name == "file.py"

  def test_deduplicates_paths(self, tmp_path: Path) -> None:
    test_file = tmp_path / "test.py"
    test_file.write_text("content")

    result = _resolve_patterns(["test.py", "test.py", "*.py"], tmp_path)

    assert len(result) == 1


class TestExtractFilesAsContext:
  def test_extracts_single_file(self, tmp_path: Path) -> None:
    test_file = tmp_path / "test.py"
    test_file.write_text("def foo():\n  pass")

    result = extract_files_as_context(["test.py"], tmp_path)

    assert len(result.files) == 1
    assert result.files[0].path == "test.py"
    assert result.files[0].is_new
    assert not result.files[0].is_deleted
    assert "+def foo():" in result.files[0].content

  def test_extracts_multiple_files(self, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("a")
    (tmp_path / "b.py").write_text("b")

    result = extract_files_as_context(["a.py", "b.py"], tmp_path)

    assert len(result.files) == 2
    paths = {f.path for f in result.files}
    assert paths == {"a.py", "b.py"}

  def test_extracts_glob_pattern(self, tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("main")
    (tmp_path / "src" / "util.py").write_text("util")

    result = extract_files_as_context(["src/*.py"], tmp_path)

    assert len(result.files) == 2

  def test_raises_on_no_matches(self, tmp_path: Path) -> None:
    with pytest.raises(FileError, match="No files matched"):
      extract_files_as_context(["nonexistent.py"], tmp_path)

  def test_raises_on_missing_file(self, tmp_path: Path) -> None:
    (tmp_path / "exists.py").write_text("content")

    with pytest.raises(FileError, match="No files matched"):
      extract_files_as_context(["missing.py"], tmp_path)

  def test_context_refs(self, tmp_path: Path) -> None:
    (tmp_path / "test.py").write_text("content")

    result = extract_files_as_context(["test.py"], tmp_path)

    assert result.base_ref == "N/A"
    assert result.target_ref == "files"
