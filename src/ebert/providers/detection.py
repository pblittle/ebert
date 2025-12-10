"""Provider status reporting."""

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
  """Reports provider availability status."""

  PROVIDER_ORDER = ("anthropic", "openai", "gemini", "ollama")
  ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
  }

  def __init__(self, providers: dict[str, Callable[[str | None], "ReviewProvider"]]):
    self._providers = providers

  def format_error(self, failed: str) -> str:
    """Format error message with provider status."""
    lines = [f"Provider '{failed}' is not available.", "", "Provider status:"]
    for status in self._get_status():
      icon = "[ok]" if status.available else "[--]"
      lines.append(f"  {icon} {status.name}: {status.reason}")
    if failed in self.ENV_VARS:
      lines.extend(["", f"Set {self.ENV_VARS[failed]} to use {failed}."])
    return "\n".join(lines)

  def _get_status(self) -> list[ProviderStatus]:
    """Get status for all registered providers."""
    return [self._check(name) for name in self.PROVIDER_ORDER if name in self._providers]

  def _check(self, name: str) -> ProviderStatus:
    """Check availability of a single provider."""
    if name in self.ENV_VARS:
      env_var = self.ENV_VARS[name]
      has_key = bool(os.environ.get(env_var))
      return ProviderStatus(name, has_key, f"{env_var} {'set' if has_key else 'not set'}")
    available = self._check_runtime(name)
    return ProviderStatus(name, available, "reachable" if available else "not reachable")

  def _check_runtime(self, name: str) -> bool:
    """Check if provider is available at runtime (for ollama)."""
    if name not in self._providers:
      return False
    try:
      return self._providers[name](None).is_available()
    except Exception:
      return False
