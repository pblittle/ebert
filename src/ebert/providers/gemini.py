"""Google Gemini provider."""

import os
from typing import Any

from ebert.models import ReviewComment, ReviewContext, ReviewResult, Severity
from ebert.providers.base import ReviewProvider
from ebert.providers.parser import extract_json
from ebert.providers.prompt import build_system_prompt, build_user_prompt
from ebert.providers.registry import register_provider


class GeminiProvider(ReviewProvider):
  """Google Gemini LLM provider."""

  DEFAULT_MODEL = "gemini-1.5-flash"

  def __init__(self, model: str | None = None):
    self._model = model or self.DEFAULT_MODEL
    self._api_key = os.environ.get("GEMINI_API_KEY")
    self._client: Any = None

  @property
  def name(self) -> str:
    return "gemini"

  @property
  def model(self) -> str:
    return self._model

  def is_available(self) -> bool:
    return self._api_key is not None

  def _get_client(self) -> Any:
    if self._client is None:
      try:
        import google.generativeai as genai
        genai.configure(api_key=self._api_key)
        self._client = genai.GenerativeModel(self._model)
      except ImportError as e:
        raise ImportError(
          "google-generativeai not installed. "
          "Install with: pip install 'ebert[gemini]'"
        ) from e
    return self._client

  def review(self, context: ReviewContext) -> ReviewResult:
    client = self._get_client()

    system_prompt = build_system_prompt(context)
    user_prompt = build_user_prompt(context)

    response = client.generate_content(
      f"{system_prompt}\n\n{user_prompt}",
      generation_config={"response_mime_type": "application/json"},
    )

    if not response.text:
      raise ValueError("Gemini returned empty response")

    return self._parse_response(response.text)

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


def _create_gemini(model: str | None) -> ReviewProvider:
  return GeminiProvider(model)


register_provider("gemini", _create_gemini)
