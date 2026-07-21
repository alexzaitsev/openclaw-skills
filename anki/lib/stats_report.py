#!/usr/bin/env python3
"""Deterministic plain-text rendering for Anki statistics."""

from __future__ import annotations

from datetime import date
from typing import Any


DECK_LABELS = {
    "Español": ("🇪🇸", "Spanish"),
    "English": ("🇬🇧", "English"),
}
TELEGRAM_LIMIT = 4096


def render_report(deck: str, history: dict[str, Any], state: dict[str, int]) -> str:
    flag, label = DECK_LABELS[deck]
    report_date = date.fromisoformat(history["report_date"])
    yesterday = history["yesterday"]
    current = history["current"]
    previous = history["previous"]

    lines = [
        f"{flag} {label} · {deck}",
        f"Report for {_display_date(report_date)} · {history['timezone']}",
        "",
        "Yesterday",
        (
            f"{yesterday['answers']} answers · {yesterday['unique_cards']} cards · "
            f"{format_duration(yesterday['duration_ms'])}"
        ),
        (
            f"Again {yesterday['again']} · answer pass "
            f"{format_percent(yesterday['answer_pass_rate'])}"
        ),
        (
            f"True retention {format_percent(yesterday['true_retention'])} "
            f"({yesterday['true_passes']}/{yesterday['true_total']})"
        ),
        "",
        "Last 7 completed days",
    ]
    for day in history["days"]:
        parsed = date.fromisoformat(day["date"])
        lines.append(
            f"{parsed.strftime('%a')} {day['answers']} · "
            f"{format_percent(day['true_retention'])}"
        )
    lines.extend(
        [
            (
                f"{current['answers']} answers · {current['days_studied']}/7 days · "
                f"{current['average_answers']}/day · {format_duration(current['duration_ms'])}"
            ),
            _comparison_line(current, previous),
            "",
            "Deck now",
            (
                f"{state['learning_items']} learning items · "
                f"{state['introduced_items']} introduced"
            ),
            (
                f"{state['mature_items']} mature learning items · "
                f"{state['cards']} cards"
            ),
            (
                f"Due now: {state['due_new']} new · {state['due_learning']} learning · "
                f"{state['due_review']} review"
            ),
        ]
    )
    report = "\n".join(lines)
    if len(report) <= TELEGRAM_LIMIT:
        return report
    return render_compact_report(deck, history, state)


def render_compact_report(
    deck: str, history: dict[str, Any], state: dict[str, int]
) -> str:
    flag, label = DECK_LABELS[deck]
    yesterday = history["yesterday"]
    current = history["current"]
    return "\n".join(
        [
            f"{flag} {label} · {deck} · {history['report_date']}",
            (
                f"Yesterday: {yesterday['answers']} answers · "
                f"{format_percent(yesterday['true_retention'])} retention"
            ),
            (
                f"7 days: {current['answers']} answers · "
                f"{format_percent(current['true_retention'])} retention · "
                f"{current['days_studied']}/7 days"
            ),
            (
                f"Deck: {state['learning_items']} items · {state['mature_items']} mature · "
                f"{state['cards']} cards"
            ),
            (
                f"Due: {state['due_new']} new · {state['due_learning']} learning · "
                f"{state['due_review']} review"
            ),
        ]
    )


def format_duration(milliseconds: int) -> str:
    seconds = max(0, round(milliseconds / 1000))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def format_percent(value: float | None) -> str:
    return "—" if value is None else f"{round(value * 100)}%"


def _display_date(value: date) -> str:
    return f"{value.strftime('%a, %b')} {value.day}"


def _comparison_line(current: dict[str, Any], previous: dict[str, Any]) -> str:
    previous_answers = previous["answers"]
    if previous_answers == 0 and current["answers"] > 0:
        answer_change = "answers new activity"
    elif previous_answers == 0:
        answer_change = "answers 0%"
    else:
        change = round((current["answers"] - previous_answers) * 100 / previous_answers)
        answer_change = f"answers {change:+d}%"

    retention = f"True retention {format_percent(current['true_retention'])}"
    if current["true_retention"] is not None and previous["true_retention"] is not None:
        points = round((current["true_retention"] - previous["true_retention"]) * 100)
        retention += f" · {answer_change} · retention {points:+d} pp"
    else:
        retention += f" · {answer_change}"
    return retention
