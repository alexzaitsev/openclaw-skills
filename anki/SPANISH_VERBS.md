# Spanish verb-card contract

Use this contract for every standalone Spanish verb request. It defines the
card payload and Telegram preview; `ANKI_ROLES.md` still defines the deck and
role, and `TG_BUTTONS.md` still defines the approval controls.

## Classification and normalization

- A standalone Spanish infinitive, conjugated form, or explicit conjugation
  request is verb practice: target physical deck `Español` with role `verbos`.
  A verb merely appearing in a sentence does not make the sentence verb
  practice.
- Normalize a clear conjugated form to its infinitive before preparing cards.
  If the infinitive, meaning, or regular/irregular classification is uncertain,
  ask rather than guess.
- A regular verb gets one infinitive card unless the operator explicitly asks
  for examples or forms.
- An irregular verb gets a choice between its infinitive alone and the
  infinitive plus the five Latin-American present-tense forms below. Treat
  `ver` as irregular. Never add `vosotros` unless the operator explicitly asks
  for it.
- Check every proposed `Front` exactly before the dry run. Never create a
  duplicate and never edit an existing card merely because it shares a form;
  editing needs a separate explicit request and its own reviewed plan.

## Required irregular-verb card shape

Use exactly these six positions for the default forms plan. All cards use the
default model, `source:telegram`, and the helper-supplied `deck:verbos` role
tag.

| Position | Front | Back | Context |
| --- | --- | --- | --- |
| Infinitive | `<infinitive>` | concise Russian infinitive translation | absent |
| First singular | `yo <form>` | first-person singular Russian translation | `<infinitive>` |
| Second singular | `tú <form>` | second-person singular Russian translation | `<infinitive>` |
| Third singular / formal | `él / ella / usted <form>` | third-person Russian translation only | `<infinitive>; usted` |
| First plural | `nosotros <form>` | first-person plural Russian translation | `<infinitive>` |
| Third plural / formal | `ellos / ellas / ustedes <form>` | third-person plural Russian translation, then formal-plural Russian translation | `<infinitive>; ustedes` |

The combined `él / ella / usted` card does not append `вы (один)` to its
`Back`: `usted` is preserved in its `Front` and `Context`. The combined
`ellos / ellas / ustedes` card retains both Russian meanings in `Back` and
marks `ustedes` in `Context`. Context is only a compact disambiguator; it must
not repeat the translation or a prose explanation of the verb.

For example, `dar` must preview these exact cards:

| Front | Back | Context |
| --- | --- | --- |
| `dar` | `давать; дать` | absent |
| `yo doy` | `я даю` | `dar` |
| `tú das` | `ты даёшь` | `dar` |
| `él / ella / usted da` | `он/она даёт` | `dar; usted` |
| `nosotros damos` | `мы даём` | `dar` |
| `ellos / ellas / ustedes dan` | `они дают, вы даёте` | `dar; ustedes` |

## Telegram preview and revision

Before sending either irregular-verb button, show every proposed non-duplicate
card as `Front → Back` plus its `Context` (or `нет`). State the deck, role,
model, fields, tags, and duplicate result once for the whole plan. Do not first
show only a count or a bare list of forms.

The preview is a draft, not a mutation. If the operator corrects any
translation, context, form, deck, role, tag, or card count before pressing a
button, discard the old dry run, perform a complete new dry run, and show the
entire revised card list with fresh buttons. A callback can execute only the
new `plan_id`; an earlier button is stale and must not write anything.

Use the irregular-verb form controls from `TG_BUTTONS.md`, not the Spanish TTS
choice. `➕ Добавить всё` executes all non-duplicate cards in the displayed
forms plan; `🔤 Только инфинитив` executes only the displayed infinitive card
when it is absent.
