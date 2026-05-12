"""CC-041: Section-aware chunking for clinical documents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TARGET_MIN = 500   # chars
_TARGET_MAX = 1500  # chars

_SECTION_PATTERNS = re.compile(
    r"^(?:ASSESSMENT|PLAN|DIAGNOSIS|DIAGNOS[EI]S|MEDICATIONS?|LABS?|LABORATORY|"
    r"VITALS?|CHIEF COMPLAINT|HISTORY|HPI|REVIEW OF SYSTEMS|PHYSICAL EXAM|"
    r"IMPRESSION|RECOMMENDATIONS?|FOLLOW[ -]UP|DISCHARGE|INSTRUCTIONS?|"
    r"ALLERGIES|PROCEDURES?|RESULTS?|SUMMARY)[:\s]*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class Chunk:
    text: str
    chunk_index: int
    page_number: int | None = None
    section: str | None = None
    char_start: int = 0
    char_end: int = 0


def chunk_clinical_document(
    text: str,
    sections: list[str] | None = None,
    page_boundaries: dict[int, int] | None = None,
) -> list[Chunk]:
    """Split a clinical document into chunks respecting section boundaries.

    Args:
        text: Full document text.
        sections: Optional list of section header names to split on.
        page_boundaries: Optional map of char_offset → page_number.

    Returns:
        List of Chunk objects.
    """
    # Split into blocks at section headers
    blocks = _split_at_sections(text)

    chunks: list[Chunk] = []
    idx = 0

    for section_name, block_text, char_start in blocks:
        # If block fits in target window, emit as-is
        if len(block_text) <= _TARGET_MAX:
            page = _page_for_offset(char_start, page_boundaries)
            chunks.append(Chunk(
                text=block_text.strip(),
                chunk_index=idx,
                page_number=page,
                section=section_name,
                char_start=char_start,
                char_end=char_start + len(block_text),
            ))
            idx += 1
        else:
            # Sliding window split within the block
            sub_chunks = _sliding_split(block_text, char_start)
            for sub_text, sub_start, sub_end in sub_chunks:
                page = _page_for_offset(sub_start, page_boundaries)
                chunks.append(Chunk(
                    text=sub_text.strip(),
                    chunk_index=idx,
                    page_number=page,
                    section=section_name,
                    char_start=sub_start,
                    char_end=sub_end,
                ))
                idx += 1

    return [c for c in chunks if len(c.text) >= 20]


def _split_at_sections(text: str) -> list[tuple[str | None, str, int]]:
    """Return list of (section_name, block_text, char_start)."""
    results: list[tuple[str | None, str, int]] = []
    last_header: str | None = None
    last_pos = 0

    for m in _SECTION_PATTERNS.finditer(text):
        block = text[last_pos:m.start()]
        if block.strip():
            results.append((last_header, block, last_pos))
        last_header = m.group(0).strip().rstrip(":")
        last_pos = m.end()

    # trailing block
    trailing = text[last_pos:]
    if trailing.strip():
        results.append((last_header, trailing, last_pos))

    # If no section headers found, return the whole text as one block
    if not results:
        results = [(None, text, 0)]

    return results


def _sliding_split(
    text: str, offset: int
) -> list[tuple[str, int, int]]:
    """Split large block with a sliding window at sentence boundaries."""
    results = []
    start = 0
    while start < len(text):
        end = min(start + _TARGET_MAX, len(text))
        if end < len(text):
            # Try to break at sentence boundary
            boundary = text.rfind(". ", start + _TARGET_MIN, end)
            if boundary != -1:
                end = boundary + 2
        chunk = text[start:end]
        results.append((chunk, offset + start, offset + end))
        start = end
    return results


def _page_for_offset(
    char_offset: int, page_boundaries: dict[int, int] | None
) -> int | None:
    if not page_boundaries:
        return None
    page = None
    for boundary, pg in sorted(page_boundaries.items()):
        if char_offset >= boundary:
            page = pg
    return page
