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
  no_ignore: bool = False,
) -> DiffContext:
  """Read files and return as DiffContext for review."""
  base_path = cwd or Path.cwd()
  expanded = _expand_directories(patterns, base_path)
  resolved = _resolve_patterns(expanded, base_path, no_ignore=no_ignore)
  files = [_read_file_as_diff(p, base_path) for p in resolved]

  if not files:
    raise FileError(_no_files_error(patterns, base_path))

  return DiffContext(files=files, base_ref="N/A", target_ref="files")


# Fallback excludes when not in a git repo
_FALLBACK_EXCLUDES: set[str] = {
  "node_modules",
  ".git",
  "__pycache__",
  ".venv",
  "venv",
  "dist",
  "build",
  ".next",
  "target",
  "vendor",
}


def _find_git_root(start: Path, cache: dict[Path, Path | None]) -> Path | None:
  """Find git repository root using filesystem traversal (no subprocess).

  Handles both regular repos (.git directory) and worktrees/submodules (.git file).
  Uses memoization via the cache dict to avoid redundant traversal.
  """
  current = start if start.is_dir() else start.parent

  # Check cache first
  if current in cache:
    return cache[current]

  # Walk up until we find .git or hit root
  visited: list[Path] = []
  while current != current.parent:
    visited.append(current)

    if current in cache:
      # Found cached result, propagate to all visited dirs
      root = cache[current]
      for d in visited:
        cache[d] = root
      return root

    git_path = current / ".git"
    if git_path.exists():
      # Found a git boundary - could be dir (normal) or file (worktree/submodule)
      for d in visited:
        cache[d] = current
      return current

    current = current.parent

  # Reached filesystem root without finding .git
  for d in visited:
    cache[d] = None
  return None


def _filter_ignored_paths(paths: list[Path], base_path: Path) -> list[Path]:
  """Filter out paths that should be ignored based on .gitignore rules.

  Uses a two-phase approach:
  1. git check-ignore for files in git repos (respects .gitignore)
  2. Fallback excludes applied to ALL paths (catches common patterns like
     nested node_modules that might not be in .gitignore)
  """
  if not paths:
    return []

  # Group paths by their git root (handles submodules)
  # Cache git roots by directory to avoid redundant filesystem traversal
  by_repo: dict[Path, list[Path]] = {}
  fallback_paths: list[Path] = []
  git_root_cache: dict[Path, Path | None] = {}

  for p in paths:
    git_root = _find_git_root(p, git_root_cache)
    if git_root:
      if git_root not in by_repo:
        by_repo[git_root] = []
      by_repo[git_root].append(p)
    else:
      fallback_paths.append(p)

  # Filter each repo's paths with its own gitignore (one subprocess per repo)
  git_filtered: list[Path] = []
  for git_root, repo_paths in by_repo.items():
    git_filtered.extend(_filter_with_git(repo_paths, git_root))

  # Apply fallback excludes to ALL results (both git-filtered and non-repo paths)
  # This catches common patterns like node_modules that might be nested and not
  # explicitly listed in .gitignore (e.g., vendors/pkg/node_modules when
  # .gitignore only has 'node_modules/' instead of '**/node_modules/')
  all_paths = git_filtered + fallback_paths
  return _filter_with_fallback(all_paths)


def _filter_with_git(paths: list[Path], base_path: Path) -> list[Path]:
  """Use git check-ignore to filter paths."""
  if not paths:
    return []

  # Convert to relative paths for git check-ignore
  # Skip paths that can't be made relative (shouldn't happen, but defensive)
  path_map: dict[str, Path] = {}
  for p in paths:
    try:
      rel = str(p.relative_to(base_path))
      path_map[rel] = p
    except ValueError:
      # Path not inside git root - this indicates an unexpected state
      # Skip it rather than passing incorrect absolute path to git
      continue

  if not path_map:
    return []

  # Batch check with git check-ignore using stdin
  # Use -z for NUL-separated I/O to handle filenames with newlines
  try:
    result = subprocess.run(
      ["git", "check-ignore", "--stdin", "-z"],
      cwd=base_path,
      input="\0".join(path_map.keys()),
      capture_output=True,
      text=True,
    )
    # git check-ignore -z returns NUL-separated ignored paths
    ignored = {p for p in result.stdout.split("\0") if p}
    return [path_map[rel] for rel in path_map if rel not in ignored]
  except (subprocess.CalledProcessError, FileNotFoundError):
    # If git fails, return all paths (fallback will be applied by caller)
    return paths


def _filter_with_fallback(paths: list[Path]) -> list[Path]:
  """Filter paths using hardcoded exclude patterns."""
  result = []
  for path in paths:
    parts = set(path.parts)
    if not parts & _FALLBACK_EXCLUDES:
      result.append(path)
  return result


# Common code file extensions by language/ecosystem
_LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
  "python": ["py"],
  "javascript": ["js", "jsx", "mjs", "cjs"],
  "typescript": ["ts", "tsx", "mts", "cts"],
  "go": ["go"],
  "rust": ["rs"],
  "java": ["java"],
  "kotlin": ["kt", "kts"],
  "ruby": ["rb"],
  "php": ["php"],
  "csharp": ["cs"],
  "cpp": ["cpp", "cc", "cxx", "c", "h", "hpp"],
  "swift": ["swift"],
  "scala": ["scala"],
}

# Files that indicate a project's primary language
_LANGUAGE_INDICATORS: dict[str, list[str]] = {
  "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
  "javascript": ["package.json"],
  "typescript": ["tsconfig.json", "package.json"],
  "go": ["go.mod", "go.sum"],
  "rust": ["Cargo.toml"],
  "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
  "kotlin": ["build.gradle.kts"],
  "ruby": ["Gemfile", "*.gemspec"],
  "php": ["composer.json"],
  "csharp": ["*.csproj", "*.sln"],
  "cpp": ["CMakeLists.txt", "Makefile"],
  "swift": ["Package.swift", "*.xcodeproj"],
  "scala": ["build.sbt"],
}


def _expand_directories(patterns: list[str], base_path: Path) -> list[str]:
  """Expand directory patterns to glob patterns based on detected language."""
  result: list[str] = []

  for pattern in patterns:
    p = Path(pattern)
    full_path = p if p.is_absolute() else base_path / p

    if full_path.is_dir():
      extensions = _detect_language_extensions(full_path)
      if extensions:
        for ext in extensions:
          result.append(str(full_path / "**" / f"*.{ext}"))
      else:
        # No language detected, keep original (will fail with helpful message)
        result.append(pattern)
    else:
      result.append(pattern)

  return result


def _detect_language_extensions(directory: Path) -> list[str]:
  """Detect programming languages in a directory and return file extensions."""
  extensions: list[str] = []

  # Check for language indicator files
  for lang, indicators in _LANGUAGE_INDICATORS.items():
    for indicator in indicators:
      if any(c in indicator for c in "*?["):
        if list(directory.glob(indicator)):
          extensions.extend(_LANGUAGE_EXTENSIONS.get(lang, []))
          break
      elif (directory / indicator).exists():
        extensions.extend(_LANGUAGE_EXTENSIONS.get(lang, []))
        break

  # Deduplicate while preserving order
  seen: set[str] = set()
  unique: list[str] = []
  for ext in extensions:
    if ext not in seen:
      seen.add(ext)
      unique.append(ext)

  return unique


def _no_files_error(patterns: list[str], base_path: Path) -> str:
  """Generate a helpful error message when no files are found."""
  dirs = [p for p in patterns if (base_path / p).is_dir() or Path(p).is_dir()]

  if dirs:
    return (
      f"No reviewable files found in: {', '.join(dirs)}\n"
      "Could not detect project language. Try specifying files directly:\n"
      f"  ebert {dirs[0]}/**/*.py    # Python\n"
      f"  ebert {dirs[0]}/**/*.ts    # TypeScript\n"
      f"  ebert {dirs[0]}/**/*.go    # Go"
    )

  return (
    f"No files matched: {', '.join(patterns)}\n"
    "Use glob patterns like: ebert 'src/**/*.py'"
  )


def _resolve_patterns(
  patterns: list[str],
  base_path: Path,
  no_ignore: bool = False,
) -> list[Path]:
  """Expand glob patterns and return unique file paths."""
  seen: set[Path] = set()
  result: list[Path] = []

  for pattern in patterns:
    paths = _expand_pattern(pattern, base_path)
    for path in paths:
      if path not in seen and path.is_file():
        seen.add(path)
        result.append(path)

  # Filter out ignored paths (unless --no-ignore)
  if no_ignore:
    return result
  return _filter_ignored_paths(result, base_path)


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
