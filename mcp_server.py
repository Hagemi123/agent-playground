"""
Model Context Protocol (MCP) stdio server for Agent Playground.
Exposes web exploration, GitHub search, platform status checks, and WeChat messaging
as standard MCP tools over newline-delimited JSON-RPC 2.0.
"""

import json
import sys
import traceback
from typing import Any, Callable, Dict, List

from core.navigator import WebNavigator
from adapters.github import GitHubAdapter
from adapters.bilibili import BilibiliAdapter
from adapters.zhihu import ZhihuAdapter

try:
    from adapters.wechat import WeChatAdapter
except ImportError:
    WeChatAdapter = None

SERVER_INFO = {
    "name": "agent-playground",
    "version": "0.4.0",
}
PROTOCOL_VERSION = "2024-11-05"


def _tool_explore_url(args: Dict[str, Any]) -> Dict[str, Any]:
    url = args["url"]
    scroll_times = int(args.get("scroll_times", 2))
    wait_seconds = float(args.get("wait_seconds", 2.0))
    capture_name = str(args.get("capture_name", "mcp_explore"))
    headless = bool(args.get("headless", True))

    nav = WebNavigator(headless=headless)
    return nav.explore_url(
        url=url,
        scroll_times=scroll_times,
        wait_seconds=wait_seconds,
        capture_name=capture_name,
    )


def _tool_github_search(args: Dict[str, Any]) -> Dict[str, Any]:
    query = args["query"]
    sort = str(args.get("sort", "stars"))
    limit = int(args.get("limit", 5))
    headless = bool(args.get("headless", True))

    with GitHubAdapter(headless=headless) as gh:
        return gh.search_repositories(query=query, sort=sort, limit=limit)


def _tool_platform_status(args: Dict[str, Any]) -> Dict[str, Any]:
    platform = str(args.get("platform", "all")).lower()
    headless = bool(args.get("headless", True))
    results: Dict[str, Any] = {}

    if platform in ("all", "github"):
        with GitHubAdapter(headless=headless) as gh:
            results["github"] = gh.check_login_status()
    if platform in ("all", "bilibili"):
        with BilibiliAdapter(headless=headless) as bili:
            results["bilibili"] = bili.check_login_status()
    if platform in ("all", "zhihu"):
        with ZhihuAdapter(headless=headless) as zh:
            results["zhihu"] = zh.check_login_status()
    if platform in ("all", "wechat"):
        if WeChatAdapter is not None:
            results["wechat"] = WeChatAdapter().check_status()
        else:
            results["wechat"] = {"running": False, "logged_in": False, "msg": "WeChat adapter not bundled."}

    return results


def _tool_wechat_send_current(args: Dict[str, Any]) -> Dict[str, Any]:
    if WeChatAdapter is None:
        return {"success": False, "error": "WeChat desktop adapter is not available in this bundle."}
    message = args["message"]
    capture_path = args.get("capture_path")
    ok = WeChatAdapter().send_message_to_current_chat(
        message=message,
        capture_path=capture_path,
    )
    return {"success": ok, "capture_path": capture_path}


TOOL_DEFS: List[Dict[str, Any]] = [
    {
        "name": "explore_url",
        "description": "Navigate to a URL with Playwright, scroll lazy feeds, capture a screenshot, and extract clean Markdown text & links.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target HTTP/HTTPS URL."},
                "scroll_times": {"type": "integer", "default": 2},
                "wait_seconds": {"type": "number", "default": 2.0},
                "capture_name": {"type": "string", "default": "mcp_explore"},
                "headless": {"type": "boolean", "default": True},
            },
            "required": ["url"],
        },
    },
    {
        "name": "github_search",
        "description": "Search GitHub repositories using the saved Playwright session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "GitHub search query."},
                "sort": {"type": "string", "default": "stars"},
                "limit": {"type": "integer", "default": 5},
                "headless": {"type": "boolean", "default": True},
            },
            "required": ["query"],
        },
    },
    {
        "name": "platform_status",
        "description": "Check authentication/runtime status for GitHub, Bilibili, Zhihu, or Windows PC WeChat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["all", "github", "bilibili", "zhihu", "wechat"],
                    "default": "all",
                },
                "headless": {"type": "boolean", "default": True},
            },
        },
    },
    {
        "name": "wechat_send_current",
        "description": "Send a text message to the currently open chat in Windows PC WeChat 4.x via Win32 desktop bridging.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message text to send."},
                "capture_path": {"type": "string", "description": "Optional verification screenshot path."},
            },
            "required": ["message"],
        },
    },
]

TOOL_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "explore_url": _tool_explore_url,
    "github_search": _tool_github_search,
    "platform_status": _tool_platform_status,
    "wechat_send_current": _tool_wechat_send_current,
}


def handle_request(request: Dict[str, Any]) -> Dict[str, Any] | None:
    """Process a single JSON-RPC 2.0 request and return a response dict (or None for notifications)."""
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params") or {}

    if method == "notifications/initialized" or req_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOL_DEFS}}

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {name}"},
            }
        try:
            data = handler(arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"{exc}\n{traceback.format_exc()}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    """Run the stdio JSON-RPC event loop."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        resp = handle_request(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
