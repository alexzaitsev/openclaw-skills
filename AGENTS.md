# OpenClaw Skills Repository Manual

This repository is the source of truth for deployable custom OpenClaw skills.
Keep each skill self-contained and deploy it from this repository; do not use a
VM workspace copy as the source of truth.

## Anki skill

`anki/` is a reviewed, owner-only AnkiConnect integration. Preserve its
loopback-only AnkiConnect model and its dry-run followed by explicit
confirmation workflow.

- `bin/anki-tool` is the Telegram-facing executable. Its mutating commands
  must be stale-safe: a dry run emits `plan_id`, and execution must validate
  that same plan against current Anki state.
- `bin/anki-admin` is SSH-only. It owns legacy migrations and JSON imports;
  do not expose it to the Telegram agent's executable allowlist.
- Keep card field conversion in small, pure functions under `anki/lib/`.
  Current and legacy Context storage must remain readable and editable.
- Keep statistics calculation and Markdown rendering deterministic and pure;
  keep AnkiConnect and OpenClaw CLI calls at their existing runtime boundaries.
- Whenever the executable surface, confirmation contract, or deployment model
  changes, update `anki/SKILL.md`, `anki/TG_BUTTONS.md`, and the relevant
  design/runbook in `../openclaw/skills/` in the same change.

## Validation

Run both mock integration suites after Anki changes:

```bash
anki/tests/anki-tool-test.sh
anki/tests/anki-stats-test.sh
```

They bind local mock HTTP servers. Run them where loopback sockets are
permitted, and keep test fixtures readable rather than replacing them with a
test framework unnecessarily.

Do not commit generated `__pycache__` files.
