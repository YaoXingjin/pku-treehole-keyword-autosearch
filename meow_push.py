"""MeoW phone push helper."""

from urllib.parse import quote

import requests


class MeowPushError(RuntimeError):
    """Raised when MeoW push fails."""


def _post_meow(endpoint, title, msg, timeout, trust_env=True):
    session = requests.Session()
    session.trust_env = trust_env
    return session.post(
        endpoint,
        params={"msgType": "text"},
        json={"title": title, "msg": msg},
        timeout=timeout,
    )


def send_meow_push(
    nickname,
    title,
    msg,
    base_url="https://api.chuckfang.com",
    timeout=20,
    direct_fallback=False,
):
    """Send a text push notification through MeoW."""
    if not nickname or "/" in nickname:
        raise ValueError("MeoW nickname must be non-empty and cannot contain '/'.")

    endpoint = f"{base_url.rstrip('/')}/{quote(nickname)}"
    try:
        resp = _post_meow(endpoint, title, msg, timeout, trust_env=True)
    except requests.RequestException:
        if not direct_fallback:
            raise
        resp = _post_meow(endpoint, title, msg, timeout, trust_env=False)

    resp.raise_for_status()

    try:
        data = resp.json()
    except ValueError as exc:
        raise MeowPushError(f"MeoW returned non-JSON response: {resp.text[:200]}") from exc

    if data.get("status") != 200:
        detail = data.get("msg") or data.get("message") or data
        raise MeowPushError(f"MeoW push failed: {detail}")

    return data
