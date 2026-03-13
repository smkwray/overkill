from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_TAXONOMY_PATH = Path("research/derived/bundle_relationships.json")


def load_bundle_relationships(path: str | Path = DEFAULT_TAXONOMY_PATH) -> dict[str, Any]:
    relationship_path = Path(path)
    if not relationship_path.is_file():
        return {
            "version": 1,
            "updated_at": None,
            "provisional_bundle_ids": [],
            "bundle_roles": [],
            "relations": [],
            "repair_prompt_queue": [],
            "deferred_repair_bundle_ids": [],
        }

    payload = json.loads(relationship_path.read_text(encoding="utf-8"))
    payload.setdefault("version", 1)
    payload.setdefault("updated_at", None)
    payload.setdefault("provisional_bundle_ids", [])
    payload.setdefault("bundle_roles", [])
    payload.setdefault("relations", [])
    payload.setdefault("repair_prompt_queue", [])
    payload.setdefault("deferred_repair_bundle_ids", [])
    return payload


def index_bundle_relationships(payload: dict[str, Any]) -> dict[str, Any]:
    roles_by_bundle = {row["bundle_id"]: row for row in payload.get("bundle_roles", [])}

    relations_by_bundle: dict[str, list[dict[str, Any]]] = {}
    relations_by_other_bundle: dict[str, list[dict[str, Any]]] = {}
    for relation in payload.get("relations", []):
        relations_by_bundle.setdefault(relation["bundle_id"], []).append(relation)
        other_bundle_id = relation.get("other_bundle_id")
        if other_bundle_id:
            relations_by_other_bundle.setdefault(other_bundle_id, []).append(relation)

    return {
        "payload": payload,
        "provisional_bundle_ids": set(payload.get("provisional_bundle_ids", [])),
        "roles_by_bundle": roles_by_bundle,
        "relations_by_bundle": relations_by_bundle,
        "relations_by_other_bundle": relations_by_other_bundle,
    }
