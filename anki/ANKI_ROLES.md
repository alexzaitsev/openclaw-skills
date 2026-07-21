# Anki language decks and study-role tags

Physical Anki decks are organized by language. Study categories live in note
tags inside each language deck; category names are not physical decks.

## Language decks

| Deck | Status | Language |
| --- | --- | --- |
| `Español` | Active | Latin American Spanish |
| `English` | Active | English |

Choose the physical deck from the language of the card front. Spanish cards
always go to `Español`. Do not route Spanish cards to `general`, `verbos`,
`reglas`, or `adjetivos`; those are legacy deck names represented by tags now.

## Spanish study-role tags

Every new note must have exactly one of these primary role tags. Additional
source or workflow tags are allowed.

| Tag | Purpose |
| --- | --- |
| `deck:adjetivos` | Standalone adjectives. |
| `deck:general` | Phrases, fixed expressions, and uncategorized vocabulary. |
| `deck:números` | Numbers and number-focused practice. |
| `deck:reglas` | Grammar rules and grammar-focused examples. |
| `deck:verbos` | Verbs, forms, and explicit verb or conjugation practice. |

The `deck:` prefix is retained for compatibility with cards migrated from the
old category decks. It describes a study role, not the current physical deck.
Never create `deck:Español` or `deck:English` merely because a card lives in
that language deck.

## English study-role tags

Every new English note currently uses this one primary role tag. Additional
source or workflow tags are allowed.

| Tag | Purpose |
| --- | --- |
| `deck:general` | All English material while English has one role. |

Do not infer any additional English role from the Spanish taxonomy. Expand this
table before assigning English notes to a more specific study role.
