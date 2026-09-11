<!-- codex-review: model=gpt-5.5 -->

`    python3 scripts/gen-backlog-page.py --self-test  # 167 cases`

Proof of subject: the remediated “Checks that can be wrong without looking wrong” group literal has 3 items: #101, #111, #112.

**Findings**
No Blocking / High / Medium / Low findings.

**Checks Run**
Reviewed the copied working tree at `/tmp/rev-desc12-r3`, not the live tree.

`HOME=/tmp/rev-desc12-r3/fakehome python3 scripts/gen-backlog-page.py` wrote the page with `113 rows, 70 open`; it emitted only the expected fake-HOME Ask-tray warning, not GROUPS/drift warnings.

`python3 scripts/gen-backlog-page.py --self-test` passed `167/167`. AST count of executed `case(...)` calls is also `167`, so the declared count is right.

Targeted mutations:
`if still:` → `if False:` failed exactly:
- `the undescribed block is printed, with its count and its remedy`
- `its count is the number of items with no sentence`

`if still:` → `if True:` failed exactly:
- `...and it is SILENT when every open item has a sentence`

On parent `28532810`, the `if True` mutation survived at `165/165`, confirming the new negative arm adds coverage.

`python3 scripts/check-review-rounds.py` exited 0:
`197 parsed, 18 pre-existing exemptions, 0 silent gaps`, with the known `569 files` warning.

**Remediation Attacks**
K: All three remaining members satisfy the narrowed framing. #101 and #111 are failures indistinguishable from a pass; #112 is the warning printed every run that nobody acts on.

L: The framing is still falsifiable, not just an inventory sentence. A reader could try to admit #104 under the broad “signal that does not do its job” phrase, but the concrete clauses exclude it. A reader could also argue #112 is not “without looking wrong” because it visibly warns, which makes the framing contestable rather than tautological.

M: #92, #94, and #104 fit “Process, tooling and bookkeeping”: wrapper detector, stop guard/docstring, and plan-gate sentinel. This does not look like an absorbing bin on this round.

N: Re-run checks passed as above; `check-review-rounds.py` exits 0.

Factual prose spot-checks held:
- `569` matches `check-review-rounds.py`.
- `gen-backlog-page.json` has 5 mutation entries; `gen-dashboard.json` has 64.
- #104’s “item 100 in this same group” is true.
- #90 no longer claims the stale `?`; current parsed bundles still include A-D and `—`.

VERDICT: CONVERGED

---

## Round 3 close, recorded by the coordinator

**CONVERGED with zero findings at any severity**, and the round was arranged so that a clean
result would mean something: it was asked specifically whether peeling two members had left the
framing as a mere INVENTORY of what it contains, which would be unfalsifiable. It answered no, and
gave both directions — a reader could try to admit #104 under the broad phrase and the concrete
clauses exclude it; a reader could argue #112 out on the grounds that it visibly warns. A framing
that can be argued in both directions is contestable, which is the property being claimed.

⚠ **A SINGLE REVIEWER'S `CONVERGED` IS WEAKER EVIDENCE THAN IT LOOKS, and this repo has measured
exactly that** — `docs/plugins.md` records a confident-but-wrong CONVERGED clearing a live defect
twice, and the memory note *dual review halves are not redundant* records Codex-only rounds
clearing a money guard that the skipped Claude half caught in one pass. Recorded here so the
verdict is read with the right weight.

⚠ **The severity curve did NOT decay monotonically** — 1 Low, then 2 Lows, then 0 — which on its
own would be the thrashing shape. It is not, and the discriminator is that every finding across all
three rounds named a member of the ORIGINAL six: #94 and #104 in r1, #92 in r2. No round found a
defect introduced by the previous round's fix. The rounds converged on a fixed set.

REVIEW GAP: claude — not invoked. Same constraint as rounds 1 and 2: only the adversarial half ran.
