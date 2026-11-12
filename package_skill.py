"""
Build clean, standalone, sanitized skill archives compatible with Antigravity
and Agensi.io's SKILL.md bundle format.

Produces:
- dist/agent-playground-skill.zip   (full bundle including Windows PC WeChat adapter)
- dist/agent-playground-agensi.zip  (cross-platform Playwright + GitHub/Bilibili/Zhihu bundle)
"""

from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
SKILL_ROOT = ROOT / ".agents" / "skills" / "agent-playground"
DIST_DIR = ROOT / "dist"

AGENSI_SKILL_MD = """---
name: agent-playground
description: >-
  Cross-platform Playwright web exploration and social platform toolkit for
  navigating JS-heavy sites, extracting clean Markdown/links, and interacting
  with GitHub, Bilibili, and Zhihu via CLI or stdio MCP server.
---

# Agent Playground Skill (Cross-Platform Web Edition)

Give any AI coding or autonomous agent clean perception over modern JS-heavy web
apps—dynamic scrolling, full-page screenshots, structured Markdown extraction,
and persistent Playwright session handling for GitHub, Bilibili, and Zhihu.

## Prerequisites

```bash
pip install -r scripts/requirements.txt
```

Uses your system Chrome (`channel="chrome"`) with automatic fallback to Edge (`msedge`).

## Quick Start (CLI)

```bash
# 1. Explore any JS-heavy URL (scroll lazy feeds + extract clean text & links)
python scripts/run.py explore --url "https://github.com/trending" --scroll 2 --capture trending

# 2. Search GitHub repositories
python scripts/run.py github-search --query "ai agent" --sort stars --limit 5

# 3. Check session status across platforms
python scripts/run.py status --platform all
```

Pass `--visible` before the subcommand to watch the browser live.

## MCP Server Integration

```json
{
  "mcpServers": {
    "agent-playground": {
      "command": "python",
      "args": ["scripts/mcp_server.py"]
    }
  }
}
```

## Safety & Session Hygiene
- Session state files are stored locally under `storage/cookies/` and never bundled.
- Never bypass CAPTCHAs or anti-bot gates; switch to `--visible` or QR login when challenged.
"""

AGENSI_NOTES_MD = """# Technical Notes: Browser Anti-Detection & QR Auth

## 1. Playwright Channel Fallback & Anti-Detection
- `core/browser.py` prefers system Chrome (`channel="chrome"`) with `--disable-blink-features=AutomationControlled` and falls back automatically to `msedge`.
- Prefer `wait_until="domcontentloaded"` on streaming/SPA pages (GitHub search, Zhihu feeds) to avoid `networkidle` hangs.

## 2. Domestic Platform Authentication (Bilibili / Zhihu)
- Headless password logins commonly trigger Geetest or NetEase NECaptcha challenges.
- Capture/display the platform's login QR code once, persist `storage_state` under `storage/cookies/*.json`, and reuse the authenticated context afterward.
"""


def _build_zip(dest: Path, include_wechat: bool) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if include_wechat:
            zf.write(SKILL_ROOT / "SKILL.md", "SKILL.md")
            zf.write(SKILL_ROOT / "reference" / "notes.md", "reference/notes.md")
        else:
            zf.writestr("SKILL.md", AGENSI_SKILL_MD)
            zf.writestr("reference/notes.md", AGENSI_NOTES_MD)

        zf.write(SKILL_ROOT / "scripts" / "run.py", "scripts/run.py")
        zf.write(ROOT / "requirements.txt", "scripts/requirements.txt")
        zf.write(ROOT / "mcp_server.py", "scripts/mcp_server.py")

        for pkg in ("core", "adapters"):
            for py_file in sorted((ROOT / pkg).glob("*.py")):
                if not include_wechat and pkg == "adapters" and py_file.name == "wechat.py":
                    continue
                zf.write(py_file, f"scripts/{pkg}/{py_file.name}")

    return dest


def main() -> None:
    full_zip = _build_zip(DIST_DIR / "agent-playground-skill.zip", include_wechat=True)
    agensi_zip = _build_zip(DIST_DIR / "agent-playground-agensi.zip", include_wechat=False)
    for zpath in (full_zip, agensi_zip):
        with zipfile.ZipFile(zpath, "r") as zf:
            names = zf.namelist()
        print(f"[+] Built {zpath.name}: {zpath.stat().st_size} bytes ({len(names)} files)")


if __name__ == "__main__":
    main()
