"""Pytest fixtures."""

import pytest
from ebert.models import (
  DiffContext,
  FileDiff,
  ReviewComment,
  ReviewContext,
  ReviewResult,
  Severity,
)


@pytest.fixture
def sample_diff() -> str:
  return """diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,5 +1,6 @@
 def hello():
-    print("hello")
+    print("hello world")
+    return True
"""


@pytest.fixture
def sample_file_diff() -> FileDiff:
  return FileDiff(
    path="test.py",
    content="""diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,5 +1,6 @@
 def hello():
-    print("hello")
+    print("hello world")
+    return True
""",
    is_new=False,
    is_deleted=False,
  )


@pytest.fixture
def sample_diff_context(sample_file_diff: FileDiff) -> DiffContext:
  return DiffContext(
    files=[sample_file_diff],
    base_ref="HEAD",
    target_ref="staged",
  )


@pytest.fixture
def sample_review_context(sample_diff_context: DiffContext) -> ReviewContext:
  return ReviewContext(diff=sample_diff_context)


@pytest.fixture
def sample_review_result() -> ReviewResult:
  return ReviewResult(
    comments=[
      ReviewComment(
        file="test.py",
        line=3,
        severity=Severity.LOW,
        message="Consider adding a docstring",
        suggestion="Add a docstring describing the function",
      ),
    ],
    summary="Minor improvements suggested",
    provider="test",
    model="test-model",
  )
