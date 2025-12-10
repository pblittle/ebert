"""Provider discovery and registration."""

from typing import Callable

from ebert.providers.base import ReviewProvider
from ebert.providers.detection import ProviderDetector


class ProviderNotFoundError(Exception):
  """Requested provider not found."""


class ProviderUnavailableError(Exception):
  """Provider found but not available (missing API key, etc)."""


ProviderFactory = Callable[[str | None], ReviewProvider]

_providers: dict[str, ProviderFactory] = {}


def register_provider(name: str, factory: ProviderFactory) -> None:
  """Register a provider factory."""
  _providers[name] = factory


def get_provider(name: str, model: str | None = None) -> ReviewProvider:
  """Get a provider by name."""
  if name not in _providers:
    available = ", ".join(_providers.keys()) or "none"
    raise ProviderNotFoundError(
      f"Provider '{name}' not found. Available: {available}"
    )

  provider = _providers[name](model)

  if not provider.is_available():
    detector = ProviderDetector(_providers)
    raise ProviderUnavailableError(detector.format_error(name))

  return provider


def list_providers() -> list[str]:
  """List registered provider names."""
  return list(_providers.keys())


class ProviderRegistry:
  """Registry for lazy provider loading."""

  @staticmethod
  def load_all() -> None:
    """Load all provider modules to trigger registration."""
    from ebert.providers import anthropic, gemini, ollama, openai  # noqa: F401
