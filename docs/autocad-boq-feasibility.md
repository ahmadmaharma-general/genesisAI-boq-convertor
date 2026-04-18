# Feasibility Research: AutoCAD to BOQ Pipeline

## 1. AutoCAD File Parsing — Recommendation

### Options Evaluated

| Library | Format | License | Maturity | Write Support |
|---------|--------|---------|----------|---------------|
| **ezdxf** | DXF (R12–R2018) | MIT | Production (v1.4.3, Oct 2025) | Full read/write |
| **LibreDWG** | DWG + DXF | GPLv3 | Beta | Partial |
| **ODA SDK** | DWG + DXF | Proprietary (fee) | Production | Full |

### Recommendation: **ezdxf**

**Rationale:**
- MIT-licensed — no commercial restrictions
- Handles binary + ASCII DXF, covers all modern AutoCAD versions (R12 through R2018)
- Pure Python, pip-installable, active maintenance
- Rich query API: filter entities by layer, type, attribute; group by layer
- Limitation: **DXF only** (not DWG). A separate DWG→DXF conversion step is required for DWG inputs

**DWG handling strategy:** Use the free [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter) CLI (batch, free) or `libredwg`'s `dwg2dxf` binary to convert DWG → DXF before processing. This keeps the core pipeline MIT-licensed.

---

## 2. AI Approaches for Construction Element Recognition

### The Core Challenge

CAD drawings do not semantically label objects — a "wall" is just a series of LINE or LWPOLYLINE entities on a layer called `A-WALL` (or whatever the drafter chose). Recognition is a layer-name heuristic + geometry problem, not a pure computer vision problem (unlike PDF/image-based drawings).

### Approaches Ranked

| Approach | Accuracy | Speed | Cost | Effort |
|----------|----------|-------|------|--------|
| **Rule-based (layer names + geometry)** | Medium (depends on discipline) | Instant | Free | Low |
| **Hybrid: rules + LLM disambiguation** | High | Fast | Low | Medium |
| **Multimodal LLM on rasterised DXF** | Medium-High | Slow | High | Medium |
| **Fine-tuned CV model on DXF images** | High | Medium | High (training) | Very High |

### Recommendation: **Hybrid rule-based + LLM disambiguation**

1. **Phase 1 — Rule-based extraction:** Map layer names to element types using a configurable dictionary (e.g. `WALLS`, `A-WALL`, `STR-WALL` → "Wall"). Apply geometry analysis: LINE/POLYLINE length → linear measure; closed LWPOLYLINE → area.
2. **Phase 2 — LLM disambiguation:** For unknown layers or ambiguous geometry, pass a JSON summary of entities to Claude (or GPT-4o) with a prompt asking it to classify the elements. This is cheap (text-only, small context) and highly accurate.
3. **Future — Computer Vision:** Rasterise DXF to PNG, use a multimodal model or fine-tuned Detectron2/GroundingDINO to detect elements in complex drawings where layer naming is non-standard.

AWS has published a reference architecture combining CV models with LLMs for construction document analysis (2025). Companies like Werk24 and Kreo already offer commercial APIs for this.

---

## 3. BOQ Standards and Formats

### Common Standards (UK-centric, most widely referenced internationally)

| Standard | Scope | Status |
|----------|-------|--------|
| **NRM2** (RICS New Rules of Measurement 2) | UK building works | Current (replaced SMM7 in 2013) |
| **CESMM4** | Civil/infrastructure works | Current |
| **SMM7** | UK building (legacy) | Superseded |
| **POMI** | Process plant | Niche |

### Common BOQ Output Format

A BOQ line item contains:
- `Item no.` — sequential reference
- `Description` — work section + element description
- `Quantity` — measured amount
- `Unit` — LM (linear metre), M2 (square metre), M3 (cubic metre), NR (number), Item
- `Rate` — unit price (populated by estimators, not by us)
- `Amount` — Qty × Rate

For software output, **CSV / Excel / JSON** are the most practical formats. The pipeline should produce structured data that can be imported into tools like Procore, CostX, or Buildsoft.

---

## 4. Minimal Proof of Concept — Results

A working PoC was built and validated (`poc_dxf_to_boq.py`):

```
python poc_dxf_to_boq.py [path/to/file.dxf]
```

**Sample output on a synthetic 10 m × 8 m building footprint:**

```
====================================================================
  BILL OF QUANTITIES  (PoC output)
====================================================================
#     Description                     Layer              Qty  Unit  
--------------------------------------------------------------------
1     Masonry / RC Walls              WALLS           36.000  LM    
2     Door Openings                   DOORS            3.000  NR    
3     Window Openings                 WINDOWS          2.000  NR    
4     Structural Columns              COLUMNS          0.000  NR    
5     Floor / Roof Slabs              SLABS           80.000  M2    
6     Structural Beams                BEAMS            0.000  LM    
7     Stair Flights                   STAIRS           0.000  NR    
====================================================================
```

The PoC correctly derives:
- **36 LM** walls (perimeter of 10 m × 8 m rectangle)
- **3 NR** doors, **2 NR** windows (from circle entities on named layers)
- **80 M²** slab (shoelace area of closed polyline)

Technology stack: Python 3.9+, ezdxf 1.4.x, stdlib only. Zero external API calls.

---

## 5. Feasibility Assessment

### Verdict: **Viable — with known constraints**

| Factor | Assessment |
|--------|-----------|
| Technical feasibility | ✅ High — ezdxf + rule-based layer mapping works today |
| DXF quality dependency | ⚠️ Medium risk — accuracy depends on drafter following layer naming conventions |
| DWG support | ⚠️ Needs ODA File Converter or LibreDWG as pre-processing step |
| 3D/BIM drawings | ⚠️ Out of scope initially — 2D plan drawings are the MVP target |
| AI disambiguation cost | ✅ Low — LLM calls on small JSON payloads are cheap |
| Competitive landscape | ⚠️ Kreo, Buildsoft, CostX already exist; differentiation must come from UX/integration |
| Time to MVP | ✅ 2–3 weeks for a working backend API |

### Key Risks

1. **Layer naming anarchy** — real-world CAD drawings vary wildly in layer conventions. A training dataset of common layer name mappings is needed.
2. **DWG is the dominant format** — most architects deliver `.dwg`, not `.dxf`. The DWG conversion step adds complexity.
3. **Multi-storey / 3D** — 2D floor plans don't capture volume (M3) quantities without manual height inputs.
4. **No rates database** — we output quantities, not costs. A rates library integration (e.g. Spon's, BCIS) is a phase 2 item.

### Recommended Next Steps

1. **Collect 10–20 real DXF files** from construction firms to build a layer-name mapping corpus
2. **Build layer-name normaliser** using LLM (one-time batch job to extend the mapping dict)
3. **Implement DWG→DXF pre-processor** using ODA File Converter CLI
4. **Design REST API** — `POST /api/boq` accepts DXF/DWG, returns BOQ JSON
5. **Pilot with a quantity surveyor** for accuracy validation before broader release
