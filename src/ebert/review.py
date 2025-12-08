"""Core review orchestration."""

from pathlib import Path

from ebert.config import Settings, load_config
from ebert.diff import extract_branch_diff, extract_files_as_context, extract_staged_diff
from ebert.models import DiffContext, FocusArea, ReviewContext, ReviewMode, ReviewResult
from ebert.providers import ProviderRegistry, get_provider


class ReviewOrchestrator:
  """Orchestrates the code review process."""

  def __init__(self, settings: Settings | None = None):
    self.settings = settings or Settings()
    ProviderRegistry.load_all()

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
  ) -> ReviewResult:
    """Review specified files."""
    diff = extract_files_as_context(files, cwd)
    return self._perform_review(diff)

  def _perform_review(self, diff: DiffContext) -> ReviewResult:
    """Perform review with configured provider."""
    if not diff.files:
      return ReviewResult(
        comments=[],
        summary="No changes to review.",
        provider=self.settings.provider,
        model=self.settings.model or "N/A",
      )

    context = ReviewContext(
      diff=diff,
      mode=self.settings.mode,
      focus=self.settings.focus,
      style_guide=self.settings.style_guide,
      max_comments=self.settings.max_comments,
    )

    provider = get_provider(self.settings.provider, self.settings.model)
    return provider.review(context)


def run_review(
  branch: str | None = None,
  base: str = "main",
  provider: str | None = None,
  model: str | None = None,
  mode: ReviewMode = ReviewMode.QUICK,
  focus: list[FocusArea] | None = None,
  config_path: Path | None = None,
  files: list[str] | None = None,
) -> ReviewResult:
  """Run a code review with the given options."""
  settings = load_config(config_path).model_copy(deep=True)

  if provider:
    settings.provider = provider
  if model:
    settings.model = model
  if mode:
    settings.mode = mode
  if focus:
    settings.focus = focus

  orchestrator = ReviewOrchestrator(settings)

  if files:
    return orchestrator.review_files(files)
  if branch:
    return orchestrator.review_branch(branch, base)
  return orchestrator.review_staged()
