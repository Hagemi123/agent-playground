# Technical Notes: Browser Anti-Detection, QR Auth & Windows Desktop Bridging

## 1. Playwright Channel Fallback & Anti-Detection
- `core/browser.py` prefers system Google Chrome (`channel="chrome"`) with `--disable-blink-features=AutomationControlled`, falling back automatically to `msedge`.
- Avoid `wait_until="networkidle"` on streaming/SPA pages (e.g., GitHub search, Zhihu feeds); prefer `wait_until="domcontentloaded"` + targeted waits.

## 2. Domestic Platform Authentication (Bilibili / Zhihu)
- Password logins in headless browsers commonly trigger Geetest or NetEase NECaptcha challenges.
- **Recommended Pattern**: Capture/poll the platform's QR login endpoint or render the QR element screenshot, let the user scan once, and persist `storage_state` under `storage/cookies/*.json`.

## 3. Windows PC WeChat 4.x (`MMUIRenderSubWindowHW`)
- Background agent processes on Windows often run inside an isolated desktop (`WinSta0\exebox-...`) rather than the user's interactive desktop (`WinSta0\Default`).
- `adapters/wechat.py` calls `OpenDesktopW("Default")` + `SetThreadDesktop(...)` **using pure `ctypes` only** before any GUI/GDI calls.
- **Crucial Pitfall**: Never import `win32ui` in the same thread before `SetThreadDesktop`, because MFC initialization creates a hidden helper window on the original desktop and causes `SetThreadDesktop` to fail with `ERROR_BUSY (170)`.
- For screen verification across GPU-accelerated Qt/Direct3D surfaces (`MMUIRenderSubWindowHW`), use `BitBlt` + `GetDIBits` without enabling per-monitor DPI virtualization in the background process.
