"""PKU Treehole 登录与关键词搜索客户端。"""

import json
import os
import random
import re
import uuid
from http.cookiejar import Cookie

import requests


class TreeholeClient:
    """封装树洞登录流程与关键词搜索 API。"""

    OAUTH_LOGIN = "https://iaaa.pku.edu.cn/iaaa/oauthlogin.do"
    REDIR_URL = "https://treehole.pku.edu.cn/cas_iaaa_login?uuid=fc71db5799cf&plat=web"
    SSO_LOGIN = "http://treehole.pku.edu.cn/cas_iaaa_login"
    UNREAD = "https://treehole.pku.edu.cn/api/mail/un_read"
    LOGIN_BY_TOKEN = "https://treehole.pku.edu.cn/api/login_iaaa_check_token"
    LOGIN_BY_MESSAGE = "https://treehole.pku.edu.cn/api/jwt_msg_verify"
    SEND_MESSAGE = "https://treehole.pku.edu.cn/api/jwt_send_msg"
    SEARCH_API = "https://treehole.pku.edu.cn/chapi/api/v3/hole/list_comments"

    def __init__(self, cookies_file=None):
        self.session = requests.Session()
        self.cookies_file = cookies_file or os.path.expanduser("~/.treehole_cookies.json")
        self.authorization = None

        self.session.headers.update(
            {
                "user-agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
                )
            }
        )
        self.load_cookies()
        self._load_token_from_cookiejar()

    def _load_token_from_cookiejar(self):
        token = self.session.cookies.get("pku_token")
        if token:
            self.authorization = token
            self.session.headers.update({"authorization": f"Bearer {token}"})

    def oauth_login(self, username, password):
        resp = self.session.post(
            self.OAUTH_LOGIN,
            data={
                "appid": "PKU Helper",
                "userName": username,
                "password": password,
                "randCode": "",
                "smsCode": "",
                "otpCode": "",
                "redirUrl": self.REDIR_URL,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def sso_login(self, token):
        resp = self.session.get(
            self.SSO_LOGIN,
            params={
                "uuid": str(uuid.uuid4()).split("-")[-1],
                "plat": "web",
                "_rand": str(random.random()),
                "token": token,
            },
            timeout=20,
        )
        resp.raise_for_status()
        m = re.search(r"token=(.*)", resp.url)
        if not m:
            raise RuntimeError("SSO 登录成功但未在跳转 URL 中找到 token")
        self.authorization = m.group(1)
        self.session.cookies.update({"pku_token": self.authorization})
        self.session.headers.update({"authorization": f"Bearer {self.authorization}"})

    def un_read(self):
        return self.session.get(self.UNREAD, timeout=20)

    def send_message(self):
        resp = self.session.post(self.SEND_MESSAGE, timeout=20)
        resp.raise_for_status()
        return resp.json()

    def login_by_message(self, code):
        resp = self.session.post(self.LOGIN_BY_MESSAGE, data={"valid_code": code}, timeout=20)
        resp.raise_for_status()
        result = resp.json()
        token = result.get("token")
        if token:
            self.authorization = token
            self.session.cookies.update({"pku_token": token})
            self.session.headers.update({"authorization": f"Bearer {token}"})
        return result

    def login_by_token(self, code):
        resp = self.session.post(self.LOGIN_BY_TOKEN, data={"code": code}, timeout=20)
        resp.raise_for_status()
        result = resp.json()
        token = result.get("token")
        if not token and isinstance(result.get("data"), dict):
            token = result["data"].get("token")
        if token:
            self.authorization = token
            self.session.cookies.update({"pku_token": token})
            self.session.headers.update({"authorization": f"Bearer {token}"})
        return result

    def ensure_login(self, username, password, interactive=True):
        """检查会话是否已登录；若未登录则完成登录和必要二次验证。"""
        resp = self.un_read()
        try:
            current = resp.json()
        except Exception:
            current = {}

        if resp.status_code == 200 and current.get("success"):
            return True

        oauth_result = self.oauth_login(username, password)
        if oauth_result.get("success") not in (True, "true"):
            raise RuntimeError(f"OAuth 登录失败: {oauth_result}")

        token = oauth_result.get("token")
        if not token:
            raise RuntimeError("OAuth 登录未返回 token")

        self.sso_login(token)

        max_attempts = 5
        for _ in range(max_attempts):
            status_resp = self.un_read()
            status_json = status_resp.json()
            if status_json.get("success"):
                self.save_cookies()
                return True

            message = status_json.get("message", "")
            if message == "请手机短信验证":
                if not interactive:
                    raise RuntimeError("登录需要手机短信验证")
                choice = input("需要短信验证，是否发送验证码？(Y/n): ").strip().lower()
                if choice in ("", "y", "yes"):
                    self.send_message()
                    code = input("请输入短信验证码: ").strip()
                    self.login_by_message(code)
                else:
                    return False
            elif message == "请进行令牌验证":
                if not interactive:
                    raise RuntimeError("登录需要 PKU Helper 手机令牌验证")
                code = input("请输入 PKU Helper 手机令牌: ").strip()
                self.login_by_token(code)
            else:
                raise RuntimeError(f"登录状态异常: {status_json}")

        return False

    def search_posts(self, keyword, page=1, limit=30, comment_limit=10):
        params = {
            "keyword": keyword,
            "page": page,
            "limit": limit,
            "comment_limit": comment_limit,
        }
        resp = self.session.get(self.SEARCH_API, params=params, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 20000:
            raise RuntimeError(f"搜索失败: {result}")

        data = result.get("data", {})
        posts = data.get("list", [])
        total = data.get("total", 0)
        return {"posts": posts, "total": total, "raw": result}

    def save_cookies(self):
        cookies_list = []
        for cookie in self.session.cookies:
            cookies_list.append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "expires": cookie.expires if cookie.expires else None,
                    "secure": cookie.secure,
                    "rest": {"HttpOnly": cookie.has_nonstandard_attr("HttpOnly")},
                }
            )

        with open(self.cookies_file, "w", encoding="utf-8") as f:
            json.dump(cookies_list, f, ensure_ascii=False, indent=2)

    def load_cookies(self):
        try:
            with open(self.cookies_file, "r", encoding="utf-8") as f:
                cookies_list = json.load(f)
            self.session.cookies.clear()
            for c in cookies_list:
                cookie = Cookie(
                    version=0,
                    name=c["name"],
                    value=c["value"],
                    port=None,
                    port_specified=False,
                    domain=c["domain"],
                    domain_specified=bool(c["domain"]),
                    domain_initial_dot=c["domain"].startswith("."),
                    path=c["path"],
                    path_specified=bool(c["path"]),
                    secure=c["secure"],
                    expires=c["expires"],
                    discard=False,
                    comment=None,
                    comment_url=None,
                    rest=c.get("rest", {}),
                )
                self.session.cookies.set_cookie(cookie)
        except FileNotFoundError:
            pass
