"""Shared response parsing utilities."""

import json
import re
from typing import Any

MAX_RESPONSE_LENGTH = 1_000_000  # 1MB limit for regex processing


def extract_json(text: str) -> dict[str, Any]:
  """Extract JSON from LLM response, handling markdown code blocks."""
  text = text.strip()

  if len(text) > MAX_RESPONSE_LENGTH:
    raise ValueError(f"Response too large ({len(text)} bytes), max {MAX_RESPONSE_LENGTH}")

  # Try direct JSON parse first
  try:
    return json.loads(text)
  except json.JSONDecodeError:
    pass

  # Try extracting from markdown code block
  json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
  if json_match:
    try:
      return json.loads(json_match.group(1).strip())
    except json.JSONDecodeError:
      pass

  # Try finding JSON object in text
  brace_match = re.search(r"\{.*\}", text, re.DOTALL)
  if brace_match:
    try:
      return json.loads(brace_match.group(0))
    except json.JSONDecodeError:
      pass

  raise ValueError(f"Could not extract valid JSON from response: {text[:200]}...")
