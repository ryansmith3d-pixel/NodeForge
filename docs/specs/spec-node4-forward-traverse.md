# Idiograph — Node 4 Forward Traversal Spec
**Status:** LIVING — freeze trigger: all Node 4 tests passing, committed to branch
**Created:** 2026-04-16
**Governs:** `forward_traverse()` implementation in `src/idiograph/domains/arxiv/pipeline.py`
**Companion documents:** spec-arxiv-pipeline-final.md, amd-016-llm-node-placement-2.md, amd-017-multi-seed-boolean-ops.md

---

## Amendment Status Check

Two amendments postdate spec-arxiv-pipeline-final.md. Both must be respected here.

**AMD-016 (LLM Node Placement):** Adds Node 0.5 and Node 5.5. No impact on Node 4.

**AMD-017 (Multi-Seed Boolean Ops):** Node 0 accepts `list[dict]` seeds. Every traversal
node must store `root_ids: list[str]` per node at traversal time. Node 4 is a traversal
node — this applies.

---

## Purpose

Node 4 is the forward traversal branch. Where Node 3 asks "what foundational works led
here?", Node 4 asks "what emerging work builds on this?" They are structurally symmetric
and semantically opposite. Their ranking functions share the `recency_weight` formula but
apply it in opposite directions — penalized in Node 3, rewarded in Node 4.

---

## Function Signature

```python
async def forward_traverse(
    seeds: list[PaperRecord],
    api_key: str,
    n_forward: int,
    alpha: float,
    beta: float,
    lambda_decay: float,
    acceleration_method: str = "first_difference",
    current_year: int | None = None,
) -> list[PaperRecord]:
```

`current_year` defaults to `datetime.date.today().year` if None. Explicit parameter
exists so tests can pass a fixed year without patching.

---

## OpenAlex Query

For each seed, fetch papers that cite it using filter `cites:<openalex_id>`.
`openalex_id` is carried on `PaperRecord` — use it directly.

`select=` fields required:
```
id,ids,title,publication_year,authorships,abstract_inverted_index,cited_by_count,counts_by_year
```

`counts_by_year` is required here — Node 3 did not need it. Do not widen Node 0's
or Node 3's `select=` to accommodate this.

Sleep 150ms between API calls (after the first). Same pattern as `backward_traverse`.

---

## Ranking Function

```
score = alpha * citation_velocity + beta * citation_acceleration * recency_weight
```

Where:
- `citation_velocity = cited_by_count / months_since_publication`
  - `months_since_publication = (current_year - pub_year) * 12`, minimum 1
  - If `pub_year` is None: velocity = 0.0
- `citation_acceleration`: see helpers below
- `recency_weight = math.exp(years_since_publication * lambda_decay)`
  - Rewarded — multiply into score (not divide as in Node 3)
  - `years_since_publication = current_year - pub_year`
  - If `pub_year` is None: treat as 0

---

## Private Helpers

### `_compute_velocity(cited_by_count, pub_year, current_year) -> float`

```python
def _compute_velocity(
    cited_by_count: int,
    pub_year: int | None,
    current_year: int,
) -> float:
```

- If `pub_year` is None: return 0.0
- `months = max(1, (current_year - pub_year) * 12)`
- Return `cited_by_count / months`

### `_compute_acceleration(counts_by_year, acceleration_method) -> float | None`

```python
def _compute_acceleration(
    counts_by_year: list[dict],
    acceleration_method: str,
) -> float | None:
```

`counts_by_year` is OpenAlex format: `[{"year": int, "cited_by_count": int}, ...]`

- Sort ascending by year before any computation
- Requires ≥ 3 entries. If fewer: return None (triggers per-paper β=0 fallback)
- `"first_difference"`:
  - Per-year velocity: `cited_by_count / 12` for each year entry
  - Deltas: year-over-year differences in velocity
  - Return `mean(deltas)`
- `"regression"`: raise `NotImplementedError("regression acceleration not yet implemented")`
  - Slot reserved. Do not stub with wrong behavior.

### `_node4_score(velocity, acceleration, pub_year, current_year, alpha, beta, lambda_decay) -> float`

```python
def _node4_score(
    velocity: float,
    acceleration: float | None,
    pub_year: int | None,
    current_year: int,
    alpha: float,
    beta: float,
    lambda_decay: float,
) -> float:
```

- If `acceleration` is None: use `beta=0` for this paper only
- `years = current_year - pub_year if pub_year else 0`
- `recency_weight = math.exp(years * lambda_decay)`
- Return `alpha * velocity + (beta if acceleration is not None else 0.0) * (acceleration or 0.0) * recency_weight`

---

## Deduplication (AMD-017 compliance)

Same logic as `backward_traverse`. On node_id collision:
- Keep lowest `hop_depth` (all forward papers are `hop_depth=1` — no collision on depth)
- Merge `root_ids` as sorted union

All forward papers:
- `hop_depth = 1`
- `root_ids = [seed.node_id]` for each seed that paper cites — merged on dedup

Exclude seed nodes from results. Seeds are roots, not traversal results.

---

## Logging

- Acceleration unavailable for a paper: `logger.debug("acceleration unavailable for %s, using beta=0", node_id)`
- Paper with no OpenAlex record: `logger.debug("no OpenAlex record for %s, skipping", identifier)`
- Do not log at WARNING or above for per-paper fallbacks — these are expected data conditions, not errors

---

## What Does Not Change

- `PaperRecord` model — do not modify
- Node 0's `select=` fields — do not widen
- Node 3's `select=` fields — do not widen
- Existing tests — do not touch

---

## Freeze Trigger

This spec freezes when the Node 4 implementation commit is on the branch and all
tests pass. Move to `docs/sessions/` as part of the session summary.
