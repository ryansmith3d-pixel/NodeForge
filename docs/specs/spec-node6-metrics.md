# Spec — Node 6: Metric Computation
**Status:** LIVING — governs implementation
**Freezes when:** all tests passing, branch merged to main
**Target file:** `src/idiograph/domains/arxiv/pipeline.py`
**Companion documents:** spec-arxiv-pipeline-final.md (frozen v3), spec-node4.5-cycle-cleaning.md, spec-node5-co-citation.md, session-2026-04-24-node6-design.md

---

## Amendment status check

| Amendment | Impact on Node 6 | Action |
|---|---|---|
| AMD-016 (LLM node placement) | None. Node 6 is pure graph computation. No LLM involvement. | None |
| AMD-017 (multi-seed `root_ids`) | **Material.** Forest graphs have multiple roots; depth semantics must be defined per root, not from a single root. See §Forest semantics. | Honor multi-root semantics in `compute_depth_metrics`. |
| AMD-019 (this spec) | **Creates.** Supersedes the `topological_depth` specification in `spec-arxiv-pipeline-final.md` §Node 6 and the renderer data contract. | See §AMD-019 below. |

---

## AMD-019 — Node 6 Depth Semantics: Per-Root BFS with Traversal Direction

**Affects:** `spec-arxiv-pipeline-final.md` (Node 6 section, renderer data contract), `PaperRecord` model, Node 4.5 `affected_node_ids` handoff semantics
**Status:** Accepted — lands with Node 6 implementation
**Decided:** 2026-04-24

**Reason.** The frozen spec defined `topological_depth` as "longest path from root in the cycle-cleaned DAG." This definition has three problems surfaced during Node 6 design:

1. **Direction ambiguity.** Citation edges point `citer → cited`. Node 3's backward-traversal output is reachable from the seed by following edges forward (descendants in the DAG). Node 4's forward-traversal output is reachable only by walking edges in reverse (ancestors). A single scalar "longest path from root" either leaves Node 4's entire output undefined, or collapses direction into magnitude — neither is honest.
2. **Forest semantics.** Under AMD-017 the graph is a forest with multiple roots. "Longest path from root" has no canonical single-root referent; "longest from any root" loses per-root information that is analytically valuable for the CRISPR-style multi-seed case.
3. **NetworkX `dag_longest_path_length` returns a graph-level scalar**, not a per-node depth. The spec's language implied a direct API call that does not exist.

**Change.** Replace `topological_depth: int | None` on `PaperRecord` with two fields that encode the honest multi-dimensional truth:

```python
hop_depth_per_root: dict[str, int]
    # Key: root node_id. Value: unsigned shortest-path distance from that root.
    # BFS over the undirected view of the cleaned citation graph.
    # Always non-negative. Zero only when the node IS that root.

traversal_direction: Literal["seed", "backward", "forward", "mixed"]
    # Categorical position relative to the seed set:
    # "seed"     — node_id is one of the roots.
    # "backward" — every reaching root reaches this node by following edges
    #              forward; no reaching root reaches it in the reverse
    #              direction. (Node 3 side; foundational lineage relative
    #              to every reaching root.)
    # "forward"  — every reaching root reaches this node by walking edges
    #              in reverse; no reaching root reaches it forward. (Node 4
    #              side; emerging work relative to every reaching root.)
    # "mixed"    — reaching roots disagree on direction: at least one
    #              reaches this node forward and at least one reaches it
    #              in reverse. Roots that do not reach the node are not
    #              required to participate; the disagreement among
    #              reaching roots is sufficient.
```

Renderer projections (e.g. Y-axis coordinate, signed scalar depth) are view-layer concerns computed from these two fields on demand. No single scalar is stored.

**Consequence for Node 4.5 handoff.** `CycleLog.affected_node_ids` no longer gates `topological_depth: null` assignment. The null-handling language in `spec-arxiv-pipeline-final.md` §Node 4.5 step 5 and §Node 6 is superseded. Node 6 under AMD-019 assigns normal values to suppressed-cycle nodes — the cleaned DAG is traversable regardless of which cycle edges were suppressed. The `affected_node_ids` property is retained for audit/provenance value (Node 8), but it is no longer a pipeline-critical handoff.

**Done when.** `PaperRecord` carries the two new fields and no `topological_depth`. `spec-arxiv-pipeline-final.md` renderer data contract is updated in a follow-up PR (same pattern as the Node 5 §Boundaries correction, PR #14). AMD-017's "Downstream Metric Behavior in a Forest" table is updated with an AMD-019 cross-reference.

---

## Prerequisite

**`CycleCleanResult` contract enforcement must land first.** Node 6 takes a `CycleCleanResult` and trusts that every endpoint in `cleaned_edges` references a `node_id` present in the input node set. Today nothing enforces this — the contract is documented in `spec-node4.5-cycle-cleaning.md` but only Node 4.5's own internal logic upholds it. A bug in `clean_cycles()` could silently produce orphaned-endpoint edges, and Node 6 would either need a defensive check (which Nodes 7, 8, 9 would also need, multiplying paranoia) or trust a contract that nothing actively guarantees.

The fix is to make orphaned endpoints unconstructible. A Pydantic `@model_validator(mode='after')` on `CycleCleanResult` fails construction if any edge endpoint is absent from a stored witness of the input node set. Once a `CycleCleanResult` exists, its invariant holds. Every downstream consumer — Node 6 today, Nodes 7/8/9 tomorrow — trusts the type and runs no per-consumer defensive check. This is the Python-idiomatic version of "make illegal states unrepresentable": the type system (such as Python's is) does the work once at the boundary, and consumption sites are pure.

**Implementation shape:**

- `CycleCleanResult` gains an excluded witness field — `input_node_ids: frozenset[str] = Field(exclude=True, repr=False)`. Required at construction. Used by the validator. Omitted from `model_dump()` JSON output and from `repr()`.
- **Not `PrivateAttr`. Not a `construct_validated` factory.** Both leave direct `CycleCleanResult(...)` construction unprotected — the invariant attaches to a specific code path rather than to the type, and any caller using regular construction silently skips the check. Inconsistent enforcement is a quieter failure mode than no enforcement. `Field(exclude=True)` on a regular required field is the Pydantic v2 pattern that fires the validator on every construction path (including `model_validate(...)`, `model_validate_json(...)`, and direct `__init__` calls) while keeping the witness out of serialization. Pydantic v2 trap to avoid: leading-underscore field names without an explicit `PrivateAttr()` default are silently ignored by the model. Do not rely on the underscore convention for privacy.
- Validator: `@model_validator(mode='after')`. Iterates `cleaned_edges`, raises `ValidationError` on the first orphaned endpoint, naming both the offending `node_id` and the edge it appears in.
- `clean_cycles()` populates `input_node_ids` from its `nodes` parameter as it builds the result. The witness is the set of `node_id`s passed in, not any post-filtering subset.
- Existing tests remain green — Node 4.5 already produces correct output, so the validator never fires on legitimate paths.
- New tests verify: (a) the validator fires on direct construction with an orphaned-endpoint edge (bypassing `clean_cycles()`); (b) `model_dump()` output omits `input_node_ids`; (c) `model_validate(model_dump(result))` raises a `ValidationError` for missing `input_node_ids` — this is the property that distinguishes `Field(exclude=True)` from `PrivateAttr` (which would round-trip silently as the default empty value) and from a factory pattern (which would not enforce on plain construction at all). Round-trip through serialization deliberately requires the witness to be re-supplied; this is the persistence contract Node 8 will honor.

**Sequencing:** lands as its own PR ("tighten CycleCleanResult contract: enforce edge endpoint membership") before the Node 6 branch opens. Same pattern as the SuppressedEdge refactor (PR #11) that preceded Node 5. This spec is written against the post-validator world. The Node 4.5 spec is updated in the same prerequisite PR to document the new constructor invariant.

**Architectural payoff beyond Node 6.** The validator pattern is reusable. When Node 7's spec is drafted, the same approach will apply: communities are computed from a `CycleCleanResult` (or a successor type that adds Node 6's metrics), and Node 7 trusts the witness. When Node 8's registry persists graphs, the persisted shape carries the validator with it — and the round-trip-requires-witness property forces every reload site to actively reconstruct `input_node_ids` from the loaded node list, keeping the invariant honest across persistence boundaries. The "stop the defensive checks from multiplying" architectural goal is solved at the type-boundary level, not per-node.

---

## Purpose

Compute per-node graph-structural metrics on the cleaned citation graph. Node 6 produces three fields per node: `hop_depth_per_root`, `traversal_direction`, and `pagerank`.

These metrics are not derivable from traversal provenance alone — they require the full cleaned-graph topology. `hop_depth_per_root` differs from `PaperRecord.hop_depth` (set at traversal time): traversal `hop_depth` is the minimum distance from the nearest seed at retrieval time; Node 6's per-root dict records distance from each root individually, computed over the final assembled graph after Node 4.5 cleaning.

**Algorithm authority:** this spec, plus the design rationale in `session-2026-04-24-node6-design.md`. Supersedes the Node 6 description in `spec-arxiv-pipeline-final.md` per AMD-019.

Node 6 is two pure functions on already-materialized data. No I/O, no network, no LLM, no async.

---

## Function signatures

Two independent functions. The pipeline orchestrator (future work) calls both and merges results into `PaperRecord` via `model_copy`.

```python
def compute_depth_metrics(
    nodes: list[PaperRecord],
    cleaned_edges: list[CitationEdge],
) -> dict[str, DepthMetrics]:
```

```python
def compute_pagerank(
    nodes: list[PaperRecord],
    cleaned_edges: list[CitationEdge],
    damping: float = 0.85,
) -> dict[str, float]:
```

**Inputs (both functions):**
- `nodes` — all papers in the assembled graph, post-Node 4.5. Roots are identified by `node_id in node.root_ids` (a node is a root iff its own `node_id` appears in its `root_ids`).
- `cleaned_edges` — DAG-safe edge set from Node 4.5 (`CycleCleanResult.cleaned_edges`). Suppressed edges are **not** in scope for Node 6. This distinguishes Node 6 from Node 5, which consumes the full cleaned ∪ suppressed union.
- `damping` (pagerank only) — PageRank damping factor. Default `0.85` per `spec-arxiv-pipeline-final.md` §Declared Parameters.

**Outputs:**
- `compute_depth_metrics` returns `dict[node_id, DepthMetrics]`. One entry per input node. Every input node is assigned a value — unreachable nodes raise (see §Contracts).
- `compute_pagerank` returns `dict[node_id, float]`. One entry per input node. Values sum to 1.0 (standard PageRank invariant) within NetworkX convergence tolerance.

**Pure functions.** No mutation of inputs. No I/O. No async. No network. No LLM.

---

## Data model — new and changed

### New model — `DepthMetrics`

Added to `src/idiograph/domains/arxiv/models.py`:

```python
class DepthMetrics(BaseModel):
    """Per-node depth metrics produced by Node 6 compute_depth_metrics.

    Merged into PaperRecord at pipeline orchestrator layer via model_copy.
    """
    hop_depth_per_root: dict[str, int] = Field(
        description="Shortest-path distance from each reaching root, over the "
                    "undirected view of the cleaned citation graph. Key: root "
                    "node_id. Value: non-negative integer distance. A node's "
                    "own node_id appears with value 0 iff the node is a root."
    )
    traversal_direction: Literal["seed", "backward", "forward", "mixed"] = Field(
        description="Categorical position relative to the seed set. See AMD-019 "
                    "for vocabulary definitions."
    )
```

**Why a Pydantic model rather than `TypedDict` or plain `dict[str, dict]`.** `DepthMetrics` is transient — produced by `compute_depth_metrics`, unpacked by the orchestrator into `PaperRecord` via `model_copy`, never persisted on its own. A named Pydantic class for a short-lived intermediate value can look like overkill. It is not. Three reasons:

1. *Validation at construction.* The `Literal["seed", "backward", "forward", "mixed"]` is enforced at the moment `compute_depth_metrics` builds each entry. A bug that produces `"foward"` (typo) or `"unreachable"` (mistaken vocabulary extension) raises at the boundary, not later when a renderer tries to interpret it. Same architectural pattern as `CycleCleanResult`'s validator from §Prerequisite — push correctness to the construction site, trust thereafter.
2. *Consistency with `models.py`.* Every other structured value in the arxiv domain — `PaperRecord`, `CitationEdge`, `SuppressedEdge`, `CycleLog`, `CycleCleanResult` — is a Pydantic model. Breaking the convention for one transient type would be a local optimization at the cost of a project-wide pattern.
3. *Forward composability with Nodes 7/8/9.* When Node 7 (communities) and future per-node metric producers are built, their return shapes will mirror this one — `dict[node_id, CommunityAssignment]`, `dict[node_id, ...]`. The orchestrator's merge step composes uniformly across producers if every producer returns Pydantic models keyed by `node_id`. Mixing Pydantic-models-here with TypedDicts-elsewhere fragments the orchestrator's seam.

`TypedDict` would give typing-only support without runtime validation; plain `dict[str, dict]` gives nothing. Neither is consistent with the rest of `models.py` or with the determinism-at-the-boundary pattern Idiograph applies elsewhere.

### Changed model — `PaperRecord`

Remove:
```python
topological_depth: int | None = Field(...)
```

Add (mirroring `DepthMetrics` shape — the merged fields live directly on `PaperRecord` after orchestrator merge):
```python
hop_depth_per_root: dict[str, int] = Field(
    default_factory=dict,
    description="Assigned by Node 6 — shortest-path distance from each "
                "reaching root over the undirected view of the cleaned "
                "citation graph. Empty dict before Node 6 runs."
)
traversal_direction: Literal["seed", "backward", "forward", "mixed"] | None = Field(
    default=None,
    description="Assigned by Node 6 — categorical position relative to the "
                "seed set. See AMD-019."
)
```

`pagerank: float | None` stays as declared — unchanged.

### Unchanged but docstring update — `CycleLog.affected_node_ids`

Docstring changes from "node_ids whose topological_depth must be null downstream (Node 6 handoff)" to reflect audit/provenance-only role:

```python
@property
def affected_node_ids(self) -> set[str]:
    """node_ids whose original edges were suppressed during cycle cleaning.
    Retained for audit and provenance (Node 8). Under AMD-019, Node 6 does
    not require this handoff — suppressed-cycle nodes receive normal depth
    metrics computed over the cleaned DAG.
    """
```

---

## Algorithm — `compute_depth_metrics`

```
Identify roots:
    roots = [n.node_id for n in nodes if n.node_id in n.root_ids]
    (A node is a root iff its own node_id appears in its root_ids list.)

Build two views of the graph:
    G_directed = DiGraph from cleaned_edges (citer -> cited)
    G_undirected = G_directed.to_undirected()

For each root r:
    Run BFS from r over G_undirected. For every reached node n, record:
        undirected_distance[r][n] = BFS distance
    Run BFS from r over G_directed (successors only). Record reached set:
        forward_from[r] = {n reachable from r by following edges forward}
    Run BFS from r over G_directed.reverse() (predecessors only). Record reached set:
        backward_from[r] = {n reachable from r by walking edges in reverse}

For each node n:
    reaching_roots = [r for r in roots if n in undirected_distance[r]]

    If not reaching_roots:
        RAISE ValueError(f"Node {n.node_id} unreachable from any root")

    hop_depth_per_root = {
        r: undirected_distance[r][n.node_id] for r in reaching_roots
    }

    If n.node_id in roots:
        direction = "seed"
    Else:
        forward_hits = [r for r in reaching_roots if n.node_id in forward_from[r]]
        backward_hits = [r for r in reaching_roots if n.node_id in backward_from[r]]

        (Note: forward_hits and backward_hits are disjoint unless a cycle existed
         between n and r, which Node 4.5 has already resolved. In a DAG, any given
         (root, node) pair has a unique direction.)

        If forward_hits == reaching_roots and not backward_hits:
            direction = "backward"   # node is a descendant in the DAG from
                                     # every reaching root; NODE 3 lineage side
        elif backward_hits == reaching_roots and not forward_hits:
            direction = "forward"    # node is an ancestor; NODE 4 side
        else:
            direction = "mixed"      # direction varies across roots

    result[n.node_id] = DepthMetrics(
        hop_depth_per_root=hop_depth_per_root,
        traversal_direction=direction,
    )

Return result
```

**Direction-labeling truth table.** The five-way classification reduces to the following cases on `forward_hits` and `backward_hits` against `reaching_roots` (with the seed check handled before this block):

| `forward_hits` | `backward_hits` | `traversal_direction` |
|---|---|---|
| empty | empty | (impossible — node would be unreachable; raises) |
| equals `reaching_roots`, non-empty | empty | `"backward"` |
| empty | equals `reaching_roots`, non-empty | `"forward"` |
| any other non-empty combination | any other non-empty combination | `"mixed"` |

The "any other" row covers two distinct shapes worth naming, both of which collapse to `"mixed"` correctly:

- *True multi-direction.* `forward_hits` and `backward_hits` are both non-empty and partition `reaching_roots` between them. The canonical CRISPR between-seeds case.
- *Partial-reach mixed.* Some roots in `reaching_roots` appear in `forward_hits`, others appear in `backward_hits`, and some roots not in `reaching_roots` at all. The directions disagree among the roots that *do* reach the node, regardless of whether other roots are absent. Same label.

The disagreement is the criterion. Roots that don't reach the node don't get a vote.

**Direction vocabulary vs. edge semantics.** Citation edges point `citer → cited`. A node that the seed cites (Node 3's backward-traversal output, foundational lineage) is a DAG *descendant* of the seed — reachable from seed by following edges forward. Hence `traversal_direction = "backward"` (the *traversal* was backward from the seed's citations), even though DAG-topologically the node is a descendant. The vocabulary matches the pipeline's traversal-side terminology (Node 3 = backward, Node 4 = forward), not the DAG's ancestor/descendant terms. This is a naming convention, not a correctness claim; the implementation does not conflate them.

**Implementation note on the three BFS passes per root.** For a graph with R roots, N nodes, and E edges, the cost is O(R · (N + E)) — negligible at Phase 9 demo scale. NetworkX offers `nx.single_source_shortest_path_length` (undirected), `nx.descendants` (directed forward), and `nx.ancestors` (directed reverse) as direct primitives. Using them is clearer than hand-rolled BFS. Prefer these.

---

## Algorithm — `compute_pagerank`

```
G = nx.DiGraph()
G.add_nodes_from(n.node_id for n in nodes)
G.add_edges_from((e.source_id, e.target_id) for e in cleaned_edges)

pr = nx.pagerank(G, alpha=damping)

Return dict(pr)  # {node_id: float}
```

**Single NetworkX call.** No bespoke logic. NetworkX PageRank is deterministic given fixed input and fixed alpha. The power-iteration convergence is internal to NetworkX; the function does not expose a seed parameter (none is needed — the algorithm is deterministic, not stochastic).

**Node presence.** `G.add_nodes_from` runs before `add_edges_from` so that isolated nodes (no citation edges to or from them) still appear in the PageRank result. Without this, `nx.pagerank` would only produce values for nodes that appear in some edge. Every node in `nodes` gets a value.

**PageRank invariant.** Output values sum to 1.0 within NetworkX convergence tolerance. This is a property worth asserting in tests (see §Tests).

---

## Forest semantics (AMD-017)

Depth metrics are computed **per root**, producing one dict entry per root that reaches a given node. This is the structural reason `hop_depth_per_root` is a dict and not a scalar.

**Seed self-entry.** A seed carries its own `node_id → 0` in its dict. In a multi-seed forest, a seed may also carry entries for other seeds that reach it via citation paths (e.g., Zhang 2013 cites Doudna 2012, so Doudna's dict carries `{doudna: 0, zhang: 1}` after Node 6). `traversal_direction` for a seed is always `"seed"`, regardless of whether other seeds reach it.

**Partial reachability.** In a three-seed graph where root C does not reach node n, n's dict carries entries only for the reaching roots (A, B). No `None` placeholders. A node unreachable from any root raises (see §Contracts — this is a pipeline bug, not a valid state).

**The "mixed" category.** A node is `"mixed"` iff its reaching roots disagree on direction — at least one reaches it forward and at least one reaches it in reverse. Roots that do not reach the node at all do not participate in the vote; the disagreement among reaching roots is sufficient. In the canonical CRISPR two-seed case (Doudna 2012, Zhang 2013), a 2012-published review that cites Doudna and is cited by Zhang lands as `"mixed"` — Doudna reaches the review by walking edges in reverse, Zhang reaches it by following edges forward. The same label applies in three-seed graphs where two reaching roots disagree on direction even if the third root does not reach the node at all. This category is the primary analytical payload of the multi-seed traversal; it identifies papers structurally between the seeds. Renderer behavior for mixed nodes (Y-axis placement, styling) is a view-layer concern — Node 6 only labels them.

PageRank is whole-graph and has no per-root or forest considerations.

---

## Contracts and edge cases

**Empty inputs.** `nodes=[]`: both functions return `{}`. No work to do, not an error. `cleaned_edges=[]` with non-empty `nodes`: `compute_depth_metrics` assigns every seed `traversal_direction="seed"` with self-entry-only dicts; non-seed nodes raise (unreachable). `compute_pagerank` returns a uniform distribution (1/N per node).

**No roots in `nodes`.** If no node in `nodes` satisfies `node.node_id in node.root_ids`, `compute_depth_metrics` raises `ValueError("No roots found in nodes")`. Indicates upstream pipeline bug — Node 0 should always produce at least one root.

**Unreachable node.** A node present in `nodes` but reachable from no root raises `ValueError(f"Node {node_id} unreachable from any root")`. Indicates upstream pipeline bug — traversal should not produce orphan nodes. Surface loudly rather than silently assigning an empty dict.

**Suppressed-cycle nodes.** Under AMD-019, these are treated as ordinary nodes. No null handling, no special casing. `cycle_log.affected_node_ids` is not consulted.

**`damping` out of range.** Values outside `(0.0, 1.0)` are passed through to NetworkX, which raises its own `ValueError`. No upfront validation in `compute_pagerank`; let NetworkX surface the error.

**Duplicate node_ids in `nodes`.** Not expected — upstream deduplication guarantees uniqueness. If present, behavior is undefined (dict construction overwrites; BFS still terminates). Do not defend against this; surface via Node 3/Node 4 invariants.

**Edges referencing unknown node_ids.** Cannot occur. The contract is enforced upstream at the `CycleCleanResult` constructor boundary — see §Prerequisite. Node 6 takes the validated result and trusts it.

**Seeds in the `"mixed"` case.** Impossible. Seeds are always `"seed"` regardless of how other roots reach them. The seed check precedes the direction check.

---

## Logging

- `compute_depth_metrics` start: INFO, `"Node 6 depth: N nodes, M edges, R roots"`
- `compute_depth_metrics` completion: INFO, `"Node 6 depth complete: seed={k}, backward={k}, forward={k}, mixed={k}"`
- Unreachable-node raise: ERROR before raise, naming the `node_id`
- `compute_pagerank` start: INFO, `"Node 6 pagerank: N nodes, M edges, alpha={damping}"`
- `compute_pagerank` completion: INFO, `"Node 6 pagerank complete"`

Standard project logger — `logging.getLogger(__name__)`.

---

## Tests — minimum set

File: `tests/domains/arxiv/test_pipeline_node6.py`

Each test has a one-line docstring. No pytest-asyncio (synchronous). No mocked HTTP (no I/O). Synthetic graph fixtures, inline helpers following the Node 4.5/Node 5 pattern (`_rec`, `_edge`).

### `compute_depth_metrics`

| Test | What it proves |
|---|---|
| `test_single_seed_backward_chain` | Seed S, S→A→B: A is "backward" d=1, B is "backward" d=2, S is "seed" with {S:0} |
| `test_single_seed_forward_chain` | Seed S, A→B→S: A is "forward" d=2, B is "forward" d=1, S is "seed" |
| `test_single_seed_mixed_graph` | Seed S with both ancestor and descendant neighbors: each labeled correctly |
| `test_seed_self_entry_zero` | Every seed carries own node_id → 0 in its dict |
| `test_two_seed_forest_no_overlap` | Two disjoint seed subtrees: all non-seed nodes reach only one seed each |
| `test_two_seed_shared_ancestor` | Both seeds cite X: X is "backward", dict has both seed entries |
| `test_two_seed_mixed_between` | Seed S2 cites seed S1; X cites S1 and is cited by S2: X is "mixed" |
| `test_two_seed_each_reaches_other` | S2 cites S1: S1's dict has {S1:0, S2:1}, S1's direction is "seed" |
| `test_three_seed_partial_reachability` | Node reachable from 2 of 3 seeds carries dict with exactly 2 entries |
| `test_three_seed_partial_reach_mixed` | Node reachable forward from one seed, backward from another, unreachable from the third: labeled "mixed" |
| `test_suppressed_cycle_node_normal_values` | Nodes in cycle_log.affected_node_ids receive normal metrics, not null |
| `test_unreachable_node_raises` | Node with no path from any root raises ValueError |
| `test_no_roots_raises` | nodes with no self-root entries raises ValueError |
| `test_empty_nodes_returns_empty` | nodes=[] returns {} |
| `test_input_not_mutated` | Original input lists unchanged after call |
| `test_deterministic_output` | Same input produces identical output across repeat calls |

### `compute_pagerank`

| Test | What it proves |
|---|---|
| `test_pagerank_networkx_agreement` | Output matches `nx.pagerank(G, alpha=damping)` on hand-constructed fixture |
| `test_pagerank_sums_to_one` | Sum of output values is 1.0 within tolerance |
| `test_pagerank_every_node_assigned` | Every node_id in nodes appears in output, including isolates |
| `test_pagerank_damping_respected` | Different damping values produce different results on same graph |
| `test_pagerank_deterministic` | Same input produces identical output across repeat calls |
| `test_pagerank_empty_nodes_returns_empty` | nodes=[] returns {} |
| `test_pagerank_empty_edges_uniform` | No edges: each of N nodes gets value 1/N |
| `test_pagerank_input_not_mutated` | Original input lists unchanged after call |

Total: 16 depth tests + 8 pagerank tests = 24 new tests.

---

## Boundaries — what Node 6 does not do

- Does not produce edges. All outputs are per-node metrics; the edge set passes through untouched.
- Does not modify `cleaned_edges`, `suppressed_edges`, or any other Node 4.5 output. Node 6 consumes only `cleaned_edges`.
- Does not consume `cycle_log` or `affected_node_ids`. Under AMD-019, Node 4.5 → Node 6 no longer has a null-depth handoff.
- Does not compute communities. That is Node 7.
- Does not compute `topological_depth` — that field is removed from `PaperRecord` per AMD-019.
- Does not mutate `PaperRecord` instances. Returns dicts; orchestrator merges via `model_copy`.
- Does not persist anything.
- Does not project per-root depths into a single scalar. Renderer computes projections on demand from `hop_depth_per_root` and `traversal_direction`.
- Does not compute centrality metrics beyond PageRank (no betweenness, closeness, eigenvector). Add per future amendment if needed.
- Does not touch `PaperRecord.hop_depth` (set at traversal time by Nodes 0/3/4). The traversal `hop_depth` and Node 6's `hop_depth_per_root` are distinct fields measuring distinct things; both are retained.

---

## Call-site assembly (informative, not part of function contract)

For reader orientation — how the pipeline orchestrator composes Node 4.5 output into Node 6 input and merges results back into `PaperRecord`:

```python
result = clean_cycles(nodes, edges)

depth_metrics = compute_depth_metrics(nodes, result.cleaned_edges)
pagerank_scores = compute_pagerank(nodes, result.cleaned_edges, damping=0.85)

nodes_with_metrics = [
    n.model_copy(update={
        "hop_depth_per_root": depth_metrics[n.node_id].hop_depth_per_root,
        "traversal_direction": depth_metrics[n.node_id].traversal_direction,
        "pagerank": pagerank_scores[n.node_id],
    })
    for n in nodes
]
```

This composition is **not Node 6's concern.** It is shown here only to clarify how Node 6's outputs land on `PaperRecord`. The assembly lives in the pipeline orchestrator (future work).

Node 5 is composed separately, earlier in the pipeline, on the full cleaned ∪ suppressed edge set. Node 6 runs after Node 5 but consumes only `cleaned_edges` — the two functions do not share edge inputs.

---

## Implementation constraints

- Pure functions. No I/O, no network, no async, no mutation of inputs.
- `encoding="utf-8"` is irrelevant — no file I/O.
- NetworkX is required for `compute_pagerank` (it is the canonical PageRank implementation for this project) and recommended for `compute_depth_metrics` via `nx.single_source_shortest_path_length`, `nx.descendants`, `nx.ancestors`. NetworkX is already a project dependency; no new imports at the package level.
- No new graph-library dependencies (igraph, graph-tool, etc). `numpy` and `scipy` are required by NetworkX's `pagerank` implementation in NetworkX ≥ 3.0 (`_pagerank_scipy` is the only convergent backend) and are pinned explicitly in `pyproject.toml` rather than left as transitive declarations of NetworkX. Pinning at our own boundary keeps the dependency contract explicit and prevents future NetworkX upgrades from silently changing what we ship.
- ruff: format new code only; do not reformat pre-existing code in `pipeline.py` or `models.py`. (Same constraint that caught out the Node 5 implementation session — see `session-2026-04-23-node5-implementation.md`.)
- Source order in `pipeline.py`: Node 6 functions follow `compute_co_citations` to match pipeline order.
- `DepthMetrics` model lives in `models.py` alongside `PaperRecord` and the other arxiv-domain models.

---

## Freeze trigger

All tests in `test_pipeline_node6.py` passing, merged to main. Baseline test count must remain green (113 post-Node-5, expected 113 + 24 Node 6 tests = 137).

Post-freeze deferred items:
- `spec-arxiv-pipeline-final.md` renderer data contract update: remove `topological_depth` row, add `hop_depth_per_root` and `traversal_direction` rows. Node 6 section rewritten to match AMD-019. Separate PR, same pattern as PR #14's Node 4.5 §Boundaries correction.
- `spec-node4.5-cycle-cleaning.md` step-5 language update: "Nodes involved in suppressed edges are marked for `topological_depth: null` downstream" becomes a note that this behavior was superseded by AMD-019. Same PR as the arxiv-pipeline-final.md update.
- `amendments.md` AMD-017 "Downstream Metric Behavior in a Forest" table: add AMD-019 cross-reference in the `topological_depth` row, or strike the row entirely and replace with rows for the two new fields. Decide at the follow-up PR drafting time.
- Orchestrator wiring — `run_arxiv_pipeline()` — not part of this spec. Separate design session.
- Additional centrality metrics (betweenness, closeness) if the renderer proves they are needed — future amendment.
