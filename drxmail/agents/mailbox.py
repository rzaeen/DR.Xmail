"""
DR.Xmail — AgentMailbox
=======================
The per-agent email engine. Each agent owns a private mailbox:
  - create()      : generate a fresh email + password, persist to store
  - load(agent_id): restore an existing agent's mailbox from disk
  - inbox()       : list messages
  - read(msg_id)  : read a message body
  - send(to,...)  : send mail (via the agent's own sender config)
  - reply(msg_id): reply to a message automatically
  - wait_for_code(): poll inbox for OTP

Receiving uses mail.tm (free, no key). Sending uses the agent's own
SMTP config (pluggable). Each agent's email+password is stored privately.
"""

from __future__ import annotations

import time
import random
import string
import requests
from typing import Optional, Callable, Dict, Any, List

from . import store
from .senders import get_sender, Sender

MAILTM_BASE = "https://api.mail.tm"
USER_AGENT = "DR.Xmail-Agent/1.0 (+https://github.com/ArabianFox/drxmail)"

_OTP_RE = __import__("re").compile(r"\b(\d{4,8})\b")
_LINK_RE = __import__("re").compile(
    r"(https?://[^\s\"'<>]*(?:confirm|verify|activate|token|verify-email|auth)[^\s\"'<>]*)",
    __import__("re").IGNORECASE,
)


def random_string(n: int = 12) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def extract_otp(text: str) -> Optional[str]:
    if not text:
        return None
    m = _OTP_RE.search(text)
    return m.group(1) if m else None


def extract_link(text: str) -> Optional[str]:
    if not text:
        return None
    m = _LINK_RE.search(text)
    return m.group(1) if m else None


class AgentMailbox:
    def __init__(self, agent_id: str = "", provider: str = "mailtm"):
        self.agent_id = agent_id
        self.provider = provider
        self.email = ""
        self.password = ""
        self.smtp_cfg: Dict[str, Any] = {}
        self._sess: Optional[requests.Session] = None
        self._token = ""

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    def create(self, agent_id: str, smtp_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a brand-new email identity for an agent and persist it."""
        self.agent_id = agent_id
        self.smtp_cfg = smtp_cfg or {}
        acc = self._create_mailtm_account()
        self.email = acc["address"]
        self.password = acc["password"]
        identity = {
            "agent_id": agent_id,
            "email": self.email,
            "password": self.password,
            "provider": "mailtm",
            "smtp": self.smtp_cfg,
        }
        store.save_identity(agent_id, identity)
        return identity

    def load(self, agent_id: str) -> bool:
        """Load an existing agent's mailbox from the store."""
        ident = store.load_identity(agent_id)
        if not ident:
            return False
        self.agent_id = agent_id
        self.email = ident.get("email", "")
        self.password = ident.get("password", "")
        self.provider = ident.get("provider", "mailtm")
        self.smtp_cfg = ident.get("smtp", {})
        self._login_mailtm()
        return True

    def exists(self, agent_id: str) -> bool:
        return store.load_identity(agent_id) is not None

    # ------------------------------------------------------------------ #
    # mail.tm primitives
    # ------------------------------------------------------------------ #
    def _session(self) -> requests.Session:
        if self._sess is None:
            self._sess = requests.Session()
            self._sess.headers.update(
                {"User-Agent": USER_AGENT, "Accept": "application/json"}
            )
        return self._sess

    def _create_mailtm_account(self) -> Dict[str, str]:
        s = self._session()
        dj = s.get(f"{MAILTM_BASE}/domains", timeout=20).json()
        members = dj if isinstance(dj, list) else dj.get("hydra:member", [])
        domain = next(
            (m["domain"] for m in members if isinstance(m, dict) and m.get("domain")),
            None,
        )
        if not domain:
            raise RuntimeError("No domain available from mail.tm")
        address = f"{random_string(12)}@{domain}"
        password = random_string(16)
        r = s.post(f"{MAILTM_BASE}/accounts",
                   json={"address": address, "password": password}, timeout=20)
        r.raise_for_status()
        self._token = s.post(f"{MAILTM_BASE}/token",
                             json={"address": address, "password": password},
                             timeout=20).json().get("token", "")
        s.headers.update({"Authorization": f"Bearer {self._token}"})
        return {"address": address, "password": password}

    def _login_mailtm(self) -> None:
        s = self._session()
        r = s.post(f"{MAILTM_BASE}/token",
                   json={"address": self.email, "password": self.password}, timeout=20)
        if r.status_code == 200:
            self._token = r.json().get("token", "")
            s.headers.update({"Authorization": f"Bearer {self._token}"})

    # ------------------------------------------------------------------ #
    # inbox
    # ------------------------------------------------------------------ #
    def inbox(self) -> List[Dict[str, Any]]:
        s = self._session()
        r = s.get(f"{MAILTM_BASE}/messages", timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return data.get("hydra:member", [])

    def read(self, msg_id: str) -> str:
        s = self._session()
        r = s.get(f"{MAILTM_BASE}/messages/{msg_id}", timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            data = data[0]

        def _as_str(v):
            if v is None:
                return ""
            if isinstance(v, list):
                return "\n".join(str(x) for x in v)
            return str(v)

        return "\n".join(p for p in [_as_str(data.get("text")),
                                     _as_str(data.get("html"))] if p)

    # ------------------------------------------------------------------ #
    # sending + replying (via the agent's own SMTP)
    # ------------------------------------------------------------------ #
    def send(self, to: str, subject: str, body: str) -> bool:
        sender: Sender = get_sender(self.smtp_cfg)
        if not self.smtp_cfg:
            raise RuntimeError(
                f"Agent '{self.agent_id}' has no SMTP config. "
                "Add 'smtp' to its identity to enable sending."
            )
        # The envelope sender must be the SMTP account (not the mail.tm address)
        frm = self.smtp_cfg.get("user") or self.smtp_cfg.get("from") or self.email
        return sender.send(frm, to, subject, body)

    def reply(self, msg_id: str, body: str,
              subject_prefix: str = "Re: ") -> bool:
        msgs = self.inbox()
        target = next((m for m in msgs if m.get("id") == msg_id), None)
        if not target:
            return False
        to_addr = target.get("from", {})
        if isinstance(to_addr, dict):
            to_addr = to_addr.get("address", "")
        subj = target.get("subject", "")
        if not subj.startswith(subject_prefix.strip()):
            subj = subject_prefix + subj
        return self.send(to_addr, subj, body)

    # ------------------------------------------------------------------ #
    # OTP / link waiters
    # ------------------------------------------------------------------ #
    def wait_for_code(self, timeout: int = 120, poll: int = 5,
                      subject_filter: Optional[Callable[[str], bool]] = None) -> Optional[str]:
        seen = set()
        deadline = time.time() + timeout
        while time.time() < deadline:
            for m in self.inbox():
                mid = m.get("id")
                if mid in seen:
                    continue
                seen.add(mid)
                subj = m.get("subject", "") or ""
                if subject_filter and not subject_filter(subj):
                    continue
                body = ""
                for _ in range(3):
                    try:
                        body = self.read(mid)
                        if body:
                            break
                    except Exception:
                        pass
                    time.sleep(1)
                code = extract_otp(body)
                if code:
                    return code
            time.sleep(poll)
        return None

    def wait_for_link(self, timeout: int = 120, poll: int = 5) -> Optional[str]:
        seen = set()
        deadline = time.time() + timeout
        while time.time() < deadline:
            for m in self.inbox():
                mid = m.get("id")
                if mid in seen:
                    continue
                seen.add(mid)
                body = ""
                for _ in range(3):
                    try:
                        body = self.read(mid)
                        if body:
                            break
                    except Exception:
                        pass
                    time.sleep(1)
                link = extract_link(body)
                if link:
                    return link
            time.sleep(poll)
        return None

    def info(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "email": self.email,
            "provider": self.provider,
            "can_send": bool(self.smtp_cfg),
        }
