"""Tests for diff extraction."""

from pathlib import Path

import pytest
from ebert.diff.extractor import (
  FileError,
  _detect_language_extensions,
  _expand_directories,
  _filter_with_fallback,
  _format_as_diff,
  _no_files_error,
  _resolve_patterns,
  extract_files_as_context,
  parse_diff_output,
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

  def test_expands_directory_with_python_project(self, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]")
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "util.py").write_text("def util(): pass")

    result = extract_files_as_context([str(tmp_path)], tmp_path)

    assert len(result.files) == 2
    paths = {f.path for f in result.files}
    assert "main.py" in paths or any("main.py" in p for p in paths)

  def test_expands_directory_with_typescript_project(self, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text("{}")
    (tmp_path / "index.ts").write_text("const x = 1;")
    (tmp_path / "util.tsx").write_text("export const Y = () => null;")

    result = extract_files_as_context([str(tmp_path)], tmp_path)

    assert len(result.files) == 2

  def test_expands_nested_directory(self, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]")
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hello')")

    result = extract_files_as_context([str(tmp_path)], tmp_path)

    assert len(result.files) == 1
    assert any("main.py" in f.path for f in result.files)


class TestDetectLanguageExtensions:
  def test_detects_python_from_pyproject(self, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("")
    result = _detect_language_extensions(tmp_path)
    assert "py" in result

  def test_detects_python_from_requirements(self, tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("")
    result = _detect_language_extensions(tmp_path)
    assert "py" in result

  def test_detects_typescript_from_tsconfig(self, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text("")
    result = _detect_language_extensions(tmp_path)
    assert "ts" in result
    assert "tsx" in result

  def test_detects_javascript_from_package_json(self, tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("")
    result = _detect_language_extensions(tmp_path)
    assert "js" in result or "ts" in result

  def test_detects_go_from_go_mod(self, tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("")
    result = _detect_language_extensions(tmp_path)
    assert "go" in result

  def test_detects_rust_from_cargo(self, tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text("")
    result = _detect_language_extensions(tmp_path)
    assert "rs" in result

  def test_returns_empty_for_unknown_project(self, tmp_path: Path) -> None:
    result = _detect_language_extensions(tmp_path)
    assert result == []

  def test_deduplicates_extensions(self, tmp_path: Path) -> None:
    # Both typescript and javascript indicators present
    (tmp_path / "tsconfig.json").write_text("")
    (tmp_path / "package.json").write_text("")
    result = _detect_language_extensions(tmp_path)
    # Should not have duplicate 'js' entries
    assert len(result) == len(set(result))


class TestExpandDirectories:
  def test_expands_directory_to_glob_patterns(self, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("")
    result = _expand_directories([str(tmp_path)], tmp_path)
    assert any("**/*.py" in p for p in result)

  def test_passes_through_non_directories(self, tmp_path: Path) -> None:
    result = _expand_directories(["src/*.py", "test.py"], tmp_path)
    assert "src/*.py" in result
    assert "test.py" in result

  def test_keeps_directory_if_no_language_detected(self, tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    result = _expand_directories([str(empty_dir)], tmp_path)
    assert str(empty_dir) in result


class TestNoFilesError:
  def test_helpful_message_for_directory(self, tmp_path: Path) -> None:
    test_dir = tmp_path / "myproject"
    test_dir.mkdir()

    error = _no_files_error([str(test_dir)], tmp_path)

    assert "No reviewable files found" in error
    assert "Could not detect project language" in error
    assert "ebert" in error
    assert "*.py" in error
    assert "*.ts" in error

  def test_simple_message_for_patterns(self, tmp_path: Path) -> None:
    error = _no_files_error(["src/*.py", "lib/*.js"], tmp_path)

    assert "No files matched" in error
    assert "src/*.py" in error


class TestFilterWithFallback:
  def test_excludes_npm_deps(self) -> None:
    # Use absolute paths to avoid pytest temp dir naming issues
    paths = [
      Path("/project/src/index.ts"),
      Path("/project/node_modules/pkg/index.js"),
    ]
    result = _filter_with_fallback(paths)
    assert len(result) == 1
    assert result[0] == Path("/project/src/index.ts")

  def test_excludes_pycache(self) -> None:
    paths = [
      Path("/project/main.py"),
      Path("/project/__pycache__/main.cpython-311.pyc"),
    ]
    result = _filter_with_fallback(paths)
    assert len(result) == 1
    assert result[0] == Path("/project/main.py")

  def test_excludes_venv(self) -> None:
    paths = [
      Path("/project/app.py"),
      Path("/project/.venv/lib/site.py"),
      Path("/project/venv/lib/site.py"),
    ]
    result = _filter_with_fallback(paths)
    assert len(result) == 1
    assert result[0].name == "app.py"

  def test_excludes_build_dirs(self) -> None:
    paths = [
      Path("/project/src/main.rs"),
      Path("/project/target/debug/main"),
      Path("/project/dist/bundle.js"),
      Path("/project/build/output.js"),
    ]
    result = _filter_with_fallback(paths)
    assert len(result) == 1
    assert result[0].name == "main.rs"

  def test_keeps_non_excluded_paths(self) -> None:
    paths = [
      Path("/project/src/main.py"),
      Path("/project/tests/test_main.py"),
      Path("/project/lib/utils.py"),
    ]
    result = _filter_with_fallback(paths)
    assert len(result) == 3


class TestResolvePatternFiltering:
  def test_filters_excluded_dirs_in_glob(self, tmp_path: Path) -> None:
    # Create structure with excluded directory
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.ts").write_text("const x = 1;")

    # Use __pycache__ instead of node_modules to avoid pytest naming issues
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "cached.pyc").write_text("cached")

    result = _resolve_patterns(["**/*.ts", "**/*.pyc"], tmp_path)

    # Should only get src/app.ts, not __pycache__ files
    assert len(result) == 1
    assert result[0].name == "app.ts"


class TestGitIgnoreFiltering:
  """Test git check-ignore based filtering."""

  def test_filters_node_modules_via_gitignore(self, tmp_path: Path) -> None:
    """Test that node_modules is filtered when listed in .gitignore."""
    import subprocess

    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    # Create .gitignore with node_modules
    (tmp_path / ".gitignore").write_text("node_modules/\n")

    # Create source files
    src = tmp_path / "src"
    src.mkdir()
    (src / "index.ts").write_text("export const x = 1;")

    # Create node_modules (should be ignored)
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    pkg = node_modules / "some-pkg"
    pkg.mkdir()
    (pkg / "index.js").write_text("module.exports = {};")

    # Test that node_modules files are filtered out
    result = _resolve_patterns(["**/*.ts", "**/*.js"], tmp_path)

    # Should only get src/index.ts, not node_modules files
    assert len(result) == 1
    assert result[0].name == "index.ts"

  def test_filters_nested_node_modules(self, tmp_path: Path) -> None:
    """Test filtering node_modules in nested directories like vendors/."""
    import subprocess

    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    # Create .gitignore - note: node_modules/ only matches at root level
    # Many projects use **/node_modules/ but some only use node_modules/
    # Our fallback should still catch nested node_modules
    (tmp_path / ".gitignore").write_text("**/node_modules/\n")

    # Create source files
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.ts").write_text("console.log('main');")

    # Create nested structure: vendors/sub-project/node_modules
    vendors = tmp_path / "vendors"
    vendors.mkdir()
    sub_project = vendors / "sub-project"
    sub_project.mkdir()
    (sub_project / "index.ts").write_text("export default {};")

    # node_modules inside the sub-project
    nested_nm = sub_project / "node_modules"
    nested_nm.mkdir()
    nested_pkg = nested_nm / "dep"
    nested_pkg.mkdir()
    (nested_pkg / "index.js").write_text("module.exports = 'dep';")

    result = _resolve_patterns(["**/*.ts", "**/*.js"], tmp_path)

    # Should get src/main.ts and vendors/sub-project/index.ts
    # but NOT vendors/sub-project/node_modules/dep/index.js
    paths = {p.name for p in result}
    assert "main.ts" in paths
    assert "index.ts" in paths
    assert "index.js" not in paths
    assert len(result) == 2

  def test_filters_nested_node_modules_without_glob_pattern(self, tmp_path: Path) -> None:
    """Test nested node_modules filtered even with root-level gitignore pattern.

    Many repos only have 'node_modules/' in .gitignore which only matches at
    root level. Our fallback should catch nested node_modules regardless.
    """
    import subprocess

    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    # Create .gitignore with ONLY root-level node_modules pattern
    # This is what many older projects have
    (tmp_path / ".gitignore").write_text("node_modules/\n")

    # Create source files
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.ts").write_text("const app = 'hello';")

    # Create nested structure where node_modules is NOT at root
    vendors = tmp_path / "vendors"
    vendors.mkdir()
    pkg = vendors / "some-pkg"
    pkg.mkdir()
    (pkg / "main.ts").write_text("export const x = 1;")

    # node_modules inside vendors/some-pkg - NOT matched by root 'node_modules/'
    nested_nm = pkg / "node_modules"
    nested_nm.mkdir()
    dep = nested_nm / "dep"
    dep.mkdir()
    (dep / "index.js").write_text("module.exports = 'nested';")

    result = _resolve_patterns(["**/*.ts", "**/*.js"], tmp_path)

    # Should get src/app.ts and vendors/some-pkg/main.ts
    # Should NOT get vendors/some-pkg/node_modules/dep/index.js
    # even though git check-ignore won't catch it (since 'node_modules/'
    # only matches root level), our fallback should filter it
    paths = {str(p.relative_to(tmp_path)) for p in result}
    assert "src/app.ts" in paths or any("app.ts" in p for p in paths)
    assert any("main.ts" in p for p in paths)
    # The key assertion: no files from node_modules
    assert not any("node_modules" in p for p in paths)
    assert len(result) == 2
