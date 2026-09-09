#!/usr/bin/env python3
"""Quick NER checks including Hindi Devanagari supplement."""

from ai.ner_pipeline import extract_entities


def test_hindi_name_extraction():
    text = "संदिग्ध राहुल शर्मा ने फोन किया।"
    found = [e.text for e in extract_entities(text) if e.entity_type == "person"]
    assert any("राहुल" in f for f in found), found


def test_english_person_extraction():
    text = "Suspect Rahul Mukherjee called from Mumbai."
    entities = extract_entities(text)
    labels = {e.text for e in entities}
    assert any("Rahul" in t for t in labels), labels
