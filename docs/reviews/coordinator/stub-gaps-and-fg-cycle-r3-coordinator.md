# Round 3 — `stub-gaps-and-fg-cycle` — coordinator — ❌ NOT CONVERGED (2 Medium, 3 Low) — split

```yaml
round: 3
fixes_nontrivial: false
subject: stub-gaps-and-fg-cycle
halves:
  claude: ran
  codex: "GAP: alternation — Codex took r2, so r3 is the Claude half (backlog #339, NEEDS-OWNER)"
findings:
  - {id: M1, severity: Medium, aim: instrument, fix_induced: false, component: stub-page, disposition: filed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: false, component: stub-page, disposition: filed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: false, component: stub-page, disposition: filed}
  - {id: L2, severity: Low, aim: instrument, fix_induced: false, component: stub-page, disposition: filed}
  - {id: L3, severity: Low, aim: records, fix_induced: true, component: records, disposition: fixed}
```

REVIEW GAP: codex — alternation under the reading this repository uses; backlog #339 asks the owner which governs.

The redesign bet is lost on two pre-existing Mediums: with a saved theme differing from the OS, the theme button's
initial `aria-pressed` is never checked; with a saved opt-out style, which option is marked is never checked. Lows:
option 1 is the only opt-out ever pressed; `--chrome-h` is read through a plain-object `style` that Chromium would
ignore. None is fix-induced (the reviewer says so per finding) and none is one of backlog #350's two named items — so
the ladder's next rung, SPLIT: what #350 and #351 named ships; the four are FILED as backlog #352. L3 (the #350 record
still said `['40px','40px']` and called both r5 mutants verbatim) FIXED. Everything else held: 9 entries bound and
killed, 112/112 attributed on re-run, six states clean, `--fg` tokens resolve, min bold 4.66:1. Round 4: Codex.
