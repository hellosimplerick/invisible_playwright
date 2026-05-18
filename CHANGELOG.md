# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-05-18

### Fixed
- **Critical**: every `page.mouse.*`, `page.click(selector)`, `locator.click()`, `page.hover()`, `mouse.wheel()` failed on the patched Firefox 150 binary with `win.windowUtils.jugglerSendMouseEvent is not a function`. The Juggler JS was porting calls to a Playwright-specific C++ method that was never landed in the FF146→FF150 port; replaced with the Mozilla chrome-scope `win.synthesizeMouseEvent` helper which is present in FF150. Six call sites patched across `juggler/protocol/PageHandler.js` and `juggler/content/PageAgent.js`. Reporter: [@trob9](https://github.com/trob9) — [#9](https://github.com/feder-cr/invisible_playwright/issues/9).
- `_linkedBrowser.scrollRectIntoViewIfNeeded()` is now guarded at both call sites in `PageHandler.js` (`dispatchMouseEvent` and `dispatchWheelEvent`) — the method is not present on the shipped FF150 `<browser>` element, so the unguarded call threw before the mouse event was dispatched.

### Added
- `tests/test_mouse.py`: 12-case regression suite covering every patched code path (mouse.move/click/dblclick/right-click, modifiers, locator.click/hover, wheel, manual mousedown+up, off-viewport move, humanize intermediate moves, scroll-and-click on offscreen element). Test cases inspired by `microsoft/playwright-python/tests/async/test_click.py`.
- Community standards: `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `.github/ISSUE_TEMPLATE/*`, `.github/PULL_REQUEST_TEMPLATE.md`.

### Notes
- The Stealthfox humanize Bezier expansion continues to fire intermediate `mousemove` events; the swap to `synthesizeMouseEvent` does not change the human-trajectory behavior (verified by test).
- The reCAPTCHA v3 score (0.90) and FingerprintPro / CreepJS results documented in the README are unaffected — `synthesizeMouseEvent` is a legitimate Mozilla helper that does not increase the anti-detect surface.
- A binary refresh of the patched Firefox archive on GitHub Releases is required for users to receive this fix (the Juggler JS is shipped inside the archive). The `BINARY_VERSION` will be bumped to `firefox-2` in that release.

## [0.1.0] - 2026-05-13

### Added
- Initial public release.
- `InvisiblePlaywright` sync and async context managers — drop-in replacement for `playwright.sync_api.Browser` / `async_api.Browser`.
- StealthFox humanize hook: Bezier-curve mouse trajectories enabled by default.
- `_fpforge` Bayesian fingerprint sampler with ~400 fields per session.
- CLI: `invisible-playwright fetch | path | version | clear-cache`.
- Pinnable fingerprint fields via `pin={...}` (see `docs/pinning.md`).
- SOCKS5 / SOCKS4 / HTTP / HTTPS proxy support with auth.
- Linux x86_64 and Windows x86_64 binary support.

[Unreleased]: https://github.com/feder-cr/invisible_playwright/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/feder-cr/invisible_playwright/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/feder-cr/invisible_playwright/releases/tag/v0.1.0
