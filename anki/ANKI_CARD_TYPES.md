# Anki card types

Choose the note type before every `add-basic` or `add-batch` dry run. The
physical language deck and study role are still selected separately through
`ANKI_ROLES.md`.

| Model | Use it when | Audio behavior |
| --- | --- | --- |
| `Basic (type in the answer + reverse)` | Default for every new card, including all English cards and ordinary Spanish cards. | No TTS. |
| `Basic (type in the answer + reverse + Spanish TTS)` | The operator explicitly requests audio for a new Spanish card, or chooses `🔊 С аудио` after the reviewed addition plan. | Uses Anki's on-device `{{tts es_MX:Front}}` only when the Spanish `Front` field is shown. It creates no MP3 and adds no media file. |

The Spanish TTS model has the same `Front` and `Back` fields, two directions,
CSS, and typing-answer behavior as the default model. It differs only by the
two TTS template placements: on the question for `Another -> Russian`, and on
the revealed answer for `Russian -> Another`. Russian is never passed to TTS.

Use the exact model name with the helper when preparing or executing the audio
alternative:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool add-basic --deck Español --role general --front "tener" --back "иметь" --model "Basic (type in the answer + reverse + Spanish TTS)"
```

Before any addition, first run `anki-tool fields --model "<chosen model>"` and
use the reported field names exactly. Do not use the Spanish TTS model for
English or any non-Spanish front: its configured locale is `es_MX`.
