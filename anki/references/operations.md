# Anki tool operations

All examples are one physical command line. Mutating commands are dry runs by
default; apply the mutation protocol in `../SKILL.md` before adding
`--execute --plan-id <reviewed-plan-id>`.

## Decks and lookups

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool decks
```

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool deck-info --deck Español
```

Use `deck-info` before answering about or deleting a deck. It reports exact
name, card/note count, child decks, and emptiness. Handle children explicitly:
`delete-deck` refuses parent decks with children.

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool check --deck Español --front "decir"
```

Use `check` for an exact front, including “add if absent.” If present, report
it; if absent, prepare the normal addition dry run.

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool search --deck Español --query "yo digo"
```

Use `search` to inspect several notes, find forms, or collect note IDs. It
returns note IDs, front, back, and context.

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool sync
```

`sync` requests synchronization without another mutation.

## Deck mutations

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool create-deck --deck English
```

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool delete-deck --deck English
```

The delete dry run reports cards, notes, and `empty`. For a non-empty deck,
include `--confirm-nonempty` only when executing the exact approved plan. The
helper uses AnkiConnect's required `cardsToo=true` only after this verified
count, so an approved empty deletion removes zero cards.

## Existing-card deletion

Use `search` or `check` first to identify the exact note ID. A note can produce
multiple cards (for example, forward and reverse); `delete-note` removes that
note and all of its generated cards, so its dry run must show the intended
front, back, affected cards, and decks before approval.

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool delete-note --note-id 123456789
```

## Additions

Before every `add-basic` or `add-batch` dry run, read `ANKI_ROLES.md` and
`ANKI_CARD_TYPES.md`, then read live fields for every selected model:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool fields --model "<chosen model>"
```

Use field names exactly. Provide relevant added fields with `--field NAME VALUE`
or `--note-field INDEX NAME VALUE`; do not assume only `Front` and `Back`.

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool add-basic --deck Español --role general --model "Basic (type in the answer + reverse)" --front "la palabra" --back "word" --context "only if needed for disambiguation" --tag source:telegram
```

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool add-batch --model "Basic (type in the answer + reverse)" --note Español general "¿Puedes cambiar tus planes?" "Ты можешь изменить свои планы?" "optional disambiguation" --note Español verbos "cambiar" "менять; изменять" --tag source:telegram
```

Use `add-batch` for every multi-note request. Each `--note` is
`LANGUAGE_DECK ROLE FRONT BACK [CONTEXT]`; omit context when absent. A role
automatically adds its `deck:<role>` tag. Do not pass that role tag separately
or derive a tag from the physical deck.

For `add-batch`, `--note-field` uses the one-based note index:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool add-batch --model "<chosen model>" --note Español general "Front" "Back" --note-field 1 "Example" "Puedes cambiar los planes."
```

## Moves and edits

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool move-note --note-id 123456789 --target Español
```

When “it” refers to a newly added note, use the immediately preceding
`add-basic` note ID.

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool edit-note --note-id 123456789 --front "decir" --back "говорить; сказать" --context "англ. say" --add-tag source:telegram --remove-tag review-later
```

`edit-note` changes any combination of front, back, context, and tags. Use
`--clear-context` to remove context and repeat `--add-tag` / `--remove-tag` as
needed. Media editing is excluded: field markup for image, audio, or video
fails rather than risking lost media.

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool edit-batch --note 1780781752051 "я смотрю" "англ. to watch" --note 1780781752083 "ты смотришь" "англ. to watch" --add-tag source:telegram --note-add-tag 1780781752051 grammar::verbs
```

Use `edit-batch` whenever one request affects multiple existing notes. Each
`--note` is `NOTE_ID BACK [CONTEXT]`; use `=` to retain back or context and
`""` to clear context. Global tag deltas use `--add-tag` / `--remove-tag`; one
note uses `--note-add-tag NOTE_ID TAG` / `--note-remove-tag NOTE_ID TAG`.
Unrelated tags are preserved.
