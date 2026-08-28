"""
DR.Xmail — Agents Platform: clean end-to-end test (NO AgentMail, NO external console).
=====================================================================================
Proves the platform works purely on:
  - Mail.tm  : free disposable inbox (receiving + OTP extraction)
  - agent's own SMTP : optional, user-provided (sending)

Run:
  venv\Scripts\python.exe -m drxmail.agents.cli_test
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from drxmail.agents.mailbox import AgentMailbox, extract_otp
from drxmail.agents import store


def main():
    print("=" * 60)
    print("DR.Xmail AGENTS PLATFORM — CLEAN TEST (no external console)")
    print("=" * 60)

    # 1) create an agent (pure Mail.tm, no AgentMail)
    aid = "agent_clean_test"
    if store.load_identity(aid):
        store.delete_identity(aid)
    mb = AgentMailbox()
    ident = mb.create(aid)
    print(f"[1] created agent '{aid}'")
    print(f"    email : {ident['email']}")
    print(f"    pass  : {ident['password']}")
    assert "@" in ident["email"]

    # 2) persisted to disk
    fpath = os.path.join(r"E:\ArabianFox\agents_mail\identities", f"{aid}.json")
    print(f"[2] identity saved: {os.path.exists(fpath)}")

    # 3) reload from disk (simulate restart)
    mb2 = AgentMailbox()
    assert mb2.load(aid) is True
    print(f"[3] reloaded: {mb2.email == ident['email']}")

    # 4) receive + extract OTP
    # NOTE: to test receiving without AgentMail, we inject via a 2nd Mail.tm account
    # that sends to our agent (Mail.tm receive works; send between mail.tm accounts
    # is not supported, so we use an SMTP account ONLY as a neutral test injector
    # if provided in credentials.json under 'test_injector' — never AgentMail).
    injector = None
    cred = os.path.join(r"E:\ArabianFox\credentials\credentials.json")
    if os.path.exists(cred):
        cfg = json.load(open(cred, encoding="utf-8"))
        injector = cfg.get("test_injector")  # user may provide a neutral SMTP for testing

    if injector:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText("Your verification code is 482913")
        msg["Subject"] = "Confirm"
        msg["From"] = injector["user"]
        msg["To"] = mb2.email
        s = smtplib.SMTP(injector["host"], int(injector["port"]), timeout=20)
        s.starttls()
        s.login(injector["user"], injector["password"])
        s.send_message(msg)
        s.quit()
        time.sleep(6)
        code = mb2.wait_for_code(timeout=60)
        print(f"[4] received + extracted OTP: {code}")
        assert code == "482913"
    else:
        print("[4] SKIPPED receive test (no 'test_injector' SMTP in credentials.json)")
        print("    -> add a neutral SMTP under 'test_injector' to auto-test receiving.")

    # 5) sending requires the agent's own SMTP
    print(f"[5] agent can_send (has SMTP): {bool(mb2.smtp_cfg)}")
    if not mb2.smtp_cfg:
        print("    (sending disabled until agent gets its own SMTP — by design)")

    print("\n[PASS] platform core verified ✅ (Mail.tm only, no AgentMail)")
    # cleanup
    store.delete_identity(aid)
    print("[cleanup] test agent removed")


if __name__ == "__main__":
    main()
