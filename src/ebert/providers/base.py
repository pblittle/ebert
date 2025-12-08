"""Base provider protocol."""

from abc import ABC, abstractmethod

from ebert.models import ReviewContext, ReviewResult


class ReviewProvider(ABC):
  """Abstract base for LLM review providers."""

  @abstractmethod
  def review(self, context: ReviewContext) -> ReviewResult:
    """Perform a code review."""
    ...

  @property
  @abstractmethod
  def name(self) -> str:
    """Provider name."""
    ...

  @property
  @abstractmethod
  def model(self) -> str:
    """Model being used."""
    ...

  @abstractmethod
  def is_available(self) -> bool:
    """Check if provider is configured and available."""
    ...
