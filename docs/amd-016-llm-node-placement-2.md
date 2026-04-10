# AMD-016 — LLM Node Placement in the arXiv Citation Pipeline

**Affects:** spec-arxiv-pipeline-final.md — adds two new nodes
**Status:** Accepted — Not Yet Implemented (v2 — vocabulary and renderer contract corrected)
**Decided:** 2026-04-07
**Follows:** AMD-015

---

## Reason

The frozen arXiv pipeline spec (spec-arxiv-pipeline-final.md) contains no LLM calls. This is a critical omission: the thesis is not that LLMs should be excluded from production pipelines — it is that they should be used correctly. A demo with no LLM does not demonstrate correct LLM integration. It demonstrates a container without its most important occupant.

The thesis requires showing exactly two things about LLMs:

1. An LLM earns its place by doing one thing no deterministic method can do, receiving typed inputs, returning typed outputs, and exiting cleanly.
2. An LLM does not orchestrate, route, or make structural decisions.

Both must be visible in the demo. Two placements satisfy this requirement. They are at opposite ends of the pipeline, performing completely different tasks. The separation is intentional — it demonstrates the thesis twice, in two different contexts, with no ambiguity about where the LLM's responsibility begins and ends.

---

## Decision

Add two LLM nodes to the arXiv pipeline. Both are typed, auditable, and logged in provenance metadata. Neither makes structural decisions.

---

### Node 0.5 — Query Normalization *(new — on the Node 1 path only)*

**Position:** between user input and Node 1 (Structured Query). Bypassed entirely on the Node 0 path — a known arXiv ID or DOI does not require language normalization.

**Purpose:** translate sloppy, ambiguous, or malformed user input into valid structured query fields before Node 1 fires. Handles misspellings, overconstrained queries likely to return nothing, ambiguous author names, and category mismatches.

**Why this placement is correct:** Node 1 requires structured field inputs. The LLM sits at exactly the boundary between human intent and machine execution — the one boundary where language understanding is genuinely required and no simpler tool suffices. Once Node 0.5 exits, the pipeline is fully deterministic.

**Input:**
```
raw_query: dict   # whatever the user submitted
```

**Output:**
```
normalized_query: dict     # corrected, validated field values
warnings: list[string]     # one entry per issue found — empty if input was clean
confidence: float          # overall confidence in the normalization
```

**Behavior:**
- Always returns a `normalized_query` — even at low confidence
- Never blocks pipeline execution
- Warns, never gates
- Warnings surface in the renderer UI — not hidden in logs or provenance only
- If confidence falls below a declared threshold, the renderer displays a visible notice: "Query was modified — review changes before proceeding"

**Thesis connection:** the LLM is a translator at the human/machine boundary. It converts ambiguous natural language into typed structured data and exits. Every subsequent node receives clean, validated inputs. The LLM does not participate in any decision downstream of this point.

**Credibility rationale:** a technical evaluator who hits a null result because of a malformed query asks immediately why the system didn't catch it. In a project that claims to demonstrate correct AI integration in 2026, a missing input normalization layer is not a minor gap — it is a credibility failure before the demo starts. Node 0.5 is the answer to that question.

---

### Node 5.5 — Semantic Relationship Annotation *(new — runs after co-citation, before metrics)*

**Position:** after Node 5 (Co-citation Computation), before Node 6 (Metric Computation). Runs at pipeline build time, not demo runtime. Results stored in registry.

**Purpose:** for each node in the assembled graph, classify the intellectual relationship between that paper and the seed paper. The citation structure tells you *that* papers are related. Node 5.5 tells you *how*.

**Why this placement is correct:** by the time Node 5.5 runs, the graph structure is completely fixed. Traversal is done, cycle cleaning is done, co-citation edges are computed. Every node is in the graph because of deterministic structural criteria. The graph does not need the LLM to select, route, or modify structure. It needs the LLM to answer one question no deterministic method can answer: what is the intellectual relationship between these two abstracts? That is a language task. The LLM performs it once per node, returns a typed result, and exits. The result flows forward as a node property like any other field.

**Input (per node):**
```
seed_abstract: string
candidate_abstract: string
seed_node_id: string
candidate_node_id: string
```

**Output (per node):**
```
relationship_type: string    # closed vocabulary — see below
semantic_confidence: float
```

**Closed vocabulary for `relationship_type`:**

| Value | Definition |
|---|---|
| `methodological_precursor` | Introduces or establishes a method the seed directly uses or extends |
| `theoretical_foundation` | Provides the conceptual or mathematical basis the seed builds on |
| `cross_domain_source` | Provides theory, method, or framing from another domain that the seed directly uses or adapts |
| `downstream_application` | Applies the seed's ideas, methods, or results to a new domain or problem space |
| `empirical_validation` | Provides experimental evidence that supports, challenges, or contextualizes the seed's claims |
| `concurrent_work` | Addresses the same problem at roughly the same time, via a different approach |
| `adjacent_work` | Operates in the same problem space without a direct intellectual dependency — lateral, not directional |
| `unclear` | Abstract does not contain sufficient information to classify the relationship confidently |

**Why `adjacent_work` is in the vocabulary:** academic citation graphs contain many papers that co-appear not because one builds on the other but because both address the same neighborhood of problems. `adjacent_work` is the semantic label for the same signal that co-citation edges carry structurally. When a strong co-citation edge and an `adjacent_work` classification agree on the same pair of nodes, confidence in the relationship is higher. When they disagree, that is informative — worth surfacing in the renderer.

**Renderer surface:** `relationship_type` is a node-level property and maps to node-level visuals only — node shape and filter controls in the influence view. Edge color is governed by edge type (`cites` vs `co_citation`), which already has a declared visual treatment in the spec. Node properties drive node visuals; edge properties drive edge visuals. The co-citation toggle already exists; a relationship type filter gives the evaluator the ability to isolate intellectual lineage (`methodological_precursor` + `theoretical_foundation`) from the competitive landscape (`concurrent_work` + `adjacent_work`). The LLM's contribution is directly visible and interrogable.

**Performance:** 150–300 Haiku calls at pipeline build time. Cost paid once. Results cached in registry under the content-addressed cache key (same seed + parameters → same annotations, no recomputation).

**Provenance:** Node 5.5 run recorded in graph provenance metadata — model used, call count, parameter values, any calls that returned `unclear` and why.

**Thesis connection:** the LLM measures a semantic property of content that is already structurally committed in the graph. It does not select nodes, modify edges, or affect execution order. Its output is a typed field. It is auditable. Removing Node 5.5 would leave the graph structurally correct and semantically opaque — you would know that papers are related but not how. That gap is exactly where the LLM belongs.

---

## Relationship Between the Two Nodes

The two nodes are independent. They run at different points in the pipeline, perform different tasks, and operate on different inputs. The separation is not incidental — it demonstrates that correct LLM integration is a design pattern, not a one-time decision.

Node 0.5: LLM as translator. Human intent → machine input. Runs at query time.
Node 5.5: LLM as classifier. Content → semantic property. Runs at build time.

Neither node orchestrates anything. Neither node's output determines pipeline structure. Both produce typed results that flow through the graph like any other field.

---

## Spec Amendment Required

`spec-arxiv-pipeline-final.md` must be updated to add:
- Node 0.5 to the pipeline node list, with full input/output contract
- Node 5.5 to the pipeline node list, with full input/output contract and relationship vocabulary
- `relationship_type` and `semantic_confidence` to the renderer data contract (node fields)
- Node 5.5 dependency added to the pipeline execution order (after Node 5, before Node 6)
- Both nodes added to the declared parameters table (model, confidence threshold)

The spec is currently marked FROZEN. This amendment supersedes the frozen state on the affected sections only. All other sections remain as declared.

---

## Architectural Constraints Added

| Decision | Affects | Rationale |
|---|---|---|
| Node 0.5 is on the Node 1 path only — Node 0 bypasses it entirely | arXiv pipeline | A known identifier does not require language normalization |
| Node 0.5 never blocks pipeline execution — warn, never gate | arXiv pipeline | The LLM is an assistant to the pipeline, not a gatekeeper |
| Node 5.5 relationship vocabulary is closed — new values require an amendment | arXiv pipeline | Open vocabulary produces unrenderable output; closed vocabulary is a schema contract |
| Both LLM nodes log to provenance metadata | arXiv pipeline | LLM contributions must be auditable, not inferred |
| Node 0 fallback to Node 1 does not trigger Node 0.5 | arXiv pipeline | A failed identifier lookup is a missing record problem, not a language normalization problem — no LLM call is warranted |
| `summarize_intent()` remains purely algorithmic — this decision does not affect it | Core | Unchanged from prior constraints |

---

*Amendment: AMD-016*
*Follows: AMD-015*
*Decided: 2026-04-07*
