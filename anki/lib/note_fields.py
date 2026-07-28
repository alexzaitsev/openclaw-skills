"""Pure field conversion for Anki notes used by the Anki skill."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
from typing import Any


CONTEXT_SUFFIX = re.compile(
    r'<br><div class="context">Контекст:\s*(.*?)</div>\s*$', re.DOTALL
)


class NoteFieldError(ValueError):
    """Raised when AnkiConnect returns fields outside this skill's contract."""


@dataclass(frozen=True)
class FrontContent:
    """One strictly reversible Front representation for content-only edits.

    ``preserved_html`` is deliberately opaque to callers.  It is copied from
    Anki verbatim, never reconstructed from parsed attributes or media paths.
    """

    content: str
    preserved_html: str
    media_types: tuple[str, ...]
    original_html_sha256: str

    @property
    def media_count(self) -> int:
        return len(self.media_types)


class _FrontStructureParser(HTMLParser):
    """Validate the intentionally small Front-with-attachments grammar.

    The editable prefix is text only.  Once preserved markup begins, only
    ``br``, media elements, and standalone ``[sound:name]`` attachments are
    accepted, with no visible text interleaved between them.  This lets the
    serializer retain the exact original suffix without trying to understand
    arbitrary Anki HTML.
    """

    _MEDIA_TAGS = {"img", "audio", "video"}

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.preserved_offset: int | None = None
        self.in_preserved = False
        self.media_types: list[str] = []
        self.error: str | None = None
        self.open_media: list[str] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        if line == 1:
            return column
        lines = self.source.splitlines(keepends=True)
        return sum(len(item) for item in lines[: line - 1]) + column

    def _fail(self, reason: str) -> None:
        if self.error is None:
            self.error = reason

    def _begin_preserved(self) -> None:
        if not self.in_preserved:
            self.in_preserved = True
            self.preserved_offset = self._offset()

    def _begin_preserved_at(self, offset: int) -> None:
        if not self.in_preserved:
            self.in_preserved = True
            self.preserved_offset = offset

    def handle_data(self, data: str) -> None:
        if not self.in_preserved:
            sound_offset = data.find("[sound:")
            if sound_offset >= 0:
                self._begin_preserved_at(self._offset() + sound_offset)
                data = data[sound_offset:]
            else:
                return
        if not data.isspace():
            if data.startswith("[sound:") and data.endswith("]") and len(data) > 8:
                self.media_types.append("sound")
            else:
                self._fail("visible text is interleaved with preserved Front markup")

    def handle_entityref(self, name: str) -> None:
        if self.in_preserved:
            self._fail("an HTML entity is interleaved with preserved Front markup")

    def handle_charref(self, name: str) -> None:
        if self.in_preserved:
            self._fail("an HTML character reference is interleaved with preserved Front markup")

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if not self.in_preserved:
            if tag not in self._MEDIA_TAGS | {"br"}:
                self._fail(f"unsupported Front element <{tag}>")
                return
            self._begin_preserved()
        if tag == "br":
            return
        if tag not in self._MEDIA_TAGS:
            self._fail(f"unsupported Front element <{tag}>")
            return
        self.media_types.append(tag)
        if tag in {"audio", "video"}:
            self.open_media.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.casefold() in {"audio", "video"} and self.open_media:
            self.open_media.pop()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag not in {"audio", "video"} or not self.open_media or self.open_media[-1] != tag:
            self._fail(f"unsupported or unbalanced Front closing tag </{tag}>")
            return
        self.open_media.pop()

    def handle_comment(self, _data: str) -> None:
        self._fail("comments are not supported in a content-editable Front")

    def handle_decl(self, _decl: str) -> None:
        self._fail("declarations are not supported in a content-editable Front")

    def unknown_decl(self, _data: str) -> None:
        self._fail("declarations are not supported in a content-editable Front")


def parse_front_content(value: object) -> FrontContent:
    """Parse the safe ``text + preserved attachments`` Front shape.

    This is intentionally not a general HTML transformation.  Any markup in
    the editable text, media without an unambiguous suffix, or interleaved
    visible content fails before an Anki write is attempted.
    """
    source = str(value)
    parser = _FrontStructureParser(source)
    parser.feed(source)
    parser.close()
    if parser.error:
        raise NoteFieldError(
            "Front content editing is not supported for this HTML structure: " + parser.error + "."
        )
    if parser.open_media:
        raise NoteFieldError(
            "Front content editing is not supported for this HTML structure: unclosed media element."
        )
    if parser.preserved_offset is None:
        if "<" in source or ">" in source:
            raise NoteFieldError(
                "Front content editing is not supported for this HTML structure: markup is ambiguous."
            )
        content = plain_text(source)
        preserved_html = ""
    else:
        content = plain_text(source[: parser.preserved_offset])
        preserved_html = source[parser.preserved_offset :]
    if not content:
        raise NoteFieldError("Front content editing requires non-empty visible text before media.")
    if preserved_html and not parser.media_types:
        raise NoteFieldError(
            "Front content editing is not supported for this HTML structure: no preserved attachment."
        )
    return FrontContent(
        content=content,
        preserved_html=preserved_html,
        media_types=tuple(parser.media_types),
        original_html_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
    )


def serialize_front_content(content: str, front: FrontContent) -> str:
    """Escape new visible text and append the exact reviewed protected suffix."""
    normalized = content.strip()
    if not normalized:
        raise NoteFieldError("Front content must be non-empty.")
    return escape(normalized) + front.preserved_html


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
