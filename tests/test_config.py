"""Tests for configuration loading."""

import tempfile
from pathlib import Path

from ebert.config.loader import _parse_config, load_config
from ebert.config.settings import Settings
from ebert.models import FocusArea, ReviewMode, Severity


class TestSettings:
  def test_default_settings(self) -> None:
    settings = Settings()
    assert settings.provider == "gemini"
    assert settings.model is None
    assert settings.mode == ReviewMode.QUICK
    assert FocusArea.ALL in settings.focus

  def test_custom_settings(self) -> None:
    settings = Settings(
      provider="openai",
      model="gpt-4",
      mode=ReviewMode.FULL,
      focus=[FocusArea.SECURITY],
    )
    assert settings.provider == "openai"
    assert settings.model == "gpt-4"
    assert settings.mode == ReviewMode.FULL
    assert settings.focus == [FocusArea.SECURITY]


class TestConfigLoader:
  def test_load_default_config(self) -> None:
    settings = load_config()
    assert isinstance(settings, Settings)

  def test_load_from_file(self) -> None:
    config_content = """
provider: anthropic
model: claude-3-sonnet
mode: full
focus:
  - security
  - bugs
max_comments: 10
"""
    with tempfile.NamedTemporaryFile(
      mode="w", suffix=".yaml", delete=False
    ) as f:
      f.write(config_content)
      f.flush()

      settings = load_config(Path(f.name))
      assert settings.provider == "anthropic"
      assert settings.model == "claude-3-sonnet"
      assert settings.mode == ReviewMode.FULL
      assert FocusArea.SECURITY in settings.focus
      assert FocusArea.BUGS in settings.focus
      assert settings.max_comments == 10

  def test_parse_config_with_enums(self) -> None:
    data = {
      "provider": "ollama",
      "mode": "quick",
      "focus": ["security"],
      "severity_threshold": "high",
    }
    settings = _parse_config(data)
    assert settings.provider == "ollama"
    assert settings.mode == ReviewMode.QUICK
    assert settings.focus == [FocusArea.SECURITY]
    assert settings.severity_threshold == Severity.HIGH

