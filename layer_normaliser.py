"""LLM-powered layer normaliser for AutoCAD DXF files.

Classifies CAD layer names to construction element types using a 34-rule
regex corpus first, then falls back to Claude Haiku for unmatched names.
Results are cached in .layer_cache.json to avoid repeat LLM calls.
"""

import json
import re
from enum import Enum
from pathlib import Path
from typing import Sequence

import anthropic

CACHE_FILE = Path(".layer_cache.json")

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


class ElementType(str, Enum):
    Wall = "Wall"
    Door = "Door"
    Window = "Window"
    Slab = "Slab"
    Column = "Column"
    Beam = "Beam"
    Stair = "Stair"
    Unknown = "Unknown"


# 34 regex rules covering ACA-style, plain, hyphenated/underscore, multi-language
_RULES: list[tuple[re.Pattern, ElementType]] = [
    # Walls — ACA / Revit / plain / multilingual
    (re.compile(r"^A[-_]?WALL", re.I), ElementType.Wall),
    (re.compile(r"^STR[-_]?WALL", re.I), ElementType.Wall),
    (re.compile(r"^WALLS?$", re.I), ElementType.Wall),
    (re.compile(r"^WL[-_]", re.I), ElementType.Wall),
    (re.compile(r"WAND", re.I), ElementType.Wall),          # German: Wand
    (re.compile(r"MUR", re.I), ElementType.Wall),            # French: Mur
    (re.compile(r"PAREDE", re.I), ElementType.Wall),         # Portuguese
    (re.compile(r"JDAR|JIDAR", re.I), ElementType.Wall),     # Arabic transliteration
    # Doors
    (re.compile(r"^A[-_]?DOOR", re.I), ElementType.Door),
    (re.compile(r"^DOORS?$", re.I), ElementType.Door),
    (re.compile(r"^DR[-_]", re.I), ElementType.Door),
    (re.compile(r"TÜR|TUER", re.I), ElementType.Door),      # German
    (re.compile(r"PORTE", re.I), ElementType.Door),          # French
    # Windows
    (re.compile(r"^A[-_]?GLAZ", re.I), ElementType.Window),
    (re.compile(r"^WINDOWS?$", re.I), ElementType.Window),
    (re.compile(r"^WIN[-_]", re.I), ElementType.Window),
    (re.compile(r"^WDW[-_]", re.I), ElementType.Window),
    (re.compile(r"FENSTER", re.I), ElementType.Window),      # German
    (re.compile(r"FENÊTRE|FENETRE", re.I), ElementType.Window),  # French
    # Slabs / floors / roofs
    (re.compile(r"^S[-_]?SLAB", re.I), ElementType.Slab),
    (re.compile(r"^SLABS?$", re.I), ElementType.Slab),
    (re.compile(r"^FLOOR", re.I), ElementType.Slab),
    (re.compile(r"^ROOF", re.I), ElementType.Slab),
    (re.compile(r"DECKE|BODEN", re.I), ElementType.Slab),   # German
    (re.compile(r"DALLE|PLANCHER", re.I), ElementType.Slab),# French
    # Columns
    (re.compile(r"^S[-_]?COLS?", re.I), ElementType.Column),
    (re.compile(r"^COLUMNS?$", re.I), ElementType.Column),
    (re.compile(r"^COL[-_]", re.I), ElementType.Column),
    (re.compile(r"STÜTZE|STUETZE", re.I), ElementType.Column),  # German
    # Beams
    (re.compile(r"^S[-_]?BEAM", re.I), ElementType.Beam),
    (re.compile(r"^BEAMS?$", re.I), ElementType.Beam),
    (re.compile(r"TRÄGER|TRAEGER", re.I), ElementType.Beam),    # German
    # Stairs
    (re.compile(r"^A[-_]?STAIR", re.I), ElementType.Stair),
    (re.compile(r"^STAIRS?$", re.I), ElementType.Stair),
]


def _rule_classify(name: str) -> ElementType | None:
    for pattern, element_type in _RULES:
        if pattern.search(name):
            return element_type
    return None


def _load_cache() -> dict[str, str]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_cache(cache: dict[str, str]) -> None:
    try:
        CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except OSError:
        pass


def _llm_classify_batch(names: list[str]) -> dict[str, ElementType]:
    """Send unmatched names to Claude Haiku for classification."""
    valid = [e.value for e in ElementType]
    prompt = (
        "You are a construction expert. Classify each CAD layer name below into exactly "
        f"one of these element types: {', '.join(valid)}.\n"
        "Return a JSON object mapping each name to its type. Use 'Unknown' if uncertain.\n\n"
        f"Layer names: {json.dumps(names)}"
    )

    client = _get_client()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    # Extract JSON from potential markdown code block
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    try:
        raw: dict[str, str] = json.loads(text)
    except json.JSONDecodeError:
        return {n: ElementType.Unknown for n in names}

    result: dict[str, ElementType] = {}
    for name in names:
        val = raw.get(name, "Unknown")
        try:
            result[name] = ElementType(val)
        except ValueError:
            result[name] = ElementType.Unknown
    return result


def normalise_layers(layer_names: Sequence[str]) -> dict[str, ElementType]:
    """Classify a list of CAD layer names to ElementType values.

    Uses regex rules first; unmatched names are sent to Claude Haiku in one
    batched call. Results are persisted in .layer_cache.json.
    """
    names = list(dict.fromkeys(layer_names))  # deduplicate, preserve order
    result: dict[str, ElementType] = {}
    cache = _load_cache()
    llm_needed: list[str] = []

    for name in names:
        rule_match = _rule_classify(name)
        if rule_match is not None:
            result[name] = rule_match
        elif name in cache:
            try:
                result[name] = ElementType(cache[name])
            except ValueError:
                result[name] = ElementType.Unknown
        else:
            llm_needed.append(name)

    if llm_needed:
        llm_results = _llm_classify_batch(llm_needed)
        for name, element_type in llm_results.items():
            result[name] = element_type
            cache[name] = element_type.value
        _save_cache(cache)

    return result
