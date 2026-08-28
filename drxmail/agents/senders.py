"""
DR.Xmail — Sender base class + factory
=======================================
Outbound email is delegated to a "sender" backend. Each agent can have its
own sender config (kept in its private identity file), so different agents
can send through different accounts. No DR.Xmail-owned console required.

Backends:
  - "smtp"   : user-provided generic SMTP (Gmail/Outlook/any)
  - "brevo"  : Brevo free SMTP relay (DKIM-signed, Gmail-deliverable)
  - "none"   : no sending (receiving/OTP only)
"""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from typing import Optional, Dict, Any


class Sender:
    """Base sender. Subclass and implement send()."""

    name = "base"

    def send(self, frm: str, to: str, subject: str, body: str) -> bool:
        raise NotImplementedError


class SMTPSender(Sender):
    name = "smtp"

    def __init__(self, cfg: Dict[str, Any]):
        self.host = cfg.get("host", "smtp.gmail.com")
        self.port = int(cfg.get("port", 587))
        self.user = cfg.get("user", "")
        self.password = cfg.get("password", "")
        self.use_ssl = bool(cfg.get("use_ssl", False))

    def send(self, frm: str, to: str, subject: str, body: str) -> bool:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = frm
        msg["To"] = to
        if self.use_ssl:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=20) as s:
                if self.user and self.password:
                    s.login(self.user, self.password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(self.host, self.port, timeout=20) as s:
                s.starttls()
                if self.user and self.password:
                    s.login(self.user, self.password)
                s.send_message(msg)
        return True


class NullSender(Sender):
    name = "none"

    def send(self, frm: str, to: str, subject: str, body: str) -> bool:
        return False


def get_sender(cfg: Optional[Dict[str, Any]]) -> Sender:
    if not cfg:
        return NullSender()
    backend = cfg.get("backend", "smtp")
    if backend == "smtp":
        return SMTPSender(cfg)
    return NullSender()
