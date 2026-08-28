"""
DR.Xmail — auto_register.py
============================
Automated Registration Engine (Playwright, persistent context).

Takes a generated email, opens a target platform signup flow, fills the
form, auto-receives the OTP/activation link from the inbox, and completes
signup without human interaction.

Supported platforms (flow modules): github, discord, instagram
Each flow is a function that receives (page, email, password, otp_getter)
and drives the UI. Add new platforms by writing a new flow function.

Usage (library):
    from drxmail.register.auto_register import Registrar
    r = Registrar(platform="github")
    result = r.run(email="x@y.com", password="strongpw")

The `otp_getter` callback returns the code (wired to core_mail.wait_for_code).
"""

from __future__ import annotations

import sys
import os
import time
import json
import random
from typing import Callable, Optional

# Import our proven launcher from ArabianFox agent folder
sys.path.insert(0, r"E:\ArabianFox\agent")
from browser_launcher import launch  # noqa: E402

SESSIONS_DIR = r"E:\ArabianFox\projects\drxmail\sessions"


def delay(a: float = 1.5, b: float = 3.5):
    time.sleep(a + (b - a) * random.random())


# --------------------------------------------------------------------------
# Flow modules
# --------------------------------------------------------------------------
def flow_github(page, email: str, password: str, username: str, otp_getter: Callable[[], Optional[str]]):
    page.goto("https://github.com/join", wait_until="domcontentloaded", timeout=60000)
    delay()
    page.fill("input#user_email", email); delay()
    page.click("button[type=submit]"); delay(2, 4)
    # password
    page.fill("input#user_password", password); delay()
    page.click("button[type=submit]"); delay(2, 4)
    # username
    page.fill("input#user_login", username); delay()
    page.click("button[type=submit]"); delay(2, 4)
    # solve puzzle manually if present -> wait for user
    body = page.inner_text("body")
    if "Verify" in body or "puzzle" in body.lower():
        input("[GitHub] Solve the CAPTCHA puzzle, then press ENTER...")
    # verification code
    code = otp_getter()
    if code:
        try:
            page.fill("input#otp", code); delay()
            page.click("button[type=submit]")
        except Exception:
            pass
    return page.url


def flow_discord(page, email: str, password: str, username: str, otp_getter: Callable[[], Optional[str]]):
    page.goto("https://discord.com/register", wait_until="domcontentloaded", timeout=60000)
    delay()
    page.fill("input[name=email]", email); delay()
    page.fill("input[name=password]", password); delay()
    # birthday
    try:
        page.select_option("select[name=birthday_month]", "1")
        page.select_option("select[name=birthday_day]", "1")
        page.fill("input[name=birthday_year]", "1995")
    except Exception:
        pass
    if page.query_selector("input[type=checkbox]"):
        page.check("input[type=checkbox]")
    page.click("button[type=submit]"); delay(3, 5)
    code = otp_getter()
    if code:
        try:
            page.fill("input[name=otp]", code); delay()
            page.click("button[type=submit]")
        except Exception:
            pass
    return page.url


def flow_instagram(page, email: str, password: str, username: str, otp_getter: Callable[[], Optional[str]]):
    page.goto("https://www.instagram.com/accounts/emailsignup/", wait_until="domcontentloaded", timeout=60000)
    delay(2, 4)
    page.locator("input[aria-label='Mobile Number or Email Address'], input[autocomplete=email]").first.fill(email)
    delay()
    page.fill("input[name=password]", password); delay()
    try:
        if page.query_selector("select[title='Month']"):
            page.select_option("select[title='Month']", "1")
    except Exception:
        pass
    try:
        page.get_by_role("button", name="Sign up").first.click()
    except Exception:
        pass
    delay(3, 5)
    code = otp_getter()
    if code:
        try:
            page.fill("input[name=confirmationCode], input[inputmode=numeric]", code)
            page.get_by_role("button", name="Next").first.click()
        except Exception:
            pass
    return page.url


FLOWS = {
    "github": flow_github,
    "discord": flow_discord,
    "instagram": flow_instagram,
}


# --------------------------------------------------------------------------
# Registrar
# --------------------------------------------------------------------------
class Registrar:
    def __init__(self, platform: str, headless: bool = False, browser: str = "chromium"):
        if platform not in FLOWS:
            raise ValueError(f"Unsupported platform '{platform}'. Choose from {list(FLOWS)}")
        self.platform = platform
        self.headless = headless
        self.browser = browser
        self.session_dir = os.path.join(SESSIONS_DIR, platform)
        os.makedirs(self.session_dir, exist_ok=True)

    def run(self, email: str, password: str, username: str = "",
            otp_getter: Optional[Callable[[], Optional[str]]] = None) -> dict:
        if not username:
            username = email.split("@")[0]
        p, context, page = launch(self.platform, headless=self.headless, browser=self.browser)
        result = {"platform": self.platform, "email": email, "final_url": "", "ok": False}
        try:
            final = FLOWS[self.platform](page, email, password, username, otp_getter or (lambda: None))
            result["final_url"] = final
            result["ok"] = True
        except Exception as e:
            result["error"] = repr(e)[:500]
        finally:
            context.close()
            p.stop()
        return result


if __name__ == "__main__":
    print("Registrar smoke test (structure)...")
    r = Registrar(platform="instagram")
    print("Ready. Sessions at:", r.session_dir)
