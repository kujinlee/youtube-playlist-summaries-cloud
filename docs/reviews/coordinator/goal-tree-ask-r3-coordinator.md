# Round 3 — coordinator: PR #558 (goal-tree Ask tray + collapsed answers + goal bindings)

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

**Subject:** `goal-tree-ask` at `d304538b` (the round-2 fold). The Claude half ran: NOT CONVERGED, one MEDIUM and
four LOW. Self-test 473/473 at review time. Held under the reviewer's probes: a BOM, a 5,000-digit `asked` and
100,000-deep nesting all refused by name with the page written; an answer for each of the 185 live thread keys
rendered exactly once, none inside a fold; the ledger's (kind, number) match on the live ledger; the stale-page
source. The 30 s compose timeout was reasoned, not re-measured (the reviewer marked it INFERRED).

```yaml
round: 3
fixes_nontrivial: false
subject: goal-tree-ask
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: I, severity: Medium, aim: deliverable, fix_induced: true, component: answers-file, disposition: fixed}
  - {id: J, severity: Low, aim: deliverable, fix_induced: false, component: answers-file, disposition: fixed}
  - {id: K, severity: Low, aim: deliverable, fix_induced: true, component: self-test, disposition: fixed}
  - {id: L, severity: Low, aim: deliverable, fix_induced: false, component: answers-file, disposition: filed}
```

| id | sev | finding | route |
|---|---|---|---|
| I (Claude M1) | MEDIUM | round 2's cases pinned only `a` and `asked`: dropping `key` or `q` from the UTF-8 check stayed 473/473, while HEAD's refusal of both was correct but unheld | fold |
| J (Claude L3, first part) | LOW | an answers file it may not read (mode 000) raised `PermissionError`; no page written. Same property as A and H | fold |
| K (Claude L4) | LOW | the round-2 end-to-end case printed its expected warning to stderr on every passing run | fold |
| L (Claude L1, L2, L3 rest) | LOW | the tray check reads a stale `out`; non-UTF-8 composer stderr raises; a key is not lowercased; blank key or answer accepted | FILED, backlog #609 |

**Fold.** I: one answers file with a bad-text row per field, each at its own entry (key@1, q@3, a@4, asked@5); the
case expects the refusal to name `entries [1, 3, 4, 5]`. Four mutations, each dropping one field from the check,
each turns that case red. J: `OSError` joins the caught exceptions, with a case on a mode-000 file and a mutation
removing it. K: the end-to-end case runs under `contextlib.redirect_stderr` and now also asserts the warning reached
stderr. Each of the six mutations on these cases (the round-2 one included, re-pointed at the renamed case) was run
in place and turned its own named case red; restored, 474/474. Pin 355 -> 360.

**Fix-induced:** I and K came from round 2's own fold (cases that pinned half the fields, and an unredirected
stream). One round, one component; no THRASHING (that needs two consecutive rounds).
