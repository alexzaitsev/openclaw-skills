#!/usr/bin/env python3
"""Minimal stateful OpenClaw cron CLI used by anki-stats integration tests."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


STATE = Path(os.environ["FAKE_OPENCLAW_STATE"])
ROOT = Path(os.environ["ANKI_STATS_RUNTIME_ROOT"]).resolve()


def initial_jobs() -> list[dict[str, object]]:
    jobs = []
    for job_id, deck, name, key, enabled in (
        ("spanish-id", "Español", "Anki stats: Spanish", "anki-stats:espanol", True),
        ("english-id", "English", "Anki stats: English", "anki-stats:english", False),
    ):
        jobs.append(
            {
                "id": job_id,
                "name": name,
                "declarationKey": key,
                "enabled": enabled,
                "updatedAtMs": 1,
                "schedule": {
                    "kind": "cron",
                    "expr": "30 8 * * *",
                    "tz": "America/Edmonton",
                    "staggerMs": 0,
                },
                "payload": {
                    "kind": "command",
                    "argv": [str(ROOT / "bin" / "anki-stats-worker"), "--deck", deck],
                    "cwd": str(ROOT),
                    "env": {"ANKI_STATS_TIMEZONE": "America/Edmonton"},
                    "timeoutSeconds": 180,
                    "outputMaxBytes": 12000,
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "telegram",
                    "accountId": "anki",
                    "to": "142309269",
                    "bestEffort": False,
                },
                "state": {},
            }
        )
    return jobs


def load() -> list[dict[str, object]]:
    if not STATE.exists():
        save(initial_jobs())
    return json.loads(STATE.read_text(encoding="utf-8"))["jobs"]


def save(jobs: list[dict[str, object]]) -> None:
    STATE.write_text(json.dumps({"jobs": jobs}, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    args = sys.argv[1:]
    jobs = load()
    if args == ["cron", "list", "--json"]:
        print(json.dumps({"jobs": jobs, "total": len(jobs)}))
        return 0
    if len(args) == 4 and args[:2] == ["cron", "show"] and args[3] == "--json":
        job = next(job for job in jobs if job["id"] == args[2])
        print(json.dumps(job))
        return 0
    if len(args) >= 3 and args[:2] == ["cron", "edit"]:
        job = next(job for job in jobs if job["id"] == args[2])
        index = 3
        while index < len(args):
            option = args[index]
            if option == "--cron":
                job["schedule"]["expr"] = args[index + 1]
                index += 2
            elif option == "--tz":
                job["schedule"]["tz"] = args[index + 1]
                index += 2
            elif option == "--command-env":
                key, value = args[index + 1].split("=", 1)
                job["payload"]["env"] = {key: value}
                index += 2
            elif option == "--enable":
                job["enabled"] = True
                index += 1
            elif option == "--disable":
                job["enabled"] = False
                index += 1
            elif option == "--exact":
                job["schedule"]["staggerMs"] = 0
                index += 1
            else:
                raise SystemExit(f"unsupported edit option: {option}")
        job["updatedAtMs"] = int(job["updatedAtMs"]) + 1
        save(jobs)
        print(json.dumps({"ok": True, "job": job}))
        return 0
    if len(args) == 5 and args[:2] == ["cron", "tamper"]:
        job = next(job for job in jobs if job["id"] == args[2])
        section, key, value = args[3].split(".", 1)[0], args[3].split(".", 1)[1], args[4]
        job[section][key] = value
        job["updatedAtMs"] = int(job["updatedAtMs"]) + 1
        save(jobs)
        return 0
    raise SystemExit(f"unsupported fake OpenClaw invocation: {args}")


if __name__ == "__main__":
    raise SystemExit(main())
