# Telegram inline-button contract

Use these buttons only in the dedicated Anki Telegram DM. After a successful
mutation dry run, send exactly one `message` call with the concise reviewed
plan and required buttons, then return `NO_REPLY`; never ask in plain text.

Each callback and a matching text reply (`да` / `нет`) authorize only the
unchanged, immediately preceding plan. Any scope, content, model, or
collection-state change requires a new dry run and new buttons.

Do not paste raw helper output. Show enough to approve the write: additions
need deck, role, model, fields, tags, and duplicate result; edits need current
front and changes; moves need source, target, count, and tags; deletion needs
deck, card/note counts, emptiness, and warning. For one staged image, add type,
dimensions, bytes, SHA-256, and `Front` placement—never its VM path.

## Standard non-addition changes

For `create-deck`, `delete-deck`, `edit-note`, `edit-batch`, and `move-note`:

```json
[
  {"text": "✅ Да", "callback_data": "anki:confirm:yes", "style": "success"},
  {"text": "❌ Нет", "callback_data": "anki:confirm:no", "style": "danger"}
]
```

## Spanish card additions with an audio choice

For every Spanish `add-basic` or `add-batch` operation that does **not** use
the irregular-verb forms choice below, prepare two complete dry runs before
sending the message:

1. default model `Basic (type in the answer + reverse)`;
2. audio model `Basic (type in the answer + reverse + Spanish TTS)`.

State that audio is on-device `es_MX` TTS with no media file. Show shared card
details once and identify both models, then use this row in this exact order:

```json
[
  {"text": "➕ Добавить", "callback_data": "anki:confirm:yes", "style": "success"},
  {"text": "🔊 С аудио", "callback_data": "anki:confirm:audio", "style": "primary"}
]
```

`anki:confirm:yes` executes only the reviewed default-model add command(s).
`anki:confirm:audio` executes only the corresponding reviewed audio-model add
command(s). Do not offer the audio button for English or non-Spanish cards:
the audio model is `es_MX` only.
When the addition also has one staged image, both alternatives must use the
same reviewed image metadata and SHA-256; execute the selected command with its
unchanged `--image` path and `--image-sha256` value. Do not create a separate
image confirmation or attach a different file to the audio alternative.

Offer alternatives only when every button executes the whole request. If only
one complete plan applies, send:

```json
[
  {"text": "➕ Добавить", "callback_data": "anki:confirm:yes", "style": "success"}
]
```

Never offer a control that adds only a subset of the requested cards.

## Irregular Spanish verb forms

For the Spanish-only irregular-verb workflow, use the forms choice rather than
audio. When the infinitive is absent, compare the forms-and-infinitive and
infinitive-only plans, then use:

```json
[
  {"text": "➕ Добавить всё", "callback_data": "anki:verb:forms", "style": "success"},
  {
    "text": "🔤 Только инфинитив",
    "callback_data": "anki:verb:infinitive",
    "style": "primary"
  }
]
```

When it exists, say no duplicate will be created, show the edit-and-forms plan,
and use:

```json
[
  {"text": "➕ Добавить всё", "callback_data": "anki:verb:forms", "style": "success"}
]
```

Each forms callback executes only its displayed complete plan. Never use this
workflow outside Spanish or add `vosotros` unless requested.

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
