"""Core review orchestration."""

from pathlib import Path

from rich.console import Console

from ebert.config import Settings, load_config
from ebert.diff import extract_branch_diff, extract_files_as_context, extract_staged_diff
from ebert.models import (
  DiffContext,
  EngineMode,
  FocusArea,
  ReviewContext,
  ReviewMode,
  ReviewResult,
)
from ebert.providers import ProviderRegistry, get_provider
from ebert.rules import RuleEngine

_console = Console(stderr=True)


class ReviewOrchestrator:
  """Orchestrates the code review process."""

  def __init__(self, settings: Settings | None = None):
    self.settings = settings or Settings()

  def review_staged(self, cwd: Path | None = None) -> ReviewResult:
    """Review staged changes."""
    diff = extract_staged_diff(cwd)
    return self._perform_review(diff)

  def review_branch(
    self,
    branch: str,
    base: str = "main",
    cwd: Path | None = None,
  ) -> ReviewResult:
    """Review changes between branches."""
    diff = extract_branch_diff(branch, base, cwd)
    return self._perform_review(diff)

  def review_files(
    self,
    files: list[str],
    cwd: Path | None = None,
    no_ignore: bool = False,
  ) -> ReviewResult:
    """Review specified files."""
    diff = extract_files_as_context(files, cwd, no_ignore=no_ignore)
    return self._perform_review(diff)

  def _perform_review(self, diff: DiffContext) -> ReviewResult:
    """Perform review with configured engine."""
    if not diff.files:
      engine_name = (
        "deterministic"
        if self.settings.engine == EngineMode.DETERMINISTIC
        else self.settings.provider
      )
      return ReviewResult(
        comments=[],
        summary="No changes to review.",
        provider=engine_name,
        model=self.settings.model or "N/A",
      )

    context = ReviewContext(
      diff=diff,
      mode=self.settings.mode,
      focus=self.settings.focus,
      style_guide=self.settings.style_guide,
      max_comments=self.settings.max_comments,
    )

    # Route based on engine mode
    if self.settings.engine == EngineMode.DETERMINISTIC:
      engine = RuleEngine()
      return engine.review(context)
    else:
      provider = get_provider(self.settings.provider, self.settings.model)
      with _console.status(f"Reviewing with {provider.name}..."):
        return provider.review(context)


def run_review(
  branch: str | None = None,
  base: str = "main",
  engine: EngineMode | None = None,
  provider: str | None = None,
  model: str | None = None,
  mode: ReviewMode = ReviewMode.QUICK,
  focus: list[FocusArea] | None = None,
  config_path: Path | None = None,
  files: list[str] | None = None,
  no_ignore: bool = False,
) -> ReviewResult:
  """Run a code review with the given options."""
  settings = load_config(config_path).model_copy(deep=True)

  # Set engine mode
  if engine:
    settings.engine = engine

  # Only load providers if using LLM engine
  if settings.engine == EngineMode.LLM:
    ProviderRegistry.load_all()
    if provider:
      settings.provider = provider
  # Note: RuleEngine handles lazy-loading of rules in its review() method

  if model:
    settings.model = model
  if mode:
    settings.mode = mode
  if focus:
    settings.focus = focus

  orchestrator = ReviewOrchestrator(settings)

  if files:
    return orchestrator.review_files(files, no_ignore=no_ignore)
  if branch:
    return orchestrator.review_branch(branch, base)
  return orchestrator.review_staged()
