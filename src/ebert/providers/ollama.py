"""Ollama local LLM provider."""

import os

import httpx

from ebert.models import ReviewComment, ReviewContext, ReviewResult, Severity
from ebert.providers.base import ReviewProvider
from ebert.providers.parser import extract_json
from ebert.providers.prompt import build_system_prompt, build_user_prompt
from ebert.providers.registry import register_provider


class OllamaProvider(ReviewProvider):
  """Ollama local LLM provider."""

  DEFAULT_MODEL = "codellama"
  DEFAULT_HOST = "http://localhost:11434"
  DEFAULT_HEALTH_TIMEOUT = 5.0

  def __init__(self, model: str | None = None):
    self._model = model or self.DEFAULT_MODEL
    self._host = os.environ.get("OLLAMA_HOST", self.DEFAULT_HOST)
    self._health_timeout = float(
      os.environ.get("OLLAMA_HEALTH_TIMEOUT", self.DEFAULT_HEALTH_TIMEOUT)
    )

  @property
  def name(self) -> str:
    return "ollama"

  @property
  def model(self) -> str:
    return self._model

  def is_available(self) -> bool:
    try:
      response = httpx.get(f"{self._host}/api/tags", timeout=self._health_timeout)
      return response.status_code == 200
    except httpx.RequestError:
      return False

  def review(self, context: ReviewContext) -> ReviewResult:
    system_prompt = build_system_prompt(context)
    user_prompt = build_user_prompt(context)

    response = self._request_with_retry(system_prompt, user_prompt)
    data = response.json()
    return self._parse_response(data.get("response", "{}"))

  def _request_with_retry(
    self,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 2,
  ) -> httpx.Response:
    """Make request with retry on transient failures."""
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
      try:
        response = httpx.post(
          f"{self._host}/api/generate",
          json={
            "model": self._model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
            "format": "json",
          },
          timeout=120.0,
        )
        response.raise_for_status()
        return response
      except (httpx.ConnectError, httpx.ReadTimeout) as e:
        last_error = e
        if attempt < max_retries:
          continue
      except httpx.HTTPStatusError:
        raise

    raise last_error or RuntimeError("Request failed")

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


def _create_ollama(model: str | None) -> ReviewProvider:
  return OllamaProvider(model)


register_provider("ollama", _create_ollama)
