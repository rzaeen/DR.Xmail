"""
DR.Xmail — core_mail.py
=========================
Email Core Engine for AI Agents (fully open / no external console).

Primary backend:
  - "mailtm"  -> free disposable mail via https://mail.tm (no API key)
                Used for: account creation, inbox polling, OTP extraction,
                and activation-link extraction.

Sending:
  - Mail.tm instances generally do NOT support outbound send.
  - For sending, the engine uses a USER-PROVIDED SMTP account
    (Gmail / Outlook / any provider) configured in credentials.json.
    No DR.Xmail-owned console or API key is required.

All functions are backend-agnostic via the MailProvider interface.
"""

from __future__ import annotations

import re
import time
import random
import string
import json
import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional, Callable

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MAILTM_BASE = "https://api.mail.tm"
USER_AGENT = "DR.Xmail/1.0 (+https://github.com/ArabianFox/drxmail)"

# user-provided SMTP (for sending) — optional, no DR.Xmail console needed
_SMTP = {}
_cred_path = r"E:\ArabianFox\credentials\credentials.json"
if os.path.exists(_cred_path):
    try:
        _cfg = json.load(open(_cred_path, encoding="utf-8"))
        _SMTP = _cfg.get("smtp_send", {})
    except Exception:
        _SMTP = {}


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------
_OTP_RE = re.compile(r"\b(\d{4,8})\b")
_LINK_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_ACTIVATION_RE = re.compile(
    r"(https?://[^\s\"'<>]*(?:confirm|verify|activate|token|verify-email|auth)[^\s\"'<>]*)",
    re.IGNORECASE,
)


def random_string(n: int = 10) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def extract_otp(text: str) -> Optional[str]:
    """Return the first plausible OTP (4-8 digits) from text."""
    if not text:
        return None
    m = _OTP_RE.search(text)
    return m.group(1) if m else None


def extract_link(text: str) -> Optional[str]:
    """Return the first activation-style link, else any link."""
    if not text:
        return None
    m = _ACTIVATION_RE.search(text)
    if m:
        return m.group(1)
    m = _LINK_RE.search(text)
    return m.group(0) if m else None


def extract_links(text: str):
    return _LINK_RE.findall(text or "")


# ---------------------------------------------------------------------------
# Base provider
# ---------------------------------------------------------------------------
class MailProvider:
    def __init__(self):
        self.address = ""
        self.password = ""

    def create_account(self, username: Optional[str] = None) -> dict:
        raise NotImplementedError

    def get_messages(self) -> list:
        raise NotImplementedError

    def get_message_body(self, msg_id: str) -> str:
        raise NotImplementedError

    def send(self, to: str, subject: str, body: str) -> bool:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Mail.tm backend (free, no key) — primary for receiving / OTP
# ---------------------------------------------------------------------------
class MailTmProvider(MailProvider):
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        self.token = ""
        self.account_id = ""

    def create_account(self, username: Optional[str] = None) -> dict:
        r = self.session.get(f"{MAILTM_BASE}/domains", timeout=20)
        r.raise_for_status()
        dom_json = r.json()
        members = dom_json if isinstance(dom_json, list) else dom_json.get("hydra:member", [])
        domain = None
        for m in members:
            if isinstance(m, dict) and m.get("isActive") and m.get("domain"):
                domain = m["domain"]
                break
        if not domain and members:
            domain = members[0].get("domain") if isinstance(members[0], dict) else None
        if not domain:
            raise RuntimeError("No available domain from mail.tm")
        if not username:
            username = random_string(12)
        address = f"{username}@{domain}"
        password = random_string(16)
        r = self.session.post(
            f"{MAILTM_BASE}/accounts",
            json={"address": address, "password": password},
            timeout=20,
        )
        r.raise_for_status()
        self.address = address
        self.password = password
        self.account_id = r.json().get("id", "")
        # login for token
        r = self.session.post(
            f"{MAILTM_BASE}/token",
            json={"address": address, "password": password},
            timeout=20,
        )
        r.raise_for_status()
        self.token = r.json().get("token", "")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        return {"address": address, "password": password}

    def get_messages(self) -> list:
        r = self.session.get(f"{MAILTM_BASE}/messages", timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return data.get("hydra:member", [])

    def get_message_body(self, msg_id: str) -> str:
        r = self.session.get(f"{MAILTM_BASE}/messages/{msg_id}", timeout=20)
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

        parts = [_as_str(data.get("text")), _as_str(data.get("html"))]
        return "\n".join(p for p in parts if p)

    def send(self, to: str, subject: str, body: str) -> bool:
        # Mail.tm generally does not support outbound send.
        # Fall back to user-provided SMTP if configured.
        if _SMTP:
            return _send_via_smtp(self.address or _SMTP.get("user", ""), to, subject, body, _SMTP)
        return False


# ---------------------------------------------------------------------------
# User SMTP sender (no DR.Xmail console; uses the user's own mail account)
# ---------------------------------------------------------------------------
def _send_via_smtp(frm: str, to: str, subject: str, body: str, cfg: dict) -> bool:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = frm
    msg["To"] = to
    host = cfg.get("host", "smtp.gmail.com")
    port = int(cfg.get("port", 587))
    user = cfg.get("user", frm)
    pwd = cfg.get("password", "")
    with smtplib.SMTP(host, port, timeout=20) as s:
        s.starttls()
        if user and pwd:
            s.login(user, pwd)
        s.send_message(msg)
    return True


def send_mail(to: str, subject: str, body: str, frm: str = "", cfg: Optional[dict] = None) -> bool:
    """Send mail using user-provided SMTP config (no external console)."""
    c = cfg or _SMTP
    if not c:
        raise RuntimeError(
            "No SMTP config. Add 'smtp_send' to credentials.json "
            "(your own Gmail/Outlook account)."
        )
    return _send_via_smtp(frm or c.get("user", ""), to, subject, body, c)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_provider(backend: str = "mailtm") -> MailProvider:
    """Only mail.tm is bundled (free, no key). Sending uses user SMTP."""
    return MailTmProvider()


# ---------------------------------------------------------------------------
# OTP / link waiters
# ---------------------------------------------------------------------------
def wait_for_code(provider: MailProvider, timeout: int = 120, poll: int = 5,
                  subject_filter: Optional[Callable[[str], bool]] = None) -> Optional[str]:
    """Poll inbox until a message arrives, return extracted OTP."""
    seen = set()
    deadline = time.time() + timeout
    while time.time() < deadline:
        msgs = provider.get_messages()
        for m in msgs:
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
                    body = provider.get_message_body(mid)
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


def wait_for_link(provider: MailProvider, timeout: int = 120, poll: int = 5) -> Optional[str]:
    seen = set()
    deadline = time.time() + timeout
    while time.time() < deadline:
        msgs = provider.get_messages()
        for m in msgs:
            mid = m.get("id")
            if mid in seen:
                continue
            seen.add(mid)
            body = ""
            for _ in range(3):
                try:
                    body = provider.get_message_body(mid)
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


if __name__ == "__main__":
    p = get_provider("mailtm")
    acc = p.create_account()
    print("CREATED:", acc)
    print("OTP test:", extract_otp("Your code is 482913"))
    print("LINK test:", extract_link("Click https://x.com/confirm?t=abc to verify"))
