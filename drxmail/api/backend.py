"""
DR.Xmail — Backend API (FastAPI)
=================================
Serves the agents mail platform over HTTP so it can run on a free cloud
server (Render/Railway) and deliver mail to real inboxes via Brevo SMTP.

Endpoints:
  POST /agents            -> create agent (returns email+password)
  GET  /agents            -> list agents
  GET  /agents/{id}/inbox -> inbox
  POST /agents/{id}/send  -> send mail (via agent's SMTP/Brevo config)
  GET  /agents/{id}/otp   -> poll for OTP
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from drxmail.agents.mailbox import AgentMailbox
from drxmail.agents import store

app = FastAPI(title="DR.Xmail Agents Platform")


class CreateReq(BaseModel):
    agent_id: str
    smtp_cfg: dict = {}


class SendReq(BaseModel):
    to: str
    subject: str
    body: str


@app.post("/agents")
def create_agent(req: CreateReq):
    if store.load_identity(req.agent_id):
        raise HTTPException(409, "agent already exists")
    mb = AgentMailbox()
    ident = mb.create(req.agent_id, smtp_cfg=req.smtp_cfg)
    return {"agent_id": req.agent_id, "email": ident["email"],
            "password": ident["password"]}


@app.get("/agents")
def list_agents():
    return store.list_agents()


@app.get("/agents/{agent_id}/inbox")
def inbox(agent_id: str):
    mb = AgentMailbox()
    if not mb.load(agent_id):
        raise HTTPException(404, "agent not found")
    return mb.inbox()


@app.post("/agents/{agent_id}/send")
def send(agent_id: str, req: SendReq):
    mb = AgentMailbox()
    if not mb.load(agent_id):
        raise HTTPException(404, "agent not found")
    if not mb.smtp_cfg:
        raise HTTPException(400, "agent has no SMTP/Brevo sender configured")
    ok = mb.send(req.to, req.subject, req.body)
    return {"sent": ok}


@app.get("/agents/{agent_id}/otp")
def otp(agent_id: str, timeout: int = 120):
    mb = AgentMailbox()
    if not mb.load(agent_id):
        raise HTTPException(404, "agent not found")
    return {"otp": mb.wait_for_code(timeout=timeout)}


@app.get("/")
def root():
    return {"service": "DR.Xmail Agents Platform", "status": "ok"}
