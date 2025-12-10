"""Tests for provider status reporting."""

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

  def test_format_error_includes_env_var_hint(self, monkeypatch, mock_providers):
    """Error message includes hint about required env var."""
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"]:
      monkeypatch.delenv(key, raising=False)

    detector = ProviderDetector(mock_providers)
    error = detector.format_error("openai")

    assert "OPENAI_API_KEY" in error
    assert "not available" in error

  def test_format_error_shows_provider_status(self, monkeypatch, mock_providers):
    """Error message shows status of all providers."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
    for key in ["OPENAI_API_KEY", "GEMINI_API_KEY"]:
      monkeypatch.delenv(key, raising=False)

    detector = ProviderDetector(mock_providers)
    error = detector.format_error("openai")

    assert "[ok] anthropic" in error
    assert "[--] openai" in error
    assert "[--] gemini" in error

  def test_format_error_no_hint_for_ollama(self, monkeypatch, mock_providers):
    """No env var hint for ollama (it has no API key)."""
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"]:
      monkeypatch.delenv(key, raising=False)

    detector = ProviderDetector(mock_providers)
    error = detector.format_error("ollama")

    assert "Set " not in error
