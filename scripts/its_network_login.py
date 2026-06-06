"""Log in to PKU ITS network service from pkuclab.

Credential priority:
1. ITS_USERNAME / ITS_PASSWORD
2. TREEHOLE_USERNAME / TREEHOLE_PASSWORD
3. USERNAME / PASSWORD from config_private.py or config_example.py
"""

import os
import json
import sys
import getpass
import urllib.parse
import urllib.request
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

try:
    from config_private import USERNAME as CONFIG_USERNAME
    from config_private import PASSWORD as CONFIG_PASSWORD
except ImportError:
    from config_example import USERNAME as CONFIG_USERNAME
    from config_example import PASSWORD as CONFIG_PASSWORD


LOGIN_URL = "https://its4.pku.edu.cn/cas/ITSClient"
TEST_URL = "https://api.chuckfang.com/"


def post_login(username, password):
    data = urllib.parse.urlencode(
        {
            "username": username,
            "password": password,
            "iprange": "free",
            "cmd": "open",
        }
    ).encode("utf-8")
    # The official CLab snippet sends these fields as query parameters even with POST.
    url = f"{LOGIN_URL}?{data.decode('utf-8')}"
    req = urllib.request.Request(url, data=b"", method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    try:
        with opener.open(req, timeout=20) as resp:
            body = resp.read(500).decode("utf-8", errors="replace")
        return resp.status, resp.geturl().split("?", 1)[0], body
    except urllib.error.HTTPError as exc:
        body = exc.read(500).decode("utf-8", errors="replace")
        return exc.code, exc.geturl().split("?", 1)[0], body


def test_meow_direct():
    try:
        with urllib.request.urlopen(TEST_URL, timeout=12) as resp:
            return True, f"{resp.status} {resp.geturl()}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def main():
    username = os.getenv("ITS_USERNAME") or os.getenv("TREEHOLE_USERNAME") or CONFIG_USERNAME
    password = os.getenv("ITS_PASSWORD") or os.getenv("TREEHOLE_PASSWORD") or CONFIG_PASSWORD

    missing_or_placeholder = (
        not username
        or not password
        or username.startswith("<")
        or password.startswith("<")
    )
    if missing_or_placeholder:
        if not sys.stdin.isatty():
            raise RuntimeError(
                "Missing gateway credentials in non-interactive mode. "
                "Set ITS_USERNAME/ITS_PASSWORD, TREEHOLE_USERNAME/TREEHOLE_PASSWORD, "
                "or configure USERNAME/PASSWORD."
            )
        username = input("请输入用户名: ").strip()
        password = getpass.getpass("请输入密码: ")

    status, url, body = post_login(username, password)
    print(f"ITS login response: status={status} url={url}")
    if body:
        print("ITS response preview:", body.replace("\n", " ")[:200])
        try:
            data = json.loads(body)
            if data.get("IP"):
                print(f"ITS authenticated IP: {data['IP']}")
            if data.get("succ") == "":
                print("ITS login reported success.")
        except json.JSONDecodeError:
            pass

    ok, detail = test_meow_direct()
    print(f"Direct MeoW connectivity after login: {ok} {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
