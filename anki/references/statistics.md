# Statistics notifications

`anki-stats` is the agent-facing settings and preview helper.
`anki-stats-worker` runs only from declared OpenClaw command cron jobs. OpenClaw
cron is the only scheduler: do not create a systemd timer, system crontab,
poller, direct Telegram sender, or another settings database.

## Read-only requests

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-stats settings --json
```

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-stats explain
```

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-stats preview --deck Español
```

`settings`, `explain`, and `preview` do not change cron. For “send my Spanish
report now,” use `preview`; never run `openclaw cron run`.

## Settings changes

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-stats configure --deck Español --enable --time 07:45 --days mon,tue,wed,thu,fri,sat
```

```bash
/home/claw/.openclaw/workspaces/anki/skills/anki/bin/anki-stats disable --deck English
```

Use lowercase `sun,mon,tue,wed,thu,fri,sat`. Partial requests retain values
that the operator did not mention. `configure` and `disable` provide old and
proposed settings, cron expression, and stale-safe `plan_id`; use the statistics
buttons in `../TG_BUTTONS.md` for the approved plan only.

The helper validates the exact worker argv, working directory, Telegram account
`anki`, destination, and immutable fields before and after execution. On a
revision or contract mismatch, report rejection; do not improvise cron commands.

The worker reads loopback AnkiConnect, emits one deterministic Russian Markdown
report, and never calls Telegram or a model. Do not run it directly or add it to
agent exec approvals.
