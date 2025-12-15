"""Core domain models for code review."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class Severity(Enum):
  """Issue severity levels."""

  CRITICAL = "critical"
  HIGH = "high"
  MEDIUM = "medium"
  LOW = "low"
  INFO = "info"


class ReviewMode(Enum):
  """Review thoroughness mode."""

  QUICK = "quick"
  FULL = "full"


class EngineMode(Enum):
  """Review execution engine."""

  DETERMINISTIC = "deterministic"
  LLM = "llm"


class FocusArea(Enum):
  """Areas to focus the review on."""

  SECURITY = "security"
  BUGS = "bugs"
  STYLE = "style"
  PERFORMANCE = "performance"
  ALL = "all"


@dataclass(frozen=True)
class FileDiff:
  """A single file's diff."""

  path: str
  content: str
  is_new: bool = False
  is_deleted: bool = False


@dataclass(frozen=True)
class DiffContext:
  """Collection of file diffs for review."""

  files: Sequence[FileDiff]
  base_ref: str = "HEAD"
  target_ref: str = "staged"


@dataclass(frozen=True)
class ReviewContext:
  """Context for a code review request."""

  diff: DiffContext
  mode: ReviewMode = ReviewMode.QUICK
  focus: Sequence[FocusArea] = field(default_factory=lambda: [FocusArea.ALL])
  style_guide: str | None = None
  max_comments: int = 20


@dataclass(frozen=True)
class ReviewComment:
  """A single review comment."""

  file: str
  line: int | None
  severity: Severity
  message: str
  suggestion: str | None = None


@dataclass(frozen=True)
class ReviewResult:
  """Result of a code review."""

  comments: Sequence[ReviewComment]
  summary: str
  provider: str
  model: str

  @property
  def has_severe_issues(self) -> bool:
    """Check if result contains HIGH or CRITICAL severity issues."""
    return any(c.severity in (Severity.HIGH, Severity.CRITICAL) for c in self.comments)
