# Copyright 2026 Ryan Smith
# SPDX-License-Identifier: Apache-2.0
#
# Idiograph — deterministic semantic graph execution for production AI pipelines.
# https://github.com/idiograph/idiograph

import asyncio
import os

import httpx
from dotenv import load_dotenv

from idiograph.core.logging_config import get_logger
from idiograph.core.models import Graph, Node, Edge
from idiograph.domains.arxiv.models import PaperRecord, make_node_id

load_dotenv()

_log = get_logger("arxiv.pipeline")

OPENALEX_BASE = "https://api.openalex.org/works"
_WORK_SELECT = (
    "id,ids,title,publication_year,authorships,"
    "abstract_inverted_index,cited_by_count"
)
_TRAVERSAL_SELECT = _WORK_SELECT + ",referenced_works"


def _get_api_key() -> str:
    key = os.getenv("OPENALEX_API_KEY")
    if not key:
        raise EnvironmentError(
            "OPENALEX_API_KEY not set. Add it to .env or set it in the environment."
        )
    return key


def reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """Reconstruct plain-text abstract from OpenAlex's inverted-index format.

    The index maps each word to the list of positions where it occurs.
    """
    if not inverted_index:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort(key=lambda p: p[0])
    return " ".join(word for _, word in positions) or None


def _strip_openalex_id(url_or_id: str) -> str:
    """'https://openalex.org/W123' -> 'W123'; passthrough for bare IDs."""
    return url_or_id.rstrip("/").split("/")[-1]


def _work_to_record(
    work: dict, hop_depth: int, root_ids: list[str]
) -> PaperRecord:
    """Map an OpenAlex work JSON object to a PaperRecord."""
    ids = work.get("ids") or {}
    arxiv_url = ids.get("arxiv")
    arxiv_id = arxiv_url.rstrip("/").split("/")[-1] if arxiv_url else None
    doi = ids.get("doi")

    authorships = work.get("authorships") or []
    authors = [
        (a.get("author") or {}).get("display_name")
        for a in authorships
        if (a.get("author") or {}).get("display_name")
    ]

    return PaperRecord(
        node_id=make_node_id(work),
        arxiv_id=arxiv_id,
        doi=doi,
        openalex_id=_strip_openalex_id(work["id"]),
        title=work.get("title") or "",
        year=work.get("publication_year"),
        authors=authors,
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        citation_count=work.get("cited_by_count") or 0,
        hop_depth=hop_depth,
        root_ids=list(root_ids),
    )


def _seed_filter(seed: dict) -> str | None:
    """Build the OpenAlex filter expression for a single seed entry."""
    if "arxiv_id" in seed and seed["arxiv_id"]:
        return f"ids.arxiv:https://arxiv.org/abs/{seed['arxiv_id']}"
    if "doi" in seed and seed["doi"]:
        return f"ids.doi:{seed['doi']}"
    return None


async def fetch_seeds(
    seed_ids: list[dict],
    client: httpx.AsyncClient,
    api_key: str,
    sleep_ms: int = 150,
) -> tuple[list[PaperRecord], list[dict]]:
    """Resolve a list of seed identifiers against OpenAlex.

    Each entry in ``seed_ids`` is one of::

        {"arxiv_id": "1234.56789"}
        {"doi": "10.1234/example"}

    Returns a tuple ``(resolved, failures)``. ``resolved`` is a list of
    ``PaperRecord`` with ``hop_depth=0`` and ``root_ids=[node_id]``.
    ``failures`` is a list of ``{"seed": <original dict>, "reason": <str>}``.

    Raises ``ValueError`` if ``seed_ids`` is empty, or if every seed fails.
    """
    if not seed_ids:
        raise ValueError("fetch_seeds requires at least one seed identifier.")

    resolved: list[PaperRecord] = []
    failures: list[dict] = []
    sleep_s = sleep_ms / 1000.0

    for idx, seed in enumerate(seed_ids):
        if idx > 0:
            await asyncio.sleep(sleep_s)

        filt = _seed_filter(seed)
        if filt is None:
            failures.append({"seed": seed, "reason": "unrecognized seed shape"})
            _log.info("Seed %s failed: unrecognized shape", seed)
            continue

        params = {
            "filter": filt,
            "select": _WORK_SELECT,
            "api_key": api_key,
        }
        try:
            response = await client.get(OPENALEX_BASE, params=params)
            response.raise_for_status()
        except httpx.HTTPError as e:
            failures.append({"seed": seed, "reason": f"http error: {e}"})
            _log.info("Seed %s failed: http error: %s", seed, e)
            continue

        results = (response.json() or {}).get("results") or []
        if not results:
            failures.append({"seed": seed, "reason": "no results"})
            _log.info("Seed %s failed: no results", seed)
            continue

        work = results[0]
        record = _work_to_record(work, hop_depth=0, root_ids=[])
        record.root_ids = [record.node_id]
        resolved.append(record)
        _log.info("Seed resolved: %s", record.node_id)

    if not resolved:
        raise ValueError(
            f"All {len(seed_ids)} seeds failed to resolve. Failures: {failures}"
        )

    return resolved, failures


ARXIV_PIPELINE: Graph = Graph(
    name="arxiv_abstract_pipeline",
    version="1.0",
    nodes=[
        Node(
            id="fetch",
            type="FetchAbstract",
            params={"paper_id": ""},  # patched at runtime via CLI
        ),
        Node(
            id="claims",
            type="LLMCall",
            params={
                "system": "You are a precise scientific analyst.",
                "prompt_template": (
                    "List the key concrete claims from this abstract as bullet points.\n\n"
                    "Title: {title}\n\nAbstract: {abstract}"
                ),
            },
        ),
        Node(
            id="evaluate",
            type="Evaluator",
            params={
                "keywords": ["method", "model", "result", "performance", "dataset"],
                "threshold": 0.4,
            },
        ),
        Node(
            id="summarize",
            type="LLMSummarize",
            params={
                "system": "You are a technical research communicator.",
                "prompt_template": (
                    "Write a 2-sentence technical summary of this paper for an AI engineer.\n\n"
                    "Title: {title}\n\nAbstract: {abstract}"
                ),
            },
        ),
    ],
    edges=[
        Edge(source="fetch",    target="claims",   type="DATA"),
        Edge(source="claims",   target="evaluate", type="DATA"),
        Edge(source="evaluate", target="summarize", type="CONTROL"),
    ],
)
