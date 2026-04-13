# Copyright 2026 Ryan Smith
# SPDX-License-Identifier: Apache-2.0
#
# Idiograph — deterministic semantic graph execution for production AI pipelines.
# https://github.com/idiograph/idiograph

"""Handler implementations for the Color Designer domain.

Six handlers back the Qt app's node types: color_swatch, color_array,
schema, assign, array_assign, write_tokens. Each follows the arXiv
convention — async, flat dict in / flat dict out, raise on error.
"""

import re
from pathlib import Path

from idiograph.apps.color_designer.token_store import TokenStore
from idiograph.core.logging_config import get_logger

_log = get_logger("handlers.color_designer")

_HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _validate_hex(value: str) -> None:
    if not isinstance(value, str) or not _HEX_RE.match(value):
        raise ValueError(f"Invalid hex color: {value!r}")


async def color_swatch(params: dict, inputs: dict) -> dict:
    """Single color swatch — validates hex, emits color + label."""
    hex_value = params["hex"]
    label = params.get("label", "")
    _validate_hex(hex_value)
    return {"color": hex_value, "label": label}


async def color_array(params: dict, inputs: dict) -> dict:
    """Ordered palette — validates each hex, emits color_array."""
    colors = params.get("colors", [])
    for entry in colors:
        _validate_hex(entry["hex"])
    return {"color_array": list(colors)}


async def schema(params: dict, inputs: dict) -> dict:
    """Load a token schema from disk via TokenStore."""
    token_file = params["token_file"]
    path = Path(token_file)
    if not path.exists():
        raise FileNotFoundError(f"Token file not found: {token_file}")
    store = TokenStore(path)
    return {"token_dict": store.tokens()}


async def assign(params: dict, inputs: dict) -> dict:
    """Pair a single upstream color with a role, emit one assignment."""
    role = params["role"]
    color_hex = next(
        (v["color"] for v in inputs.values() if isinstance(v, dict) and "color" in v),
        None,
    )
    if color_hex is None:
        raise ValueError("assign: no upstream input with 'color' key.")
    return {"assignment": {"role": role, "hex": color_hex}}


async def array_assign(params: dict, inputs: dict) -> dict:
    """Positional zip — color_array index i → token_dict role index i."""
    color_array = next(
        (v["color_array"] for v in inputs.values()
         if isinstance(v, dict) and "color_array" in v),
        None,
    )
    token_dict = next(
        (v["token_dict"] for v in inputs.values()
         if isinstance(v, dict) and "token_dict" in v),
        None,
    )
    if color_array is None:
        raise ValueError("array_assign: no upstream input with 'color_array' key.")
    if token_dict is None:
        raise ValueError("array_assign: no upstream input with 'token_dict' key.")

    roles = list(token_dict.keys())
    assignments = [
        {"role": roles[i], "hex": color_array[i]["hex"]}
        for i in range(min(len(color_array), len(roles)))
    ]
    return {"assignments": assignments}


async def write_tokens(params: dict, inputs: dict) -> dict:
    """Write upstream assignments into a token file via TokenStore."""
    token_file = params["token_file"]
    path = Path(token_file)
    if not path.exists():
        path.write_text("{}", encoding="utf-8")

    store = TokenStore(path)
    count = 0
    for v in inputs.values():
        if not isinstance(v, dict):
            continue
        if "assignment" in v:
            a = v["assignment"]
            store.set(a["role"], a["hex"])
            count += 1
        elif "assignments" in v:
            for a in v["assignments"]:
                store.set(a["role"], a["hex"])
                count += 1
    store.save()
    _log.info("write_tokens: wrote %d token(s) to %s", count, path)
    return {"status": "written", "count": count, "path": str(path)}
