# spec-color-designer-domain-impl.md
**Status:** LIVING
**Freeze trigger:** Merge of `feat/color-designer-domain` to `main` complete, 44-test gate passing
**Created:** 2026-04-13

---

## Scope

This spec covers the implementation session that wires Color Designer into the Idiograph
executor. The structural refactor (moving files, optional extras, handler registration)
is complete. This session adds execution.

---

## What Gets Built

```
src/idiograph/domains/color_designer/
  __init__.py       ← register_color_designer_handlers()
  handlers.py       ← six handler implementations
  pipeline.py       ← canonical color pipeline Graph definition

src/idiograph/apps/color_designer/
  nodes/
    swatch_node.py      ← add to_idiograph_node()
    array_node.py       ← add to_idiograph_node()
    schema_node.py      ← add to_idiograph_node()
    assign_node.py      ← add to_idiograph_node()
    array_assign_node.py ← add to_idiograph_node()
    write_node.py       ← add to_idiograph_node(); wire Save to execute_graph()
  canvas.py             ← add build_graph()
  main.py               ← register_color_designer_handlers() at boot
```

---

## Handler Contracts

All handlers follow the arXiv convention:
- `async def handler_name(params: dict, inputs: dict) -> dict`
- `_log = get_logger("handlers.color_designer")`
- Raise on error — executor catches and records FAILED status
- Return flat dict
- File header: Copyright 2026 Ryan Smith / Apache-2.0

### `color_swatch`
```python
# params: {"hex": "#7eb8f7", "label": "node.selected"}
# inputs: {}
# validates hex format — raises ValueError if not a valid 3 or 6 digit hex color
# returns: {"color": "#7eb8f7", "label": "node.selected"}
```

### `color_array`
```python
# params: {"colors": [{"label": "...", "hex": "..."}, ...]}
# inputs: {}
# validates each hex value — raises ValueError on first invalid entry
# returns: {"color_array": [{"label": "...", "hex": "..."}, ...]}
```

### `schema`
```python
# params: {"token_file": "/path/to/tokens.seed.json"}
# inputs: {}
# loads via TokenStore — raises FileNotFoundError if path missing
# returns: {"token_dict": {"node.selected": "#7eb8f7", ...}}
```

### `assign`
```python
# params: {"role": "node.selected"}
# inputs: one upstream result containing "color" key
# finds upstream color by inspecting inputs.values() for "color" key
# returns: {"assignment": {"role": "node.selected", "hex": "#7eb8f7"}}
```

### `array_assign`
```python
# params: {}
# inputs: two upstream results — one with "color_array" key, one with "token_dict" key
# resolved by content shape — inspect inputs.values() for key presence
# positional zip: index 0 color → index 0 role, roles past array length are dropped
# returns: {"assignments": [{"role": "...", "hex": "..."}, ...]}
```

### `write_tokens`
```python
# params: {"token_file": "/path/to/tokens.seed.json"}
# inputs: one or more upstream results with "assignment" or "assignments" key
# "assignment" → single (role, hex) pair from AssignNode
# "assignments" → list of (role, hex) pairs from ArrayAssignNode
# creates file if missing (writes "{}")
# uses TokenStore — constructor → set() × N → save()
# returns: {"status": "written", "count": N, "path": str(path)}
```

---

## Input Resolution — Content Shape

`array_assign` and `write_tokens` distinguish upstream inputs by inspecting
the keys present in each result dict. This works because handler output
contracts are closed and controlled:

```python
# array_assign
color_array = next(v["color_array"] for v in inputs.values() if "color_array" in v)
token_dict  = next(v["token_dict"]  for v in inputs.values() if "token_dict"  in v)

# write_tokens
for v in inputs.values():
    if "assignment" in v:
        result[v["assignment"]["role"]] = v["assignment"]["hex"]
    elif "assignments" in v:
        for a in v["assignments"]:
            result[a["role"]] = a["hex"]
```

Edge label routing is the eventual solution when a pipeline requires it.
This is a known limitation documented in the AMD file.

---

## Canonical Pipeline Graph

The canonical demo pipeline — ArrayAssign variant:

```
ColorArray ──[color_array]──→ ArrayAssign ──[assignment]──→ Write
Schema     ──[token_dict] ──→ ArrayAssign
```

Node IDs and types for `pipeline.py`:

```python
COLOR_DESIGNER_PIPELINE = Graph(
    name="color_designer_pipeline",
    version="1.0",
    nodes=[
        Node(id="palette",      type="color_array",   params={"colors": []}),
        Node(id="schema",       type="schema",        params={"token_file": ""}),
        Node(id="array_assign", type="array_assign",  params={}),
        Node(id="write",        type="write_tokens",  params={"token_file": ""}),
    ],
    edges=[
        Edge(source="palette",      target="array_assign", type="DATA"),
        Edge(source="schema",       target="array_assign", type="DATA"),
        Edge(source="array_assign", target="write",        type="DATA"),
    ],
)
```

`token_file` params are empty strings in the template — patched at runtime
by the Qt canvas before execution, same pattern as `paper_id` in arXiv.

---

## Qt Node Translation

Each Qt node implements `to_idiograph_node() -> Node`. The node uses its
`self.node_id` (AMD-018) as the Idiograph Node id.

### SwatchNode
```python
def to_idiograph_node(self) -> Node:
    return Node(
        id=self.node_id,
        type="color_swatch",
        params={"hex": self.current_hex, "label": self.label},
    )
```

### ArrayNode
```python
def to_idiograph_node(self) -> Node:
    return Node(
        id=self.node_id,
        type="color_array",
        params={"colors": [{"label": lbl, "hex": h} for h, lbl in self.rows]},
    )
```
Note: `self.rows` stores `(hex, label)` tuples — order confirmed from array_node.py.

### SchemaNode
```python
def to_idiograph_node(self) -> Node:
    return Node(
        id=self.node_id,
        type="schema",
        params={"token_file": str(self.token_path)},
    )
```

### AssignNode
```python
def to_idiograph_node(self) -> Node:
    return Node(
        id=self.node_id,
        type="assign",
        params={"role": self.current_role},
    )
```

### ArrayAssignNode
```python
def to_idiograph_node(self) -> Node:
    return Node(
        id=self.node_id,
        type="array_assign",
        params={},
    )
```

### WriteNode
```python
def to_idiograph_node(self) -> Node:
    return Node(
        id=self.node_id,
        type="write_tokens",
        params={"token_file": str(self.token_path)},
    )
```

---

## Canvas — build_graph()

`canvas.py` adds one method. It knows the topology through the wire system.
It does not know params — those come from `to_idiograph_node()` on each node.

```python
def build_graph(self) -> Graph:
    nodes = [item.to_idiograph_node()
             for item in self.scene().items()
             if isinstance(item, BaseNode)]
    edges = [
        Edge(source=wire.source_port.parentItem().node_id,
             target=wire.target_port.parentItem().node_id,
             type="DATA")
        for wire in self._wires  # or however canvas tracks live wires
    ]
    return Graph(name="color_design", version="1.0", nodes=nodes, edges=edges)
```

Note: Claude Code must confirm how the canvas tracks live wires before
writing this method — inspect `canvas.py` for the wire collection.

---

## Save Button — main.py

The Save button currently calls `write_node.save()` directly. After this
refactor it calls `execute_graph()`:

```python
import asyncio
from idiograph.core.executor import execute_graph

def _on_save(self) -> None:
    graph = self.canvas.build_graph()
    results = asyncio.run(execute_graph(graph))
    # log results — check for FAILED nodes and surface to UI if needed
```

Note: `asyncio.run()` is correct here — same pattern as the CLI. Qt's event
loop and asyncio do not share a loop in this setup.

---

## Registration

```python
# domains/color_designer/__init__.py
def register_color_designer_handlers() -> None:
    from idiograph.core.executor import register_handler
    from idiograph.domains.color_designer.handlers import (
        color_swatch, color_array, schema,
        assign, array_assign, write_tokens,
    )
    register_handler("color_swatch",  color_swatch)
    register_handler("color_array",   color_array)
    register_handler("schema",        schema)
    register_handler("assign",        assign)
    register_handler("array_assign",  array_assign)
    register_handler("write_tokens",  write_tokens)
```

```python
# apps/color_designer/main.py — add at top of MainWindow.__init__
from idiograph.domains.color_designer import register_color_designer_handlers
register_color_designer_handlers()
```

---

## Implementation Order

Test gate: `uv run pytest` must pass before and after each step.
Branch: `feat/color-designer-domain`

| Step | Action |
|---|---|
| 1 | Create branch |
| 2 | Create `domains/color_designer/` skeleton (`__init__.py`, `handlers.py`, `pipeline.py`) |
| 3 | Implement all six handlers in `handlers.py` |
| 4 | Implement `register_color_designer_handlers()` in `__init__.py` |
| 5 | Implement `COLOR_DESIGNER_PIPELINE` in `pipeline.py` |
| 6 | Add `to_idiograph_node()` to all six Qt node classes |
| 7 | Inspect `canvas.py` wire tracking, then implement `build_graph()` |
| 8 | Wire Save button to `execute_graph()` in `main.py` |
| 9 | Register handlers at boot in `main.py` |
| 10 | Manual verification — launch Qt app, trigger Save, confirm token file written |
| 11 | Commit and merge to `main` |

---

## Test Coverage

Existing 44-test suite must pass throughout. No new tests are strictly
required for this session — the Qt app manual verification (Step 10) is the
functional gate. If time permits, add handler unit tests under
`tests/test_color_designer_handlers.py` following the arXiv handler test
pattern.

---

*Companion documents: spec-color-designer-domain-refactor.md, session-2026-04-13.md,
docs/decisions/amendments.md (AMD-018)*
