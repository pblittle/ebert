"""Git diff extraction and file scanning."""

import glob as globmod
import subprocess
from pathlib import Path

from ebert.models import DiffContext, FileDiff


class GitError(Exception):
  """Git command failed."""


class FileError(Exception):
  """File operation failed."""


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


def extract_files_as_context(
  patterns: list[str],
  cwd: Path | None = None,
) -> DiffContext:
  """Read files and return as DiffContext for review."""
  base_path = cwd or Path.cwd()
  resolved = _resolve_patterns(patterns, base_path)
  files = [_read_file_as_diff(p, base_path) for p in resolved]

  if not files:
    raise FileError("No files matched the provided patterns")

  return DiffContext(files=files, base_ref="N/A", target_ref="files")


def _resolve_patterns(patterns: list[str], base_path: Path) -> list[Path]:
  """Expand glob patterns and return unique file paths."""
  seen: set[Path] = set()
  result: list[Path] = []

  for pattern in patterns:
    paths = _expand_pattern(pattern, base_path)
    for path in paths:
      if path not in seen and path.is_file():
        seen.add(path)
        result.append(path)

  return result


def _expand_pattern(pattern: str, base_path: Path) -> list[Path]:
  """Expand a single pattern to matching paths."""
  p = Path(pattern)
  glob_path = p if p.is_absolute() else base_path / p

  if any(c in pattern for c in "*?["):
    return [Path(match) for match in globmod.glob(str(glob_path), recursive=True)]
  return [glob_path]


def _read_file_as_diff(file_path: Path, base_path: Path) -> FileDiff:
  """Read a file and format as a synthetic diff."""
  try:
    rel_path = str(file_path.relative_to(base_path))
  except ValueError:
    rel_path = str(file_path)

  try:
    content = file_path.read_text()
  except (OSError, UnicodeDecodeError) as e:
    raise FileError(f"Cannot read {rel_path}: {e}") from e

  return FileDiff(
    path=rel_path,
    content=_format_as_diff(rel_path, content),
    is_new=True,
    is_deleted=False,
  )


def _format_as_diff(path: str, content: str) -> str:
  """Format file content as unified diff."""
  lines = content.split("\n") if content else []
  line_count = len(lines)

  header = "\n".join([
    f"diff --git a/{path} b/{path}",
    "new file mode 100644",
    "--- /dev/null",
    f"+++ b/{path}",
    f"@@ -0,0 +1,{line_count} @@",
  ])

  body = "\n".join(f"+{line}" for line in lines)
  return f"{header}\n{body}"
