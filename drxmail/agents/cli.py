"""
DR.Xmail — Agents CLI
=====================
Manage agent mailboxes from the terminal.

Examples:
  python -m drxmail.agents.cli create agent_01
  python -m drxmail.agents.cli list
  python -m drxmail.agents.cli inbox agent_01
  python -m drxmail.agents.cli send agent_01 --to a@b.com --subject hi --body hello
  python -m drxmail.agents.cli delete agent_01
"""

from __future__ import annotations

import sys
import argparse
import json

from .mailbox import AgentMailbox
from . import store


def cmd_create(args):
    mb = AgentMailbox()
    smtp = None
    if args.smtp:
        smtp = json.loads(args.smtp)
    ident = mb.create(args.agent_id, smtp_cfg=smtp)
    print(f"[created] agent={args.agent_id}")
    print(f"  email : {ident['email']}")
    print(f"  pass   : {ident['password']}")
    print(f"  saved  : E:\\ArabianFox\\agents_mail\\identities\\{args.agent_id}.json")


def cmd_list(args):
    agents = store.list_agents()
    if not agents:
        print("(no agents yet)")
        return
    for aid, meta in agents.items():
        print(f"  - {aid:20s} {meta.get('email',''):30s} [{meta.get('provider','')}]")


def cmd_inbox(args):
    mb = AgentMailbox()
    if not mb.load(args.agent_id):
        print(f"[error] agent '{args.agent_id}' not found")
        return
    msgs = mb.inbox()
    print(f"[inbox] {mb.email} — {len(msgs)} message(s)")
    for m in msgs:
        frm = m.get("from", {})
        if isinstance(frm, dict):
            frm = frm.get("address", "")
        print(f"  - {m.get('id')[:12]} | {frm} | {m.get('subject','')}")


def cmd_send(args):
    mb = AgentMailbox()
    if not mb.load(args.agent_id):
        print(f"[error] agent '{args.agent_id}' not found")
        return
    if not mb.smtp_cfg:
        print("[error] this agent has no SMTP config (cannot send)")
        return
    ok = mb.send(args.to, args.subject, args.body)
    print(f"[sent] -> {args.to}: {'OK' if ok else 'FAILED'}")


def cmd_delete(args):
    ok = store.delete_identity(args.agent_id)
    print(f"[deleted] {args.agent_id}: {'OK' if ok else 'not found'}")


def build_parser():
    p = argparse.ArgumentParser(prog="agents", description="DR.Xmail agent mailboxes")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="create a new agent mailbox")
    c.add_argument("agent_id")
    c.add_argument("--smtp", help='JSON smtp cfg {"host","port","user","password"}')
    c.set_defaults(func=cmd_create)

    l = sub.add_parser("list", help="list agents")
    l.set_defaults(func=cmd_list)

    i = sub.add_parser("inbox", help="show inbox")
    i.add_argument("agent_id")
    i.set_defaults(func=cmd_inbox)

    s = sub.add_parser("send", help="send mail")
    s.add_argument("agent_id")
    s.add_argument("--to", required=True)
    s.add_argument("--subject", required=True)
    s.add_argument("--body", required=True)
    s.set_defaults(func=cmd_send)

    d = sub.add_parser("delete", help="delete agent")
    d.add_argument("agent_id")
    d.set_defaults(func=cmd_delete)
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
