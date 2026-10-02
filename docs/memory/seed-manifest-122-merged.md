---
name: seed-manifest-122-merged
description: "FIRES-WHEN: citing backlog #122 or PR #311 — Backlog #122 CLOSED — PR #311 merged (32c56bfa). explainer-serve.py: 42 mutation entries, suite 144→196, 685/685/685/0. Successors #129 and #130 are OPEN"
metadata:
  type: project
---

**PR #311 merged 2026-09-16 as `32c56bfa`**, closing backlog **#122**.
`scripts/explainer-serve.py` went from **0 mutation entries to 42**; suite **144 → 196**; repo-wide
declared total **643 → 685**; full sweep **685 mutations, 685 killed, 685 attributed, 0 survivors**.
Its `WIDENED_MANIFEST_DEBT` pin is paid down, and `check-fixture-variation`'s `safe_path.root` pin
went with it (127 → 126).

⭐ **SEEDING IT FOUND SEVEN LIVE DEFECTS**, every one a decision with a careful comment and no check:
`SERVABLE` widenable until `/src/.env.local` was servable · a CORS header emittable · `HOST`
changeable to `0.0.0.0` · **the `/regenerate` allow-list deletable** (a POST body reached the command
line, answered `ok: true`) · a rebuild **timeout** reportable as `200 {"ok": true}` · **`/questions`
able to record nothing and answer ok**, including append→overwrite · `status()` exiting 0 with
nothing listening.

⚠ **OPEN SUCCESSORS, and they are NOT #122 reopened:**
- **#130** — 77 survivors outside the process layer; the sharpest cluster is `RELOAD_JS`, where six
  documented decisions survive because every case asserts **a token is present in a source string**
  rather than that the client behaves. Needs a delivery-level harness.
- **#129** — the process layer (`start`, `stop`, `detach_streams`, `main`). Needs a bound port.

⛔ **CODEX TIMED OUT ON ALL THREE ROUNDS** (`gate_ran=false` each time, `REVIEW GAP:` recorded in
every round doc). This merged on **three rounds of SINGLE-half review**. The stand-ins were
productive — rounds 2 and 3 each found a High against the previous round's own work — but
`docs/plugins.md` records the halves catch different classes. **Re-attempt Codex before working #130.**

The scope line is written down in the r3 coordinator doc: covering a 2,100-line file has no endpoint,
so #122 closed on its stated work (seed a manifest, add the key, raise the sum) plus a **clean
attribution audit** — all 42 entries kill the case they name, none by exception.

See [[a-case-can-pass-for-an-ambient-reason]], [[split-295-src-root-merged]].
