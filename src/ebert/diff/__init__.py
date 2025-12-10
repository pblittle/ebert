"""Diff extraction and parsing."""

from ebert.diff.extractor import (
    FileError,
    extract_branch_diff,
    extract_files_as_context,
    extract_staged_diff,
)

__all__ = [
  "extract_branch_diff",
  "extract_files_as_context",
  "extract_staged_diff",
  "FileError",
]
