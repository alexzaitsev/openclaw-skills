---
name: anki
description: REQUIRED for every Anki request. Read this skill before acting; use only anki-tool for direct AnkiConnect checks and confirmed additions.
bins: ["python3"]
---

# Anki

Manage the operator's language-organized Anki collection through local
AnkiConnect on the OpenClaw VM. For every Anki request, use only the reviewed
executables and this skill's references; never substitute inline Python, `curl`,
or generic shell commands, including for lookups.

## Read before acting

| Request | Required reading |
| --- | --- |
| Any addition | `ANKI_ROLES.md`, `ANKI_CARD_TYPES.md`, and [operations](references/operations.md) |
| Any mutation or Telegram callback | `TG_BUTTONS.md`, then the relevant operation reference |
| Statistics or notification settings | [statistics](references/statistics.md) |
| Telegram screenshot or an image on a card | [screenshots and images](references/screenshots-and-images.md) |

`ANKI_ROLES.md` selects the physical language deck and one study role; they
are separate. `ANKI_CARD_TYPES.md` selects the model. Read both before every
`add-basic` or `add-batch` dry run.

## Execution boundary

- Use only `anki-tool`, `anki-stats`, and `stage-inbound-image` as documented.
  `anki-stats-worker` is cron-only; `anki-admin` is SSH-only. For a
  machine-readable inventory, run `/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool capabilities --json`.
- Put each helper invocation on exactly one physical shell-command line. Do not
  use a newline, trailing `\`, shell wrapper, loop, or inline code.
- Do not initiate source inspection, `find`, `ls`, `sed`, `grep`, `rg`, `cat`,
  direct AnkiConnect requests, OpenClaw cron commands, or broad shell commands
  unless the operator explicitly requested that exact action.
- AnkiConnect must remain loopback-only at `http://127.0.0.1:8765`. Override
  `ANKI_CONNECT_URL` only on explicit request. Check availability with
  `/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool ping`.

## Mutation protocol

1. Perform necessary read checks and then the complete dry run. A successful
   lookup is never a substitute for a dry run.
2. Read `TG_BUTTONS.md` and send its required concise approval message and
   buttons in one `message` call, then return `NO_REPLY`. Never ask for an
   unbuttoned confirmation.
3. Execute only after a later explicit confirmation of that unchanged plan,
   with `--execute --plan-id <reviewed-plan-id>`. An exec approval is not Anki
   confirmation. Standalone `sync` is the only Telegram-facing exception.
4. Any content, scope, model, deck, duplicate, schema, image, or collection
   state change invalidates the plan: rerun the complete dry run and request a
   new confirmation.

Report a successful mutation as `sync: requested`, never as completed: this
AnkiConnect version does not expose sync completion. The other Anki client must
still sync to download server-side changes.

## Card decisions

- The learner studies Latin American Spanish; avoid Spain-only usage unless
  asked. Translate `usted` as `вы (один)` and `ustedes` as `вы (много)`.
- Select the language deck from the card front: Spanish is `Español`, English
  is `English`. Never use a role as a physical deck or create `deck:Español` /
  `deck:English` tags.
- Infer a clear role from `ANKI_ROLES.md`; ask only when the learning purpose is
  genuinely ambiguous. Each requested item keeps its own role in a compound
  request. `context` is only for disambiguation, never the answer.
- An ordinary Spanish phrase or screenshot defaults to `general`; the presence
  of a verb alone does not make it verb practice. Normalize a clear conjugated
  Spanish form to its infinitive.
- For a regular Spanish verb, add the infinitive unless examples or forms are
  requested. For an irregular standalone Spanish verb, follow the Spanish-only
  forms workflow in `TG_BUTTONS.md`: check each exact front first, never add
  `vosotros` unless requested, and treat `ver` as irregular.
- Do not infer extra English roles. Until `ANKI_ROLES.md` changes, every English
  card uses `general`; never apply the Spanish irregular-verb workflow to it.

## Hard boundaries

- Do not expose AnkiConnect, edit Anki's SQLite collection, or use raw
  `findNotes`, `notesInfo`, or `updateNoteFields` calls.
- Use only `check` or `search` for read-only card discovery.
- Do not move, edit, or delete without the mutation protocol. Use
  `delete-note` for an existing card: it deletes the underlying note and every
  card generated from it. Inspect a deck before deletion; never delete a
  parent deck with children. Use `--confirm-nonempty` only after approval of
  that exact non-empty deck plan.
- Use the dedicated Anki Telegram account, not the main OpenClaw chat.

## Reference map

- [Operations](references/operations.md): deck, card, and edit commands.
- [Statistics notifications](references/statistics.md): reports and cron-backed
  notification settings.
- [Screenshots and card images](references/screenshots-and-images.md): inbound
  media staging, visual extraction, and the one-image card workflow.
- `TG_BUTTONS.md`: authoritative Telegram UI and callback contract.

## SSH-only administration

`tag-decks`, `import-json`, and `merge-decks` belong to `bin/anki-admin` for an
SSH operator. Do not invoke, suggest, or confirm them in Telegram. They retain
their dry-run and exact-`plan_id` workflow; after a partial failure, report
reconciled state and never imply an automatic rollback.
