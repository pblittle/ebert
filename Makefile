.PHONY: install test lint review clean help

provider ?= gemini

help:
	@echo "Usage: make <target> [provider=<name>]"
	@echo ""
	@echo "Targets:"
	@echo "  install   Install dependencies (provider=gemini|openai|anthropic|ollama|all)"
	@echo "  test      Run tests"
	@echo "  lint      Run linter"
	@echo "  review    Review staged changes"
	@echo "  clean     Remove build artifacts"

install:
	@command -v poetry >/dev/null 2>&1 || { echo "Poetry required. Install: curl -sSL https://install.python-poetry.org | python3 -"; exit 1; }
	poetry install --extras $(provider)

test:
	poetry run pytest

lint:
	poetry run ruff check .

review:
	poetry run ebert

clean:
	rm -rf dist/ *.egg-info/ .pytest_cache/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
