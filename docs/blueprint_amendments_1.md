# Idiograph – Blueprint Amendments & Decision Log

This document tracks amendments to the original Blueprint, and the reasoning behind each one.
The Blueprint itself is not modified — this file sits alongside it as the living layer.

Each entry records: what changes, which phase it affects, why it was decided, and what "done" looks like.

---

## Amendment Format

```
### AMD-[N] — [Short Title]
Affects: Phase X
Status: PENDING | ACTIVE | COMPLETE
Decided: [date or session]
Reason: [why]
Change: [what specifically is added or altered]
Done when: [concrete completion criterion]
```

---

## Amendments

---

### AMD-001 — Pydantic Field Descriptions as Agent Documentation
Affects: Phase 3 (Data Models & Typing)  
Status: COMPLETE  
Decided: 2026-03  
Reason: An agent calling a tool like `update_node()` needs to understand what each parameter
means without a human writing a wrapper to explain it. `Field(description="...")` on every
model field turns the schema itself into agent-readable documentation. Costs nothing in Phase 3,
pays dividends in Phase 8 when tool interfaces are generated from those schemas.  
Change: Every Pydantic field on `Node`, `Edge`, and `Graph` models must include a
`description=` argument written for an agent reader, not just a human one. Treat it like
docstrings for tools, not comments for developers.  
Done when: All Phase 3 model fields have `Field(description="...")` and the JSON Schema
output (via `model.model_json_schema()`) reads as a self-contained agent manual.

---

### AMD-002 — Semantic Intent Summary Tool
Affects: Phase 4.5 (Graph Query & Analysis)  
Status: PENDING  
Decided: 2026-03  
Reason: Phase 4.5 plans traversal, query, and cycle detection — all structural operations.
What's missing is a tool that answers a different kind of question: "what does this subgraph
*do*?" An LLM cannot reason effectively over a raw 1000-node graph. It needs a summarized,
intent-oriented view. This is distinct from `summarize()` (which is statistics) — it's a
semantic description oriented toward agent reasoning and decision-making.  
Change: Add a `summarize_intent(graph, subgraph_ids=None)` function to the query layer.
Output is a structured dict (JSON-serializable) describing: what the subgraph computes,
its domain (VFX / AI / mixed), its critical path, and any failure points or bottlenecks.
Expose via CLI as `idiograph query intent`.  
Done when: An agent can call `summarize_intent()` on a subgraph and receive a structured
response that meaningfully answers "what does this do and where might it fail?" without
needing to inspect individual nodes.

---

### AMD-003 — Edge Type Must Be Extensible, Not a Closed Enum
Affects: Phase 3 (Data Models & Typing)  
Status: COMPLETE  
Decided: 2026-03  
Reason: Phase 10 requires causal edge semantics beyond DATA and CONTROL — specifically
MODULATES, DRIVES, OCCLUDES, EMITS, and PROJECTS_TO. A closed `Literal` or `Enum` on
the `Edge` model would require a breaking change to accommodate these. The fix is trivial
in Phase 3 but expensive to retrofit later.  
Change: The `type` field on the `Edge` model must be defined as an open string (`str`),
not a closed `Literal["DATA", "CONTROL"]` or Python `Enum`. Validation of known types
can still be documented via `Field(description="...")` and enforced in a validator if
desired, but the field itself must accept arbitrary string values to remain extensible.  
Done when: The `Edge` model accepts "DATA", "CONTROL", and any future string type without
a code change to the model definition. Verified by a test that constructs an edge with
type "MODULATES" and confirms it passes validation.

---

### AMD-004 — MCP as Explicit Implementation Target for Phase 8
Affects: Phase 8 (Agent Integration)  
Status: PENDING  
Decided: 2026-03  
Reason: The Blueprint says "integrate with LLM frameworks" — MCP (Model Context Protocol)
is now the dominant open standard for exactly this. Naming it explicitly means Phase 8 has
a concrete delivery target rather than a vague integration goal. MCP means any agent
(Claude, GPT, local models) can connect to Idiograph without bespoke adapters. This also
strengthens the thesis demo: you're not showing a Claude-specific tool, you're showing a
standards-compliant agent-operable system.  
Change: Phase 8 delivery target is an MCP Server wrapping Idiograph's core tool interfaces.
Tools exposed via MCP: `get_node`, `get_edges_from`, `update_node`, `summarize_intent`,
`validate_graph`, `execute_graph` (once Phase 6 is complete). The MCP server is the
proof-of-concept artifact for the thesis — not just an integration detail.  
Done when: A Claude agent (or equivalent) can connect to the Idiograph MCP server,
inspect a graph, modify a node parameter, and re-validate — with no human-written adapter
code between the agent and the graph.

---

### AMD-005 — Graph-Level Referential Integrity Validation
Affects: Phase 4.5 (Graph Query & Analysis)  
Status: PENDING  
Decided: 2026-03  
Reason: Pydantic validates each model in isolation. The `Edge` model has no visibility into
the node list, so an edge referencing a non-existent node ID passes schema validation
silently. This is not a Phase 3 problem — the model layer is not the right place to enforce
cross-object constraints. But it becomes a real problem in Phase 4.5 when traversal follows
edges to nodes that don't exist, producing silent `None` returns or unexpected query behavior.  
Change: Add a graph-level integrity check function — `validate_integrity(graph)` — to the
query/analysis layer in Phase 4.5. It must verify that every `source` and `target` ID on
every edge corresponds to a node that exists in the graph. Returns a structured result
listing any dangling edge references. Expose via CLI as part of the `validate` command or
as a separate `idiograph check` command.  
Done when: A graph containing an edge that references a non-existent node ID is caught and
reported with the specific edge and missing node ID identified. Clean graphs pass silently.

---

## Architectural Constraints Log

These are decisions that constrain future phases. Tracked here so they don't get re-litigated.

| Decision | Affects | Rationale |
|---|---|---|
| Edge `type` must be an open/extensible string, not a closed enum | Phase 3 onward | Covered in AMD-003. Phase 10 requires causal edge types (MODULATES, DRIVES, OCCLUDES, EMITS, PROJECTS_TO). A closed enum would require breaking changes. |
| Node domain (VFX / AI / rendering) is metadata only, never a structural constraint | Phase 3 onward | Phase 10 rendering nodes must fit the same architecture without special-casing. Domain is a label for query filtering, not a type gate. |
| Content-addressed caching preferred over dirty flagging | Phase 6+ | Hash each node's params + input hashes as the cache key. Stateless, fits JSON-serializable graph, reinforces determinism thesis. Event sourcing is a secondary option for agent audit trails only. |
| Idiograph is not a DCC adapter | All phases | The system is an independent semantic graph — not a Houdini plugin or a wrapper for proprietary tools. Agent integration targets the Idiograph graph directly, not downstream software. |
| File I/O must specify UTF-8 encoding explicitly | Phase 3 onward | Windows default encoding is cp1252. Any open() call on a JSON file without encoding="utf-8" will silently misread non-ASCII characters. All file reads and writes in Idiograph must specify encoding explicitly. |

---

## Open Questions

Things that have come up but are not yet decided.

| Question | Raised | Notes |
|---|---|---|
| Should `summarize_intent()` use an LLM call internally, or be purely algorithmic? | 2026-03 | Algorithmic is safer for determinism thesis. LLM-assisted version could be a Phase 9 extension. Don't conflate the two. |
| MCP server: stdio transport or HTTP/SSE? | Not yet raised | stdio is simpler for local dev; HTTP/SSE supports remote agents. Decide at Phase 8 start based on demo requirements. |

---

*Last updated: 2026-03*  
*Owner: Idiograph project*