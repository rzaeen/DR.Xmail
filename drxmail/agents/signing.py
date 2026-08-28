"""
DR.Xmail — HTTP Signatures (ActivityPub standard)
==================================================
Many ActivityPub inboxes require requests to be signed with the sender's
RSA private key (RFC 9421 / the widely-used draft-cavage HTTP Signatures).
This module creates and attaches a valid Signature header so our agents
can deliver Notes to real Fediverse nodes (Mastodon etc.).

Each federated agent generates its own RSA keypair (stored in its identity
file) and publishes the public key in its actor document.
"""

from __future__ import annotations

import time
import base64
import hashlib
from typing import Dict, Any, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key, Encoding, PrivateFormat, PublicFormat,
    NoEncryption as _no_a,
)

DEFAULT_HEADERS = "(request-target) host date digest"


def generate_keypair() -> Dict[str, str]:
    """Generate an RSA keypair. Returns PEM private + public strings."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = key.private_bytes(
        Encoding.PEM, PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=_no_a()
    ).decode()
    pub_pem = key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
    return {"private": priv_pem, "public": pub_pem}


def private_to_public(pem: str) -> str:
    """Return the public-key PEM for a given private-key PEM."""
    key = load_pem_private_key(pem.encode(), password=None)
    return key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def build_signature_header(private_pem: str, key_id: str, method: str,
                            path: str, host: str, body: str,
                            digest: Optional[str] = None) -> str:
    priv = load_pem_private_key(private_pem.encode(), password=None)
    if digest is None:
        digest = _b64(hashlib.sha256(body.encode()).digest())
    parts = {
        "(request-target)": f"{method.lower()} {path}",
        "host": host,
        "date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
        "digest": f"SHA-256={digest}",
    }
    signing_str = "\n".join(f"{k}: {parts[k]}" for k in
                            ["(request-target)", "host", "date", "digest"])
    sig = priv.sign(signing_str.encode(), padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = _b64(sig)
    headers = "(request-target) host date digest"
    return (f'keyId="{key_id}",algorithm="rsa-sha256",headers="{headers}",'
            f'signature="{sig_b64}"')


def signed_post(private_pem: str, key_id: str, inbox_url: str,
                activity: Dict[str, Any]) -> Any:
    """POST an activity with a valid HTTP Signature. Returns requests.Response."""
    import requests
    import urllib.parse as up
    body = _json_dumps(activity)
    digest = _b64(hashlib.sha256(body.encode()).digest())
    parsed = up.urlparse(inbox_url)
    host = parsed.netloc
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    sig = build_signature_header(private_pem, key_id, "POST", path, host, body, digest)
    headers = {
        "Host": host,
        "Date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
        "Digest": f"SHA-256={digest}",
        "Signature": sig,
        "Content-Type": "application/activity+json",
    }
    return requests.post(inbox_url, data=body.encode(), headers=headers, timeout=20)


def _json_dumps(obj: Dict[str, Any]) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)
