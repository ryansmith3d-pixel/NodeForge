# Copyright 2026 Ryan Smith
# SPDX-License-Identifier: Apache-2.0
#
# Idiograph — deterministic semantic graph execution for production AI pipelines.
# https://github.com/idiograph/idiograph

"""Canonical Color Designer pipeline graph.

Defines COLOR_DESIGNER_PIPELINE — the ArrayAssign demo topology:
ColorArray + Schema → ArrayAssign → Write. Token file paths are empty
strings in the template; the Qt canvas patches them at runtime before
execution, same pattern as `paper_id` in the arXiv pipeline.
"""

from idiograph.core.models import Edge, Graph, Node

COLOR_DESIGNER_PIPELINE = Graph(
    name="color_designer_pipeline",
    version="1.0",
    nodes=[
        Node(id="palette",      type="color_array",  params={"colors": []}),
        Node(id="schema",       type="schema",       params={"token_file": ""}),
        Node(id="array_assign", type="array_assign", params={}),
        Node(id="write",        type="write_tokens", params={"token_file": ""}),
    ],
    edges=[
        Edge(source="palette",      target="array_assign", type="DATA"),
        Edge(source="schema",       target="array_assign", type="DATA"),
        Edge(source="array_assign", target="write",        type="DATA"),
    ],
)
