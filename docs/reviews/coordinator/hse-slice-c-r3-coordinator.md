# Round 3 — `hse-slice-c` — coordinator — ⟳ NOT CONVERGED (Claude half) — ⛔ PHASE 6 ARMED

Claude (Opus, `docs/reviews/claude/hse-slice-c-r3-claude.md`) reviewed `cca375ab`: the round-2 fold (`c223fcbf`)
plus a manifest-only anchor fix (`cca375ab`, entry 157's find-string duplicated entry 156's; CI refused it).
2 MAJOR, 1 MINOR, no BLOCKER. It re-ran every round-2 input; all six are fixed at HEAD.

REVIEW GAP: codex — alternation (rounds 2+ run ONE half; Codex ran round 2).

```yaml
round: 3
fixes_nontrivial: true
subject: hse-slice-c
halves:
  claude: ran
  codex: alternation
findings:
  - {id: CM1, severity: High, aim: deliverable, fix_induced: true, component: optional-edges, disposition: filed}
  - {id: CM2, severity: High, aim: deliverable, fix_induced: false, component: edge-reader, disposition: filed}
  - {id: Cm3, severity: Medium, aim: deliverable, fix_induced: true, component: optional-edges, disposition: filed}
```

| Id | Finding |
|---|---|
| CM1 | the existence-guard proof accepts a test on a DIFFERENT path: an unreadable base is dropped, so `(Path.cwd()/"secret.py").is_file()` "guards" `run_path(HERE/"secret.py")`; closure says `optional:`, 0 gaps; the materialised script dies FileNotFoundError (`check-shipping-sets.py:310`, `:344`, `:374`) |
| CM2 | loads silently DROPPED, neither edge nor `unresolved:` — `p = p + '.py'`, `p += '.py'`, a `global` rebind, a tuple target or `except … as` shadowing a module name (the last also adds a false edge); the round-2 docstring's "never dropped" is false (`:379`, `:250-261`). Reader code is round 1's; the false claim is round 2's |
| Cm3 | the proof checks the guard's POSITION, not that the file exists when the load runs: a `global` rebind, `os.remove` or a lazy generator between test and load passes (`:286-290`) |

Live tree unaffected: self-test 126/126; `--map` and `--closure` 0 gaps; none of the 28 `unresolved:` lines hides a
shipped dependency; the one optional load (`regen-pages.py:871`) is guarded correctly.

**⛔ Phase 6 ARMED — THRASHING.** Round 2 (XM1–XM5) and round 3 (CM1, Cm3) both carry findings caused by the previous
round's own fold, in one component (`optional-edges`, with `edge-reader` beside it). The findings are NOT folded
here — `disposition: filed` records them as OPEN (the grammar has no `deferred`), and this document is rewritten with
the real disposition after Phase 6. An architecture review decides first whether a redesign removes the class. Questions it must answer:

1. **Can `optional-edges` be removed outright?** It exists for ONE live load (`regen-pages.py:871`). Shipping that
   target, or making the dependency unconditional, deletes the guard proof, and CM1 and Cm3 with it.
2. **Can the reader fail CLOSED by construction?** CM2 is the reader proving what a load is NOT (a list of forms it
   recognises, everything else falling through). Inverting it — only a positively read form is an edge; every other
   loader call is `unresolved:` — makes "never dropped" true by structure, not by enumeration.

Round 3 is the last folding round: from round 4 findings are FILED unless a BLOCKER (review-method §0 Q4c).
Scheduled for the next usage day (weekly usage 76% at 15:15 on 11-16, past the day's 75.3% cap).
