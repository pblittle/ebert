"""Tests for diff extraction."""

import pytest

from ebert.diff.extractor import parse_diff_output


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
