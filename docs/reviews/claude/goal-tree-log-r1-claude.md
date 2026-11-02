# goal-tree NEEDS YOU audit — PR #433 (backlog #363), round 1, Claude half

Subject: `scripts/goal-tree.py` at `80c79603` (pinned worktree `pin-363`), rendered with
`python3 scripts/goal-tree.py --print` / `--page --out <mktemp>/gt.html`. `origin/master` has no commits
after `80c79603` (`git log 80c79603..origin/master` is empty), so the backlog read is current.
Mandate: does each listed item really wait on "a decision only the owner can make, open now"? Refuting, not
confirming. The coordinator's standing rule, in the owner's own words on the goal tree (2026-10-26 21:08):
*"try not to be blocked by non-critical decisions"*; CRITICAL = deploy, data loss, spend, a real loosening.

Sources: every row read in full from `docs/backlog.md` through `gen-backlog-page.parse` (345 rows, 0 unread,
215 open); the owner's 2026-10-28 answers (`owner-answers-1023.md`); the ledger `.claude/inflight.jsonl`
in the main checkout; the roles-review page `docs/explainers/2026-10-28-topic-suite-roles-review.fragment.html`.

## Classification

| Item | Class | One-line evidence |
|---|---|---|
| backlog #86 | BLOCKED-ON-OWNER-ACTION | Durable copy shipped (`b3d44f09`, PR #210); only the `/plugin update` precedence falsifier remains, which mutates the local plugin install. An action, not a decision. |
| backlog #90 | LIVE | Raised by the user 2026-09-03, *"explicitly later"*. Decision: split stories→roadmap / tasks→task list, or keep one table with a checked `Kind` column. It changes how the owner's own work is organised. |
| backlog #114 | NOT THE OWNER'S | Moving `.gitignore` out of `PROSE_FILES` TIGHTENS a gate, and keeping it is the status quo. Neither is a loosening. The row's own quoted authority (dev-process "any config → Branch + PR, always") already gives the answer: move it. The *"user's call"* text was the filer's, written 2026-09-14, before the owner's 10-26 rule. |
| backlog #117 | NOT THE OWNER'S | An engineering trade-off between three reshapings on a `NO-CALLER` script, so no CI consumes its verdict. Reversible. Option (1), a fenced `json` + `json.loads`, is the row's own "cheapest". The owner's 10-28 ruling on #327 (SIMPLIFY) may also reshape this tool, so check that first. |
| backlog #126 | **STALE** | Its NEEDS-OWNER tail says it *"waits on [backlog #193]'s is the restart feature wanted? decision"*. **The owner answered #193 on 2026-10-28: "A — not now, leave it open, unscheduled"** (owner-answers L1; #193's row now reads `DECIDED … NOT NOW`). The question it waits on is answered, so it is parked, not open. |
| backlog #194 | LIVE | Corpus and explainers are in the repo (`5128b99b` PR #360, `74a44551` PR #370). Decision: does `.claude/plans/` (gitignored at `.gitignore:96`) travel into git, and is a redaction pass needed first? Pushing it is outward-facing and cannot be undone once pushed, so it is legitimately the owner's. |
| backlog #198 | LIVE | The recall vocabulary for CONTEXT.md is assigned to a grilling conversation. That is the Phase-1 human step (`grill-with-docs`), and the row forbids inventing terms from identifiers. Decision: name the recall-subsystem terms, together with the owner. |
| backlog #211 | NOT THE OWNER'S | Changing it touches one constant (`DECLARED_RENDER[3]`), is reversible, and is not critical. The row's own analysis favours ⑴: rc 5's entry *"argues the OPPOSITE for the identical situation"*, so ⑴ restores consistency. Take ⑴ and say so. |
| backlog #222 | NOT THE OWNER'S | Scoping a guard. The row's own FAILS-IF condition already fired 4 times on 2026-10-02, which is the evidence for (a). The row says it is *"NOT a re-litigation of ADR-0014"*. Reversible. |
| backlog #224 | NOT THE OWNER'S | Options (a) and (b) are engineering: adding a dynamic half tightens D2. Only (c), amending ADR-0014's Decision to say "source text", would be a definitional loosening and a first-of-its-kind ADR edit. So the coordinator can take (a) or (b). Only choosing (c) would need the owner. |
| backlog #288 | NOT THE OWNER'S | The row supplies its own answer: *"a reader follows a `SKILL.md`; nobody follows a 2026-08 plan"*. So the rule-bearing surfaces are SKILL.md files and shared canons, not dated records or plans. Doc and guard work. |
| backlog #306 | NOT THE OWNER'S | Back-authoring r1/r2/r4/r7/r8 with hindsight is warned against by #318 and #314, so the recommended option is to change what `sequence_error` asks. The tool is `NO-CALLER` (#117), so no gate loosens. #327's SIMPLIFY ruling may reshape it. |
| backlog #307 | LIVE | The owner reserved it in their own words: *"work with me together when I get back to desk"*. Decision: does `MEMORY.md` keep its prose hooks at all, i.e. is the matcher the sole matching path? ⚠ #191's row says *"the keying fork is answered"* (2026-09-29), while #307 (2026-10-19) says the question is untouched. These are two different questions under one name (see Minor 3). |
| backlog #308 | NOT THE OWNER'S | The look is already decided by the owner and written in CONTEXT.md. What remains is a 52-page restyle *"with no defect underneath it"*, then a guard. That is scheduling work: no spend, reversible. |
| backlog #318 | NOT THE OWNER'S | Whether `redesigned`, `retreat` and `moot` count as ANSWERED is a vocabulary choice inside `check-review-decision.py`, which is `NO-CALLER`, so no gate moves. Each value has an author-written meaning to map from. |
| backlog #347 | **STALE** (mooted) | The row says it *"waits on the owner together with backlog #339"*. **The owner answered #339 on 2026-10-28: ONE REVIEWER PER ROUND in rounds 2+.** Under that reading no round 2+ has a second half reviewing an in-round fold, which is the case #347 asks about. What is left is writing that consequence into the template and re-reading the historical r6 header. That is coordinator doc work. |
| ledger `roles-review-answers` | LIVE | The roles page (#384's spec walkthrough, the human gate) shows **14 items "not yet answered"**: R1–R8, L1 and R-open-1..5. The owner's 10-28 answers cover only the 7 dashboard asks, not this page. ⚠ One NEEDS YOU line stands for about 14 decisions. |

**Counts:** LIVE **5** (#90, #194, #198, #307, roles-review-answers) · STALE **2** (#126, #347) ·
NOT THE OWNER'S **9** (#114, #117, #211, #222, #224, #288, #306, #308, #318) ·
BLOCKED-ON-OWNER-ACTION **1** (#86). **12 of the 17 items are not "a decision only you can make, open now".**

## The code's rule

The selection is `scripts/goal-tree.py:310-317`:

```python
def needs_owner(row: dict) -> bool:
    s = row.get("status") or ""
    i = s.rfind(NEEDS_OWNER)
    return (not row.get("closed") and i >= 0
            and not re.match(r"\W*answered\b", s[i + len(NEEDS_OWNER):], re.I))
```

`NEEDS_OWNER = "NEEDS-OWNER"` (`:78`); `needs_from_backlog` (`:342-356`) applies it to `gen-backlog-page.parse`.
A row is listed when its STATUS cell is open, contains the literal `NEEDS-OWNER`, and the text after the
last marker does not begin with `answered`. All 16 backlog markers were written by one audit pass,
`⟳ audited 2026-10-26: NEEDS-OWNER — …`. The rule faithfully reproduces that audit's judgement. Its
docstring states the bound (*"the marker is the claim"*). The defects below are mostly in the DATA the
rule trusts, plus one consequence of the rule's design.

## Findings

### MAJOR 1 — 9 of 17 items fail the page's own header claim; the markers carry an audit's judgement, not the owner's rule
- **Where:** `docs/backlog.md` STATUS cells of #114, #117, #211, #222, #224, #288, #306, #308, #318, as read by
  `scripts/goal-tree.py:310-317`. The header text is at `:533`: `"NEEDS YOU — {n} decision(s) only you can make, open now"`.
- **Input:** the current backlog.
- **Observed:** these 9 rows are reversible tooling or process choices. None is a deploy, data loss, spend or
  loosening. Most rows name, or plainly imply, their own recommended option. The owner's standing request is
  *"try not to be blocked by non-critical decisions"*. Yet the page tells the owner that 17 decisions wait on
  them. The cost is the same one `nothing-needs-you-must-read-the-dashboard` records in the other direction:
  a list the owner learns to distrust stops being read.
- **Fix (data, not code):** re-audit the markers. For each of the 9, take the recommended option, record it
  as `DECIDED <date> by the coordinator under the standing rule: <option>`, and remove `NEEDS-OWNER`.
  #224 keeps a sentence saying that only option (c) would need the owner. Optional code hardening: none
  needed; the rule is right to trust the marker, and the marker is what is wrong.

### MAJOR 2 — a row that waits on ANOTHER row's answer stays listed after that answer lands (#126, and #347)
- **Where:** `scripts/goal-tree.py:310-317`. It reads only the row's own text after its own last marker.
- **Input:** #126's status is `… NEEDS-OWNER — … travels with backlog #193 and waits on that row's *is the
  restart feature wanted?* decision`. #193's status is `… ⟳ **2026-10-28, decided by the owner (selection card): NOT NOW.**`
  The same shape holds for #347 → #339 (*"waits on the owner together with backlog #339"*), and #339 is now `DECIDED 2026-10-28`.
- **Observed:** both rows are listed as "open now" hours after the owner answered the question they wait on.
  When the owner's answers were recorded, the parent rows were updated (#193, #339) but their dependants were
  not. Nothing points from the parent row to its dependants.
- **Fix:** (1) data: update #126 to "parked with #193 (owner: not now, 2026-10-28)" without the marker, and
  update #347 to record the consequence of #339's ruling. (2) Process: the step that records an owner's answer
  should grep for `backlog #<N>` inside other rows' NEEDS-OWNER tails, and clear or re-word them in the same
  commit. (3) Optionally, the code could flag a listed row whose tail names a `backlog #N` that is closed or
  whose own status carries `DECIDED`/`answered`, rendering it as "may be answered by #N". That is cheap, and it
  turns a silent stale item into a visible one. Do not drop the row automatically; the dependency is prose.

### MINOR 1 — an open owner walkthrough, backlog #384, is listed only through a gitignored ledger line
- **Where:** `docs/backlog.md` row 384: `OPEN — filed 2026-10-27; needs an owner walkthrough (spec), not a build`.
  It carries no `NEEDS-OWNER`, so `needs_owner` returns False.
- **Observed:** today it reaches NEEDS YOU only through the ledger entry `roles-review-answers`, which lives in
  `.claude/inflight.jsonl` (gitignored, session-scoped). When that entry is removed or the session ends, a real
  open human-gate item disappears from the list while #384 is still open.
- **Fix:** mark #384 `NEEDS-OWNER — walk through the roles page (R1–R8, L1, R-open-1..5) before the spec`.

### MINOR 2 — one listed item stands for about 14 decisions, so the count undercounts
- **Where:** `:533` counts list items. `roles-review-answers` is one item, and its page shows 14 "not yet
  answered" boxes.
- **Fix:** either word the header as "N item(s)", or let the ledger text carry a count ("14 answers open").
  Low priority.

### MINOR 3 — #307's "keying question" and #191's "the keying fork is answered" are two questions with one name
- **Where:** `docs/backlog.md` #191 (`2026-09-29 — THE KEYING FORK IS ANSWERED BY MEASUREMENT … OPERATIONS`)
  against #307 (`Blocked on the same keying question as backlog #191`, `THE KEYING QUESTION IS UNTOUCHED`).
- **Observed:** a reader of NEEDS YOU who opens #191 finds it answered and may conclude that #307 is stale.
  It is not: #307's open question is whether the index keeps prose hooks at all, which the owner reserved.
- **Fix:** re-word #307's tail to name its own question rather than "the same keying question as #191".

### MINOR 4 — a candidate the rule misses: backlog #66's second half
- **Where:** #66 status: `The other half of the row's SHAPE — revive or retire the SDD-ledger row in docs/dev-process.md — was not on the card and is still open.`
- **Observed:** the row calls this "doc work", so it is probably correctly unlisted. But retiring a layer of
  the spine's three-layer roadmap rule edits a process the owner set. Listed here so the coordinator decides
  it deliberately rather than by omission. No other open row was found: I grepped 215 open rows for
  owner/user call, decision, waits on/for the owner or user, selection card and blocked on a decision. Rows
  #26, #27, #28, #53, #193, #327, #337, #339 all carry `DECIDED 2026-10-28`, and the rule correctly leaves them out.

### Not a finding — checked
- The dashboard source contributed 0 asks and 0 unreadable entries at this head, so the 17 are all backlog
  or ledger items. I did not audit the dashboard store's own resolution logic; that is outside this mandate.
- `answered` handling: the cases at `:937-945` cover the last-marker rule. Every audit tail that the owner
  has answered was rewritten to `owner question (answered 2026-10-28)`, which carries no marker, so none
  of those leak into the list.

VERDICT: NOT CONVERGED
