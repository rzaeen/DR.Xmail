"""
DR.Xmail — Agents Platform UI (Streamlit)
==========================================
A dashboard to manage agent mailboxes: create, list, view inbox,
send mail, and watch OTP extraction — all per-agent and private.
"""

from __future__ import annotations

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

from drxmail.agents.mailbox import AgentMailbox, extract_otp, extract_link
from drxmail.agents import store

st.set_page_config(page_title="DR.Xmail — Agents Platform", layout="wide")
st.title("📧 DR.Xmail — منصة البريد للوكلاء")

# ---------------------------------------------------------------- sidebar
st.sidebar.header("الوكلاء (Agents)")
agents = store.list_agents()
agent_ids = list(agents.keys())

mode = st.sidebar.radio("الوضع", ["لوحة التحكم", "إنشاء وكيل", "صندوق الوارد", "إرسال", "التسجيل الآلي"])

if mode == "إنشاء وكيل":
    st.header("➕ إنشاء وكيل جديد")
    aid = st.text_input("معرّف الوكيل (agent_id)", "agent_01")
    with st.expander("إعداد الإرسال SMTP (اختياري)"):
        smtp_host = st.text_input("SMTP host", "smtp.gmail.com")
        smtp_port = st.number_input("SMTP port", 587)
        smtp_user = st.text_input("SMTP user (email)")
        smtp_pass = st.text_input("SMTP password / app password", type="password")
    if st.button("إنشاء"):
        mb = AgentMailbox()
        smtp = None
        if smtp_user and smtp_pass:
            smtp = {"host": smtp_host, "port": int(smtp_port),
                    "user": smtp_user, "password": smtp_pass}
        ident = mb.create(aid, smtp_cfg=smtp)
        st.success(f"تم إنشاء الوكيل {aid}")
        st.code(f"email: {ident['email']}\npassword: {ident['password']}")

elif mode == "لوحة التحكم":
    st.header("🎛️ لوحة التحكم")
    if not agent_ids:
        st.info("لا يوجد وكلاء بعد. أنشئ واحداً من القائمة الجانبية.")
    for aid in agent_ids:
        meta = agents[aid]
        st.markdown(f"**{aid}** — `{meta.get('email','')}` — provider: {meta.get('provider','')}")

elif mode == "صندوق الوارد":
    st.header("📥 صندوق الوارد")
    sel = st.selectbox("اختر وكيل", agent_ids) if agent_ids else None
    if sel:
        mb = AgentMailbox()
        if mb.load(sel):
            if st.button("🔄 تحديث"):
                st.experimental_rerun()
            msgs = mb.inbox()
            st.write(f"الإيميل: `{mb.email}` — عدد الرسائل: {len(msgs)}")
            for m in msgs:
                frm = m.get("from", {})
                if isinstance(frm, dict):
                    frm = frm.get("address", "")
                with st.expander(f"{m.get('subject','')} — {frm}"):
                    body = mb.read(m["id"])
                    st.text(body[:1000])
                    otp = extract_otp(body)
                    link = extract_link(body)
                    if otp:
                        st.success(f"🔑 OTP مستخرج: {otp}")
                    if link:
                        st.info(f"🔗 رابط: {link}")

elif mode == "إرسال":
    st.header("📤 إرسال من وكيل")
    sel = st.selectbox("من وكيل", agent_ids) if agent_ids else None
    if sel:
        mb = AgentMailbox()
        if not mb.load(sel):
            st.error("تعذّر التحميل")
        else:
            to = st.text_input("إلى (to)")
            subj = st.text_input("الموضوع", "Hello from DR.Xmail agent")
            body = st.text_area("النص")
            if st.button("إرسال"):
                if not mb.smtp_cfg:
                    st.error("هذا الوكيل ليس لديه إعداد SMTP — لا يمكن الإرسال.")
                else:
                    try:
                        ok = mb.send(to, subj, body)
                        st.success("تم الإرسال ✅" if ok else "فشل الإرسال")
                    except Exception as e:
                        st.error(repr(e))

elif mode == "التسجيل الآلي":
    st.header("🤖 التسجيل الآلي")
    sel = st.selectbox("وكيل البريد", agent_ids) if agent_ids else None
    platform = st.selectbox("المنصة", ["github", "discord", "instagram"])
    if sel and st.button("ابدأ التسجيل"):
        sys.path.insert(0, r"E:\ArabianFox\agent")
        from drxmail.register.auto_register import Registrar
        mb = AgentMailbox()
        mb.load(sel)
        reg = Registrar(platform=platform, headless=False)
        result = reg.run(
            email=mb.email,
            password=mb.password + "Aa1!",
            username=sel.replace("_", ""),
            otp_getter=lambda: mb.wait_for_code(timeout=120),
        )
        st.json(result)

st.sidebar.markdown("---")
st.sidebar.caption("DR.Xmail · ArabianFox · كل وكيل إيميله الخاص المحفوظ محلياً")
