"""
DR.Xmail — Federated Mail (ActivityPub, decentralized)
=====================================================
Pure peer-to-peer agents mail over ActivityPub. No central server,
no Gmail, no external console. Each agent is an "actor" (user) on a
node; messages are JSON ActivityPub Notes delivered over HTTP.

How it works (decentralized):
  - Each agent has a local actor identity stored in its identity file.
  - To send, the agent POSTs an ActivityPub "Create/Note" to the
    recipient actor's inbox URL.
  - To receive, the agent runs a tiny local inbox server (or shares a
    node) that accepts incoming Notes.

This is a minimal, dependency-free implementation suitable for
agent-to-agent messaging on a local network or across nodes.

Actor identity (stored per agent):
  {
    "actor_id": "agent_01",
    "preferred_username": "agent_01",
    "inbox_url": "http://<host>:<port>/agents/agent_01/inbox",
    "node": "http://localhost:8000"   # this agent's node base URL
  }
"""

from __future__ import annotations

import json
import time
import uuid
import hashlib
from typing import Dict, Any, List, Optional


def make_actor_id(username: str, node: str) -> str:
    node = node.rstrip("/")
    return f"{node}/agents/{username}"


def make_note_activity(sender_id: str, recipient_id: str,
                       recipient_inbox: str, subject: str, body: str) -> Dict[str, Any]:
    """Build an ActivityPub Create/Note activity (the "email")."""
    note_id = f"{sender_id}#note-{uuid.uuid4().hex[:12]}"
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{sender_id}#activity-{uuid.uuid4().hex[:12]}",
        "type": "Create",
        "actor": sender_id,
        "to": [recipient_id],
        "object": {
            "id": note_id,
            "type": "Note",
            "attributedTo": sender_id,
            "to": [recipient_id],
            "summary": subject,        # like an email subject
            "content": body,           # the email body
            "published": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "recipient_inbox": recipient_inbox,
    }


def parse_note(activity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract a readable message from an incoming activity."""
    obj = activity.get("object", {})
    if obj.get("type") != "Note":
        return None
    return {
        "from": activity.get("actor", ""),
        "to": obj.get("to", []),
        "subject": obj.get("summary", ""),
        "body": obj.get("content", ""),
        "ts": obj.get("published", ""),
        "id": obj.get("id", ""),
    }


def actor_doc(actor_id: str, inbox_url: str, username: str,
              public_key_pem: str = "") -> Dict[str, Any]:
    """Standard ActivityPub actor description (served at /agents/<id>)."""
    doc = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            {"publicKey": {
                "id": "#main-key",
                "type": "Key",
                "owner": actor_id,
                "publicKeyPem": public_key_pem,
            }},
        ],
        "id": actor_id,
        "type": "Person",
        "preferredUsername": username,
        "inbox": inbox_url,
        "outbox": inbox_url.replace("/inbox", "/outbox"),
    }
    if public_key_pem:
        doc["publicKey"] = {
            "id": f"{actor_id}#main-key",
            "type": "Key",
            "owner": actor_id,
            "publicKeyPem": public_key_pem,
        }
    return doc


def fingerprint(actor_id: str) -> str:
    """Deterministic short id (no crypto needed for local trust)."""
    return hashlib.sha256(actor_id.encode()).hexdigest()[:16]
