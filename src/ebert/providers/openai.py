"""OpenAI provider."""

import os
from typing import Any

from ebert.models import ReviewComment, ReviewContext, ReviewResult, Severity
from ebert.providers.base import ReviewProvider
from ebert.providers.parser import extract_json
from ebert.providers.prompt import build_system_prompt, build_user_prompt
from ebert.providers.registry import register_provider


class OpenAIProvider(ReviewProvider):
  """OpenAI LLM provider."""

  DEFAULT_MODEL = "gpt-4o-mini"

  def __init__(self, model: str | None = None):
    self._model = model or self.DEFAULT_MODEL
    self._api_key = os.environ.get("OPENAI_API_KEY")
    self._client: Any = None

  @property
  def name(self) -> str:
    return "openai"

  @property
  def model(self) -> str:
    return self._model

  def is_available(self) -> bool:
    return self._api_key is not None

  def _get_client(self) -> Any:
    if self._client is None:
      try:
        from openai import OpenAI
        self._client = OpenAI(api_key=self._api_key)
      except ImportError as e:
        raise ImportError(
          "openai not installed. Install with: pip install 'ebert[openai]'"
        ) from e
    return self._client

  def review(self, context: ReviewContext) -> ReviewResult:
    client = self._get_client()

    system_prompt = build_system_prompt(context)
    user_prompt = build_user_prompt(context)

    response = client.chat.completions.create(
      model=self._model,
      messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
      ],
      response_format={"type": "json_object"},
    )

    return self._parse_response(response.choices[0].message.content or "{}")

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


def _create_openai(model: str | None) -> ReviewProvider:
  return OpenAIProvider(model)


register_provider("openai", _create_openai)
