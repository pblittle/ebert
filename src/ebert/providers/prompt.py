"""Shared prompt construction for providers."""

from ebert.models import FocusArea, ReviewContext, ReviewMode


def build_system_prompt(context: ReviewContext) -> str:
  """Build the system prompt for code review."""
  focus_desc = _get_focus_description(context.focus)
  mode_desc = _get_mode_description(context.mode)

  prompt = f"""You are an expert code reviewer. {mode_desc}

{focus_desc}

Rules:
- Only flag issues you are confident about. Avoid false positives.
- Check if an issue is mitigated elsewhere before flagging it.
- HIGH/CRITICAL: Must be exploitable or cause real bugs. Theoretical risks are MEDIUM at most.
- Do not flag missing trailing newlines, formatting, or style unless explicitly requested.
- Do not suggest changes that are already handled in the code.
- If the code looks correct, return an empty comments array.

Respond with JSON in this exact format:
{{
  "summary": "Brief overall assessment",
  "comments": [
    {{
      "file": "path/to/file.py",
      "line": 42,
      "severity": "high",
      "message": "Description of issue",
      "suggestion": "How to fix (optional)"
    }}
  ]
}}

Severity levels:
- critical: Security vulnerability, data loss, or crash in production
- high: Bug that will cause incorrect behavior
- medium: Code smell, potential issue, or maintainability concern
- low: Minor improvement suggestion
- info: Observation, no action required

Maximum comments: {context.max_comments}
Only include actionable feedback. Be concise."""

  if context.style_guide:
    prompt += f"\n\nStyle guide to follow:\n{context.style_guide}"

  return prompt


def build_user_prompt(context: ReviewContext) -> str:
  """Build the user prompt containing the diff."""
  files_desc = "\n".join(
    f"- {f.path} ({'new' if f.is_new else 'deleted' if f.is_deleted else 'modified'})"
    for f in context.diff.files
  )

  diff_content = "\n\n".join(f.content for f in context.diff.files)

  return f"""Review these changes:

Files changed:
{files_desc}

Diff:
```
{diff_content}
```"""


def _get_focus_description(focus: tuple[FocusArea, ...] | list[FocusArea]) -> str:
  """Get description for focus areas."""
  if FocusArea.ALL in focus:
    return "Review for security, bugs, style, and performance issues."

  descriptions = {
    FocusArea.SECURITY: "security vulnerabilities",
    FocusArea.BUGS: "bugs and logic errors",
    FocusArea.STYLE: "code style and readability",
    FocusArea.PERFORMANCE: "performance issues",
  }

  areas = [descriptions[f] for f in focus if f in descriptions]
  return f"Focus on: {', '.join(areas)}."


def _get_mode_description(mode: ReviewMode) -> str:
  """Get description for review mode."""
  if mode == ReviewMode.QUICK:
    return "Provide a quick review focusing on critical issues only."
  return "Provide a thorough, comprehensive code review."
