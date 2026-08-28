"""
DR.Xmail — Local Message Bus (no external email, no AgentMail)
==============================================================
Agents and the operator (DR.X) exchange messages entirely inside the
ArabianFox workspace. No SMTP, no third-party mail service.

Messages are stored as JSON lines under:
    E:\\ArabianFox\\agents_mail\\messages\\<owner>\\inbox.jsonl

Each message:
    {"from": "...", "to": "...", "subject": "...", "body": "...", "ts": "..."}
"""

from __future__ import annotations

import os
import time
from typing import List, Dict, Any

BASE = r"E:\ArabianFox\agents_mail\messages"
OPERATOR = "DR.X"


def _inbox_path(owner: str) -> str:
    d = os.path.join(BASE, owner)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "inbox.jsonl")


def send(frm: str, to: str, subject: str, body: str) -> Dict[str, Any]:
    """Deliver a message locally to `to`'s inbox. Returns the message."""
    msg = {
        "from": frm,
        "to": to,
        "subject": subject,
        "body": body,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    path = _inbox_path(to)
    with open(path, "a", encoding="utf-8") as f:
        f.write(__import__("json").dumps(msg, ensure_ascii=False) + "\n")
    return msg


def inbox(owner: str) -> List[Dict[str, Any]]:
    """Read all messages in `owner`'s local inbox."""
    path = _inbox_path(owner)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(__import__("json").loads(line))
    return out


def clear(owner: str) -> None:
    path = _inbox_path(owner)
    if os.path.exists(path):
        os.remove(path)


if __name__ == "__main__":
    send("agent_01", OPERATOR, "test", "hello DR.X")
    print("inbox(DR.X):", inbox(OPERATOR))
