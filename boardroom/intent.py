"""Turn a plain-language request into the kind of session the Chair will run."""

from __future__ import annotations

import re

from boardroom.models import Kind

_DELETE = re.compile(r"\b(delete|erase|wipe|destroy|purge|shred|trash)\b", re.IGNORECASE)
_REMOVE = re.compile(r"\bremove\b", re.IGNORECASE)
_DUPLICATE = re.compile(r"\b(duplicates?|dupes?|dedup|cleanup|clean up)\b", re.IGNORECASE)
_SIGNATURE = re.compile(r"\b(sign|signed|signature|contract|agreement|quarter)\b", re.IGNORECASE)
_QUESTION = re.compile(
    r"\b(what|which|who|when|where|why|did|show|find|list|summarize|summary)\b|\?",
    re.IGNORECASE,
)


def classify(request: str) -> Kind:
    """Classify a request. A destructive verb outranks a cleanup noun."""
    text = request.strip()
    if _DELETE.search(text):
        return "delete"
    if _REMOVE.search(text):
        if _DUPLICATE.search(text):
            return "duplicate"
        return "delete"
    if _SIGNATURE.search(text) and (_QUESTION.search(text) or "quarter" in text.lower()):
        return "question"
    if _DUPLICATE.search(text):
        return "duplicate"
    # Anything else is an open review. A document answer is only issued
    # for a signature question, so a vague "what" cannot borrow a nearby file.
    return "review"


def wants_last_quarter(request: str) -> bool:
    return bool(re.search(r"\blast\s+quarter\b", request, re.IGNORECASE))


def is_signature_question(request: str) -> bool:
    return bool(re.search(r"\b(sign|signed|signature|contract|agreement)\b", request, re.IGNORECASE))


def photo_scope(request: str) -> bool:
    return bool(
        re.search(r"\b(photos?|images?|pictures?|jpegs?|jpgs?|pngs?)\b", request, re.IGNORECASE)
    )


def confirmed(request: str) -> bool:
    return bool(re.search(r"\bi confirm\b", request, re.IGNORECASE))
