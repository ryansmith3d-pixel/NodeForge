# NodeForge – Blueprint Amendments & Decision Log (Addendum 2)

Continues from `blueprint_amendments-1.md`.
Last amendment in previous log: AMD-005.

---

## Amendments

---

### AMD-006 — arXiv Pipeline as Phase 6 Demo Domain
Affects: Phase 6 (Async & Orchestration)  
Status: ACTIVE  
Decided: 2026-03  
Reason: The Blueprint describes Phase 6 as making the graph executable, but does not
specify what executes. The original intent implied VFX handlers — `ShaderValidate`,
`RenderComparison`, etc. — operating on production assets. Two problems with that:

First, VFX production handlers require DCC tool dependencies (Arnold, USD, Hydra) that
would make Phase 6 primarily about installation and integration rather than execution
architecture. That inverts the priority.

Second, and more importantly: NodeForge is not a VFX tool. It is a proof-of-concept
system for the thesis. Using VFX-specific handler implementations risks making the system
look domain-specific rather than domain-agnostic. The thesis claims the architecture
works for any production pipeline — the demo domain should demonstrate that, not
contradict it.

The selected demo domain is an **arXiv abstract processing pipeline** using the public
arXiv API (no key required). This domain was chosen because:

- Data is real and free — no invented fixtures
- Natural pipeline structure: fetch → extract → evaluate → route → summarize
- The LLM node adds genuine value, not decoration — claim extraction from academic
  abstracts is a task with real variance and real failure modes
- The content domain (AI and graphics research) is directly relevant to the thesis
  narrative — processing AI research papers using an AI pipeline demonstrates the
  argument without any rhetorical overhead. The demo is self-referential in a useful way.
- No new dependencies beyond what Phase 8 already requires (Anthropic API)

The pipeline structure:

```
FetchAbstract → LLMCall (extract claims) → Evaluator → Router
                                                          ├── LLMCall (technical summary)
                                                          └── Discard
```

Node responsibilities:
- `FetchAbstract` — hits arXiv API, returns structured abstract data. Real network I/O
  that fails realistically on bad IDs, network errors, or malformed responses.
- `LLMCall (claims)` — extracts concrete, falsifiable claims from the abstract. Output
  variance is intentional — the evaluator must handle both crisp and vague abstracts.
- `Evaluator` — scores claims against criteria defined in `params`, not hardcoded in
  logic. Threshold also lives in params. An agent can modify both without touching code.
- `Router` — activates one downstream branch via CONTROL edges based on evaluator output.
  The routing decision is preserved in graph state, not lost in an if/else.
- `LLMCall (summary)` — produces a technical summary for papers that pass evaluation.
- `Discard` — a no-op node that records the rejection. The graph preserves the decision
  trail even for dead ends.

The node type names carry VFX pipeline semantics where appropriate (e.g. `Evaluator`
maps conceptually to `ShaderValidate` — a quality gate with defined criteria). The
handler implementations are domain-specific, but the graph structure is identical.

Change: Phase 6 implementation uses the arXiv pipeline as its primary execution demo.
VFX node types remain in the schema and sample pipeline. The executor is not
VFX-specific. Handler implementations for the arXiv domain live in a separate module
and are registered via the handler registry (see AMD-007).

Done when: The arXiv pipeline graph executes end-to-end via the Phase 6 executor,
with at least one realistic failure demonstrated (bad paper ID, evaluator threshold
not met, LLM output that fails parsing) and that failure surfaced legibly in graph state.

---

### AMD-007 — Handler Registry Pattern for Executor
Affects: Phase 6 (Async & Orchestration)  
Status: ACTIVE  
Decided: 2026-03  
Reason: The execution engine must remain abstract. If the executor contains references
to specific handler implementations (arXiv, LLM calls, etc.), it becomes coupled to
those implementations and loses the property the thesis depends on: that the graph
architecture is domain-agnostic.

The standard solution for this class of problem is a handler registry — a mapping from
node type strings to async handler functions. The executor looks up a handler by
`node.type`, calls it with `(params, inputs)`, and returns the output dict. The executor
never imports handler modules directly.

```python
# Executor sees only this interface
HANDLERS: dict[str, Callable] = {}

def register_handler(node_type: str, fn: Callable) -> None:
    HANDLERS[node_type] = fn

async def execute_node(node: Node, inputs: dict) -> dict:
    handler = HANDLERS.get(node.type)
    if handler is None:
        raise ValueError(f"No handler registered for node type '{node.type}'")
    return await handler(node.params, inputs)
```

Handler implementations are registered at application startup, not imported into the
executor. This means:

- The executor can be tested with stub handlers independently of real implementations
- New node types require no changes to the executor — only a new registration
- The same executor runs VFX handlers, AI handlers, or any future domain without
  modification
- An agent operating on the graph never needs to know what the handler does — only
  what the node type expects as input and produces as output

This is a standard plugin/dispatch pattern. Apache Airflow uses it for operators.
Prefect uses it for tasks. The pattern is well-understood and carries no architectural
risk.

Change: The Phase 6 executor is implemented with a handler registry. Handler
implementations (arXiv domain) live in `src/nodeforge/handlers/arxiv.py` and are
registered in `src/nodeforge/handlers/__init__.py`. The executor lives in
`src/nodeforge/core/executor.py` and imports nothing from the handlers module.

Done when: The executor can be instantiated and run with stub handlers registered
programmatically, independently of whether the arXiv handlers are present. Verified by
tests that register mock handlers and confirm execution order, data flow, and failure
handling without any real I/O.

---

### AMD-008 — Handler Scope Constraint (30-Line Business Logic Rule)
Affects: Phase 6 onward  
Status: ACTIVE  
Decided: 2026-03  
Reason: There is a real risk in Phase 6 that handler implementations grow into their
own subsystems. If a handler requires 200 lines to function correctly, one of two things
is true: either the handler is doing too much (the node should be decomposed into
multiple nodes), or the implementation detail has become the project.

Either outcome undermines the thesis. NodeForge is an architecture demonstration, not
a pipeline tool. Handler implementations are evidence that the architecture works under
real conditions — they are not the system.

The 30-line constraint applies to **business logic only** — the core computation a
handler performs. Error handling, logging, and type coercion are necessary for the system
to behave correctly at runtime and are not counted toward this limit. A handler that
requires significant error handling around a trivial core operation is not a scoping
violation; it is responsible production code.

The constraint is a **code review flag**, not a hard tooling gate. When a handler's
business logic approaches or exceeds 30 lines, the correct response is to stop and ask
whether the node is correctly scoped. The answer to that question is itself a
thesis-relevant finding: one of the architectural properties of a well-designed semantic
graph is that nodes are small, composable, and independently replaceable. A handler
whose logic cannot be expressed concisely is a signal that the node boundary is in the
wrong place.

Change: Handler business logic in Phase 6 (and subsequent phases) should not exceed
30 lines. If it does, decompose the node in the graph rather than extend the handler.
Reviewed at each phase post-mortem by convention, not automated tooling.

Done when: All Phase 6 handler implementations are reviewed at post-mortem. Any handler
whose business logic approached or exceeded the limit is noted, with an explanation of
whether the response was decomposition, justified exception, or a flag for later
refactoring.

---

## Architectural Constraints Log — Additions

New rows to append to the constraints table in `blueprint_amendments-1.md`:

| Decision | Affects | Rationale |
|---|---|---|
| Executor must not import handler modules directly | Phase 6 onward | Covered in AMD-007. The executor is domain-agnostic. Handler registration happens at startup, not at import time. Keeps the core layer independent of implementation details. |
| Handler business logic is capped at 30 lines | Phase 6 onward | Covered in AMD-008. Error handling and logging are excluded from the count. A handler whose core logic exceeds this limit is a signal that the node is incorrectly scoped, not that the limit should be raised. |
| Demo domain is arXiv pipeline, not VFX tool handlers | Phase 6 | Covered in AMD-006. The thesis claims domain-agnosticism. The demo domain should demonstrate that. VFX node types remain in the schema — VFX tool dependencies do not enter the codebase. |

---

## Open Questions — Additions

| Question | Raised | Notes |
|---|---|---|
| Should the handler registry support async-only handlers, or mixed sync/async? | 2026-03 | Async-only is cleaner and consistent with the execution model. Sync handlers can be wrapped with `asyncio.to_thread` if needed. Decide at Phase 6 implementation start. |
| How should the results dict handle failed nodes — omit the key, or store the error? | 2026-03 | Storing a structured error dict under the node ID is preferable. Downstream nodes can inspect it; the executor can distinguish "not run yet" from "ran and failed." Decide at Phase 6 implementation start. |
| Should `Discard` be a real node type or a terminal status on `Router`? | 2026-03 | Separate node is preferable — preserves the decision trail in graph state and keeps Router's responsibility narrow. But worth confirming once the routing logic is implemented. |
| How does the discrete node/edge model handle continuous field evaluation in Phase 10 without losing the clean input/output contract the executor depends on? | 2026-03 | Field nodes in Phase 10 (ScalarField, VectorField, OrientationField) are continuous mathematical objects — they evaluate over a surface or volume rather than consuming and producing discrete data dicts. This is structurally different from every other node type in the system. Three candidate approaches: (1) handlers return a callable (the field function itself) as a value in the output dict — downstream projection nodes invoke it; (2) fields are evaluated at a fixed sample set defined in params and returned as a structured array; (3) field evaluation is treated as a dedicated pre-execution pass, separate from the main executor loop. Option 1 has two compounding problems: it breaks JSON serializability, and it breaks agent-readability — an agent inspecting graph state post-execution would find an opaque callable object where it expects structured data. That is a thesis violation, not merely a technical inconvenience. Option 2 preserves serializability but discretizes what is inherently continuous — the fidelity loss may be acceptable for a demo but is architecturally dishonest. Option 3 introduces a second execution model, which sounds like a compromise but may be the most defensible: a well-defined field evaluation pass with explicit structure and clear semantics is fully consistent with the thesis. The thesis does not require one execution model for everything — it requires explicit structure at every level. A principled second pass is not a contradiction; a collapsed workaround is. Resolve at Phase 10 design stage, not before — but the resolution should be framed as an architectural decision, not a technical patch. |

---

*Last updated: 2026-03*  
*Owner: NodeForge project*