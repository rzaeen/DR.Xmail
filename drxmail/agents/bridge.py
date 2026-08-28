"""
DR.Xmail — Federation Bridge (talk to EXTERNAL agents via ActivityPub)
========================================================================
Lets our local agents discover and message ANY external ActivityPub actor
(e.g. a Mastodon account, or another DR.Xmail node). This is how DR.Xmail
agents communicate with "AI agents like you" across the open Fediverse.

External actor example (Mastodon):
  handle : @user@instance.social
  actor  : https://instance.social/users/user
  inbox  : https://instance.social/users/user/inbox

We resolve the handle -> actor doc -> inbox URL, then POST a Note.
"""

from __future__ import annotations

import requests
from typing import Optional, Dict, Any

from . import fedimail as fm


def resolve_actor(handle_or_url: str) -> Optional[Dict[str, Any]]:
    """Resolve an ActivityPub actor from a handle (@user@host) or URL.

    For a handle we query the host's WebFinger endpoint. Many nodes (Mastodon)
    require signed GET for the actor document, so we fall back to building the
    inbox URL from the WebFinger 'self' link when the document fetch fails.
    """
    actor_url = None
    if handle_or_url.startswith("@"):
        parts = handle_or_url.lstrip("@").split("@")
        if len(parts) != 2:
            return None
        user, host = parts
        wf = f"https://{host}/.well-known/webfinger"
        try:
            r = requests.get(wf, params={"resource": f"acct:{user}@{host}"},
                              headers={"Accept": "application/json"}, timeout=20)
            if r.status_code != 200:
                return None
            link = next((l for l in r.json().get("links", [])
                         if l.get("rel") == "self"
                         and "activity+json" in l.get("type", "")), None)
            if not link:
                return None
            actor_url = link["href"]
        except Exception:
            return None
    else:
        actor_url = handle_or_url

    # try to fetch the actor document (may need signature on some nodes)
    try:
        r = requests.get(actor_url,
                         headers={"Accept": "application/activity+json"}, timeout=20)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass

    # fallback: derive inbox from actor URL (Mastodon convention)
    # https://host/users/X  ->  https://host/users/X/inbox
    inbox = actor_url.rstrip("/") + "/inbox"
    return {
        "id": actor_url,
        "preferredUsername": handle_or_url.lstrip("@").split("@")[0] if handle_or_url.startswith("@") else actor_url.split("/")[-1],
        "inbox": inbox,
        "type": "Person",
    }


def send_to_external(sender_actor_id: str, recipient_handle_or_url: str,
                      subject: str, body: str,
                      private_pem: Optional[str] = None) -> Dict[str, Any]:
    """Send a Note from our agent to an external ActivityPub actor.

    If private_pem is provided, the request is HTTP-signed (required by
    Mastodon and most Fediverse nodes). Without it, we try an unsigned POST
    (works for our own local nodes and some lenient relays).

    Returns a status dict (delivered / actor / error).
    """
    actor = resolve_actor(recipient_handle_or_url)
    if not actor:
        return {"delivered": False, "error": "could not resolve actor"}
    inbox = actor.get("inbox") or (actor.get("endpoints") or {}).get("sharedInbox")
    if not inbox:
        return {"delivered": False, "error": "actor has no inbox"}
    activity = fm.make_note_activity(
        sender_id=sender_actor_id,
        recipient_id=actor.get("id", recipient_handle_or_url),
        recipient_inbox=inbox,
        subject=subject,
        body=body,
    )
    try:
        if private_pem:
            from . import signing
            key_id = f"{sender_actor_id}#main-key"
            resp = signing.signed_post(private_pem, key_id, inbox, activity)
        else:
            import requests
            resp = requests.post(
                inbox, json=activity,
                headers={"Content-Type": "application/activity+json"}, timeout=20)
        return {"delivered": resp.status_code in (200, 201, 202),
                "status_code": resp.status_code, "actor": actor.get("id")}
    except Exception as e:
        return {"delivered": False, "error": str(e)}


def discover_federated(handle_or_url: str) -> Optional[Dict[str, Any]]:
    """Return a minimal agent card for an external actor (for our registry)."""
    actor = resolve_actor(handle_or_url)
    if not actor:
        return None
    return {
        "actor_id": actor.get("id", ""),
        "username": actor.get("preferredUsername", ""),
        "inbox": actor.get("inbox", ""),
        "type": actor.get("type", ""),
        "external": True,
    }
