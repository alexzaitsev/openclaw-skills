# Telegram inline-button contract

Use these buttons only in the dedicated Anki Telegram DM. After a successful
dry run, send exactly one `message` tool call containing the concise reviewed
plan and its required inline buttons, then return `NO_REPLY`. Never ask for
confirmation as unbuttoned text.

All callbacks authorize only the unchanged, immediately preceding plan. A text
reply of `да` or `нет` has the same scope as the matching button. Any content,
scope, model, or collection-state change invalidates the plan and requires a
new dry run and new buttons.

Do not paste raw helper output into Telegram. A concise approval view must keep
the details needed to approve the actual write: for additions, deck, role,
model, front, back, context, extra fields, tags, and duplicate result; for
edits, current front text and only the changes; for moves/imports/merges, the
source, destination, affected count, and tag changes; and for deck deletion,
the exact deck name, card/note counts, emptiness, and non-empty warning.

## Standard non-addition changes

For `create-deck`, `delete-deck`, `edit-note`, `edit-batch`, `tag-decks`,
`move-note`, `import-json`, and `merge-decks`, send `✅ Да` and `❌ Нет` with
callbacks `anki:confirm:yes` and `anki:confirm:no`.

## Spanish card additions with an audio choice

For every Spanish `add-basic` or `add-batch` operation that does **not** use
the irregular-verb forms choice below, prepare two complete dry runs before
sending the message:

1. default model `Basic (type in the answer + reverse)`;
2. audio model `Basic (type in the answer + reverse + Spanish TTS)`.

The message must state that the audio alternative uses on-device `es_MX` TTS
and no media files. Show the relevant shared card details once and identify the
two model alternatives clearly. Then send this single-row button set, in this
exact order:

```json
{
  "action": "send",
  "channel": "telegram",
  "accountId": "anki",
  "target": "142309269",
  "message": "<reviewed default and audio addition plans>\\n\\nЧто добавить?",
  "buttons": [[
    {
      "text": "✅ Да",
      "callback_data": "anki:confirm:yes",
      "style": "success"
    },
    {
      "text": "🔊 Да, с аудио",
      "callback_data": "anki:confirm:audio",
      "style": "primary"
    },
    {
      "text": "❌ Нет",
      "callback_data": "anki:confirm:no",
      "style": "danger"
    }
  ]]
}
```

`anki:confirm:yes` executes only the reviewed default-model add command(s).
`anki:confirm:audio` executes only the corresponding reviewed audio-model add
command(s). `anki:confirm:no` cancels both alternatives. Do not offer the
audio button for English or non-Spanish cards: the audio model is `es_MX` only.

## Irregular Spanish verb forms

For the existing Spanish-only irregular-verb workflow, retain the forms choice
instead of adding an audio button. When the infinitive is absent, use
`✅ Да, с формами`, `⚠️ Да, инфинитив`, and `❌ Нет`, with callbacks
`anki:verb:forms`, `anki:verb:infinitive`, and `anki:verb:no`. When the
infinitive already exists, use only `✅ Да, с формами` and `❌ Нет` with
`anki:verb:forms` and `anki:verb:no`.

For an absent infinitive, the message is a comparison of the reviewed
forms-and-infinitive plan and infinitive-only plan, followed by this row:

```json
[
  {"text": "✅ Да, с формами", "callback_data": "anki:verb:forms", "style": "success"},
  {"text": "⚠️ Да, инфинитив", "callback_data": "anki:verb:infinitive", "style": "primary"},
  {"text": "❌ Нет", "callback_data": "anki:verb:no", "style": "danger"}
]
```

For an existing infinitive, state that no duplicate infinitive will be created,
show the reviewed edit-and-forms plan, and use this row:

```json
[
  {"text": "✅ Да, с формами", "callback_data": "anki:verb:forms", "style": "success"},
  {"text": "❌ Нет", "callback_data": "anki:verb:no", "style": "danger"}
]
```

Each forms callback executes only its already displayed, unchanged complete
plan. The forms workflow remains Spanish-only and never adds `vosotros` unless
requested.

## Statistics settings

For `anki-stats configure` and `anki-stats disable`, use `✅ Да` and `❌ Нет`
with `anki:stats:yes:<plan-id>` and `anki:stats:no:<plan-id>`. The message
must contain the current and proposed settings plus `Подтверждаешь?`; the
callback executes only the matching unchanged plan ID.

```json
[
  {"text": "✅ Да", "callback_data": "anki:stats:yes:<plan-id>", "style": "success"},
  {"text": "❌ Нет", "callback_data": "anki:stats:no:<plan-id>", "style": "danger"}
]
```
