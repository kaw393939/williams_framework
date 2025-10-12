"""Basic heuristic content transformer."""
from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime
from typing import Iterable
from urllib.parse import urlparse

from app.core.models import ProcessedContent, RawContent, ScreeningResult

from .base import ContentTransformer


STOPWORDS: set[str] = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "from",
    "this",
    "have",
    "will",
    "your",
    "about",
    "into",
    "their",
    "there",
    "where",
    "which",
    "while",
    "using",
    "against",
    "should",
    "would",
    "could",
    "because",
    "however",
    "among",
    "across",
    "being",
    "over",
    "under",
    "after",
    "before",
}


class BasicContentTransformer(ContentTransformer):
    """Derive summaries, key points, and tags using lightweight heuristics."""

    def __init__(self, *, max_summary_length: int = 400, max_key_points: int = 3, max_tags: int = 5):
        self._max_summary_length = max_summary_length
        self._max_key_points = max_key_points
        self._max_tags = max_tags

    async def transform(self, raw_content: RawContent) -> ProcessedContent:
        text = raw_content.raw_text.strip()

        summary = self._build_summary(text)
        key_points = self._extract_key_points(text)
        tags = self._generate_tags(text)
        screening_result = self._score_content(text)

        title = raw_content.metadata.get("title") or self._fallback_title(str(raw_content.url))

        return ProcessedContent(
            url=raw_content.url,
            source_type=raw_content.source_type,
            title=title,
            summary=summary,
            key_points=key_points,
            tags=tags,
            screening_result=screening_result,
            processed_at=datetime.now(),
        )

    def _build_summary(self, text: str) -> str:
        if not text:
            return ""

        sentences = self._split_sentences(text)
        if not sentences:
            return text[: self._max_summary_length]

        summary = " ".join(sentences[:2])
        return summary[: self._max_summary_length]

    def _extract_key_points(self, text: str) -> list[str]:
        sentences = self._split_sentences(text)
        if not sentences:
            return [text] if text else []

        return sentences[: self._max_key_points]

    def _generate_tags(self, text: str) -> list[str]:
        tokens = [token.lower() for token in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text)]
        filtered = [t for t in tokens if len(t) > 3 and t not in STOPWORDS]
        if not filtered:
            return tokens[: self._max_tags]

        counts = Counter(filtered)
        top = counts.most_common(self._max_tags)
        return [word for word, _ in top]

    def _score_content(self, text: str) -> ScreeningResult:
        tokens = re.findall(r"[\w']+", text.lower())
        word_count = len(tokens)
        unique_count = len(set(tokens))
        sentence_count = max(1, len(self._split_sentences(text)))

        richness = unique_count / word_count if word_count else 0.0
        structure = sentence_count / max(1, math.sqrt(word_count))

        quality = 3.0 + (richness * 4.0) + min(2.0, word_count / 400.0) + min(1.0, structure)
        quality = max(0.0, min(10.0, round(quality, 2)))

        if quality >= 7.5:
            decision = "ACCEPT"
            reasoning = "Content is comprehensive and well structured."
        elif quality >= 5.5:
            decision = "MAYBE"
            reasoning = "Content is decent but may need review."
        else:
            decision = "REJECT"
            reasoning = "Content appears too sparse for high confidence."

        screening_score = max(0.0, min(10.0, quality - 0.5))

        return ScreeningResult(
            screening_score=screening_score,
            decision=decision,
            reasoning=reasoning,
            estimated_quality=quality,
        )

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    @staticmethod
    def _fallback_title(url: str) -> str:
        parsed = urlparse(url)
        candidate = parsed.path.rstrip("/").split("/")[-1]
        if candidate and len(candidate) >= 8 and any(ch.isalpha() for ch in candidate):
            return candidate.replace("-", " ").strip()
        return url
