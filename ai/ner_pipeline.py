from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

EntityKind = Literal["person", "phone", "organization", "location", "account", "alias"]

PHONE_RE = re.compile(r"(?:\+91[\s-]?)?(?:91[\s-]?)?([6-9]\d{9})")
ACCOUNT_RE = re.compile(r"\b(?:A/C|account|acct)[\s:#-]*(\d{8,18})\b", re.I)
VEHICLE_RE = re.compile(r"\b([A-Z]{2}\d{2}[A-Z]{1,2}\d{4})\b")
# Hindi/Devanagari person names (2–4 words) — regex supplement; English uses spaCy
HINDI_NAME_RE = re.compile(
    r"([\u0900-\u097F]{2,12})\s+([\u0900-\u097F]{2,12})(?=\s|[,.]|$)"
)
HINDI_NEXT_WORD = re.compile(r"^\s+([\u0900-\u097F]{2,12})(?=\s|[,.]|$)")
HINDI_STOP = frozenset({"संदिग्ध", "फोन", "किया", "संदेश", "शिकायत"})
ALIAS_RE = re.compile(
    r"(?:aka|a\.k\.a\.|alias|also known as|identifies as)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",
    re.I,
)

_spacy_nlp = None


def _load_spacy():
    global _spacy_nlp
    if _spacy_nlp is not None:
        return _spacy_nlp
    try:
        import spacy

        _spacy_nlp = spacy.load("en_core_web_sm")
    except Exception:
        _spacy_nlp = False
    return _spacy_nlp


def spacy_available() -> bool:
    return bool(_load_spacy())


def nlp_engine_name() -> str:
    return "spacy" if spacy_available() else "regex"


@dataclass
class ExtractedEntity:
    text: str
    entity_type: EntityKind
    start: int
    end: int
    confidence: float


def _dedupe(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    seen: set[tuple[str, EntityKind]] = set()
    out: list[ExtractedEntity] = []
    for ent in sorted(entities, key=lambda e: (-e.confidence, e.start)):
        key = (ent.text.lower().strip(), ent.entity_type)
        if key in seen:
            continue
        seen.add(key)
        out.append(ent)
    return sorted(out, key=lambda e: e.start)


def extract_entities(text: str) -> list[ExtractedEntity]:
    """Extract persons, phones, orgs, locations from FIR/CDR/chat text."""
    if not text.strip():
        return []

    entities: list[ExtractedEntity] = []

    for match in PHONE_RE.finditer(text):
        entities.append(
            ExtractedEntity(
                text=match.group(1),
                entity_type="phone",
                start=match.start(1),
                end=match.end(1),
                confidence=0.98,
            )
        )

    for match in ACCOUNT_RE.finditer(text):
        entities.append(
            ExtractedEntity(
                text=match.group(1),
                entity_type="account",
                start=match.start(1),
                end=match.end(1),
                confidence=0.9,
            )
        )

    for match in VEHICLE_RE.finditer(text):
        entities.append(
            ExtractedEntity(
                text=match.group(1),
                entity_type="location",
                start=match.start(1),
                end=match.end(1),
                confidence=0.78,
            )
        )

    for match in ALIAS_RE.finditer(text):
        entities.append(
            ExtractedEntity(
                text=match.group(1).strip(),
                entity_type="alias",
                start=match.start(1),
                end=match.end(1),
                confidence=0.88,
            )
        )

    for match in HINDI_NAME_RE.finditer(text):
        w1, w2 = match.group(1), match.group(2)
        if w1 in HINDI_STOP and w2 in HINDI_STOP:
            continue
        if w1 in HINDI_STOP:
            next_match = HINDI_NEXT_WORD.match(text[match.end(2) :])
            if next_match and next_match.group(1) not in HINDI_STOP:
                name = f"{w2} {next_match.group(1)}"
                end = match.end(2) + next_match.end(1)
            else:
                name = w2
                end = match.end(2)
            start = match.start(2)
        elif w2 in HINDI_STOP:
            name = w1
            start = match.start(1)
            end = match.end(1)
        else:
            name = f"{w1} {w2}"
            start = match.start(1)
            end = match.end(2)
        entities.append(
            ExtractedEntity(
                text=name,
                entity_type="person",
                start=start,
                end=end,
                confidence=0.75,
            )
        )

    nlp = _load_spacy()
    if nlp:
        doc = nlp(text[:100000])
        for span in doc.ents:
            if span.label_ == "PERSON" and len(span.text.strip()) >= 3:
                entities.append(
                    ExtractedEntity(
                        text=span.text.strip(),
                        entity_type="person",
                        start=span.start_char,
                        end=span.end_char,
                        confidence=0.86,
                    )
                )
            elif span.label_ == "ORG":
                entities.append(
                    ExtractedEntity(
                        text=span.text.strip(),
                        entity_type="organization",
                        start=span.start_char,
                        end=span.end_char,
                        confidence=0.82,
                    )
                )
            elif span.label_ in {"GPE", "LOC", "FAC"}:
                entities.append(
                    ExtractedEntity(
                        text=span.text.strip(),
                        entity_type="location",
                        start=span.start_char,
                        end=span.end_char,
                        confidence=0.8,
                    )
                )

    # Capitalized name supplement (spaCy may miss Indian names in FIR prose)
    name_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b")
    skip_names = {"police station", "first information", "information report"}
    for match in name_pattern.finditer(text):
        candidate = match.group(1)
        if candidate.lower() in skip_names:
            continue
        entities.append(
            ExtractedEntity(
                text=candidate,
                entity_type="person",
                start=match.start(1),
                end=match.end(1),
                confidence=0.74 if nlp else 0.72,
            )
        )

    return _dedupe(entities)
