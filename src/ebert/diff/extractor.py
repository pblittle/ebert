"""Git diff extraction."""

import subprocess
from pathlib import Path

from ebert.models import DiffContext, FileDiff


class GitError(Exception):
  """Git command failed."""


def _sanitize_error(stderr: str) -> str:
  """Remove potentially sensitive path information from error messages."""
  lines = stderr.strip().split("\n")
  sanitized = []
  for line in lines:
    if "fatal:" in line or "error:" in line:
      sanitized.append(line.split("/")[-1] if "/" in line else line)
    else:
      sanitized.append(line)
  return "\n".join(sanitized)


def run_git(*args: str, cwd: Path | None = None) -> str:
  """Run a git command and return stdout."""
  try:
    result = subprocess.run(
      ["git", *args],
      capture_output=True,
      text=True,
      check=True,
      cwd=cwd,
    )
    return result.stdout
  except subprocess.CalledProcessError as e:
    sanitized = _sanitize_error(e.stderr)
    raise GitError(f"git {' '.join(args)} failed: {sanitized}") from e


def extract_staged_diff(cwd: Path | None = None) -> DiffContext:
  """Extract diff of staged changes."""
  diff_output = run_git("diff", "--cached", cwd=cwd)
  files = parse_diff_output(diff_output)
  return DiffContext(files=files, base_ref="HEAD", target_ref="staged")


def extract_branch_diff(
  branch: str,
  base: str = "main",
  cwd: Path | None = None,
) -> DiffContext:
  """Extract diff between branch and base."""
  diff_output = run_git("diff", f"{base}...{branch}", cwd=cwd)
  files = parse_diff_output(diff_output)
  return DiffContext(files=files, base_ref=base, target_ref=branch)


def extract_unstaged_diff(cwd: Path | None = None) -> DiffContext:
  """Extract diff of unstaged changes."""
  diff_output = run_git("diff", cwd=cwd)
  files = parse_diff_output(diff_output)
  return DiffContext(files=files, base_ref="HEAD", target_ref="working")


def parse_diff_output(diff_output: str) -> list[FileDiff]:
  """Parse git diff output into structured format."""
  if not diff_output.strip():
    return []

  files: list[FileDiff] = []
  current_file: str | None = None
  current_content: list[str] = []
  is_new = False
  is_deleted = False

  for line in diff_output.split("\n"):
    if line.startswith("diff --git"):
      if current_file is not None:
        files.append(FileDiff(
          path=current_file,
          content="\n".join(current_content),
          is_new=is_new,
          is_deleted=is_deleted,
        ))
      parts = line.split(" b/")
      current_file = parts[-1] if len(parts) > 1 else None
      current_content = [line]
      is_new = False
      is_deleted = False
    elif line.startswith("new file"):
      is_new = True
      current_content.append(line)
    elif line.startswith("deleted file"):
      is_deleted = True
      current_content.append(line)
    elif current_file is not None:
      current_content.append(line)

  if current_file is not None:
    files.append(FileDiff(
      path=current_file,
      content="\n".join(current_content),
      is_new=is_new,
      is_deleted=is_deleted,
    ))

  return files
