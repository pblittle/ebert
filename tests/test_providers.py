"""Tests for provider registry."""

import pytest
from ebert.models import ReviewContext, ReviewResult
from ebert.providers.base import ReviewProvider
from ebert.providers.registry import (
  ProviderNotFoundError,
  get_provider,
  list_providers,
  register_provider,
)


class MockProvider(ReviewProvider):
  def __init__(self, model: str | None = None):
    self._model = model or "mock-model"
    self._available = True

  @property
  def name(self) -> str:
    return "mock"

  @property
  def model(self) -> str:
    return self._model

  def is_available(self) -> bool:
    return self._available

  def review(self, context: ReviewContext) -> ReviewResult:
    return ReviewResult(
      comments=[],
      summary="Mock review",
      provider=self.name,
      model=self.model,
    )


class TestProviderRegistry:
  def test_register_and_get_provider(self) -> None:
    register_provider("mock", lambda m: MockProvider(m))
    provider = get_provider("mock")
    assert provider.name == "mock"

  def test_provider_not_found(self) -> None:
    with pytest.raises(ProviderNotFoundError):
      get_provider("nonexistent_provider_xyz")

  def test_list_providers(self) -> None:
    register_provider("mock2", lambda m: MockProvider(m))
    providers = list_providers()
    assert "mock2" in providers

  def test_provider_with_model(self) -> None:
    register_provider("mock3", lambda m: MockProvider(m))
    provider = get_provider("mock3", "custom-model")
    assert provider.model == "custom-model"
