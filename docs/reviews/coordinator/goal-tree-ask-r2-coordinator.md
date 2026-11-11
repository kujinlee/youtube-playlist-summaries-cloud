# Round 2 — coordinator: PR #558 (goal-tree Ask tray + collapsed answers + goal bindings)

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

**Subject:** `goal-tree-ask` at `1f43cf06` (the round-1 fold). Codex ran: NOT CONVERGED, one MEDIUM. Every other
fold (A's twelve malformed shapes, B's five escapes, C, D, E against all seven real ledger entries, F, G's
arithmetic) was tried and held. Self-test 471/471 at review time.

```yaml
round: 2
fixes_nontrivial: false
subject: goal-tree-ask
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: H, severity: Medium, aim: deliverable, fix_induced: false, component: answers-file, disposition: fixed}
```

| id | sev | finding | route |
|---|---|---|---|
| H (Codex M1) | MEDIUM | JSON's `\ud800` parses to an unpaired surrogate; `load_answers` accepted it, the page write raised `UnicodeEncodeError` and NO page was written, with nothing on stderr. Same property as A, a shape A's checks did not reach | fold |

**Fold.** `load_answers` refuses any row whose `key`, `q`, `a` or `asked` will not encode as UTF-8, by name ("entry
[1] carries text that is not valid UTF-8"). Two cases: the refusal at two distinct fields and positions (`a` at entry
0, `asked` at entry 1), and an end-to-end `write_page` with a tray-less composer that writes the page carrying the
warning, without raising. Disabling the check turns both red (471/473); restored 473/473. One mutation added
(`if unenc:` → `if False:`), pin 354 → 355.

**Not fix-induced:** A's checks were type checks; this is a value no type check sees. Class search: the other
JSON this page reads is the in-flight ledger, `.claude/inflight.jsonl` (`json.loads` at `scripts/goal-tree.py`
lines 1093 and 1205), and its text reaches the page, so a `\ud800` there would stop the page write the same way.
That path predates this PR and the ledger is written only by this repo's own scripts, so it is FILED, not folded:
backlog #608. `docs/goal-threads.md` is Markdown read with `encoding="utf-8"`, where invalid bytes fail at decode.
