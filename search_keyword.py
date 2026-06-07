"""登录 PKU Treehole 并搜索指定关键词，有新增结果时推送通知。"""

import argparse
import json
import os
from datetime import datetime

from client import TreeholeClient
from meow_push import send_meow_push

try:
    from config_private import (
        USERNAME,
        PASSWORD,
        KEYWORD,
        SEARCH_PAGE,
        SEARCH_LIMIT,
        COMMENT_LIMIT,
        COOKIES_FILE,
    )
except ImportError:
    from config_example import (
        USERNAME,
        PASSWORD,
        KEYWORD,
        SEARCH_PAGE,
        SEARCH_LIMIT,
        COMMENT_LIMIT,
        COOKIES_FILE,
    )


try:
    from config_private import MEOW_NICKNAME as DEFAULT_MEOW_NICKNAME
except ImportError:
    try:
        from config_example import MEOW_NICKNAME as DEFAULT_MEOW_NICKNAME
    except ImportError:
        DEFAULT_MEOW_NICKNAME = "<YOUR_MEOW_NICKNAME>"


def load_seen_state(state_file):
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        pass
    return {}


def save_seen_state(state_file, state):
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def format_readable_time(ts):
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    return "未知时间"


def env_flag(name, default=True):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


def get_meow_nickname():
    nickname = os.getenv("MEOW_NICKNAME") or DEFAULT_MEOW_NICKNAME
    if not nickname or nickname.startswith("<"):
        raise RuntimeError(
            "缺少 MeoW 昵称：请设置环境变量 MEOW_NICKNAME，或在 config_private.py 中填写 MEOW_NICKNAME"
        )
    return nickname


def compact_text(text, limit):
    text = (text or "").replace("\r", " ").replace("\n", " ").strip()
    if not text:
        return "[无文本内容]"
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def iter_post_summary_lines(post, idx, post_text_limit=300, comment_text_limit=160, max_comments=3):
    pid = post.get("pid")
    reply = post.get("reply", 0)
    like = post.get("likenum", 0)
    readable_time = format_readable_time(post.get("timestamp"))
    preview = compact_text(post.get("text"), post_text_limit)

    yield f"{idx}. #{pid} | {readable_time} | 赞 {like} | 评 {reply}"
    yield f"   {preview}"

    comments = post.get("comment_list") or post.get("comments") or []
    for comment in comments[:max_comments]:
        comment_time = format_readable_time(comment.get("timestamp"))
        comment_preview = compact_text(comment.get("text"), comment_text_limit)
        yield f"   - [{comment_time}] {comment_preview}"


def iter_push_post_lines(post, idx, post_text_limit=180, comment_text_limit=120, max_comments=3):
    pid = post.get("pid")
    reply = post.get("reply", 0)
    readable_time = format_readable_time(post.get("timestamp"))
    preview = compact_text(post.get("text"), post_text_limit)

    yield f"{idx}. #{pid} | {readable_time} | 评论 {reply}"
    yield f"   > {preview}"

    comments = post.get("comment_list") or post.get("comments") or []
    for comment in comments[:max_comments]:
        comment_preview = compact_text(comment.get("text"), comment_text_limit)
        yield f"   -  {comment_preview}"


def safe_int_env(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def build_push_message(keyword, total, posts_count, new_posts, max_chars=None, max_comments=5):
    lines = []

    for idx, post in enumerate(new_posts, start=1):
        lines.extend(iter_push_post_lines(post, idx, max_comments=max_comments))
        lines.append("")

    message = "\n".join(lines).strip()
    if max_chars is None or len(message) <= max_chars:
        return message

    suffix = "\n\n[消息过长，已截断；完整内容请在脚本终端输出或 MeoW App 内查看。]"
    return message[: max_chars - len(suffix)].rstrip() + suffix


def build_full_push_message(keyword, total, posts_count, new_posts):
    return build_push_message(keyword, total, posts_count, new_posts, max_chars=None)


def print_new_posts(keyword, total, posts_count, new_posts):
    print(f"关键词: {keyword}")
    print(f"总匹配数(接口返回): {total}")
    print(f"本页返回帖子数: {posts_count}")
    print(f"新增帖子数: {len(new_posts)}")

    for idx, post in enumerate(new_posts, start=1):
        for line in iter_post_summary_lines(
            post,
            idx,
            post_text_limit=120,
            comment_text_limit=100,
        ):
            print(line)

    if not new_posts:
        print("本次无新增帖子。")


def push_if_needed(keyword, total, posts_count, new_posts):
    if not new_posts:
        return

    title = f"检索到 {len(new_posts)} 条「{keyword}」树洞"
    max_chars = safe_int_env("MEOW_MAX_CHARS", 1800)
    max_comments = safe_int_env("MEOW_COMMENT_LIMIT", 5)
    message = build_push_message(
        keyword,
        total,
        posts_count,
        new_posts,
        max_chars=max_chars,
        max_comments=max_comments,
    )

    nickname = get_meow_nickname()
    if not env_flag("MEOW_ENABLED", default=True):
        print("MeoW 推送已关闭，以下为本应推送的内容：")
        print(f"[{title}]")
        print(message)
        return

    base_url = os.getenv("MEOW_BASE_URL") or "https://api.chuckfang.com"
    result = send_meow_push(
        nickname=nickname,
        title=title,
        msg=message,
        base_url=base_url,
        direct_fallback=env_flag("MEOW_DIRECT_FALLBACK", default=True),
    )
    print(f"MeoW 推送成功: {result}")


def notify_login_verification_required(error_message):
    title = "树洞定时搜索需要令牌验证"
    message = (
        f"{error_message}\n\n"
        "本次定时搜索没有执行。请登录云主机，在项目目录手动运行：\n"
        "python search_keyword.py\n\n"
        "按提示输入 PKU Helper 手机令牌后，后续定时任务会继续复用登录态。"
    )

    nickname = get_meow_nickname()
    base_url = os.getenv("MEOW_BASE_URL") or "https://api.chuckfang.com"
    result = send_meow_push(
        nickname=nickname,
        title=title,
        msg=message,
        base_url=base_url,
        direct_fallback=env_flag("MEOW_DIRECT_FALLBACK", default=True),
    )
    print(f"登录验证提醒已推送: {result}")


def send_test_push():
    nickname = get_meow_nickname()
    base_url = os.getenv("MEOW_BASE_URL") or "https://api.chuckfang.com"
    title = "树洞推送测试"
    message = (
        "这是一条 MeoW 推送验证消息。\n"
        "如果你在手机上看到它，说明 MeoW 推送通道可以正常使用。"
    )
    result = send_meow_push(
        nickname=nickname,
        title=title,
        msg=message,
        base_url=base_url,
        direct_fallback=env_flag("MEOW_DIRECT_FALLBACK", default=True),
    )
    print(f"MeoW 测试推送成功: {result}")


def parse_args():
    parser = argparse.ArgumentParser(description="搜索树洞关键词，有新增帖子时推送到手机。")
    parser.add_argument(
        "--test-push",
        action="store_true",
        help="只发送一条 MeoW 测试推送，不登录树洞、不搜索。",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="非交互模式；需要短信或令牌验证时直接失败，适合定时任务。",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.test_push:
        send_test_push()
        return

    # 环境变量优先，配置文件兜底
    username = os.getenv("TREEHOLE_USERNAME") or USERNAME
    password = os.getenv("TREEHOLE_PASSWORD") or PASSWORD
    keyword = os.getenv("TREEHOLE_KEYWORD") or KEYWORD
    state_file = os.getenv("TREEHOLE_STATE_FILE") or "seen_posts_state.json"
    comment_limit = safe_int_env("TREEHOLE_COMMENT_LIMIT", COMMENT_LIMIT)

    if username.startswith("<") or password.startswith("<"):
        raise RuntimeError(
            "缺少账号密码：请在环境变量 TREEHOLE_USERNAME/TREEHOLE_PASSWORD 设置，或在 config_private.py 填写"
        )

    client = TreeholeClient(cookies_file=COOKIES_FILE)
    try:
        ok = client.ensure_login(username, password, interactive=not args.non_interactive)
    except RuntimeError as exc:
        error_message = str(exc)
        if args.non_interactive and "令牌验证" in error_message:
            notify_login_verification_required(error_message)
        raise

    if not ok:
        raise RuntimeError("登录失败（可能需要二次验证但未完成）")

    result = client.search_posts(
        keyword=keyword,
        page=SEARCH_PAGE,
        limit=SEARCH_LIMIT,
        comment_limit=comment_limit,
    )

    posts = result["posts"]
    total = result["total"]

    state = load_seen_state(state_file)
    keyword_state = state.get(keyword, {})
    seen_pids = set(keyword_state.get("seen_pids", []))

    new_posts = []
    for post in posts:
        pid = post.get("pid")
        if pid is None:
            continue
        if pid not in seen_pids:
            new_posts.append(post)

    print_new_posts(keyword, total, len(posts), new_posts)
    push_if_needed(keyword, total, len(posts), new_posts)

    current_pids = [post.get("pid") for post in posts if post.get("pid") is not None]
    merged_pids = list(dict.fromkeys(current_pids + list(seen_pids)))
    # 防止状态文件无限增长，仅保留最近的 5000 条 pid
    merged_pids = merged_pids[:5000]
    state[keyword] = {"seen_pids": merged_pids}
    save_seen_state(state_file, state)
    print(f"已更新状态文件: {state_file}")


if __name__ == "__main__":
    main()
