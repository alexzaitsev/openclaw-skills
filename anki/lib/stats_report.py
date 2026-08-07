#!/usr/bin/env python3
"""Deterministic Markdown rendering for Anki statistics."""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any


DECK_LABELS = {
    "Español": ("🇪🇸", "Испанский"),
    "English": ("🇬🇧", "Английский"),
}
WEEKDAY_LABELS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
MONTH_LABELS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)
def render_report(deck: str, history: dict[str, Any], state: dict[str, int]) -> str:
    flag, label = DECK_LABELS[deck]
    report_date = date.fromisoformat(history["report_date"])
    run_date = report_date + timedelta(days=1)
    yesterday = history["yesterday"]
    new_days = _new_days(state["unstarted_cards"], state["due_new"])
    lines = [
        f"**{flag} {label} · {deck}**",
        "",
        f"**Вчера · {_display_date(report_date)}**",
        _code_block(
            [
                _aligned("Повторено:", yesterday["review_cards"]),
                _aligned("Новых:", yesterday["new_cards"]),
                _aligned("Время:", _report_duration(yesterday["duration_ms"])),
            ]
        ),
        "",
        f"**Сегодня · {_display_date(run_date)}**",
        _code_block(
            [
                _aligned("Повторить:", state["due_review"]),
                _aligned("Новых:", state["due_new"]),
            ]
        ),
        "",
        "**Прогресс**",
        _code_block(
            [
                _aligned(
                    "Не начато:",
                    f"{_percent(state['unstarted_cards'], state['cards'])}% "
                    f"({state['unstarted_cards']})",
                ),
                _aligned(
                    "Изучается:",
                    f"{_percent(state['studying_cards'], state['cards'])}% "
                    f"({state['studying_cards']})",
                ),
                _aligned(
                    "Закреплено:",
                    f"{_percent(state['mature_cards'], state['cards'])}% "
                    f"({state['mature_cards']})",
                ),
                _aligned("Новых на:", _days_ahead(new_days)),
            ]
        ),
    ]
    return "\n".join(lines)


def render_compact_report(
    deck: str, history: dict[str, Any], state: dict[str, int]
) -> str:
    return render_report(deck, history, state)


def format_duration(milliseconds: int) -> str:
    seconds = max(0, round(milliseconds / 1000))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours} ч {minutes} мин"
    if minutes:
        return f"{minutes} мин {seconds} с"
    return f"{seconds} с"


def format_percent(value: float | None) -> str:
    return "—" if value is None else f"{round(value * 100)}%"


def _report_duration(milliseconds: int) -> str:
    """Render report study time as completed whole minutes."""
    return f"{max(0, milliseconds // 60_000)} мин"


def _aligned(label: str, value: int | str) -> str:
    return f"{label:<12}{value}"


def _code_block(lines: list[str]) -> str:
    return "```\n" + "\n".join(lines) + "\n```"


def _percent(value: int, total: int) -> int:
    return round(value * 100 / total) if total else 0


def _new_days(unstarted_cards: int, new_per_day: int) -> int | None:
    if new_per_day <= 0:
        return None
    return math.ceil(max(0, unstarted_cards) / new_per_day)


def _days_ahead(value: int | None) -> str:
    if value is None:
        return "—"
    return f"{value} {_count(value, 'день', 'дня', 'дней').split(' ', 1)[1]} вперед"


def _display_date(value: date) -> str:
    weekday = WEEKDAY_LABELS[value.weekday()].lower()
    return f"{weekday} {value.day} {MONTH_LABELS[value.month - 1]}"


def _count(value: int, one: str, few: str, many: str) -> str:
    remainder_100 = abs(value) % 100
    remainder_10 = remainder_100 % 10
    if 11 <= remainder_100 <= 14:
        word = many
    elif remainder_10 == 1:
        word = one
    elif 2 <= remainder_10 <= 4:
        word = few
    else:
        word = many
    return f"{value} {word}"


def _mature_word(value: int) -> str:
    """Return the compact maturity label used in the deck-state summary."""
    remainder_100 = abs(value) % 100
    return "закреплён" if remainder_100 % 10 == 1 and remainder_100 != 11 else "закреплено"
