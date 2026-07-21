#!/usr/bin/env python3
"""Narrow, stale-safe reconciliation for declared OpenClaw statistics jobs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_TIMEZONE = "America/Edmonton"
DEFAULT_ROOT = Path("/home/claw/.openclaw/workspaces/anki/skills/anki")
DAY_NAMES = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")
DAY_NUMBERS = {name: index for index, name in enumerate(DAY_NAMES)}


class CronContractError(RuntimeError):
    """Raised when a cron job is missing, stale, or outside the fixed contract."""


def runtime_root() -> Path:
    return Path(os.environ.get("ANKI_STATS_RUNTIME_ROOT", str(DEFAULT_ROOT))).resolve()


def job_specs() -> dict[str, dict[str, Any]]:
    root = runtime_root()
    worker = str(root / "bin" / "anki-stats-worker")
    common = {
        "argv": [worker, "--deck"],
        "cwd": str(root),
        "channel": "telegram",
        "account": "anki",
        "to": "142309269",
        "timeout_seconds": 180,
        "output_max_bytes": 12000,
    }
    return {
        "Español": {
            **common,
            "name": "Anki stats: Spanish",
            "declaration_key": "anki-stats:espanol",
        },
        "English": {
            **common,
            "name": "Anki stats: English",
            "declaration_key": "anki-stats:english",
        },
    }


class CronManager:
    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or os.environ.get("OPENCLAW_BIN", "openclaw")

    def settings(self, deck: str | None = None) -> list[dict[str, Any]]:
        decks = [deck] if deck else list(job_specs())
        return [self._settings_for_job(self.load_job(item), item) for item in decks]

    def load_job(self, deck: str) -> dict[str, Any]:
        spec = _spec(deck)
        payload = self._run_json("cron", "list", "--json")
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise CronContractError("OpenClaw returned an invalid cron job list.")
        matches = [
            job
            for job in jobs
            if isinstance(job, dict)
            and job.get("declarationKey") == spec["declaration_key"]
        ]
        if len(matches) != 1:
            raise CronContractError(
                f"Expected exactly one cron job with declaration key "
                f"{spec['declaration_key']}; found {len(matches)}."
            )
        job_id = str(matches[0].get("id", ""))
        if not job_id:
            raise CronContractError("OpenClaw cron job has no id.")
        shown = self._run_json("cron", "show", job_id, "--json")
        job = shown.get("job") if isinstance(shown, dict) and "job" in shown else shown
        if not isinstance(job, dict):
            raise CronContractError("OpenClaw returned an invalid cron job.")
        self.validate_contract(job, deck)
        return job

    def plan(
        self,
        deck: str,
        *,
        enabled: bool | None = None,
        clock: str | None = None,
        days: str | None = None,
        timezone: str | None = None,
    ) -> dict[str, Any]:
        job = self.load_job(deck)
        current = self._settings_for_job(job, deck)
        proposed = dict(current)
        if enabled is not None:
            proposed["enabled"] = enabled
        if clock is not None:
            hour, minute = parse_clock(clock)
            proposed["time"] = f"{hour:02d}:{minute:02d}"
        if days is not None:
            proposed["days"] = parse_days(days)
        if timezone is not None:
            proposed["timezone"] = validate_timezone(timezone)
        proposed["cron"] = build_cron(proposed["time"], proposed["days"])
        plan_id = self._plan_id(job, proposed)
        return {"deck": deck, "current": current, "proposed": proposed, "plan_id": plan_id}

    def apply(
        self,
        deck: str,
        plan_id: str,
        *,
        enabled: bool | None = None,
        clock: str | None = None,
        days: str | None = None,
        timezone: str | None = None,
    ) -> dict[str, Any]:
        plan = self.plan(
            deck,
            enabled=enabled,
            clock=clock,
            days=days,
            timezone=timezone,
        )
        if not plan_id or plan_id != plan["plan_id"]:
            raise CronContractError(
                "Statistics settings plan is stale or does not match the reviewed plan."
            )
        job = self.load_job(deck)
        if self._plan_id(job, plan["proposed"]) != plan_id:
            raise CronContractError("Statistics settings changed after plan review.")
        proposed = plan["proposed"]
        arguments = [
            "cron",
            "edit",
            str(job["id"]),
            "--cron",
            proposed["cron"],
            "--tz",
            proposed["timezone"],
            "--exact",
            "--command-env",
            f"ANKI_STATS_TIMEZONE={proposed['timezone']}",
            "--enable" if proposed["enabled"] else "--disable",
        ]
        self._run(*arguments)
        updated = self.load_job(deck)
        actual = self._settings_for_job(updated, deck)
        for key in ("enabled", "time", "days", "timezone", "cron"):
            if actual[key] != proposed[key]:
                raise CronContractError(
                    f"OpenClaw cron verification failed for {key}: "
                    f"expected {proposed[key]!r}, got {actual[key]!r}."
                )
        return {"deck": deck, "result": "updated", "settings": actual}

    def validate_contract(self, job: dict[str, Any], deck: str) -> None:
        spec = _spec(deck)
        failures: list[str] = []
        payload = job.get("payload")
        schedule = job.get("schedule")
        delivery = job.get("delivery")
        if job.get("declarationKey") != spec["declaration_key"]:
            failures.append("declaration key")
        if job.get("name") != spec["name"]:
            failures.append("job name")
        if not isinstance(payload, dict):
            failures.append("command payload")
            payload = {}
        expected_argv = [*spec["argv"], deck]
        if payload.get("kind") != "command" or payload.get("argv") != expected_argv:
            failures.append("exact command argv")
        if payload.get("cwd") != spec["cwd"]:
            failures.append("working directory")
        if not _matches_int(payload.get("timeoutSeconds"), spec["timeout_seconds"]):
            failures.append("command timeout")
        if not _matches_int(payload.get("outputMaxBytes"), spec["output_max_bytes"]):
            failures.append("output bound")
        if not isinstance(schedule, dict) or schedule.get("kind") != "cron":
            failures.append("cron schedule")
            schedule = {}
        timezone = schedule.get("tz")
        environment = payload.get("env")
        if environment != {"ANKI_STATS_TIMEZONE": timezone}:
            failures.append("timezone environment")
        if schedule.get("staggerMs") not in (0, None):
            failures.append("exact schedule")
        if not isinstance(delivery, dict):
            failures.append("announce delivery")
            delivery = {}
        if delivery.get("mode") != "announce":
            failures.append("announce delivery")
        if delivery.get("channel") != spec["channel"]:
            failures.append("delivery channel")
        account = delivery.get("accountId", delivery.get("account"))
        if account != spec["account"]:
            failures.append("delivery account")
        if str(delivery.get("to", "")) != spec["to"]:
            failures.append("delivery destination")
        if delivery.get("bestEffort", False):
            failures.append("best-effort delivery")
        if failures:
            raise CronContractError(
                f"Cron contract violation for {deck}: {', '.join(sorted(set(failures)))}."
            )

    def _settings_for_job(self, job: dict[str, Any], deck: str) -> dict[str, Any]:
        schedule = job["schedule"]
        expression = str(schedule.get("expr", schedule.get("cron", "")))
        clock, days = parse_cron(expression)
        return {
            "deck": deck,
            "job_id": str(job["id"]),
            "declaration_key": _spec(deck)["declaration_key"],
            "enabled": bool(job.get("enabled", False)),
            "time": clock,
            "days": days,
            "timezone": validate_timezone(str(schedule.get("tz", ""))),
            "cron": expression,
        }

    def _plan_id(self, job: dict[str, Any], proposed: dict[str, Any]) -> str:
        snapshot = {
            key: value
            for key, value in job.items()
            if key not in {"state", "deliveryPreview", "createdAtMs"}
        }
        encoded = json.dumps(
            {"job": snapshot, "proposed": proposed},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:16]

    def _run_json(self, *arguments: str) -> dict[str, Any]:
        output = self._run(*arguments)
        try:
            result = json.loads(output)
        except json.JSONDecodeError as exc:
            raise CronContractError("OpenClaw returned invalid JSON.") from exc
        if not isinstance(result, dict):
            raise CronContractError("OpenClaw returned an invalid JSON object.")
        return result

    def _run(self, *arguments: str) -> str:
        try:
            completed = subprocess.run(
                [self.executable, *arguments],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CronContractError(f"Could not run OpenClaw cron: {exc}") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[:1000]
            raise CronContractError(f"OpenClaw cron command failed: {detail}")
        return completed.stdout


def parse_clock(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{2}):(\d{2})", value.strip())
    if not match:
        raise CronContractError("Time must use 24-hour HH:MM format.")
    hour, minute = map(int, match.groups())
    if hour > 23 or minute > 59:
        raise CronContractError("Time must be between 00:00 and 23:59.")
    return hour, minute


def parse_days(value: str) -> list[str]:
    raw = [item.strip().lower() for item in value.split(",") if item.strip()]
    if not raw:
        raise CronContractError("At least one delivery weekday is required.")
    unknown = sorted(set(raw) - set(DAY_NUMBERS))
    if unknown:
        raise CronContractError(f"Unknown weekday(s): {', '.join(unknown)}.")
    return [name for name in DAY_NAMES if name in set(raw)]


def build_cron(clock: str, days: list[str]) -> str:
    hour, minute = parse_clock(clock)
    normalized = parse_days(",".join(days))
    day_field = (
        "*"
        if len(normalized) == 7
        else ",".join(str(DAY_NUMBERS[day]) for day in normalized)
    )
    return f"{minute} {hour} * * {day_field}"


def parse_cron(expression: str) -> tuple[str, list[str]]:
    fields = expression.split()
    if len(fields) != 5 or fields[2:4] != ["*", "*"]:
        raise CronContractError("Statistics job has an unsupported cron expression.")
    try:
        minute, hour = int(fields[0]), int(fields[1])
    except ValueError as exc:
        raise CronContractError("Statistics cron hour and minute must be numeric.") from exc
    clock = f"{hour:02d}:{minute:02d}"
    parse_clock(clock)
    if fields[4] == "*":
        days = list(DAY_NAMES)
    else:
        numbers: set[int] = set()
        for item in fields[4].split(","):
            if "-" in item:
                start_text, end_text = item.split("-", 1)
                start, end = int(start_text), int(end_text)
                if start > end:
                    raise CronContractError("Descending weekday ranges are not supported.")
                numbers.update(range(start, end + 1))
            else:
                numbers.add(int(item))
        numbers = {0 if number == 7 else number for number in numbers}
        if not numbers or any(number not in range(7) for number in numbers):
            raise CronContractError("Statistics cron contains an invalid weekday.")
        days = [DAY_NAMES[number] for number in range(7) if number in numbers]
    return clock, days


def validate_timezone(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise CronContractError("An IANA timezone is required.")
    try:
        ZoneInfo(cleaned)
    except ZoneInfoNotFoundError as exc:
        raise CronContractError(f"Unknown IANA timezone: {cleaned}.") from exc
    return cleaned


def _spec(deck: str) -> dict[str, Any]:
    try:
        return job_specs()[deck]
    except KeyError as exc:
        raise CronContractError(f"Unsupported statistics deck: {deck}.") from exc


def _matches_int(value: object, expected: int) -> bool:
    try:
        return int(value) == expected
    except (TypeError, ValueError):
        return False
