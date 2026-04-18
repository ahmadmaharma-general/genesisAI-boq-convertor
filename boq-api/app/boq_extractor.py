"""BOQ extraction logic — converts a DXF file to a list of BOQ line items."""

import math
from typing import Any

import ezdxf

from app.layer_normaliser import ElementType, normalise_layers

# NRM2 section codes per element type
_NRM2_CODES: dict[ElementType, str] = {
    ElementType.Wall: "14",
    ElementType.Door: "25.1",
    ElementType.Window: "25.2",
    ElementType.Slab: "13",
    ElementType.Column: "12.1",
    ElementType.Beam: "12.2",
    ElementType.Stair: "24",
    ElementType.Unknown: "99",
}

_DESCRIPTIONS: dict[ElementType, str] = {
    ElementType.Wall: "Masonry / RC Walls",
    ElementType.Door: "Door Openings",
    ElementType.Window: "Window Openings",
    ElementType.Slab: "Floor / Roof Slabs",
    ElementType.Column: "Structural Columns",
    ElementType.Beam: "Structural Beams",
    ElementType.Stair: "Stair Flights",
    ElementType.Unknown: "Unclassified Elements",
}

_UNITS: dict[ElementType, str] = {
    ElementType.Wall: "LM",
    ElementType.Door: "NR",
    ElementType.Window: "NR",
    ElementType.Slab: "M2",
    ElementType.Column: "NR",
    ElementType.Beam: "LM",
    ElementType.Stair: "NR",
    ElementType.Unknown: "Item",
}


def _polyline_length(entity) -> float:
    """Return approximate perimeter of a LWPOLYLINE."""
    pts = list(entity.get_points("xy"))
    if len(pts) < 2:
        return 0.0
    total = 0.0
    for i in range(len(pts) - 1):
        dx = pts[i + 1][0] - pts[i][0]
        dy = pts[i + 1][1] - pts[i][1]
        total += math.hypot(dx, dy)
    if entity.is_closed and len(pts) >= 2:
        dx = pts[0][0] - pts[-1][0]
        dy = pts[0][1] - pts[-1][1]
        total += math.hypot(dx, dy)
    return total


def _polyline_area(entity) -> float:
    """Shoelace formula area for a closed LWPOLYLINE."""
    pts = list(entity.get_points("xy"))
    n = len(pts)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
    return abs(area) / 2.0


def _line_length(entity) -> float:
    s = entity.dxf.start
    e = entity.dxf.end
    return math.hypot(e.x - s.x, e.y - s.y)


def extract_boq(dxf_path: str) -> list[dict[str, Any]]:
    """Parse a DXF file and return BOQ line items.

    Each item: {item_no, nrm2_code, description, layer, quantity, unit}
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Collect all layer names present in modelspace
    layer_names = {e.dxf.layer for e in msp if hasattr(e.dxf, "layer")}
    normalised = normalise_layers(list(layer_names))

    # Accumulate quantities per layer
    quantities: dict[str, float] = {ln: 0.0 for ln in layer_names}
    counts: dict[str, int] = {ln: 0 for ln in layer_names}

    for entity in msp:
        layer = getattr(entity.dxf, "layer", None)
        if layer is None:
            continue
        element_type = normalised.get(layer, ElementType.Unknown)
        dxf_type = entity.dxftype()

        if element_type in (ElementType.Door, ElementType.Window,
                             ElementType.Column, ElementType.Stair,
                             ElementType.Unknown):
            counts[layer] += 1
        elif element_type in (ElementType.Wall, ElementType.Beam):
            if dxf_type == "LINE":
                quantities[layer] += _line_length(entity)
            elif dxf_type in ("LWPOLYLINE", "POLYLINE"):
                quantities[layer] += _polyline_length(entity)
        elif element_type == ElementType.Slab:
            if dxf_type in ("LWPOLYLINE", "POLYLINE") and entity.is_closed:
                quantities[layer] += _polyline_area(entity)

    # Build output grouped by element type, then layer
    items: list[dict[str, Any]] = []
    seen_types: dict[ElementType, dict[str, Any]] = {}

    for layer, element_type in normalised.items():
        if element_type not in seen_types:
            seen_types[element_type] = {
                "layers": [],
                "quantity": 0.0,
                "count": 0,
            }
        seen_types[element_type]["layers"].append(layer)
        seen_types[element_type]["quantity"] += quantities.get(layer, 0.0)
        seen_types[element_type]["count"] += counts.get(layer, 0)

    order = [
        ElementType.Wall, ElementType.Door, ElementType.Window,
        ElementType.Slab, ElementType.Column, ElementType.Beam,
        ElementType.Stair, ElementType.Unknown,
    ]
    item_no = 1
    for element_type in order:
        if element_type not in seen_types:
            continue
        data = seen_types[element_type]
        unit = _UNITS[element_type]
        if unit in ("NR", "Item"):
            qty = float(data["count"])
        else:
            qty = round(data["quantity"], 3)

        items.append({
            "item_no": item_no,
            "nrm2_code": _NRM2_CODES[element_type],
            "description": _DESCRIPTIONS[element_type],
            "layers": data["layers"],
            "quantity": qty,
            "unit": unit,
        })
        item_no += 1

    return items
