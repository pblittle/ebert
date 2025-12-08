"""Configuration file loading."""

from pathlib import Path

import yaml

from ebert.config.settings import Settings
from ebert.models import FocusArea, ReviewMode, Severity

CONFIG_FILENAMES = [".ebert.yaml", ".ebert.yml", "ebert.yaml", "ebert.yml"]


def load_config(config_path: Path | None = None) -> Settings:
  """Load configuration from file or defaults."""
  if config_path:
    return _load_from_file(config_path)

  for filename in CONFIG_FILENAMES:
    path = Path.cwd() / filename
    if path.exists():
      return _load_from_file(path)

  return Settings()


def _load_from_file(path: Path) -> Settings:
  """Load settings from a YAML file."""
  if not path.exists():
    raise FileNotFoundError(f"Config file not found: {path}")

  with open(path) as f:
    data = yaml.safe_load(f) or {}

  return _parse_config(data)


def _parse_config(data: dict) -> Settings:
  """Parse config dict into Settings."""
  if "focus" in data:
    data["focus"] = [FocusArea(f) for f in data["focus"]]

  if "mode" in data:
    data["mode"] = ReviewMode(data["mode"])

  if "severity_threshold" in data:
    data["severity_threshold"] = Severity(data["severity_threshold"])

  return Settings(**data)
