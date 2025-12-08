# ebert

Uncompromising AI code review from the command line.

ebert reviews your staged git changes using any LLM provider - Claude, GPT, Gemini, or local models via Ollama. It returns concise, high-signal comments focused on bugs, security issues, and correctness. Works with any programming language your LLM understands.

## Example Output

```
$ git add .
$ ebert

╭─────────────────── Code Review (anthropic/claude-opus-4-5-20251101) ───────────────────╮
│ Clean implementation with good separation of concerns. Two issues need attention.      │
╰────────────────────────────────────────────────────────────────────────────────────────╯

┃ Severity ┃ File              ┃ Line ┃ Issue                                            ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ HIGH     │ src/auth.py       │   42 │ SQL injection via unsanitized user input         │
│ MEDIUM   │ src/api/routes.py │   87 │ Missing error handling for network timeout       │
└──────────┴───────────────────┴──────┴──────────────────────────────────────────────────┘

2 issue(s) found
```

## Quick Start

```bash
git clone https://github.com/pblittle/ebert.git && cd ebert
make install provider=anthropic
export ANTHROPIC_API_KEY=your-key
make review
```

## Usage

```bash
ebert                        # Review staged changes
ebert src/auth.py            # Review specific file
ebert src/*.py               # Review files matching glob
ebert src/ lib/              # Review multiple paths
ebert --full                 # Comprehensive review (not just critical issues)
ebert --branch feature/foo   # Review branch against main
ebert --focus security,bugs  # Focus on specific areas
ebert --format markdown      # Output for PR comments
ebert --provider ollama      # Use local model
```

## Providers

| Provider | Default Model | API Key |
|----------|---------------|---------|
| anthropic | claude-opus-4-5-20251101 | `ANTHROPIC_API_KEY` |
| openai | gpt-4o-mini | `OPENAI_API_KEY` |
| gemini | gemini-1.5-flash | `GEMINI_API_KEY` |
| ollama | codellama | (none - local) |

Install with: `make install provider=<name>` or `make install provider=all`

## Configuration

Optional. Create `.ebert.yaml` in your project:

```yaml
provider: anthropic
model: claude-opus-4-5-20251101
focus:
  - security
  - bugs
style_guide: |
  Follow PEP-8
  Use type hints
max_comments: 20
```

## License

MIT
