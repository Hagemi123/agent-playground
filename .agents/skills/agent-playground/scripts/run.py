"""
Unified CLI runner for the agent-playground skill.
Works both inside the hagemiplayground workspace and inside a standalone skill bundle.
"""

import argparse
import json
import sys
from pathlib import Path

# Support both standalone skill bundle (scripts/core, scripts/adapters)
# and workspace layout (<repo_root>/core, <repo_root>/adapters).
SCRIPT_DIR = Path(__file__).resolve().parent
CANDIDATE_ROOTS = [
    SCRIPT_DIR,
    SCRIPT_DIR.parents[3] if len(SCRIPT_DIR.parents) >= 4 else SCRIPT_DIR.parent,
]
for root in CANDIDATE_ROOTS:
    if (root / "core").is_dir() and (root / "adapters").is_dir():
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        break

from core.navigator import WebNavigator
from adapters.github import GitHubAdapter
from adapters.bilibili import BilibiliAdapter
from adapters.zhihu import ZhihuAdapter

try:
    from adapters.wechat import WeChatAdapter
except ImportError:
    WeChatAdapter = None


def cmd_explore(args: argparse.Namespace) -> dict:
    nav = WebNavigator(headless=not args.visible)
    return nav.explore_url(
        url=args.url,
        scroll_times=args.scroll,
        wait_seconds=args.wait,
        capture_name=args.capture,
    )


def cmd_github_search(args: argparse.Namespace) -> dict:
    with GitHubAdapter(headless=not args.visible) as gh:
        return gh.search_repositories(query=args.query, sort=args.sort, limit=args.limit)


def cmd_status(args: argparse.Namespace) -> dict:
    platform = args.platform.lower()
    headless = not args.visible
    out: dict = {}

    if platform in ("all", "github"):
        with GitHubAdapter(headless=headless) as gh:
            out["github"] = gh.check_login_status()
    if platform in ("all", "bilibili"):
        with BilibiliAdapter(headless=headless) as bili:
            out["bilibili"] = bili.check_login_status()
    if platform in ("all", "zhihu"):
        with ZhihuAdapter(headless=headless) as zh:
            out["zhihu"] = zh.check_login_status()
    if platform in ("all", "wechat"):
        if WeChatAdapter is not None:
            out["wechat"] = WeChatAdapter().check_status()
        else:
            out["wechat"] = {"running": False, "logged_in": False, "msg": "WeChat adapter not bundled."}
    return out


def cmd_wechat_send(args: argparse.Namespace) -> dict:
    if WeChatAdapter is None:
        return {"success": False, "error": "WeChat desktop adapter is not available in this bundle."}
    ok = WeChatAdapter().send_message_to_current_chat(
        message=args.message,
        capture_path=args.capture_path,
    )
    return {"success": ok, "capture_path": args.capture_path}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent Playground multi-platform CLI")
    parser.add_argument("--visible", action="store_true", help="Launch visible browser window instead of headless")
    sub = parser.add_subparsers(dest="command", required=True)

    p_exp = sub.add_parser("explore", help="Explore a URL, scroll lazy feeds, extract clean text & screenshot")
    p_exp.add_argument("--url", required=True)
    p_exp.add_argument("--scroll", type=int, default=2)
    p_exp.add_argument("--wait", type=float, default=2.0)
    p_exp.add_argument("--capture", default="skill_explore")
    p_exp.set_defaults(func=cmd_explore)

    p_gh = sub.add_parser("github-search", help="Search GitHub repositories")
    p_gh.add_argument("--query", required=True)
    p_gh.add_argument("--sort", default="stars")
    p_gh.add_argument("--limit", type=int, default=5)
    p_gh.set_defaults(func=cmd_github_search)

    p_st = sub.add_parser("status", help="Check login/runtime status across platforms")
    p_st.add_argument("--platform", default="all", choices=["all", "github", "bilibili", "zhihu", "wechat"])
    p_st.set_defaults(func=cmd_status)

    p_wx = sub.add_parser("wechat-send", help="Send a message to the currently open Windows PC WeChat chat")
    p_wx.add_argument("--message", required=True)
    p_wx.add_argument("--capture-path", default=None)
    p_wx.set_defaults(func=cmd_wechat_send)

    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
