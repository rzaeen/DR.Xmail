"""
DR.Xmail — tests/test_core.py
Verifies core_mail engine end-to-end against the real Mail.tm API.
Run: python -m pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drxmail.core.core_mail import (
    get_provider,
    extract_otp,
    extract_link,
    extract_links,
)


def test_extract_otp():
    assert extract_otp("Your code is 482913") == "482913"
    assert extract_otp("رمز: 1234") == "1234"
    assert extract_otp("no digits here") is None


def test_extract_link():
    assert "x.com/confirm" in extract_link("verify https://x.com/confirm?t=abc NOW")
    assert extract_link("nothing") is None


def test_extract_links_multiple():
    links = extract_links("a https://a.com b https://b.com")
    assert len(links) == 2


def test_mailtm_create_and_inbox():
    """Live test against Mail.tm (needs network)."""
    p = get_provider("mailtm")
    acc = p.create_account()
    assert "@" in acc["address"]
    msgs = p.get_messages()
    assert isinstance(msgs, list)
