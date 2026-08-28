"""
DR.Xmail — app.py
================
Streamlit dashboard for the DR.Xmail email + automation engine.

Features:
  - Create a disposable email (Mail.tm) or use AgentMail inbox
  - Live inbox viewer (auto-refresh)
  - Send email (AgentMail SMTP)
  - Auto-extract OTP / activation link from latest message
  - One-click automated registration on GitHub / Discord / Instagram
  - Live system logs

Run:  streamlit run drxmail/ui/app.py
"""

from __future__ import annotations

import sys
import os
import time
import json
import threading

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from drxmail.core.core_mail import (  # noqa: E402
    get_provider,
    extract_otp,
    extract_link,
    wait_for_code,
    wait_for_link,
)

try:
    from drxmail.register.auto_register import Registrar  # noqa: E402
except Exception:
    Registrar = None

# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------
if "provider" not in st.session_state:
    st.session_state.provider = None
if "logs" not in st.session_state:
    st.session_state.logs = []


def log(msg: str):
    st.session_state.logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    if len(st.session_state.logs) > 200:
        st.session_state.logs = st.session_state.logs[-200:]


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
st.set_page_config(page_title="DR.Xmail", layout="wide")
st.title("📧 DR.Xmail — Agent Email & Automation Engine")

backend = st.sidebar.selectbox("Email Backend", ["mailtm", "agentmail"])
st.sidebar.markdown("---")

if st.sidebar.button("🆕 Create New Email"):
    try:
        prov = get_provider(backend)
        acc = prov.create_account()
        st.session_state.provider = prov
        st.session_state.backend = backend
        log(f"Created inbox: {prov.address}")
        st.sidebar.success(f"✅ {prov.address}")
    except Exception as e:
        log(f"ERROR creating inbox: {repr(e)[:200]}")
        st.sidebar.error("Failed to create inbox (see logs)")

current_addr = st.session_state.provider.address if st.session_state.provider else "—"
st.sidebar.info(f"**Current inbox:**\n{current_addr}")

# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📥 Inbox", "📤 Send", "🤖 Auto-Register", "📜 Logs"])

# --- Inbox ---
with tab1:
    st.header("Inbox")
    if st.button("🔄 Refresh"):
        log("Inbox refreshed")
    if st.session_state.provider:
        try:
            msgs = st.session_state.provider.get_messages()
            if not msgs:
                st.info("No messages yet.")
            for m in msgs:
                mid = m.get("id") if isinstance(m, dict) else m
                subj = m.get("subject", "(no subject)") if isinstance(m, dict) else "(message)"
                with st.expander(f"📨 {subj}"):
                    body = st.session_state.provider.get_message_body(mid)
                    st.text_area("Body", body[:3000], height=200, key=f"body_{mid}")
                    col1, col2 = st.columns(2)
                    col1.metric("OTP", extract_otp(body) or "—")
                    col2.markdown(f"[Activation Link]({extract_link(body) or '#'})")
        except Exception as e:
            st.error(f"Inbox error: {repr(e)[:200]}")
    else:
        st.warning("Create an inbox first (sidebar).")

# --- Send ---
with tab2:
    st.header("Send Email (AgentMail SMTP)")
    to = st.text_input("To")
    subject = st.text_input("Subject", "Hello from DR.Xmail")
    body = st.text_area("Body", "أنا موجود")
    if st.button("📤 Send"):
        if not st.session_state.provider:
            st.error("No inbox selected.")
        else:
            try:
                ok = st.session_state.provider.send(to, subject, body)
                if ok:
                    log(f"Sent mail to {to}")
                    st.success("✅ Sent")
                else:
                    st.error("Send returned False")
            except Exception as e:
                log(f"Send error: {repr(e)[:200]}")
                st.error(repr(e)[:200])

# --- Auto-Register ---
with tab3:
    st.header("Automated Registration")
    if Registrar is None:
        st.error("auto_register module failed to load.")
    else:
        platform = st.selectbox("Platform", ["github", "discord", "instagram"])
        reg_password = st.text_input("Account Password", type="password")
        reg_username = st.text_input("Username (optional)")
        if st.button("🚀 Start Registration"):
            if not st.session_state.provider:
                st.error("Create an inbox first.")
            elif not reg_password:
                st.error("Enter a password.")
            else:
                log(f"Starting {platform} registration for {st.session_state.provider.address}...")
                prov = st.session_state.provider

                def otp_getter():
                    return wait_for_code(prov, timeout=120)

                try:
                    r = Registrar(platform=platform, headless=False)
                    res = r.run(
                        email=prov.address,
                        password=reg_password,
                        username=reg_username,
                        otp_getter=otp_getter,
                    )
                    log(f"Result: {json.dumps(res, ensure_ascii=False)[:300]}")
                    st.json(res)
                except Exception as e:
                    log(f"Registration error: {repr(e)[:200]}")
                    st.error(repr(e)[:300])

# --- Logs ---
with tab4:
    st.header("System Logs")
    st.text_area("Live Logs", "\n".join(st.session_state.logs), height=400, key="logbox")
