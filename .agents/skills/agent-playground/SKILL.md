---
name: agent-playground
description: >-
  Autonomous multi-platform web exploration and interaction toolkit for GitHub,
  Bilibili, Zhihu, and Windows PC WeChat 4.x. Use when navigating JS-heavy pages,
  extracting clean Markdown/links, checking authenticated platform sessions, or
  bridging to local Windows desktop WeChat via MCP or CLI.
---

# Agent Playground Skill

Give any coding or autonomous agent structured perception and execution across modern web apps and local social platforms without fragile one-off scraping scripts.

## Quick Start (CLI)

Run commands via `scripts/run.py`:

```bash
# 1. Explore any webpage (dynamic scroll + screenshot + clean Markdown extraction)
python scripts/run.py explore --url "https://github.com/trending" --scroll 2 --capture trending

# 2. Search GitHub repositories (uses saved Playwright session if available)
python scripts/run.py github-search --query "ai agent" --sort stars --limit 5

# 3. Check login/runtime status across platforms
python scripts/run.py status --platform all

# 4. Send a message to the active chat in Windows PC WeChat 4.x (Windows only)
python scripts/run.py wechat-send --message "Hello from Agent Playground!"
```

Add `--visible` before the subcommand to watch the browser live.

## MCP Server Integration

Expose the same capabilities over stdio JSON-RPC 2.0 (`mcp_server.py`):

```json
{
  "mcpServers": {
    "agent-playground": {
      "command": "python",
      "args": ["mcp_server.py"]
    }
  }
}
```

Exposed MCP tools:
- `explore_url`
- `github_search`
- `platform_status`
- `wechat_send_current`

## Safety & Session Hygiene
- Never commit or bundle `storage/cookies/*.json`, `.env`, or screenshot captures containing private conversations.
- Never attempt to bypass CAPTCHAs or anti-bot challenges; prompt the user for QR/interactive verification when needed.
- On Windows, keep `adapters/wechat.py` pure-ctypes so `SetThreadDesktop` attaches cleanly to `WinSta0\Default` (see `reference/notes.md`).
