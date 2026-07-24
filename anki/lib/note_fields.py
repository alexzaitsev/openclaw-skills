"""Pure field conversion for Anki notes used by the Anki skill."""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser
from typing import Any


CONTEXT_SUFFIX = re.compile(
    r'<br><div class="context">Контекст:\s*(.*?)</div>\s*$', re.DOTALL
)


class NoteFieldError(ValueError):
    """Raised when AnkiConnect returns fields outside this skill's contract."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(value: object) -> str:
    parser = _TextExtractor()
    parser.feed(str(value))
    parser.close()
    return " ".join("".join(parser.parts).split())


def html_front(front: str, image_name: str | None = None) -> str:
    if not image_name:
        return escape(front)
    return f'{escape(front)}<br><img alt="{escape(front)}" src="{escape(image_name)}">'


def html_back(back: str, context: str | None = None) -> str:
    if not context:
        return escape(back)
    return (
        f'{escape(back)}<br><div class="context">Контекст: {escape(context)}</div>'
    )


def contains_media(value: object) -> bool:
    return bool(
        re.search(r"(?:<(?:img|audio|video)\b|\[sound:)", str(value), re.IGNORECASE)
    )


def read_note_content(note: dict[str, Any], note_id: int) -> dict[str, object]:
    """Return display content and its context storage for one Anki note.

    Current models store context in a dedicated ``Context`` field. Older cards
    may retain the skill's legacy HTML suffix in ``Back``; it stays readable
    and editable without being mistaken for a second context value.
    """
    fields = note.get("fields")
    if not isinstance(fields, dict):
        raise NoteFieldError(f"AnkiConnect returned invalid fields for note {note_id}.")
    front_html = _field_value(fields, "Front", note_id)
    back_html = _field_value(fields, "Back", note_id)
    has_context_field = "Context" in fields
    context_html = _field_value(fields, "Context", note_id) if has_context_field else ""
    legacy_match = CONTEXT_SUFFIX.search(back_html)

    if has_context_field:
        context = plain_text(context_html) or None
        # A blank Context field on an older note can coexist with legacy markup.
        # Read it faithfully, then let a later edit normalize it to the field.
        if context is None and legacy_match:
            return {
                "front": plain_text(front_html),
                "back": plain_text(back_html[: legacy_match.start()]),
                "context": plain_text(legacy_match.group(1)) or None,
                "has_context_field": True,
            }
        return {
            "front": plain_text(front_html),
            "back": plain_text(back_html),
            "context": context,
            "has_context_field": True,
        }

    if legacy_match:
        back_html = back_html[: legacy_match.start()]
        context = plain_text(legacy_match.group(1)) or None
    else:
        context = None
    return {
        "front": plain_text(front_html),
        "back": plain_text(back_html),
        "context": context,
        "has_context_field": False,
    }


def build_note_fields(
    front: str,
    back: str,
    context: str | None,
    model_fields: list[str],
    extra_fields: dict[str, str],
    image_name: str | None = None,
) -> dict[str, str]:
    """Build a complete field mapping for a new note in the live model schema."""
    fields = {name: "" for name in model_fields}
    fields["Front"] = html_front(front, image_name)
    fields["Back"] = html_back(back, None if "Context" in fields else context)
    if "Context" in fields:
        fields["Context"] = escape(context or "")
    fields.update({name: escape(value) for name, value in extra_fields.items()})
    return fields


def build_text_updates(
    content: dict[str, object],
    *,
    front: str,
    back: str,
    context: str | None,
    change_front: bool,
    change_back_or_context: bool,
) -> dict[str, str]:
    """Build only changed editable fields while preserving their storage contract."""
    updates: dict[str, str] = {}
    if change_front:
        updates["Front"] = html_front(front)
    if change_back_or_context:
        if bool(content["has_context_field"]):
            updates["Back"] = html_back(back)
            updates["Context"] = escape(context or "")
        else:
            updates["Back"] = html_back(back, context)
    return updates


def _field_value(fields: dict[str, Any], name: str, note_id: int) -> str:
    field = fields.get(name)
    value = field.get("value") if isinstance(field, dict) else None
    if value is None:
        raise NoteFieldError(f"Note {note_id} has no {name} field.")
    return str(value)
