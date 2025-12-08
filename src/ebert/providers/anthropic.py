"""Anthropic Claude provider."""

import os
from typing import Any

from ebert.models import ReviewComment, ReviewContext, ReviewResult, Severity
from ebert.providers.base import ReviewProvider
from ebert.providers.parser import extract_json
from ebert.providers.prompt import build_system_prompt, build_user_prompt
from ebert.providers.registry import register_provider


class AnthropicProvider(ReviewProvider):
  """Anthropic Claude LLM provider."""

  DEFAULT_MODEL = "claude-opus-4-5-20251101"

  def __init__(self, model: str | None = None):
    self._model = model or self.DEFAULT_MODEL
    self._api_key = os.environ.get("ANTHROPIC_API_KEY")
    self._client: Any = None

  @property
  def name(self) -> str:
    return "anthropic"

  @property
  def model(self) -> str:
    return self._model

  def is_available(self) -> bool:
    return self._api_key is not None

  def _get_client(self) -> Any:
    if self._client is None:
      try:
        from anthropic import Anthropic
        self._client = Anthropic(api_key=self._api_key)
      except ImportError as e:
        raise ImportError(
          "anthropic not installed. Install with: pip install 'ebert[anthropic]'"
        ) from e
    return self._client

  def review(self, context: ReviewContext) -> ReviewResult:
    client = self._get_client()

    system_prompt = build_system_prompt(context)
    user_prompt = build_user_prompt(context)

    response = client.messages.create(
      model=self._model,
      max_tokens=4096,
      system=system_prompt,
      messages=[{"role": "user", "content": user_prompt}],
    )

    content = response.content[0].text if response.content else "{}"
    return self._parse_response(content)

  def _parse_response(self, response_text: str) -> ReviewResult:
    data = extract_json(response_text)

    comments = [
      ReviewComment(
        file=c.get("file", "unknown"),
        line=c.get("line"),
        severity=Severity(c.get("severity", "medium")),
        message=c.get("message", ""),
        suggestion=c.get("suggestion"),
      )
      for c in data.get("comments", [])
    ]

    return ReviewResult(
      comments=comments,
      summary=data.get("summary", "No summary provided."),
      provider=self.name,
      model=self.model,
    )


def _create_anthropic(model: str | None) -> ReviewProvider:
  return AnthropicProvider(model)


register_provider("anthropic", _create_anthropic)
