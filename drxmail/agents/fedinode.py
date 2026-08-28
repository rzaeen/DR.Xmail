"""
DR.Xmail — Federated Node (local inbox server, decentralized)
=============================================================
A minimal HTTP node that lets agents receive ActivityPub Notes from
other agents/nodes. Runs locally (or on any host). No central server.

Endpoints (per agent):
  GET  /agents/<id>           -> actor document
  POST /agents/<id>/inbox     -> receive a Note (the "email")
  GET  /agents/<id>/outbox    -> list sent (optional)
  GET  /agents/<id>/messages  -> list received messages (for UI)

Messages are stored in:
  E:\\ArabianFox\\agents_mail\\fedimail\\<id>\\inbox.jsonl
"""

from __future__ import annotations

import os
import json
import uuid
from typing import Dict, Any

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from . import fedimail as fm

BASE = r"E:\ArabianFox\agents_mail\fedimail"


def _store_dir(agent_id: str) -> str:
    d = os.path.join(BASE, agent_id)
    os.makedirs(d, exist_ok=True)
    return d


def _inbox_path(agent_id: str) -> str:
    return os.path.join(_store_dir(agent_id), "inbox.jsonl")


def save_message(agent_id: str, msg: Dict[str, Any]) -> None:
    with open(_inbox_path(agent_id), "a", encoding="utf-8") as f:
        f.write(json.dumps(msg, ensure_ascii=False) + "\n")


def load_messages(agent_id: str) -> list:
    path = _inbox_path(agent_id)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: Dict[str, Any]):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/activity+json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = urlparse(self.path)
        segs = [s for s in parts.path.split("/") if s]
        # /agents/<id> or /agents/<id>/messages
        if len(segs) >= 2 and segs[0] == "agents":
            aid = segs[1]
            if len(segs) == 2:
                self._send(200, fm.actor_doc(
                    fm.make_actor_id(aid, f"http://{self.headers.get('Host','localhost')}"),
                    f"http://{self.headers.get('Host','localhost')}/agents/{aid}/inbox",
                    aid))
                return
            if segs[2] == "messages":
                self._send(200, {"messages": load_messages(aid)})
                return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        parts = urlparse(self.path)
        segs = [s for s in parts.path.split("/") if s]
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            activity = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send(400, {"error": "bad json"})
            return
        if len(segs) >= 3 and segs[0] == "agents" and segs[2] == "inbox":
            aid = segs[1]
            msg = fm.parse_note(activity)
            if msg:
                save_message(aid, msg)
                self._send(202, {"accepted": True})
                return
        self._send(404, {"error": "no inbox"})

    def log_message(self, *a):
        pass


def run_node(host: str = "0.0.0.0", port: int = 8000):
    """Run the federated node (blocking)."""
    print(f"[fedinode] listening on http://{host}:{port}")
    HTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    run_node()
