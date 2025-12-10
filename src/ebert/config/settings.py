"""Application settings."""

from pydantic import BaseModel, ConfigDict, Field

from ebert.models import EngineMode, FocusArea, ReviewMode, Severity


class Settings(BaseModel):
  """Application configuration."""

  model_config = ConfigDict(use_enum_values=False)

  engine: EngineMode = EngineMode.DETERMINISTIC
  provider: str = "gemini"
  model: str | None = None
  mode: ReviewMode = ReviewMode.QUICK
  focus: list[FocusArea] = Field(default_factory=lambda: [FocusArea.ALL])
  style_guide: str | None = None
  severity_threshold: Severity = Severity.LOW
  max_comments: int = 20
