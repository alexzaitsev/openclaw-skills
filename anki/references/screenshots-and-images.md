# Screenshots and card images

## Screenshot to card

For an inbound `[media attached: <path> ...]`, first stage that exact path:

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/stage-inbound-image --source "<path>"
```

Use the `image` tool on the returned workspace path. Do not use `cp`, `mv`,
`read`, or the image tool on the original path. The helper accepts only managed
inbound locations and returns an immutable, private content-addressed path for
the reviewed plan.

For completed Duolingo translation exercises, use the submitted answer (usually
green selected words above the divider) as the Spanish front. Use the prompt or
speech bubble only to infer its meaning; ignore unused word-bank choices and UI
text.

Unless another format is requested, prepare one basic card with Spanish front
and concise Russian back. Do not retain the screenshot by default. Infer the
role after visual inspection; ask only when the answer, meaning, or learning
purpose is genuinely ambiguous. A compound request uses one `add-batch` dry run
for all requested notes.

After execute, report `verified_deck` rather than the requested deck. For
Spanish it must be `Español`; also report the helper's sync result. If the local
write succeeds but sync fails, say so without implying rollback.

## One image on a new card

Attach an image only when the operator explicitly asks for a card with it. This
V1 flow supports one staged JPEG or PNG on `Front` of one new `add-basic` card.
It excludes URLs, generated images, GIF/WebP, arbitrary paths, batches, and
edits of existing notes.

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool add-basic --deck Español --role general --front "gato" --back "кот" --image "<staged-path>"
```

The dry run must include `image`, `image_sha256`, and `image_placement: Front`.
Show format, dimensions, bytes, digest, and placement in the Telegram approval,
but never its VM path. The digest is part of the plan.

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-tool add-basic --deck Español --role general --front "gato" --back "кот" --image "<staged-path>" --image-sha256 "<reviewed-sha256>" --execute --plan-id "<reviewed-plan-id>"
```

Never invent, omit, or replace `--image-sha256`; an image change requires a new
dry run. For Spanish audio alternatives, both plans use the same staged image
and digest. After execution, report `verified_deck` and `verified_image`.
