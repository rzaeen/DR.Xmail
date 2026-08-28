"""
DR.Xmail — Federated Agent Mailbox
===================================
Wraps the decentralized ActivityPub mail for a single agent.

Each agent gets:
  - a local actor identity (node URL + inbox)
  - send(): POST an ActivityPub Note to another agent's inbox
  - receive(): read messages stored by the federated node
  - reply(): send a Note back to the original sender

No central server, no Gmail, no external console. Pure agent-to-agent.
"""

from __future__ import annotations

import sys
import os
import requests
from typing import Optional, Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json

from . import fedimail as fm
from . import fedinode


class FederatedAgent:
    def __init__(self, agent_id: str, node: str = "http://localhost:8000"):
        self.agent_id = agent_id
        self.node = node.rstrip("/")
        self.actor_id = fm.make_actor_id(agent_id, self.node)
        self.inbox_url = f"{self.node}/agents/{agent_id}/inbox"

    # ------------------------------------------------------------------ #
    def send(self, to_actor_id: str, to_inbox_url: str,
             subject: str, body: str) -> bool:
        """Send a decentralized Note to another agent's inbox."""
        activity = fm.make_note_activity(
            sender_id=self.actor_id,
            recipient_id=to_actor_id,
            recipient_inbox=to_inbox_url,
            subject=subject,
            body=body,
        )
        try:
            r = requests.post(
                to_inbox_url,
                json=activity,
                headers={"Content-Type": "application/activity+json"},
                timeout=20,
            )
            return r.status_code in (200, 201, 202)
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    def receive(self) -> List[Dict[str, Any]]:
        """Read messages delivered to this agent's local inbox."""
        return fedinode.load_messages(self.agent_id)

    # ------------------------------------------------------------------ #
    def reply(self, original_msg: Dict[str, Any], body: str,
              subject_prefix: str = "Re: ") -> bool:
        sender = original_msg.get("from", "")
        # need the sender's inbox URL; for our local network we can
        # derive it if same node, else caller must supply.
        if sender.startswith(self.node):
            uname = sender.rstrip("/").split("/agents/")[-1]
            to_inbox = f"{self.node}/agents/{uname}/inbox"
            subj = original_msg.get("subject", "")
            if not subj.startswith(subject_prefix.strip()):
                subj = subject_prefix + subj
            return self.send(sender, to_inbox, subj, body)
        # cross-node: attempt well-known inbox derivation not available;
        # require explicit inbox. For demo we just log.
        return False

    # ------------------------------------------------------------------ #
    def doc(self) -> Dict[str, Any]:
        return fm.actor_doc(self.actor_id, self.inbox_url, self.agent_id)

    def info(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "actor_id": self.actor_id,
            "inbox": self.inbox_url,
            "decentralized": True,
        }
