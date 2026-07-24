# Changelog

## 2026-07-20

- Added deterministic per-deck statistics calculation and plain-text reports.
- Added the cron-only `anki-stats-worker` and the reviewed `anki-stats`
  settings/preview helper.
- Added stale-safe, immutable-contract validation for the declared OpenClaw
  cron jobs and dedicated statistics confirmation callbacks.
- Added unit and mock integration coverage for metrics, rendering, cron
  reconciliation, failures, and stale plans.
- Cron reconciliation explicitly includes disabled jobs so the retained
  English schedule remains manageable while paused.

## Unreleased

- Made the `anki-tool` mock integration harness portable and order-independent:
  it canonicalizes temporary paths, derives fixture metadata and created IDs,
  and verifies each sync call relative to the operation that triggered it.
- Added a pure shared note-field layer. `add-basic`, `search`, `edit-note`,
  and `edit-batch` now consistently support both dedicated `Context` fields
  and the legacy context suffix in `Back`.
- Every Telegram-facing mutation except standalone `sync` now emits a
  stale-safe `plan_id` and requires it for `--execute`. The fingerprint covers
  the reviewed request and the relevant current Anki state.
- Split legacy bulk operations into SSH-only `bin/anki-admin`; the
  Telegram-facing `anki-tool` no longer exposes imports or deck migrations.
  Imports and merges now verify post-write state and report reconciled partial
  completion rather than implying a rollback.
- Simplified the deck-state summary to one line with total, introduced, and
  consolidated learning items; removed card and due-now counts. The seven-day
  summary now omits the preceding week's retention value.
- Ordinary Spanish-addition controls now use `➕ Добавить` and `🔊 С аудио`.
  The cancel button is no longer shown for that flow.
- Irregular Spanish verb controls now use `➕ Добавить всё` and, when the
  infinitive is absent, `🔤 Только инфинитив`; they show no refusal button.
  For a mixed addition request, use only `➕ Добавить` when it is the sole
  control that can execute the complete reviewed plan.
- Added the reviewed Spanish TTS card model
  `Basic (type in the answer + reverse + Spanish TTS)`, which uses on-device
  `es_MX` speech only when the Spanish side is shown and stores no audio media.
- `add-basic`, `add-batch`, `fields`, and optional exact-card `check` now
  support the two reviewed model names. The helper reports the selected model
  in every add plan and rejects all other model names.
- Replaced `DECKS.md` with `ANKI_ROLES.md`, added `ANKI_CARD_TYPES.md`, and
  moved Telegram confirmation-button rules into `TG_BUTTONS.md`. Ordinary
  Spanish additions now offer a separate audio choice; irregular Spanish verb
  forms retain their dedicated forms choice.
- Context markup now uses only the card model's shared `.context` CSS; inline
  context presentation is not supported.
- Added Spanish role `números`, which creates `deck:números` for number and
  number-focused practice.
- Fixed `edit-note` and `edit-batch` tag verification to compare a
  case- and Unicode-normalized reviewed tag set rather than AnkiConnect's
  response order. Batch updates now continue when Anki normalizes tag order or
  Unicode representation after a successful write.
- Added a restrained Markdown hierarchy and Russian localization to statistics
  reports, including deterministic dates, weekdays, durations, and plurals.
- Simplified report wording to `Последние 7 дней`, labelled mature items as
  `элементов закреплено`, and replaced percentage-point deltas with the prior
  week's retention value.
- Moved the report and run dates into the `Вчера` and `Колода сейчас` headings
  and removed the separate timezone line.
- For an irregular **Spanish** verb whose infinitive already exists, the
  confirmation does not offer a duplicate infinitive-only path. Its
  `➕ Добавить всё` choice applies the reviewed existing-note edit and missing
  conjugation forms together.
- Made the required handling of `anki:verb:*` Telegram callbacks explicit:
  OpenClaw passes them to the agent as `callback_data: anki:verb:*`; execute
  the already reviewed selected plan immediately, without a further question
  or dry run.
- Made the irregular-verb workflow an explicit Spanish-only boundary. English
  verbs always use the ordinary add/edit dry run and `✅ Да` / `❌ Нет` buttons;
  they never receive Spanish conjugation forms or `anki:verb:*` buttons.

- For a new irregular Spanish verb, the agent prepares two reviewed
  alternatives before any write: infinitive plus Latin American present-tense
  forms, or the infinitive only. The Telegram choices are `➕ Добавить всё`
  and `🔤 Только инфинитив`; selecting one confirms only its corresponding
  displayed dry run. `ver` is explicitly treated as irregular.
- `stage-inbound-image` accepts only the two managed OpenClaw inbound roots:
  the legacy global location and the dedicated Anki workspace location used by
  current Telegram attachment delivery. It still rejects arbitrary paths,
  validates the image signature and size, and stages the copy with mode `0600`.
- Physical decks now represent languages: Spanish additions target `Español`,
  while `English` is reserved for a future English deck with its own role
  taxonomy. The former Spanish category decks are represented by
  `deck:general`, `deck:verbos`, `deck:reglas`, and `deck:adjetivos` tags.
- `add-basic` now requires `--role`; `add-batch --note` now takes
  `LANGUAGE_DECK ROLE FRONT BACK [CONTEXT]`; and JSON import groups require a
  `role`. New notes derive `deck:<role>` from the explicit language-specific
  role instead of the physical deck name.
- The machine-readable capabilities contract is now version `2` and declares
  the language-deck / `deck:<role>` organization explicitly.
- New notes created by `add-basic`, `add-batch`, and `import-json` now always
  receive their explicit `deck:<role>` tag in addition to requested non-role
  tags. Manually passing a second `deck:*` tag is rejected.
- Added `tag-decks --all` for aggregate, reviewed legacy deck-role tagging. It
  adds `deck:<deck-name>` without replacing current note tags, reports only
  counts per deck, verifies writes, and requires a dry-run `plan_id` to execute.
- Added `anki-tool capabilities --json` as the reviewed, machine-readable
  command inventory. The skill now forbids agent-initiated source inspection,
  shell loops, and generic shell commands; non-helper commands require the
  operator to ask for that exact action.
- `edit-batch` now supports global and per-note tag additions/removals. It
  reads and preserves each note's unrelated existing tags, verifies the final
  full tag set, and requires a dry-run `plan_id` for execute mode so stale
  plans cannot apply after another tag or field change.
- Added `edit-batch` for one dry-run/confirmation/execute operation across
  several existing notes. This replaces unsafe agent-generated shell loops and
  verifies each edit before one sync request.
- Telegram edit plans now identify cards by their front text, not just opaque
  note IDs, and every completed dry run that expects `да`/`нет` must include
  the inline confirmation buttons.
- Telegram confirmation buttons are now required for every Anki data-change
  dry run, including `edit-note`, moves, imports, and merges. The approval
  message is a concise change summary rather than an unreadable raw helper
  dump; text confirmations remain supported.
- `edit-note` now supports repeatable `--add-tag` and `--remove-tag` options,
  with dry-run output, post-write verification, and one sync request.
- Moved `Подтверждаешь?` into the button-plan message so it renders alongside
  the controls without a duplicate final response.
- Added Telegram inline confirmation buttons for Anki addition dry runs. The
  `✅ Да` and `❌ Нет` callbacks preserve the existing two-step confirmation
  policy, while normal text replies and plan edits keep working unchanged.
- `add-batch --note` now accepts an optional fourth `CONTEXT` value for each
  note, matching `add-basic --context` without making context mandatory.
- `add-basic` and `add-batch` now read the live Anki model field list before
  every add operation. The new read-only `anki-tool fields` command exposes the
  current schema to the agent.
- Added extensible fields: `add-basic --field NAME VALUE` and
  `add-batch --note-field INDEX NAME VALUE`. Unknown or duplicate field names
  fail before any write, so a changed Anki model cannot silently receive a
  stale field mapping.
- Updated the skill contract: the agent must refresh the model schema before
  each add dry run and include relevant new fields in the reviewed plan.
