# Round 4 — `backlog-multi-tag` — coordinator — ⟳ NOT CONVERGED (Codex confirmation); DEFER, with the class fixed

REVIEW GAP: claude — round 4 is the SPLIT route's Codex confirmation round; round 3 ran both halves and they agreed on one finding.

```yaml
round: 4
fixes_nontrivial: true
subject: backlog-multi-tag
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: check-features, disposition: fixed}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
```

Codex on `20b6f675`. **X1:** a row under a table header the parser does not recognise (`| No |`), or under none, is
skipped before `unread` is recorded — master exits 1, HEAD 0. **X2:** filing #383 (open, feature-map) moved the suite
counts to 31 distinct / feature-map 3; the prose still said 30 / 2. **Held:** 61 paired probes otherwise clean; #383's
pre-existing omission confirmed on both refs; 30/30 checker mutations attributed; 2329 real.

**The pattern, said plainly.** Rounds 2, 3 and 4 each found the SAME hole — *the gate adopted a forgiving parser and
loses rows master's positional read saw* — by a different route (a misspelled header; an unreadable number; an
unrecognised header). None was caused by the previous round's fix, so thrashing is not armed by its letter; but the
folds closed ROUTES, not the class. The class is: **a `|` block the parser does not recognise must itself be an
error.** Every table block in `docs/backlog.md` must begin with a declared header.

**Route: DEFER** (accrete, redesign and split all lost). This ends the loop. The one fold permitted is the class fix plus
the count correction, because a gate looser than master's is not shippable under the owner's standing rule. Its
termination gate is EXECUTED: Codex r4's 61 paired probes re-run on both refs, zero master-red/HEAD-green. Any
finding after that is filed, not folded, unless it is itself a loosening.
