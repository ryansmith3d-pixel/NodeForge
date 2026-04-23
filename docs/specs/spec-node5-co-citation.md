# Spec — Node 5: Co-Citation Edge Computation
**Status:** LIVING — governs implementation
**Freezes when:** all tests passing, branch merged to main
**Target file:** `src/idiograph/domains/arxiv/pipeline.py`
**Companion documents:** spec-arxiv-pipeline-final.md (frozen v3), spec-node4.5-cycle-cleaning.md, session-2026-04-21-node5-design.md, session-2026-04-21-node5-design-addendum.md

---

## Amendment status check

| Amendment | Impact on Node 5 | Action |
|---|---|---|
| AMD-016 (LLM node placement) | None. Node 5 is pure topology computation. No LLM involvement. | None |
| AMD-017 (multi-seed `root_ids`) | **Material.** Co-citation emits across root-subtree boundaries — the cross-lineage structural overlap AMD-017 was designed to expose. See §Forest semantics. | Honor global semantics in algorithm. |

---

## Prerequisite

**`SuppressedEdge` refactor must land first.** This spec assumes `SuppressedEdge` composes a full `CitationEdge` as `.original`:

```python
class SuppressedEdge(BaseModel):
    original: CitationEdge
    citation_sum: int
    cycle_members: list[str]
```

Rationale and sequencing are captured in session-2026-04-21-node5-design.md (primary) and session-2026-04-21-node5-design-addendum.md §"Node 4.5 Output Contract (Promoted to Named Principle)." The refactor ships as its own PR ("fix SuppressedEdge data loss") before the Node 5 branch opens. This spec is written against the refactored shape.

---

## Purpose

Compute co-citation edges across the cleaned-and-suppressed citation graph. A co-citation relationship exists between two papers A and B whenever any third paper C cites both. The count of such shared citers is the **strength** of the co-citation.

Co-citation edges surface structural overlap that directional citation edges do not — two papers may never cite each other but share dozens of common citers, indicating they belong to the same research conversation. For the CRISPR demo case (AMD-017), Doudna 2012 and Zhang 2013 are not directly connected but share a substantial set of backward citers; co-citation edges expose that lineage.

**Algorithm authority:** `docs/specs/spec-arxiv-pipeline-final.md` §Node 5, refined by the decisions locked in session-2026-04-21-node5-design.md and its addendum.

Node 5 is a pure function on already-materialized data. No I/O, no network, no LLM, no async.

---

## Function signature

```python
def compute_co_citations(
    nodes: list[PaperRecord],
    cites_edges: list[CitationEdge],
    min_strength: int = 2,
    max_edges: int | None = None,
) -> list[CitationEdge]:
```

**Inputs:**
- `nodes` — all papers in the assembled graph (Node 3 ∪ Node 4, post-deduplication). Used to validate edge endpoints and to constrain co-citation to in-graph nodes only.
- `cites_edges` — **full citation edge set**: `cleaned_edges ∪ [s.original for s in suppressed_edges]`. The merge happens at the call site in the pipeline orchestrator, not inside this function. Node 5 is ignorant of whether an edge was cleaned or suppressed upstream.
- `min_strength` — minimum number of shared citers required to emit a co-citation edge. Default `2`. Strength 1 (a single shared citer) is noise-adjacent; requiring 2 means at least two independent confirmations.
- `max_edges` — optional hard cap on returned edge count. Default `None` (no cap). Semantic filtering is `min_strength`'s job; `max_edges` is a display/performance concern, owned by the caller.

**Output:** `list[CitationEdge]` — co-citation edges only. The input `cites_edges` are **not** in the return value.

**Pure function.** No mutation of inputs. No I/O. No async. No network. No LLM.

---

## Data model — edge shape

Co-citation edges reuse the existing `CitationEdge` model with the following field semantics:

| Field | Value |
|---|---|
| `source_id` | Lexicographically smaller of the two node_ids (canonical form). |
| `target_id` | Lexicographically larger of the two node_ids. |
| `type` | `"co_citation"` — lowercase snake_case, matches `"cites"` convention within the arxiv domain. |
| `citing_paper_year` | `None`. Co-citation is an aggregate relationship across many citers; a single year is not meaningful. |
| `strength` | Integer count of shared citing papers within the in-graph edge set. |

**No new models required.** `CitationEdge` already carries the needed fields. If `CitationEdge.strength` is currently optional (`int | None`), this spec does not widen or narrow that — co-citation edges always populate it with a positive integer.

---

## Algorithm

```
Build an index: for each node_id t, collect the set of citer node_ids s
    such that (s, t, type="cites") appears in cites_edges.
    Ignore edges where source_id == target_id (self-citations — defensive,
    not expected in input).
    Restrict to edges where both endpoints appear in nodes (defensive —
    upstream should guarantee this; see §Contracts).

For each pair of distinct target nodes (t1, t2) with t1 < t2 lexicographically:
    shared_citers = citers[t1] ∩ citers[t2]
    strength = len(shared_citers)
    if strength >= min_strength:
        emit CitationEdge(
            source_id=t1,
            target_id=t2,
            type="co_citation",
            citing_paper_year=None,
            strength=strength,
        )

Sort the resulting list by:
    (strength descending, source_id ascending, target_id ascending).

If max_edges is not None:
    truncate to the first max_edges entries.

Return the list.
```

**Iteration strategy.** The naive O(N²) pairwise iteration over targets is acceptable for Phase 9 demo graphs (hundreds to low thousands of nodes). A scalable variant — iterate citers once, emit pairs from each citer's outgoing edges to in-graph targets, aggregate — is a Phase 11 concern if profiling shows need. Do not prematurely optimize; the explicit pairwise form reads cleanly against the spec and is trivially correct.

**Canonical form at construction time.** The `t1 < t2` constraint in the iteration produces canonical-form edges directly. No post-hoc deduplication or swap is required.

---

## Forest semantics (AMD-017)

Co-citation is computed **globally** across the entire assembled graph, without regard to root-subtree boundaries. A shared citer of Doudna 2012 (root A) and Zhang 2013 (root B) produces a co-citation edge between them even though they are in different root subtrees.

Within-root-only semantics would eliminate exactly the cross-lineage structural signal AMD-017 was designed to expose. This is not a tunable — it is the thesis of the multi-seed boolean-ops feature.

No per-node filtering by `root_ids` occurs in this function.

---

## Sort and truncation — implementation

Single stable sort with a tuple key, then optional slice:

```python
co_edges.sort(
    key=lambda e: (-e.strength, e.source_id, e.target_id)
)
if max_edges is not None:
    co_edges = co_edges[:max_edges]
```

Negation on `e.strength` flips descending for the numeric field without flipping the string tiebreakers. Python's `list.sort()` is stable; within a strength tier, secondary keys produce a total ordering. Hard cap — ties at the boundary are resolved by the secondary sort keys, not expanded to include all ties.

This ordering is part of the function contract. Consumers may rely on it.

---

## Contracts and edge cases

**Empty inputs.** `nodes=[]` or `cites_edges=[]`: return `[]`. No citers, no pairs, no co-citation. Not an error.

**Single node.** One paper, no pairs possible: return `[]`.

**Self-citations in input.** An edge with `source_id == target_id` is defensive — upstream deduplication should prevent it, but if present it is filtered out of the citer index. Do not emit a co-citation edge from a paper to itself.

**Edges referencing unknown node_ids.** An edge whose `source_id` or `target_id` is not present in `nodes` is skipped from the citer index with a WARNING log entry naming the missing `node_id`. Do not raise. Same pattern as Node 4.5's `test_missing_citation_node_warns` contract.

**`min_strength < 1`.** Values less than 1 are invalid (strength is a positive count). Raise `ValueError` with a clear message. `min_strength=1` is valid — it means "emit every co-citation pair with any shared citer."

**`max_edges=0`.** Valid — returns `[]`. `max_edges=None` (default) means "no cap." Negative values raise `ValueError`.

**Cleaned vs. suppressed edge provenance.** Node 5 treats all `cites_edges` as equivalent citation facts. Cycle-cleaning status does not propagate into co-citation computation. This is a deliberate architectural boundary — see session-2026-04-21-node5-design.md §Decisions Locked row 1.

**No emitted warnings beyond missing-node.** Unlike Node 4.5, Node 5 has no heuristic decisions requiring audit-trail warnings. Pure topology computation, deterministic result, no judgment calls surfacing through logs.

---

## Logging

- Node 5 start: INFO, `"Node 5: co-citation on N nodes, M citation edges, min_strength={min_strength}"`
- Missing-node citation lookup: WARNING with the `node_id` (same pattern as Node 4.5)
- Completion: INFO, `"Node 5 complete: K co-citation edges emitted (min_strength={min_strength}, max_edges={max_edges})"`
- Zero output: DEBUG, `"Node 5: no co-citation pairs met min_strength threshold"`

Standard project logger — `logging.getLogger(__name__)`.

---

## Tests — minimum set

File: `tests/domains/arxiv/test_pipeline_node5.py`

Each test has a one-line docstring. No pytest-asyncio (synchronous). No mocked HTTP (no I/O). Synthetic graph fixtures, inline helpers following the Node 4.5 pattern (`_rec`, `_edge`, plus a new `_triples` helper for co-citation assertions).

| Test | What it proves |
|---|---|
| `test_minimal_co_citation` | Three papers, C cites A and B: one edge A↔B with strength=1, min_strength=1 |
| `test_strength_accumulates` | C and D both cite A and B: one edge with strength=2 |
| `test_multiple_independent_pairs` | C cites A,B; D cites E,F: two edges, no cross-contamination |
| `test_min_strength_filters_singletons` | Default min_strength=2 drops strength-1 edges |
| `test_min_strength_one_includes_all` | min_strength=1 emits every shared-citer pair |
| `test_max_edges_none_emits_all` | Default max_edges=None returns all qualifying edges |
| `test_max_edges_enforces_hard_cap` | max_edges=N returns exactly N highest-strength edges |
| `test_output_sorted_by_contract` | Output order is (strength desc, source_id asc, target_id asc) |
| `test_canonical_form_dedup` | Pairs emit once with source_id < target_id, not twice |
| `test_no_self_co_citation` | Self-citation edges in input do not produce self co-citation edges |
| `test_cross_root_co_citation` | AMD-017: papers in different root_ids co-cite when they share citers |
| `test_truncation_boundary_deterministic` | Ties straddling max_edges cutoff resolve by secondary sort, same on repeat |
| `test_edge_type_is_co_citation` | All emitted edges have type="co_citation" |
| `test_input_not_mutated` | Original input lists unchanged after call (pure function property) |
| `test_routing_independence` | Same logical citations via cleaned/suppressed/union route produce identical output |
| `test_missing_citation_node_warns` | Edge referencing unknown node_id: skipped with WARNING, no raise |
| `test_min_strength_zero_raises` | min_strength < 1 raises ValueError |
| `test_max_edges_negative_raises` | max_edges < 0 raises ValueError |

---

## Boundaries — what Node 5 does not do

- Does not modify `cites_edges` or emit modified citation edges. Co-citation is a new edge set, orthogonal to citations.
- Does not reach into `cycle_log` or any Node 4.5 provenance. The full citation set is assembled at the call site and passed in explicitly. Node 5 is ignorant of cycle-cleaning.
- Does not store the identities of the shared citing papers on each edge. That list is reconstructable at query time by intersecting incoming citers. Denormalizing it onto the edge is deferred.
- Does not normalize strength (Jaccard, cosine, PMI). Strength is a raw integer count — an audit-inspectable fact, not a score. Normalization, if ever needed, is a separate computation layer.
- Does not respect root-subtree boundaries. See §Forest semantics.
- Does not enforce a default `max_edges` cap. That is a caller concern (renderer, demo config).
- Does not compute topological metrics, communities, or centrality. Those are Node 6 and Node 7, operating on `cleaned_edges` only.
- Does not touch `PaperRecord` fields.
- Does not persist anything.

---

## Call-site assembly (informative, not part of function contract)

For reader orientation — how the pipeline orchestrator composes Node 4.5 output into Node 5 input:

```python
result = clean_cycles(nodes, edges)
all_cites = result.cleaned_edges + [
    s.original for s in result.cycle_log.suppressed_edges
]
co_edges = compute_co_citations(nodes, all_cites, min_strength=2)
```

This composition is **not Node 5's concern.** It is shown here only to clarify how the "cleaned ∪ suppressed" input arrives. The assembly lives in the pipeline orchestrator alongside the other stage calls.

---

## Implementation constraints

- Pure function. No I/O, no network, no async, no mutation of inputs.
- `encoding="utf-8"` is irrelevant — no file I/O.
- NetworkX is available but **not required** — co-citation is index-and-intersect, not graph traversal. Using `nx.Graph` internally is permitted if it reads cleaner, but adds no algorithmic value. Prefer plain dict/set operations for readability.
- No new top-level dependencies.
- ruff: format new code only; do not reformat pre-existing code in `pipeline.py` or `models.py`.

---

## Freeze trigger

All tests in `test_pipeline_node5.py` passing, merged to main. Baseline test count must remain green (93 pre-refactor, expected 93 + refactor delta + 18 Node 5 tests).

Post-freeze deferred items:
- `min_strength=2` default validation against real arXiv co-citation distributions (seed pair validation spikes).
- `max_edges` tuning, if needed, at the demo/renderer layer — not a Node 5 concern.
- Scalable iteration variant (citer-indexed pair emission) — Phase 11 if profiling warrants.
- Node 4.5 spec §Boundaries update: current text says "Node 5 runs on the cleaned graph"; correct language is "Node 5 runs on the full citation set (cleaned ∪ suppressed)." Small edit, separate PR.
