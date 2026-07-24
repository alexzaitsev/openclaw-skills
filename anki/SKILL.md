---
name: anki
description: REQUIRED for every Anki request. Read this skill before acting; use only anki-tool for direct AnkiConnect checks and confirmed additions.
bins: ["python3"]
---

# Anki

Use this skill to manage the operator's language-organized Anki collection
through local AnkiConnect on the OpenClaw VM. Physical decks represent
languages; each language has its own study-role tags in `ANKI_ROLES.md`.
Choose a note type from `ANKI_CARD_TYPES.md` before every addition.

For every request involving Anki cards, decks, checks, additions, statistics,
or notification settings, read this file before taking any action. Use only
the reviewed executables documented here. Never substitute an inline Python
snippet, `curl`, or a generic shell command, even for a read-only lookup.

## Critical Confirmation UI Rule

After **every successful dry run for a data-changing operation**, the next
outbound Telegram response must be exactly one `message` tool call with the
required inline buttons from `TG_BUTTONS.md`, followed by `NO_REPLY`. This
includes `edit-note` and `edit-batch`, even when the operator only asked to
add examples or context to an existing card.

If the proposed reply contains `Подтверждаешь?`, do **not** send it as normal
assistant text. Send it through the `message` tool with the buttons. A plain
text plan asking for confirmation is a contract failure, not a fallback UI.

## Exec Command Format

Every `exec` tool call for `anki-tool`, `anki-stats`, or
`stage-inbound-image` must contain exactly **one physical shell-command line**.
Do not use a trailing `\`, a newline, a shell wrapper, or any other multiline
formatting, even when an example in this document is wrapped for readability.
Pass every argument in that one line. OpenClaw treats line continuations as an
unanalyzable shell construct, so they bypass this agent's exact-executable
allowlist and incorrectly request a system approval. This rule applies to all
dry runs as well as execute-mode commands.

## Reviewed Command Surface

The exact `anki-tool` commands documented in this skill are the normal Anki
content-management surface. For a machine-readable current inventory, use
this read-only command instead of inspecting files or source code:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool capabilities --json
```

It reports reviewed commands, whether they mutate Anki, dry-run support, and
the current model fields. If a requested operation is absent from that
inventory, report that it is not supported; do not invent or implement it in
the Telegram session.

The statistics surface is the separately reviewed `anki-stats` executable
documented in [Statistics notifications](#statistics-notifications). The agent
may execute `anki-tool`, `anki-stats`, and `stage-inbound-image` only as
documented here. It must never execute `anki-stats-worker`; that executable is
reserved for declared OpenClaw command cron jobs.

The agent must not initiate `find`, `ls`, `sed`, `grep`, `rg`, `cat`, shell
loops, inline Python, `curl`, generic shell commands, or direct source-file
inspection. Those actions are permitted only when the operator explicitly
initiates that exact action. This does not authorize the agent to infer such
permission from a general Anki request.

## Runtime Contract

Anki must already be running under `claw` through:

```bash
systemctl --user status anki.service --no-pager
```

AnkiConnect must answer on loopback only:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool ping
```

The expected AnkiConnect URL is `http://127.0.0.1:8765`. Override it with
`ANKI_CONNECT_URL` only when the operator explicitly asks.

Every successful mutating command requests Anki sync once after its local
changes have been verified. This AnkiConnect version acknowledges the request
but does not expose sync completion status, so report `sync: requested` and do
not claim that synchronization has completed. The operator's other Anki client
must still sync to download server-side changes.

For additions, treat the physical language deck and study role as separate
required values. Spanish content goes to physical deck `Español`; `--role`
selects one Spanish role and the helper creates its `deck:<role>` tag. Never
use a role name as the physical deck and never derive `deck:Español` from the
physical deck. The active `English` deck currently has exactly one approved
role, `general`; use it for English additions until `ANKI_ROLES.md` defines a more
specific English role table.

Before every addition, read the deployed `ANKI_ROLES.md` to resolve the
language deck and study role, then read `ANKI_CARD_TYPES.md` to select the
card model. These required reference reads are allowed; the source-inspection
prohibition above applies to helper implementation files, not to these
reference files.

## Supported Operations

List decks:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool decks
```

Inspect one deck before answering questions about it or proposing deletion:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool deck-info \
  --deck Español
```

`deck-info` is read-only. It reports the exact deck name, card count, unique
note count, child decks, and whether it is empty. If child decks exist, report
them; `delete-deck` deliberately refuses to delete a parent deck until each
child deck is handled explicitly.

Create a new physical deck through the normal dry-run and confirmation flow:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool create-deck \
  --deck English
```

The dry run prints `plan_id`. After explicit confirmation, rerun the same
command with `--execute --plan-id <reviewed-plan-id>`. The helper verifies the
deck exists and requests sync once.

Delete one physical deck only after its mandatory emptiness check:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool delete-deck \
  --deck English
```

This dry run always prints card and note counts plus `empty`. For an empty
deck, execute only after the normal explicit confirmation with
`--execute --plan-id <reviewed-plan-id>`. For a non-empty deck, the plan says
that confirmation is required and execution must additionally include
`--confirm-nonempty`. That flag is permitted only after the operator has
explicitly confirmed this exact plan; it deletes the reported cards together
with the deck. Never add the flag merely because the original request asked to
delete the deck. The installed AnkiConnect requires its `cardsToo=true` API
mode even for an empty deck; the helper uses it only after this verified count,
so an empty-deck deletion still has zero cards to remove.

Read the live card-field schema for the chosen model before every `add-basic`
or `add-batch` dry run. Do not assume that the model will always contain only
`Front` and `Back`:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool fields --model "<chosen model>"
```

Use the reported field names exactly. `Front`, `Back`, and optional `context`
remain normal arguments. If the model has additional fields, include a value
for each relevant one with `--field NAME VALUE` for one note or
`--note-field INDEX NAME VALUE` for a batch. This lookup is required even when
the request is ordinary: it makes the agent adapt to a changed card schema
before it prepares the dry run.

Check whether an exact Spanish front already exists (optionally in one deck):

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool check \
  --deck Español \
  --front "decir"
```

`check` is read-only. Use it for requests such as "check whether `decir`
exists, and add it if it does not." It is implemented by the deployed Python
helper, which calls AnkiConnect directly at `127.0.0.1:8765`; do not replace it
with inline Python, `curl`, or another shell command. If `result: present`,
report the match and do not prepare an addition. If `result: absent`, prepare a
normal dry run and follow the confirmation protocol below before adding.

Search existing notes and show their note IDs and text fields:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool search \
  --deck Español \
  --query "yo digo"
```

`search` is read-only. Use it when the operator asks to inspect several notes,
find conjugated forms, or collect note IDs before an edit. It prints the
matching note IDs, front, back, and context. For every lookup, use `check` or
`search`; never use inline Python, `curl`, raw `findNotes`, `notesInfo`, or any
other direct AnkiConnect request.

Request sync without another mutation:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool sync
```

Add a basic Spanish note:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool add-basic \
  --deck Español \
  --role general \
  --model "Basic (type in the answer + reverse)" \
  --front "la palabra" \
  --back "word" \
  --context "only if needed for disambiguation" \
  --tag source:telegram
```

Every newly created note automatically receives the study-role tag derived
from `--role` (for example, `--role general` adds `deck:general`). This is in
addition to any requested tag such as `source:telegram`; do not also supply the
role tag with `--tag`. The same invariant applies to `add-batch`. No tag is
derived from the physical language deck.

The command is a dry run by default and prints `plan_id`. Add `--execute
--plan-id <reviewed-plan-id>` only after reviewing the printed plan.

### Attach one inbound image to a new card

Support one explicitly requested Telegram attachment on the `Front` of one new
`add-basic` note. Do not attach a screenshot merely because it was used to
read a word or phrase: attach it only when the operator asks for a card *with*
that image. JPEG and PNG are the only supported formats. Do not use image URLs,
generated images, GIF/WebP, an arbitrary host path, a batch addition, or an
existing-note edit in this V1 workflow.

First stage the exact inbound attachment as in the screenshot workflow. Then
prepare the normal one-note dry run with its returned staging path:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool add-basic --deck Español --role general --front "gato" --back "кот" --image "<staged-path>"
```

The dry run must show `image`, `image_sha256`, and `image_placement: Front`.
The Telegram confirmation view must state the format, dimensions, byte size,
SHA-256, and that the image will be attached to `Front`; do not reveal the VM
path. Treat that image digest as part of the reviewed plan. After the normal
inline approval, execute the unchanged command with both `--execute` and the
exact dry-run digest:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool add-basic --deck Español --role general --front "gato" --back "кот" --image "<staged-path>" --image-sha256 "<reviewed-sha256>" --execute --plan-id "<reviewed-plan-id>"
```

Never invent, omit, or replace `--image-sha256`. A changed image invalidates
the plan and requires a new dry run. For Spanish, retain the normal default/TTS
choice from `TG_BUTTONS.md`: prepare both model alternatives with this same
staged image and digest, then include that exact digest in whichever confirmed
execute command runs. Report both `verified_deck` and `verified_image` after a
successful execution. The helper accepts images only from its content-addressed
inbound staging directory, checks their size, MIME signature, dimensions, and
digest, and verifies the stored media before it reports success.

Prepare multiple notes as one reviewed operation:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool add-batch --model "Basic (type in the answer + reverse)" --note Español general "¿Puedes cambiar tus planes?" "Ты можешь изменить свои планы?" "optional disambiguation" --note Español verbos "cambiar" "менять; изменять" --tag source:telegram
```

Use `add-batch` whenever one operator request asks for multiple notes. It is a
dry run by default. After one confirmation, rerun the same complete batch with
`--execute`; the helper verifies every note's deck and requests sync once.
Each `--note` takes `LANGUAGE_DECK ROLE FRONT BACK` and optional `CONTEXT`.
Omit the fifth value when no context is needed. Every item has its own role so
one batch can add a sentence tagged `deck:general` and a verb tagged
`deck:verbos` to the same `Español` deck. For a changed model schema, attach
extra values to the corresponding one-based batch item, for example:

```bash
  --note-field 1 "Example" "Puedes cambiar los planes."
```

Move every card generated by one note to another physical language deck:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool move-note \
  --note-id 123456789 \
  --target Español
```

Use the note ID reported by the immediately preceding `add-basic` operation
when the operator says to move "it" or "that card." The command is a dry run by
default; rerun it with `--execute` only after explicit confirmation. Do not
inspect the workspace or improvise Python or shell commands for this workflow.

Edit the text fields of one existing note:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool edit-note \
  --note-id 123456789 \
  --front "decir" \
  --back "говорить; сказать" \
  --context "англ. say" \
  --add-tag source:telegram \
  --remove-tag review-later
```

`edit-note` is a dry run by default. It can change any combination of `Front`,
`Back`, `context`, and tags; use `--clear-context` to remove an existing
context. Use repeatable `--add-tag` and `--remove-tag` for existing notes.
Tags apply to the note and therefore to all cards generated from it; Anki
creates a tag automatically when it is first added. The command reads the
existing note, shows current and proposed fields and tags, and verifies both
after an execute-mode edit. Run it with `--execute` only after a later explicit
confirmation of that exact dry run. Media editing is deliberately out of scope:
if an edited field contains image, audio, or video markup, the command fails
rather than risk discarding the media.

Edit several existing notes as one reviewed operation:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool edit-batch \
  --note 1780781752051 "я смотрю" "англ. to watch" \
  --note 1780781752083 "ты смотришь" "англ. to watch" \
  --add-tag source:telegram \
  --note-add-tag 1780781752051 grammar::verbs
```

Each `--note` takes `NOTE_ID BACK` and optional `CONTEXT`. Use `=` for `BACK`
or `CONTEXT` to keep its current value; pass an empty quoted context (`""`) to
clear it. Use repeatable `--add-tag` / `--remove-tag` for every note in the
batch, and `--note-add-tag NOTE_ID TAG` / `--note-remove-tag NOTE_ID TAG` for
one note. Tags are delta operations: existing unrelated tags are preserved,
not replaced. `edit-batch` is dry-run by default and prints `plan_id`; its
`--execute` invocation must include that exact `--plan-id`. It verifies every
changed note after execution and requests one sync for the whole batch. Use it
whenever the same request affects more than one existing note. Never implement
a batch edit with a shell loop, inline Python, or repeated raw AnkiConnect
calls.

## SSH-only administration

`tag-decks`, `import-json`, and `merge-decks` are legacy migration or bulk
operations. They are available only through `bin/anki-admin` to an SSH
operator and are not part of the Telegram agent's reviewed executable surface.
Do not invoke, suggest, or confirm them in Telegram. Each still uses a dry run
and its exact `--plan-id` before execution. If a sequential import or merge
fails after a local write, the helper reports the reconciled affected note IDs
or card placement and requests one sync when possible; it never claims an
automatic rollback.

## Statistics notifications

Statistics notifications use two reviewed executables inside this skill:

- `anki-stats` is the agent-facing settings and preview helper;
- `anki-stats-worker` is invoked only by declared OpenClaw command cron jobs.

OpenClaw cron is the only notification scheduler. Do not create a `systemd`
timer, system crontab, separate polling process, direct Telegram sender, or a
second settings database.

Show the current Spanish and English notification settings:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-stats settings --json
```

Explain the report metrics and deck-history limitations:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-stats explain
```

Preview one report in the current Telegram conversation:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-stats preview \
  --deck Español
```

`settings`, `explain`, and `preview` are read-only with respect to cron. A
preview does not run, reschedule, enable, or disable a cron job. For requests
such as "send my Spanish report now", use `preview`; never call
`openclaw cron run` from the agent.

Prepare a notification settings change without applying it:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-stats configure \
  --deck Español \
  --enable \
  --time 07:45 \
  --days mon,tue,wed,thu,fri,sat
```

Use lowercase English weekday names from `sun,mon,tue,wed,thu,fri,sat`. Partial
requests preserve unmentioned values. For example, "skip Sundays" reads the
current job and changes only the weekday set.

Pause one deck with a dry run:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-stats disable \
  --deck English
```

Every `configure` or `disable` dry run prints the old settings, proposed
settings, exact cron expression, and a stale-safe `plan_id`. Send its concise
diff through the statistics button flow in `TG_BUTTONS.md`; the callback may
execute only that unchanged plan ID.

Statistics configuration changes only the declared job's enabled state,
time, weekdays, and timezone. The helper verifies the exact worker argv,
working directory, Telegram account `anki`, operator destination, and all
other immutable fields before and after execution. If that contract or the
plan revision changed, report the rejection and do not improvise a cron
command.

The scheduled worker reads aggregate data through loopback AnkiConnect, prints
one deterministic Russian-language, Markdown-formatted report, and never calls
Telegram or a model. The agent must not run it directly, add it to agent exec
approvals, or expose a general OpenClaw cron administration command.

## Telegram Confirmation Buttons

Use the complete UI, callback, and concise-plan contract in `TG_BUTTONS.md`.
It is mandatory for every data-changing Anki operation. Never send an
unbuttoned confirmation request: preparing a dry run needs no confirmation,
and only the completed dry run is shown with the specified buttons.

### Irregular Spanish verb choice

This is a **Spanish-only** workflow. Apply its irregularity check, present-tense
form planning, and `anki:verb:*` buttons only when the requested standalone
verb is Spanish and targets physical deck `Español`. Never apply any part of
this workflow to English or to an English card in physical deck `English`.
English verbs use the ordinary add/edit dry-run and normal `✅ Да` / `❌ Нет`
confirmation flow, unless the operator explicitly requests another supported
English operation.

For every standalone Spanish verb, first determine whether its present
indicative is irregular. Do this even when the infinitive already exists and
the operator requested only an edit such as a context change. Treat `ver` as
irregular (`veo`, `ves`, `ve`, `vemos`, `ven`).

For an irregular verb, determine first whether an exact infinitive card
already exists.

- If it does **not** exist, prepare both complete alternatives before sending a
  Telegram response: (a) the infinitive plus its six short present-tense notes,
  and (b) the infinitive only.
- If it **does** exist, do **not** offer an infinitive-only alternative. Prepare
  one full dry run only: the requested `edit-note` for that existing infinitive
  (if it needs an edit) plus an `add-batch` dry run for the missing short
  present-tense notes. The forms choice applies that complete plan, including
  the edit. It never creates a duplicate infinitive card.

Before either dry run, use `check --deck Español --front` for every exact card
front in its respective plan. Do not treat another sentence that merely
contains a conjugated word as satisfying that card. Omit already-present exact
cards from the addition plan and say so in the Telegram summary.

Use the irregular-verb message, button, and callback contract in
`TG_BUTTONS.md`. A valid forms callback executes only its already displayed,
unchanged complete plan; do not ask another question or run another dry run
unless collection state, content, or requested scope changed.

For a request that combines additions with different card types, languages, or
workflows, offer an audio or irregular-verb alternative only when each choice
still executes a complete plan for every requested card. If there is only one
complete applicable plan, use the single `➕ Добавить` button specified in
`TG_BUTTONS.md`; never make a button execute only part of the request.

## Confirmation Protocol For All Data Changes

Every data-changing operation requires a two-message confirmation flow,
without exception:

1. On an initial request, run any needed read-only check first, then **always**
   run the relevant dry run before asking for confirmation. A
   successful `check` is not a substitute for an add dry run. Keep the complete
   helper output as the execution check, then show the concise Telegram
   approval view described above and explicitly ask whether to apply that exact
   plan.
2. Do **not** use `--execute` in that same turn. An OpenClaw exec approval,
   including `allow-once`, authorizes a command invocation only; it is never
   confirmation to add an Anki note.
3. Use `--execute --plan-id <reviewed-plan-id>` only after a later, explicit
   operator reply confirming the currently displayed plan. Every Telegram-facing
   mutation except standalone `sync` requires that exact dry-run ID; if the
   live note, deck, duplicate check, model schema, or staged image changed in
   the meantime, the helper rejects execution as stale and requires a new dry
   run.
4. If the operator replies with an edit, correction, alternative translation,
   deck change, added item, or any other modification, do not execute the old
   plan. Apply the edit, rerun the complete dry run, display the revised plan,
   and ask for a new explicit confirmation. Execute only after a subsequent
   confirmation of that revised plan.

This applies equally to `create-deck`, `delete-deck`, `add-basic`, `add-batch`,
`edit-note`, `edit-batch`, and `move-note`. Never
infer confirmation from the original request, an exec approval, or a reply
that changes the proposed content. Never ask for confirmation before the
current plan's dry run has completed and been shown to the operator.

## Language Rules

- The learner studies Latin American Spanish.
- Prefer Latin American usage and avoid Spain-only forms unless requested.
- Choose the physical deck by language, independently of the study role.
  Spanish cards always go to `Español`. English cards go to `English`; its
  current sole role is `general` and creates the tag `deck:general`.
- Infer the language-specific study role from `ANKI_ROLES.md` whenever the content
  has a clear fit. Do not ask the operator to choose a role in that case.
- For Spanish, tag standalone adjectives with `deck:adjetivos`.
- For Spanish, tag standalone verbs, conjugated forms, and sentences explicitly
  requested as verb or conjugation practice with `deck:verbos`.
- For Spanish, tag standalone grammar rules and grammar-focused examples with
  `deck:reglas`.
- For Spanish, tag numbers and number-focused practice with `deck:números`.
- For Spanish, tag fixed expressions, conversational phrases, nouns, adverbs,
  and other material that clearly does not fit a specialized role with
  `deck:general`.
- Default an ordinary Spanish screenshot phrase or sentence to role `general`.
  The mere presence of a verb does not make a sentence verb practice. Choose
  role `verbos` only when the operator's request or the exercise clearly
  focuses on a verb or conjugation.
- Treat each requested item independently. In "add this sentence and the verb
  cambiar," both notes belong in physical deck `Español`; the ordinary
  sentence gets `deck:general` and the standalone infinitive gets
  `deck:verbos`. Mentioning a standalone verb does not turn the accompanying
  sentence into verb practice. Never silently drop one item from a compound
  request.
- Normalize a requested conjugated form to its infinitive when the screenshot
  and language context make that inference clear, for example `cambian` to
  `cambiar`.
- For a regular **Spanish** verb, add the infinitive only unless the operator
  explicitly asks for examples or conjugations; use the applicable card-model
  and confirmation workflow in `ANKI_CARD_TYPES.md` and `TG_BUTTONS.md`.
- For an irregular **Spanish** verb, use the forms workflow in `TG_BUTTONS.md`.
  Use Latin American Spanish and never add `vosotros` unless requested. Never
  use that workflow for English.
- Ask for the language only when the card language is genuinely ambiguous, and
  ask for the study role only when its learning purpose is genuinely ambiguous.
  Do not use role `general` merely to avoid classifying ambiguous material.
- Do not infer additional English roles from the Spanish taxonomy. Until
  `ANKI_ROLES.md` expands the English table, every English card uses its sole
  approved role, `general`.
- Use `usted` as `вы (один)` and `ustedes` as `вы (много)` in Russian.
- Use `context` only for disambiguation and never to reveal the answer.
- If the operator expands an edit from one conjugation to "other forms", find
  every matching requested form and the infinitive when it was included in the
  original request. Present one `edit-batch` dry run for that complete set; do
  not silently keep the edit limited to `yo` or ask a second yes/no question
  before preparing the dry run.

## Hard Boundaries

- Do not expose AnkiConnect beyond `127.0.0.1`.
- Do not edit Anki's SQLite collection directly.
- Do not move or delete cards without a dry run and explicit operator approval.
- Do not delete a deck before `delete-deck` has completed its mandatory
  emptiness check. If the deck is non-empty, require a later explicit approval
  of the displayed card count and use `--confirm-nonempty` only for that
  approved execution.
- Do not use `general`, `verbos`, `reglas`, or `adjetivos` as physical target
  decks. They are Spanish study roles represented by `deck:*` tags inside
  `Español`.
- Do not create `deck:Español` or `deck:English` as study-role tags.
- Do not edit a note without an `edit-note` dry run and explicit operator
  approval. Do not use `updateNoteFields` through inline Python or another raw
  AnkiConnect request.
- For read-only card discovery, use only `check` or `search`; do not run raw
  `findNotes` or `notesInfo` requests.
- Do not delete a parent deck with child decks; the helper refuses it so child
  decks must be inspected and deleted explicitly.
- Do not initiate broad shell commands or source inspection. Unless the
  operator explicitly requests that exact action, use only the deployed
  `anki-tool`, `anki-stats`, and `stage-inbound-image` commands documented in
  this skill. Do not improvise inline Python, `curl`, raw AnkiConnect requests,
  direct OpenClaw cron commands, or `anki-stats-worker` execution.
- Do not use the main OpenClaw Telegram chat for this workflow once the
  dedicated Anki Telegram account exists.

## Screenshot Workflow

When a request such as "добавь эту фразу" or "add this word" includes a
`[media attached: <path> ...]` line, first stage that exact local path with:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/stage-inbound-image \
  --source "<path>"
```

Then call the `image` tool on the workspace path printed by the helper. The
helper accepts only validated images from OpenClaw's managed inbound-media
locations.
Do not use `cp`, `mv`, `read`, or the `image` tool directly on the original
out-of-workspace path. Never ask which phrase or word the operator means before
inspecting the staged image with model-side vision. The staging helper creates
a private content-addressed filename; treat its path as immutable for one
reviewed plan.

For a completed Duolingo translation exercise, use the submitted answer as the
target Spanish content. It is usually shown as green selected words above the
divider. Ignore unused word-bank choices, navigation labels, status text, and
other interface copy. Use the prompt or speech-bubble translation to determine
meaning, not as the card front.

After visual inspection, extract the Spanish answer, use physical deck
`Español`, and infer its Spanish study role using the rules above. Do not ask
for a role when the classification is clear. For example, `por supuesto` is a
fixed expression and uses role `general`, which creates `deck:general`.

Unless the operator requests a different format, prepare one basic card with
the Spanish word or phrase on the front and a concise Russian translation on
the back. Use text visible in another language only to understand meaning; the
card back should still be Russian. Add examples only when the operator asks for
examples or when a requested verb workflow requires conjugation examples.
Do not retain the screenshot in Anki by default. Retain it only through the
explicit one-card image workflow above.

Treat requests such as "добавь эту фразу" as sufficient intent to prepare the
normal dry-run plan. Call
`/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool add-basic`
with `--deck Español --role <inferred-role>` and without `--execute`, report
the language deck, inferred role, and card fields, and ask only for confirmation
to execute the reviewed plan in a later message. Never treat an exec approval
as that confirmation.

For compound screenshot requests, call `add-batch` once with every requested
note. Show the complete dry-run plan and ask for one confirmation. Do not run
only the first item and merely mention the others in prose.

If the operator edits a displayed screenshot plan, apply the edit to the full
set of notes and rerun `add-basic` or `add-batch` without `--execute`. Show the
new dry run and ask again. Do not execute the earlier plan or treat the edit as
approval.

After `add-basic --execute`, rely on its `verified_deck` output rather than the
requested deck shown in the plan. For Spanish it must report `Español`. The
helper corrects note-model deck overrides and fails if Anki does not place
every generated card in the requested language deck.
Also report the helper's sync result. If the local operation succeeded but sync
failed, say so explicitly and do not imply that the note was rolled back.

Ask for clarification only after staging and inspecting the image and finding
that the Spanish answer is unreadable, multiple submitted answers remain
plausible, the Russian meaning cannot be inferred safely, or the learning
purpose is genuinely ambiguous between study roles. If staging or the
image tool fails, report that specific failure instead of asking the operator
which visible phrase they mean.
