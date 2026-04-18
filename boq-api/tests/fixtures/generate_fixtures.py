"""Generate the 8 sample DXF test fixtures and ground_truth.json."""

import json
import math
from pathlib import Path

import ezdxf

OUT = Path(__file__).parent


def add_rect_walls(msp, x0, y0, w, h, layer="WALLS"):
    pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
    for i in range(4):
        msp.add_line(pts[i], pts[(i + 1) % 4], dxfattribs={"layer": layer})


def add_closed_slab(msp, x0, y0, w, h, layer="SLABS"):
    poly = msp.add_lwpolyline(
        [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)],
        dxfattribs={"layer": layer},
    )
    poly.close(True)
    return poly


def add_doors(msp, n, layer="DOORS"):
    for i in range(n):
        msp.add_circle((i * 2, -1), 0.4, dxfattribs={"layer": layer})


def add_windows(msp, n, layer="WINDOWS"):
    for i in range(n):
        msp.add_circle((i * 2, -2), 0.3, dxfattribs={"layer": layer})


def add_columns(msp, positions, layer="COLUMNS"):
    for x, y in positions:
        msp.add_circle((x, y), 0.2, dxfattribs={"layer": layer})


def add_beams(msp, lines, layer="BEAMS"):
    for start, end in lines:
        msp.add_line(start, end, dxfattribs={"layer": layer})


def save(doc, name):
    doc.saveas(OUT / name)
    print(f"  wrote {name}")


# --- fixture 1: simple_room_aia.dxf ---
def make_simple_room_aia():
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    add_rect_walls(msp, 0, 0, 10, 8, "A-WALL")
    add_closed_slab(msp, 0, 0, 10, 8, "S-SLAB")
    add_doors(msp, 1, "A-DOOR")
    add_windows(msp, 2, "A-GLAZ")
    save(doc, "simple_room_aia.dxf")
    return {
        "Wall": {"quantity": 36.0, "unit": "LM"},
        "Slab": {"quantity": 80.0, "unit": "M2"},
        "Door": {"count": 1, "unit": "NR"},
        "Window": {"count": 2, "unit": "NR"},
    }


# --- fixture 2: multi_room_standard.dxf ---
def make_multi_room_standard():
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    add_rect_walls(msp, 0, 0, 10, 8, "WALLS")
    add_rect_walls(msp, 5, 0, 5, 8, "WALLS")  # interior divider
    add_closed_slab(msp, 0, 0, 10, 8, "SLABS")
    add_doors(msp, 3, "DOORS")
    add_windows(msp, 4, "WINDOWS")
    save(doc, "multi_room_standard.dxf")
    return {
        "Wall": {"quantity": 54.0, "unit": "LM"},
        "Slab": {"quantity": 80.0, "unit": "M2"},
        "Door": {"count": 3, "unit": "NR"},
        "Window": {"count": 4, "unit": "NR"},
    }


# --- fixture 3: office_structural.dxf ---
def make_office_structural():
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    add_rect_walls(msp, 0, 0, 20, 15, "STR-WALL")
    add_closed_slab(msp, 0, 0, 20, 15, "S-SLAB")
    cols = [(5, 5), (15, 5), (5, 10), (15, 10)]
    add_columns(msp, cols, "S-COLS")
    add_beams(msp, [((5, 5), (15, 5)), ((5, 10), (15, 10))], "S-BEAM")
    save(doc, "office_structural.dxf")
    return {
        "Wall": {"quantity": 70.0, "unit": "LM"},
        "Slab": {"quantity": 300.0, "unit": "M2"},
        "Column": {"count": 4, "unit": "NR"},
        "Beam": {"quantity": 20.0, "unit": "LM"},
    }


# --- fixture 4: mixed_use_building.dxf ---
def make_mixed_use_building():
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    add_rect_walls(msp, 0, 0, 30, 20, "A-WALL")
    add_closed_slab(msp, 0, 0, 30, 20, "SLABS")
    add_doors(msp, 5, "DOORS")
    add_windows(msp, 8, "WINDOWS")
    cols = [(10, 10), (20, 10)]
    add_columns(msp, cols, "COLUMNS")
    save(doc, "mixed_use_building.dxf")
    return {
        "Wall": {"quantity": 100.0, "unit": "LM"},
        "Slab": {"quantity": 600.0, "unit": "M2"},
        "Door": {"count": 5, "unit": "NR"},
        "Window": {"count": 8, "unit": "NR"},
        "Column": {"count": 2, "unit": "NR"},
    }


# --- fixture 5: nonstandard_layers.dxf (LLM fallback needed) ---
def make_nonstandard_layers():
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    add_rect_walls(msp, 0, 0, 8, 6, "PARTITION-01")
    add_closed_slab(msp, 0, 0, 8, 6, "FLOOR-FINISH")
    add_doors(msp, 2, "OPENING-D")
    save(doc, "nonstandard_layers.dxf")
    return {
        "Wall": {"quantity": 28.0, "unit": "LM"},
        "Slab": {"quantity": 48.0, "unit": "M2"},
        "Door": {"count": 2, "unit": "NR"},
    }


# --- fixture 6: mixed_conventions.dxf ---
def make_mixed_conventions():
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    add_rect_walls(msp, 0, 0, 12, 9, "WL-EXT")
    add_rect_walls(msp, 3, 0, 6, 9, "A-WALL")
    add_closed_slab(msp, 0, 0, 12, 9, "ROOF")
    add_windows(msp, 3, "WDW-TYPE-A")
    save(doc, "mixed_conventions.dxf")
    return {
        "Wall": {"quantity": 54.0, "unit": "LM"},
        "Slab": {"quantity": 108.0, "unit": "M2"},
        "Window": {"count": 3, "unit": "NR"},
    }


# --- fixture 7: edge_cases.dxf (empty layers, single point) ---
def make_edge_cases():
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (0, 0), dxfattribs={"layer": "WALLS"})  # zero-length
    add_closed_slab(msp, 0, 0, 5, 5, "SLABS")
    save(doc, "edge_cases.dxf")
    return {
        "Wall": {"quantity": 0.0, "unit": "LM"},
        "Slab": {"quantity": 25.0, "unit": "M2"},
    }


# --- fixture 8: german_french_layers.dxf ---
def make_german_french_layers():
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    add_rect_walls(msp, 0, 0, 10, 8, "WAND-AUSSEN")
    add_closed_slab(msp, 0, 0, 10, 8, "DECKE-EG")
    add_doors(msp, 2, "TUER-01")
    add_windows(msp, 3, "FENSTER-01")
    save(doc, "german_french_layers.dxf")
    return {
        "Wall": {"quantity": 36.0, "unit": "LM"},
        "Slab": {"quantity": 80.0, "unit": "M2"},
        "Door": {"count": 2, "unit": "NR"},
        "Window": {"count": 3, "unit": "NR"},
    }


if __name__ == "__main__":
    ground_truth = {
        "simple_room_aia.dxf": make_simple_room_aia(),
        "multi_room_standard.dxf": make_multi_room_standard(),
        "office_structural.dxf": make_office_structural(),
        "mixed_use_building.dxf": make_mixed_use_building(),
        "nonstandard_layers.dxf": make_nonstandard_layers(),
        "mixed_conventions.dxf": make_mixed_conventions(),
        "edge_cases.dxf": make_edge_cases(),
        "german_french_layers.dxf": make_german_french_layers(),
    }
    (OUT / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2))
    print("ground_truth.json written")
