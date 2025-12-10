# Agent Guidelines for Ebert

## Before You Start

Read this entire file before making any changes to the codebase.

## Project Context

Ebert is an "uncompromising" AI code review CLI. The name references film critic Roger Ebert - the tool provides direct, honest feedback without unnecessary praise.

## Design Principles

1. **Provider Agnostic** - All LLM logic goes through the provider abstraction
2. **Immutability** - Domain models are frozen dataclasses
3. **Composition** - No deep inheritance hierarchies
4. **Minimal Dependencies** - Provider SDKs are optional extras
5. **Defensive Parsing** - Never trust LLM output format

## Code Patterns

### Adding a New Provider

1. Create `src/ebert/providers/<name>.py`
2. Inherit from `ReviewProvider` base class
3. Implement `review()`, `name`, `model`, `is_available()`
4. Register via `register_provider(name, factory)` in module
5. Add to `ProviderRegistry.load_all()` in `registry.py`
6. Add optional dependency to `pyproject.toml` extras

### Adding a New Output Format

1. Create formatter class in `src/ebert/output/formatter.py`
2. Implement `format(result: ReviewResult) -> str`
3. Add to `get_formatter()` factory function

## Testing Requirements

- All new code requires tests in `tests/`
- Run `make test` before committing
- Run `make lint` to check style

## Style Guide

- 2-space indentation (configured in ruff)
- 100 character line length
- Type hints on all public functions
- Docstrings for public APIs only
- No emoji in code or comments

## Common Pitfalls

- Don't import provider SDKs at module level (they're optional)
- Don't assume LLM response format - use `extract_json()` parser
- Don't leak file paths in error messages - sanitize them
- Don't add features beyond what's requested

## Review Modes

Ebert supports three review modes:

1. **Staged changes** (default) - `ebert` reviews `git diff --cached`
2. **Branch comparison** - `ebert --branch feature/x` compares against base
3. **File scanning** - `ebert src/*.py` reviews files directly without git

File scanning uses `extract_files_as_context()` which formats files as synthetic diffs.

## File Structure

```
src/ebert/
  __init__.py          # Version definition
  cli.py               # Entry point (don't add business logic here)
  models.py            # Domain models (keep frozen)
  review.py            # Orchestration (main flow)
  config/
    settings.py        # Pydantic settings model
    loader.py          # YAML loading
  diff/
    extractor.py       # Git operations + file scanning
  providers/
    base.py            # Abstract interface
    registry.py        # Factory pattern
    prompt.py          # Shared prompt building
    parser.py          # JSON extraction
    anthropic.py       # Provider implementations
    openai.py
    gemini.py
    ollama.py
  output/
    formatter.py       # All formatters
```

## Environment Variables

| Variable | Required For |
|----------|--------------|
| `ANTHROPIC_API_KEY` | anthropic provider |
| `OPENAI_API_KEY` | openai provider |
| `GEMINI_API_KEY` | gemini provider |
| `OLLAMA_HOST` | custom ollama endpoint |
