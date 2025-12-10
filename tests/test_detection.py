"""Tests for provider auto-detection."""

import pytest
from ebert.providers.detection import ProviderDetector


@pytest.fixture
def mock_providers():
  """Create mock provider factories for testing."""
  def make_factory(available: bool):
    def factory(model=None):
      class MockProvider:
        def is_available(self):
          return available
      return MockProvider()
    return factory

  return {
    "anthropic": make_factory(True),
    "openai": make_factory(True),
    "gemini": make_factory(True),
    "ollama": make_factory(False),
  }


class TestProviderDetector:
  """Tests for ProviderDetector."""

  @pytest.mark.parametrize("env_var,expected", [
    ("ANTHROPIC_API_KEY", "anthropic"),
    ("OPENAI_API_KEY", "openai"),
    ("GEMINI_API_KEY", "gemini"),
  ])
  def test_detect_by_env_var(self, monkeypatch, mock_providers, env_var, expected):
    """Detects provider based on environment variable."""
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"]:
      monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(env_var, "test-key")

    detector = ProviderDetector(mock_providers)
    assert detector.detect() == expected

  def test_detect_priority_order(self, monkeypatch, mock_providers):
    """Prefers anthropic over openai when both available."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key1")
    monkeypatch.setenv("OPENAI_API_KEY", "key2")

    detector = ProviderDetector(mock_providers)
    assert detector.detect() == "anthropic"

  def test_detect_falls_back_to_ollama(self, monkeypatch, mock_providers):
    """Falls back to ollama when no API keys set."""
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"]:
      monkeypatch.delenv(key, raising=False)
    mock_providers["ollama"] = lambda m: type("P", (), {"is_available": lambda s: True})()

    detector = ProviderDetector(mock_providers)
    assert detector.detect() == "ollama"

  def test_detect_returns_none_when_nothing_available(self, monkeypatch, mock_providers):
    """Returns None when no providers available."""
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"]:
      monkeypatch.delenv(key, raising=False)

    detector = ProviderDetector(mock_providers)
    assert detector.detect() is None

  def test_get_status_returns_all_providers(self, monkeypatch, mock_providers):
    """Returns status for all providers in order."""
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    for key in ["ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
      monkeypatch.delenv(key, raising=False)

    detector = ProviderDetector(mock_providers)
    status = detector.get_status()

    assert [s.name for s in status] == ["anthropic", "openai", "gemini", "ollama"]
    assert status[1].available is True
    assert status[0].available is False

  def test_format_error_includes_env_var_hint(self, monkeypatch, mock_providers):
    """Error message includes hint about required env var."""
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"]:
      monkeypatch.delenv(key, raising=False)

    detector = ProviderDetector(mock_providers)
    error = detector.format_error("openai")

    assert "OPENAI_API_KEY" in error
    assert "not available" in error
