<!-- codex-review: model=gpt-5.5 -->

Low — `scripts/gen-dashboard.py:1828`: the repaired hiding check still parses the whole rendered HTML with `re.findall(r"([^{}]+)\{([^{}]*)\}", html)`, not just stylesheet text. Because it only filters selectors containing `.pick` at `scripts/gen-dashboard.py:1829` and then scans declarations at `scripts/gen-dashboard.py:1831-1833`, a harmless script string like `.pick{display:none}` would be treated as CSS and fail the self-test. It also misses CSS-valid `opacity:.0` because the bad list only covers `opacity:0;` / `opacity:0}` at `scripts/gen-dashboard.py:1832`. This is a test fragility, not a product regression in the current emitted rules: the real `.needs .pick` rule uses `opacity:.55` at `scripts/gen-dashboard.py:1339-1341`, and the hover/focus rule raises it to `opacity:1` at `scripts/gen-dashboard.py:1342`.

No Blocking or High findings.

Verification notes:
- Repair A looks correct in the committed script: it records `var stale = floaterNow();` before dispatch at `scripts/gen-dashboard.py:616-617`, refuses that same element by identity at `scripts/gen-dashboard.py:628-629`, and no longer bricks the button on fallback; it restores the label after 4s at `scripts/gen-dashboard.py:637-639`.
- The current generated dashboard tray creates a fresh floater (`/Users/kujinlee/explainers/dashboard.html:6954`) after removing the old one (`/Users/kujinlee/explainers/dashboard.html:6949`), so the identity comparison is sound against the live tray artifact I inspected. The under-3-character path removes the old floater, returns without creating a new one, and therefore terminates through the bounded fallback (`/Users/kujinlee/explainers/dashboard.html:6949-6952`, `scripts/gen-dashboard.py:630-639`).
- Re-derived the `h4` slice: questions render as `<h4 class="q">` at `scripts/gen-dashboard.py:980`, the self-test binds to that tag at `scripts/gen-dashboard.py:1807-1810`, and the tray injects heading buttons only into `h2, h3` in the generated artifact (`/Users/kujinlee/explainers/dashboard.html:6929`).
- Re-derived the collapsed-title guard: it scopes to `.entry .title{...}` at `scripts/gen-dashboard.py:2063-2069` and asserts the slice was actually found at `scripts/gen-dashboard.py:2072-2073`.
- Manifest/count checks passed: `gen-dashboard --self-test` was `325/325`; `check-plan-code --self-test` was `128/128`; `EXPECTED_MUTATIONS["scripts/gen-dashboard.py"]` is `68` at `scripts/check-plan-code.py:572`; the declared sum is `633` at `scripts/check-plan-code.py:3146`; `scripts/mutations/gen-dashboard.json` has 68 entries. The exact-count drift check is enforced at `scripts/check-plan-code.py:1055-1064`.
- I started `python3 scripts/check-plan-code.py --mutate .`; it reached 240/633 with no failures before I interrupted it for time, so full mutation verification is partial, not complete.

CONVERGED.
