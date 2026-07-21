#!/usr/bin/env python3
"""Deterministic Markdown rendering for Anki statistics."""

from __future__ import annotations

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
TELEGRAM_LIMIT = 4096


def render_report(deck: str, history: dict[str, Any], state: dict[str, int]) -> str:
    flag, label = DECK_LABELS[deck]
    report_date = date.fromisoformat(history["report_date"])
    run_date = report_date + timedelta(days=1)
    yesterday = history["yesterday"]
    current = history["current"]
    previous = history["previous"]
    yesterday_answers = _count(
        yesterday["answers"], "ответ", "ответа", "ответов"
    )
    yesterday_cards = _count(
        yesterday["unique_cards"],
        "карточка",
        "карточки",
        "карточек",
    )
    current_answers = _count(
        current["answers"], "ответ", "ответа", "ответов"
    )
    learning_items = _count(
        state["learning_items"],
        "учебный элемент",
        "учебных элемента",
        "учебных элементов",
    )
    mature_items = _count(
        state["mature_items"],
        "элемент закреплён",
        "элемента закреплено",
        "элементов закреплено",
    )
    cards = _count(
        state["cards"], "карточка", "карточки", "карточек"
    )

    yesterday_lines = [
        (
            f"{yesterday_answers} · {yesterday_cards} · "
            f"{format_duration(yesterday['duration_ms'])}"
        ),
        (
            f"Снова {yesterday['again']} · успешных ответов "
            f"{format_percent(yesterday['answer_pass_rate'])}"
        ),
        (
            f"**Запоминание {format_percent(yesterday['true_retention'])}** "
            f"({yesterday['true_passes']}/{yesterday['true_total']})"
        ),
    ]
    seven_day_lines = []
    for day in history["days"]:
        parsed = date.fromisoformat(day["date"])
        seven_day_lines.append(
            f"{WEEKDAY_LABELS[parsed.weekday()]} {day['answers']} · "
            f"{format_percent(day['true_retention'])}"
        )
    seven_day_lines.extend(
        [
            (
                f"**{current_answers}** · {current['days_studied']}/7 дней · "
                f"{current['average_answers']}/день · "
                f"{format_duration(current['duration_ms'])}"
            ),
            _comparison_line(current, previous),
        ]
    )
    lines = [
        f"**{flag} {label} · {deck}**",
        "",
        f"**Колода сейчас · {_display_date(run_date)}**",
        f"{learning_items} · начато {state['introduced_items']}",
        f"{mature_items} · {cards}",
        (
            f"**Доступно сейчас:** новых {state['due_new']} · "
            f"изучаются {state['due_learning']} · "
            f"к повторению {state['due_review']}"
        ),
        "",
        f"**Вчера · {_display_date(report_date)}**",
        _spoiler(yesterday_lines),
        "",
        "**Последние 7 дней**",
        _spoiler(seven_day_lines),
    ]
    report = "\n".join(lines)
    if len(report) <= TELEGRAM_LIMIT:
        return report
    return render_compact_report(deck, history, state)


def render_compact_report(
    deck: str, history: dict[str, Any], state: dict[str, int]
) -> str:
    flag, label = DECK_LABELS[deck]
    report_date = date.fromisoformat(history["report_date"])
    run_date = report_date + timedelta(days=1)
    yesterday = history["yesterday"]
    current = history["current"]
    yesterday_answers = _count(
        yesterday["answers"], "ответ", "ответа", "ответов"
    )
    current_answers = _count(
        current["answers"], "ответ", "ответа", "ответов"
    )
    learning_items = _count(
        state["learning_items"],
        "учебный элемент",
        "учебных элемента",
        "учебных элементов",
    )
    mature_items = _count(
        state["mature_items"],
        "элемент закреплён",
        "элемента закреплено",
        "элементов закреплено",
    )
    return "\n".join(
        [
            f"**{flag} {label} · {deck}**",
            f"**Колода сейчас · {_display_date(run_date)}:** "
            f"{learning_items} · {mature_items} · "
            f"карточек {state['cards']}",
            (
                f"**Доступно:** новых {state['due_new']} · "
                f"изучаются {state['due_learning']} · "
                f"к повторению {state['due_review']}"
            ),
            f"**Вчера · {_display_date(report_date)}**",
            _spoiler(
                [
                    f"{yesterday_answers} · "
                    f"запоминание {format_percent(yesterday['true_retention'])}"
                ]
            ),
            "**Последние 7 дней**",
            _spoiler(
                [
                    f"**{current_answers}** · запоминание "
                    f"{format_percent(current['true_retention'])} · "
                    f"{current['days_studied']}/7 дней"
                ]
            ),
        ]
    )


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


def _spoiler(lines: list[str]) -> str:
    """Wrap one section's content in Telegram's Markdown spoiler syntax."""
    return "||" + "\n".join(lines) + "||"


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


def _comparison_line(current: dict[str, Any], previous: dict[str, Any]) -> str:
    previous_answers = previous["answers"]
    if previous_answers == 0 and current["answers"] > 0:
        answer_change = "ответы: новая активность"
    elif previous_answers == 0:
        answer_change = "ответы 0%"
    else:
        change = round((current["answers"] - previous_answers) * 100 / previous_answers)
        answer_change = f"ответы {change:+d}%"

    retention = (
        f"**Запоминание {format_percent(current['true_retention'])}**"
    )
    if current["true_retention"] is not None and previous["true_retention"] is not None:
        previous_retention = format_percent(previous["true_retention"])
        retention += (
            f" · {answer_change} · неделей ранее {previous_retention}"
        )
    else:
        retention += f" · {answer_change}"
    return retention
