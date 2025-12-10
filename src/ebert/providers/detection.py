"""Provider auto-detection."""

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
  from ebert.providers.base import ReviewProvider


@dataclass(frozen=True)
class ProviderStatus:
  """Availability status for a provider."""

  name: str
  available: bool
  reason: str


class ProviderDetector:
  """Detects available providers based on environment."""

  DETECTION_ORDER = ("anthropic", "openai", "gemini", "ollama")
  ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
  }

  def __init__(self, providers: dict[str, Callable[[str | None], "ReviewProvider"]]):
    self._providers = providers

  def detect(self) -> str | None:
    """Return first available provider, or None."""
    for name in self.DETECTION_ORDER:
      if self._is_available(name):
        return name
    return None

  def get_status(self) -> list[ProviderStatus]:
    """Get status for all providers in detection order."""
    return [self._check(name) for name in self.DETECTION_ORDER if name in self._providers]

  def format_error(self, failed: str) -> str:
    """Format error message with provider status."""
    lines = [f"Provider '{failed}' is not available.", "", "Provider status:"]
    for s in self.get_status():
      lines.append(f"  {'[ok]' if s.available else '[--]'} {s.name}: {s.reason}")
    if failed in self.ENV_VARS:
      lines.extend(["", f"Set {self.ENV_VARS[failed]} to use {failed}."])
    return "\n".join(lines)

  def _is_available(self, name: str) -> bool:
    if name not in self._providers:
      return False
    if name in self.ENV_VARS:
      return bool(os.environ.get(self.ENV_VARS[name]))
    try:
      return self._providers[name](None).is_available()
    except Exception:
      return False

  def _check(self, name: str) -> ProviderStatus:
    if name in self.ENV_VARS:
      env_var = self.ENV_VARS[name]
      has_key = bool(os.environ.get(env_var))
      return ProviderStatus(name, has_key, f"{env_var} {'set' if has_key else 'not set'}")
    available = self._is_available(name)
    return ProviderStatus(name, available, "reachable" if available else "not reachable")
