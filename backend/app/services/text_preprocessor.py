"""
text_preprocessor.py

Lightweight, dependency-free NLP preprocessing utilities: sentence
segmentation, section/heading detection and word statistics. Avoiding a
heavy NLP library (spaCy etc.) keeps the project easy to install for a
college lab machine while still giving solid results on structured legal
text.
"""
from __future__ import annotations

import re
from typing import List, Dict

SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

# Matches contract-style section headings e.g. "1. Termination", "Section 4:",
# "ARTICLE III - LIABILITY", "4.2 Payment Terms"
HEADING_REGEX = re.compile(
    r"^(?:(?:ARTICLE|SECTION|CLAUSE)\s+[IVXLC\d]+\b|(?:\d{1,2}(?:\.\d{1,2})?)[.)]\s+)"
    r"([A-Za-z][A-Za-z0-9 ,/&'-]{2,80})",
    re.IGNORECASE,
)

ALL_CAPS_HEADING_REGEX = re.compile(r"^[A-Z][A-Z0-9 ,/&'-]{3,60}$")


def split_sentences(text: str) -> List[str]:
    """Simple, robust sentence splitter tuned for legal prose."""
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    sentences = SENTENCE_SPLIT_REGEX.split(normalized)
    return [s.strip() for s in sentences if s.strip()]


def split_paragraphs(text: str) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    return paragraphs


def detect_sections(text: str) -> List[Dict]:
    """
    Detect contract sections/headings and the text belonging to each, so
    downstream clause detection can search within a bounded context window
    and clause explanations can quote the right paragraph.
    """
    lines = text.split("\n")
    sections = []
    current_heading = "Preamble"
    current_start = 0
    buffer: List[str] = []
    cursor = 0

    for line in lines:
        line_stripped = line.strip()
        is_heading = False
        heading_text = None

        match = HEADING_REGEX.match(line_stripped)
        if match:
            is_heading = True
            heading_text = line_stripped
        elif ALL_CAPS_HEADING_REGEX.match(line_stripped) and len(line_stripped.split()) <= 8:
            is_heading = True
            heading_text = line_stripped

        if is_heading and buffer:
            sections.append(
                {
                    "heading": current_heading,
                    "content": "\n".join(buffer).strip(),
                    "start_index": current_start,
                    "end_index": cursor,
                }
            )
            buffer = []
            current_heading = heading_text
            current_start = cursor
        elif is_heading and not buffer:
            current_heading = heading_text
            current_start = cursor
        else:
            buffer.append(line)

        cursor += len(line) + 1

    if buffer:
        sections.append(
            {
                "heading": current_heading,
                "content": "\n".join(buffer).strip(),
                "start_index": current_start,
                "end_index": cursor,
            }
        )

    # Fallback: no headings detected at all -> treat whole doc as one section
    if not sections:
        sections = [{"heading": "Full Document", "content": text, "start_index": 0, "end_index": len(text)}]

    return [s for s in sections if s["content"]]


_LEADING_HEADING_RE = re.compile(r"^(?:[A-Z][A-Z0-9,/&'-]*\s+){1,8}(?=[A-Z][a-z])")


def strip_leading_heading(sentence: str) -> str:
    """Drop an ALL-CAPS section heading that sentence splitting merged into the sentence."""
    return _LEADING_HEADING_RE.sub("", sentence)


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def find_context_window(text: str, index: int, window: int = 160) -> str:
    """Return a snippet of text around a matched index for display/highlighting."""
    start = max(0, index - window)
    end = min(len(text), index + window)
    snippet = text[start:end].strip()
    return ("..." if start > 0 else "") + snippet + ("..." if end < len(text) else "")
