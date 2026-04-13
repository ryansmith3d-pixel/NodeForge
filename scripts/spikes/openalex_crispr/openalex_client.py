# Copyright 2026 Ryan Smith
# SPDX-License-Identifier: Apache-2.0
#
# Idiograph — deterministic semantic graph execution for production AI pipelines.
# https://github.com/idiograph/idiograph

import time

import httpx

BASE_URL = "https://api.openalex.org"
MAILTO = "api@theidiograph.com"
SLEEP_SECONDS = 0.1


def get_work(openalex_id_or_doi: str) -> dict:
    if openalex_id_or_doi.startswith("10."):
        path = f"/works/https://doi.org/{openalex_id_or_doi}"
    elif openalex_id_or_doi.startswith("https://doi.org/"):
        path = f"/works/{openalex_id_or_doi}"
    else:
        path = f"/works/{openalex_id_or_doi}"

    url = f"{BASE_URL}{path}"
    response = httpx.get(url, params={"mailto": MAILTO}, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    time.sleep(SLEEP_SECONDS)
    return data


def search_works(query: str, per_page: int = 5) -> list[dict]:
    url = f"{BASE_URL}/works"
    params = {
        "search": query,
        "per-page": per_page,
        "mailto": MAILTO,
    }
    response = httpx.get(url, params=params, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    time.sleep(SLEEP_SECONDS)
    return data.get("results", [])
