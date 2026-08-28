"""
DR.Xmail — Federated Node (decentralized inbox server)
========================================================
A minimal HTTP node that lets agents receive ActivityPub Notes from
other agents/nodes. Runs locally OR on any public host (Render, Railway,
a VPS...). No central server.

Endpoints (per agent):
  GET  /.well-known/webfinger?resource=acct:<id>@<host>  -> webfinger (Fediverse discovery)
  GET  /agents/<id>           -> actor document (with public key)
  GET  /agents/<id>/publickey -> raw public key (PEM)
  POST /agents/<id>/inbox     -> receive a Note (the "email")
  GET  /agents/<id>/outbox    -> list sent (optional)
  GET  /agents/<id>/messages  -> list received messages (for UI)

Messages are stored in:
  <BASE>/<id>/inbox.jsonl   (BASE from FEDIMAIL_DIR env, default ./fedimail)
"""

from __future__ import annotations

import os
import sys
import json
import uuid
import base64
from typing import Dict, Any, Optional

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from . import fedimail as fm
from . import signing

BASE = os.environ.get("FEDIMAIL_DIR", os.path.join(os.getcwd(), "fedimail"))


def _store_dir(agent_id: str) -> str:
    d = os.path.join(BASE, agent_id)
    os.makedirs(d, exist_ok=True)
    return d


def _inbox_path(agent_id: str) -> str:
    return os.path.join(_store_dir(agent_id), "inbox.jsonl")


def _key_path(agent_id: str) -> str:
    return os.path.join(_store_dir(agent_id), "key.pem")


def ensure_keypair(agent_id: str) -> Dict[str, str]:
    """Create (or load) an RSA keypair for an agent so it can be discovered
    and verified by external Fediverse nodes."""
    p = _key_path(agent_id)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            priv = f.read()
        pub = signing.private_to_public(priv)
        return {"private": priv, "public": pub}
    kp = signing.generate_keypair()
    with open(p, "w", encoding="utf-8") as f:
        f.write(kp["private"])
    return kp


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


def _node_base() -> str:
    """Public base URL of this node (used in actor ids)."""
    return os.environ.get("FEDIMAIL_BASE", "").rstrip("/")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: Any, ctype: str = "application/activity+json"):
        if isinstance(obj, (dict, list)):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        else:
            body = str(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _host(self) -> str:
        return self.headers.get("Host", "localhost")

    def _base(self) -> str:
        cfg = _node_base()
        if cfg:
            return cfg
        return f"http://{self._host()}"

    def do_GET(self):
        parts = urlparse(self.path)
        segs = [s for s in parts.path.split("/") if s]
        base = self._base()

        # WebFinger discovery (so external agents can resolve @id@host)
        if segs and segs[0] == ".well-known" and "webfinger" in segs:
            q = parse_qs(parts.query)
            res = q.get("resource", [""])[0]
            if res.startswith("acct:"):
                handle = res[len("acct:"):]
                aid = handle.split("@")[0]
                actor_id = fm.make_actor_id(aid, base)
                self._send(200, {
                    "subject": res,
                    "links": [{
                        "rel": "self",
                        "type": "application/activity+json",
                        "href": actor_id,
                    }],
                }, ctype="application/json")
                return

        if len(segs) >= 2 and segs[0] == "agents":
            aid = segs[1]
            if len(segs) == 2:
                kp = ensure_keypair(aid)
                self._send(200, fm.actor_doc(
                    fm.make_actor_id(aid, base),
                    f"{base}/agents/{aid}/inbox",
                    aid, public_key_pem=kp["public"]))
                return
            if segs[2] == "publickey":
                kp = ensure_keypair(aid)
                self._send(200, kp["public"], ctype="application/pem-key")
                return
            if segs[2] == "messages":
                self._send(200, {"agent": aid, "messages": load_messages(aid)},
                           ctype="application/json")
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
    """Run the federated node (blocking). PORT from env on Render."""
    port = int(os.environ.get("PORT", port))
    print(f"[fedinode] listening on http://{host}:{port}")
    HTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    run_node()
