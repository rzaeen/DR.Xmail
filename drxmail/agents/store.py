"""
DR.Xmail — Agent Identity Store
================================
Persists each agent's own email + password + provider locally and securely.

Every agent gets a private identity file:
    E:\ArabianFox\agents_mail\identities\<agent_id>.json
    {
      "agent_id": "agent_01",
      "email": "xxxx@emalupe.com",
      "password": "....",
      "provider": "mailtm",
      "created_at": "...",
      "smtp": {...}            # optional sending config for this agent
    }

A registry index is kept at:
    E:\ArabianFox\agents_mail\identities\index.json
"""

from __future__ import annotations

import os
import json
import time
from typing import Optional, Dict, Any

BASE = r"E:\ArabianFox\agents_mail"
IDENTITIES_DIR = os.path.join(BASE, "identities")
INDEX_PATH = os.path.join(IDENTITIES_DIR, "index.json")

os.makedirs(IDENTITIES_DIR, exist_ok=True)


def _load_index() -> Dict[str, Any]:
    if not os.path.exists(INDEX_PATH):
        return {}
    try:
        return json.load(open(INDEX_PATH, encoding="utf-8"))
    except Exception:
        return {}


def _save_index(idx: Dict[str, Any]) -> None:
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)


def save_identity(agent_id: str, identity: Dict[str, Any]) -> str:
    """Persist an agent's private email identity. Returns the file path."""
    identity["agent_id"] = agent_id
    identity.setdefault("created_at", time.strftime("%Y-%m-%d %H:%M:%S"))
    path = os.path.join(IDENTITIES_DIR, f"{agent_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(identity, f, ensure_ascii=False, indent=2)
    # update registry index (no secrets in index, just mapping)
    idx = _load_index()
    idx[agent_id] = {
        "email": identity.get("email", ""),
        "provider": identity.get("provider", ""),
        "created_at": identity.get("created_at", ""),
        "file": path,
    }
    _save_index(idx)
    return path


def load_identity(agent_id: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(IDENTITIES_DIR, f"{agent_id}.json")
    if not os.path.exists(path):
        return None
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


def list_agents() -> Dict[str, Any]:
    return _load_index()


def delete_identity(agent_id: str) -> bool:
    path = os.path.join(IDENTITIES_DIR, f"{agent_id}.json")
    if os.path.exists(path):
        os.remove(path)
        idx = _load_index()
        idx.pop(agent_id, None)
        _save_index(idx)
        return True
    return False


if __name__ == "__main__":
    print("Identities dir:", IDENTITIES_DIR)
    print("Current agents:", list(list_agents().keys()))
