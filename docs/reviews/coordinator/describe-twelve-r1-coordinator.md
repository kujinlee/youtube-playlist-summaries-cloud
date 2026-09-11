<!-- codex-review: model=gpt-5.5 -->

`python3 scripts/gen-backlog-page.py --self-test  # 167 cases`; new group literal item count: 6.

**Blocking**
None.

**High**
None.

**Medium**
None.

**Low**
[scripts/gen-backlog-page.py](/tmp/rev-desc12/scripts/gen-backlog-page.py:229) — The new group claims “Six items, one shape,” defined as either a check whose failure is indistinguishable from a pass or a warning that reaches nobody. Reading all six rows, that does not hold cleanly: #94 is a guard/documentation mismatch where the behavior is right but the description/escape hatch is wrong; #104 is a stale sentinel lifecycle problem that blocks unrelated work once tripped. Those are process-state defects, not the same “looks green / warning ignored” shape as #92, #101, #111, and #112. This would fail if the grouping is meant to be a falsifiable claim rather than a loose bin.

**Checks Run**
`HOME=/tmp/rev-desc12/fakehome python3 scripts/gen-backlog-page.py` wrote the page with no GROUPS drift warnings; only the expected missing Ask-tray warning appeared.

`python3 scripts/gen-backlog-page.py --self-test` passed `167/167`. AST count is also 167 executable `case(...)` calls. Parent is `165/165`; the count moved by two executable cases, not three.

Mutation checks:
`if still:` -> `if False:` failed the two expected cases: “the undescribed block is printed…” and “its count is the number…”.
`if still:` -> `if True:` failed the new silent negative arm.
The same `if True` mutation survived on parent `28532810` at `165/165`.

Fact checks:
`check-review-rounds.py` reports `569 files... carry no round number`.
Mutation manifests are `gen-backlog-page.json = 5` and `gen-dashboard.json = 64`.
The `59, 61 and 63` claim is present in `docs/backlog.md` row #90 as historical measured evidence; I found no contradiction in this commit.

VERDICT: NOT CONVERGED

---

## Round 1 remediation, recorded by the coordinator

The single Low is **accepted and acted on**, and it was checked rather than taken on trust.

- **#104** — the coordinator had already reached the same finding independently before this
  review returned, and had moved it.
- **#94** — found by this reviewer only. The coordinator had "fixed" #104, believed the group
  sound, and stopped. Instance, not class.

Both moved to *Process, tooling and bookkeeping*. The framing was **narrowed to four items, not
widened to admit six** — widening is refused by the create/retire policy filed on backlog row #90
in this same commit, which says a framing widened to admit a member has stopped being a claim.

REVIEW GAP: claude — not invoked. The coordinator could not dispatch an independent Claude
reviewer in this session, so only the adversarial half ran. A coordinator self-review WAS
performed and found the #104 instance, but it is recorded here as the author checking their own
work, NOT as the second half: it missed #94, which is exactly the asymmetry
`docs/plugins.md` warns about when it says the two halves are not redundant.
