# OpenClaw Skills Repository

This repository is the source of truth for deployable custom OpenClaw skills.
Keep every skill self-contained; do not edit a VM workspace copy as its source.
Keep runtime documentation lean: use `SKILL.md` plus direct references for
needed detail, and keep change history in Git rather than a skill-local
`CHANGELOG.md`.

## Anki

`anki/` is an owner-only, loopback AnkiConnect integration. Preserve its
dry-run, explicit-confirmation, stale-safe write model.

- `bin/anki-tool` is the Telegram-facing executable. Every mutation must emit
  a `plan_id` on dry run and validate that plan against current Anki state at
  execution.
- `bin/anki-admin` is SSH-only for legacy migrations and JSON imports; never
  add it to the Telegram executable allowlist.
- Keep card-field conversion, statistics calculation, and Markdown rendering
  small, deterministic, and pure under `anki/lib/`. Keep AnkiConnect and
  OpenClaw CLI calls at their existing runtime boundaries. Both current and
  legacy Context storage must remain readable and editable.
- When changing the executable surface, confirmation contract, or deployment
  model, update `anki/SKILL.md`, `anki/TG_BUTTONS.md`, and the matching
  design/runbook in `../openclaw/skills/` together.

## Validation

Run both mock integration suites after Anki changes:

```bash
anki/tests/anki-tool-test.sh
anki/tests/anki-stats-test.sh
```

They bind local mock HTTP servers. Keep fixtures readable; do not introduce a
test framework solely for them. Do not commit generated `__pycache__` files.
