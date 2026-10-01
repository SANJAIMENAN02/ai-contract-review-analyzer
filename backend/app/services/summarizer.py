"""
summarizer.py

Generates a contract summary two ways:

1. Extractive summarization (default, no external dependency): a simple
   TextRank-like algorithm that scores sentences by word-overlap similarity
   and picks the highest scoring, most representative sentences. This is
   what runs "out of the box" with no API key.

2. Optional AI enhancement: if OPENAI_API_KEY (or ANTHROPIC_API_KEY) is set
   in the environment, we call an OpenAI-compatible chat completion endpoint
   to produce a more fluent abstractive summary. If the call fails for any
   reason (no internet, bad key, rate limit) we silently fall back to the
   extractive summary so the app never breaks.
"""
from __future__ import annotations

import os
import re
import math
from collections import Counter
from typing import List, Dict

import httpx

from app.services.text_preprocessor import split_sentences, strip_leading_heading

STOPWORDS = set(
    """a an the and or but if while is are was were be been being to of in on for with
    as by at from this that these those it its it's their his her they he she we you your
    shall will may not no such other than any all each per hereby herein thereof whereas
    party parties agreement contract""".split()
)


def _tokenize(sentence: str) -> List[str]:
    words = re.findall(r"[a-zA-Z]+", sentence.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def _sentence_similarity(tokens_a: List[str], tokens_b: List[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    set_a, set_b = set(tokens_a), set(tokens_b)
    overlap = len(set_a & set_b)
    if overlap == 0:
        return 0.0
    return overlap / (math.log(len(set_a) + 1) + math.log(len(set_b) + 1) + 1e-9)


def extractive_summary(text: str, max_sentences: int = 6) -> str:
    """
    A dependency-free TextRank-style extractive summarizer:
      1. Split into sentences
      2. Build a similarity graph between sentences
      3. Score sentences via a simplified power-iteration (like PageRank)
      4. Return the top-N sentences, re-ordered by original position for readability
    """
    sentences = [strip_leading_heading(s) for s in split_sentences(text)]
    # Filter out extremely short / boilerplate lines (e.g. page numbers, headers)
    sentences = [s for s in sentences if len(s.split()) >= 6]

    if not sentences:
        return "This document did not contain enough extractable prose to summarize."

    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    tokenized = [_tokenize(s) for s in sentences]
    n = len(sentences)

    # Build similarity matrix
    similarity = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                similarity[i][j] = _sentence_similarity(tokenized[i], tokenized[j])

    # Simplified PageRank via power iteration
    scores = [1.0] * n
    damping = 0.85
    for _ in range(20):
        new_scores = [0.0] * n
        for i in range(n):
            incoming = 0.0
            for j in range(n):
                if i == j:
                    continue
                row_sum = sum(similarity[j])
                if row_sum > 0:
                    incoming += (similarity[j][i] / row_sum) * scores[j]
            new_scores[i] = (1 - damping) + damping * incoming
        scores = new_scores

    # Boost sentences that mention key contract concepts (parties, term, payment, termination)
    boost_terms = ["agreement", "party", "parties", "shall", "term", "payment", "terminat", "liab"]
    for i, sent in enumerate(sentences):
        lower = sent.lower()
        if any(term in lower for term in boost_terms):
            scores[i] *= 1.15

    ranked_indices = sorted(range(n), key=lambda i: scores[i], reverse=True)[:max_sentences]
    ranked_indices.sort()  # restore original order for readability

    summary = " ".join(sentences[i] for i in ranked_indices)
    return summary


async def ai_summary(text: str) -> str | None:
    """
    Optional enhancement: call an OpenAI-compatible chat completions endpoint
    if an API key is configured. Returns None (never raises) if unavailable
    or on any error, so the caller can fall back to extractive_summary().
    """
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        return None

    truncated_text = text[:12000]  # keep prompt cost/size reasonable

    prompt = (
        "You are a contract analysis assistant. Summarize the following contract in "
        "4-6 sentences, covering: the parties involved, the purpose of the contract, "
        "duration, key payment obligations, termination conditions, and the most "
        "significant risks. Be concise and neutral.\n\nCONTRACT TEXT:\n" + truncated_text
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 400,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content if content else None
    except Exception:  # noqa: BLE001 -- any failure silently falls back
        return None


async def generate_summary(text: str) -> str:
    """Public entry point: try AI summary first (if configured), else extractive."""
    summary = await ai_summary(text)
    if summary:
        return summary
    return extractive_summary(text)


async def generate_summary_with_mode(text: str) -> tuple[str, str]:
    """Like generate_summary(), but also reports which mode produced it ('ai' or 'local')."""
    summary = await ai_summary(text)
    if summary:
        return summary, "ai"
    return extractive_summary(text), "local"
