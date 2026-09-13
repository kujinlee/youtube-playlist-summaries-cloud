# `schema-index-bound-stale` (PR #296) — round 1, CLAUDE half

**VERDICT: the change is SOUND and the diagnosis is CORRECT, both measured on both sides. NOT
CONVERGED — 1 Medium, 3 Low.** The Medium is a written justification that execution falsifies; it
changes no verdict today and would mislead the next person to touch `probe_kind`. Nothing here
argues for reverting: master is red on exactly one assertion, that assertion is the stale one, and
the replacement probe is measurably the *strongest* of the four kind-probes rather than the weakest.

**Independence disclosure.** I did not open `docs/reviews/codex/schema-index-bound-r1-codex.md`.
I could not avoid learning its verdict: the Codex half is **committed on the branch under review**,
so `git log` printed the subject of `57fd9d17` (*"Codex r1: no Blocking/High/Medium, one Low — a
count labelled harness that was suite-wide"*) and the second dashboard entry — part of the diff I
had to read — names the grade and the finding. The findings below were reached from the code and
from runs; none of them is that Low.

---

## What I most feared, and what would have found it

**The fear:** a new probe whose ✓ is earned by *pre-existing* coverage rather than by
`unexpected()` — r3 HIGH 1's defect, where the POLICY probe went red because `_policies()` is
spliced into the `table:` digest, so the tick was paid for by mutation 27.

**What found it, or rather cleared it.** I ran the harness with `probe_kind` printing the drift
lines it matched on (`v4-show-drift.sh`). The four probes do not print the same thing:

```
>>> DRIFT LINES for POLICY:
  ⛔ AND 1 object(s) EXIST ON A RELATION M4 OWNS THAT THE MANIFEST DOES NOT NAME —
        + pol:video_artifacts.m4_mut_pol@9cb6c8df955b004d2ddb793589742037
>>> DRIFT LINES for INDEX:
  ⛔ 1 object(s) EXIST ON A RELATION M4 OWNS THAT THE MANIFEST DOES NOT NAME —
        + idx:workspace_videos.m4_mut_idx@627756ceac7479eda87c3b2007e05621
```

The `AND ` joiner is `check-live-schema.py:1004` — it appears only when `gone or bad` is already
non-empty, i.e. when the subset test *also* failed. POLICY carries it; **INDEX does not.** So for
the new probe the manifest is fully present, `residue()` is empty, and `unexpected()` is the sole
reason the gate is red. The INDEX case is the one kind-probe that could not be earned by anything
else in the file. That is the opposite of the defect I came looking for, and it is worth saying
plainly rather than burying under the findings.

It also settles the author's claim 2 by execution: the drift entry **names its relation** —
`idx:workspace_videos.m4_mut_idx` — which is the whole thing that changed on 2026-08-28.

---

## The diagnosis (author's claim 1) — VERIFIED, with a control

| Claim | Evidence |
|---|---|
| `idx` is attributable now | `check-live-schema.py:227` `ATTRIBUTABLE_KINDS = ("col","con","trg","pol","idx")` |
| the catalog emits `idx:<relation>.<index>` | `m4_catalog.py:416-421` — `'idx:' \|\| t.relname \|\| '.' \|\| i.relname`, `join pg_class t on t.oid = x.indrelid` |
| the 12 manifest `idx:` entries were regenerated with relations | measured: `live-manifest.txt` holds **161** objects, **12** `idx:`, and **0** `idx:` entries without a relation |
| the self-test already covers the kind | `check-live-schema.py:650-654` — `("INDEX", "idx:workspaces.ws_rev_uq@x6")`, added 2026-09-08 with the note that removing `idx` from the tuple had survived every case |
| the ✗ was a stale assertion, not a hole | **master, full harness, run via a symlink farm (no checkout): 54 ✓ / 1 ✗, exit 1.** The single ✗ is `BOUND: a bare INDEX on an M4 relation still PASSES — idx: carries no relation name — MUTATION SURVIVED`. Nothing else on master is red |

So the premise died, the assertion outlived it, and the red named it. The branch's reading is right.

---

## Findings

### MEDIUM 1 — `probe_kind` emits a SECOND assertion that IS an expected-pass, and it IS earned by SQL that never ran. The comment says that is impossible.

`scripts/mutate-live-schema-check.sh:341-346` justifies dropping `landed`:

> *"Here the assertion is expected-RED, matched on the drift SENTENCE, which only `unexpected()`
> emits: a mutation that never lands produces no sentence and reports MUTATION SURVIVED. **There is
> no green left for an unapplied mutation to earn.**"*

The first three sentences are true and I measured them. The last one is false, because `probe_kind`
does not emit one assertion — it emits **two**, at `:303` and `:308`, and the second is expected-`pass`:

```
report "…and undoing the $1 goes GREEN again" pass "$r"
```

**MEASURED** (`v3-create-fails.sh` — the branch harness with the probe's mutate SQL changed to
`create index m4_mut_idx on public.workspace_videos (no_such_column);`, so the mutation cannot land):

```
  ✗ ⭐ backlog 65: an unexpected INDEX names DRIFT (not merely a red gate) — MUTATION SURVIVED
  ✓ …and undoing the INDEX goes GREEN again
```

That ✓ is a green statement about undoing an index that never existed — precisely *"a green over an
unapplied mutation"*, which the surviving comment six lines below at `:357-360` calls **"the exact
shape this harness exists to prevent."** The branch removes `landed` from this case while writing
that the shape cannot occur, and it can, on the half of the probe the reasoning did not count.

**Two honest qualifications.** (a) It costs nothing today: the first half goes red, `fail=1`, the run
exits 1, so there is no false green at the harness level — the author's *soundness* argument survives
intact and I confirmed it. (b) The property is not new: POLICY, CONSTRAINT and TRIGGER have had the
same unguarded second half since backlog 65. What is new is the sentence asserting they don't.

**Why Medium and not Low.** This file's own history is a list of rounds spent on justifications that
read true and were not executed (`check-catalog-coverage.py:170-175` exists because of exactly that).
The comment is the reason a previously-reviewed guard was deleted, and the next person to extend
`probe_kind` — a fifth kind, or a refactor that keeps only the undo half — will read "structurally
impossible" and inherit an unguarded assertion.

**Falsifier.** Re-run `v3-create-fails.sh`; if the `…and undoing the INDEX goes GREEN again` line
comes back ✗, or if `probe_kind` is changed to emit one report, this finding is void.

**Cheapest fix (either, not both).** Fold a `landed`-style postcondition into `probe_kind` so all
four kinds get it — one call, four cases covered, and `landed` stops being a special case for the
FOREIGN bound. Or narrow the comment to *"no green left for the DRIFT assertion to earn"* and say
the undo half is still unguarded.

---

### LOW 1 — the probe was inserted UPSTREAM of an expected-PASS bound in the same commit that deleted the cleanup which used to backstop it. A failed undo now reds an unrelated assertion.

Two edits combine:

* the INDEX probe creates `m4_mut_idx` at `:347-349`, **before** the FOREIGN bound at `:369-375`
  (on master the index was created at `master:353`, **after** that bound at `master:346-349`);
* `drop index if exists m4_mut_idx;` was deleted from the shared cleanup at `:399-402`.

So `m4_mut_idx` now has exactly one dropper, and an expected-**pass** assertion sits downstream of it.

**MEASURED — branch** (`v2-undo-desynced.sh`, the probe's undo changed to
`drop index if exists m4_mut_idx_DESYNCED;` so the index is left behind):

```
  ✓ ⭐ backlog 65: an unexpected INDEX names DRIFT (not merely a red gate)
  ✗ …and undoing the INDEX goes GREEN again — MUTATION SURVIVED
  ✗ BOUND: a new column on a FOREIGN relation (videos) still PASSES — MUTATION SURVIVED
```

**CONTROL — master** (`v2m-master-leftover.sh`, master's cleanup drop desynced the same way):

```
  ✓ BOUND: a new column on a FOREIGN relation (videos) still PASSES — not M4's to bound
  ✗ BOUND: a bare INDEX on an M4 relation still PASSES — MUTATION SURVIVED
```

One red on master, two on the branch, and the extra one lands on a bound that has nothing to do with
indexes. This is the hazard the file documents in the comment it **kept**, at `:390-394`: *"failing
loudly in the WRONG ASSERTION sends the next reader to the wrong defect."*

The stated reason for the deletion — *"Two droppers for one object is a second owner that can
silently disagree"* (`:395-398`) — does not hold for this dropper. It is `drop index **if exists**`;
it cannot disagree with the probe, only absorb what the probe missed. That is what "belt and braces"
means, and it is why it was written with `if exists` in the first place.

**Reachability is genuinely low** and I am not overstating it: the undo is `if exists`, so it fails
only if the `docker exec`/session fails, in which case the run is red anyway. The cost is a second,
misattributed ✗, not a false green.

**Falsifier.** Re-run `v2-undo-desynced.sh` and observe one red rather than two.

**Fix.** Either move `probe_kind "INDEX"` below the FOREIGN bound, or restore
`drop index if exists m4_mut_idx;` to the `:399` cleanup block.

---

### LOW 2 — the corrected backlog row renders a stray literal `**`, and the word it meant to bold isn't bold.

`docs/backlog.md:93` now contains nested emphasis:

```
⚠ **RESIDUE — ✅ **PAID 2026-08-28, and the sentence it replaces is kept below … two weeks.**
```

Measured through the project's own renderer (`page_markup.render_inline`, which
`gen-backlog-page.py:827` routes every row cell through):

```
⚠ **RESIDUE — ✅ <strong>PAID 2026-08-28, … two weeks.</strong> It read: …
```

**Control:** `render_inline(master row 65).count("**")` → **0**; `render_inline(branch row 65)` → **1**.
`python3 scripts/gen-backlog-page.py` regenerates 113 rows cleanly, so this surfaces on the page a
reader actually looks at, in the heading of the correction itself.

**Falsifier.** The count above is 0 on the branch row.

**Fix.** `**RESIDUE — ✅ PAID 2026-08-28, … two weeks.**` — drop the inner `**`.

---

### LOW 3 — two stated justifications that do not survive checking. Both decisions are right; the reasons given are not.

**(a) The "only one artifact still asserts the old world" claim is short by one.** The author states
that only `docs/reviews/backlog-65-live-schema-drift-self-review.md:71` remains, deliberately, as a
dated record. `docs/reviews/backlog-65-live-schema-drift-claude.md:54-57` also carries it in the
present tense: *"`create unique index rev_uq on video_artifacts (video_id)` **passes** … the hole is
now described as being on the money path, **which is where it is**."* It is the same class — a dated
review record, correctly left alone — so the *decision* is right and only the enumeration is
incomplete. I swept `--include=*.md/*.py/*.sh/*.txt` for `idx:<indexname>` / `no relation` /
`create unique index`; everything else (`check-live-schema.py:224`, `:273-282`,
`check-plan-code.py:688-691`, `verify-exclusion-reasons.py:85-89`) is past-tense or unrelated.

**(b) The dashboard correction's stated reason for appending rather than editing is false as
written.** The new entry says *"rewriting 2026-09-12/4 would renumber ids that other entries already
point at."* Ids are `YYYY-MM-DD/N` counting **blocks** sharing a date, so editing the *text* inside
block 4 changes no ordinal; only inserting, deleting or reordering a block renumbers. The append was
nevertheless the correct and mandated action — `.claude/skills/dashboard/SKILL.md:29-36` says *"Append
one block. Never edit or delete an existing one"* — and that skill is where the loose reason
originates, so this is inherited, not invented. Flagging it only because the entry is a durable
record that a future reader will reason from.

**Falsifier for both.** (a) the claude review doc contains no present-tense assertion; (b) an in-place
text edit to a dashboard block changes some entry's id.

---

## Claim-by-claim, including the ones I could not break

| # | Claim | Result |
|---|---|---|
| 1 | Diagnosis: the bound was stale, not a hole | **VERIFIED** — see the table above; master's only ✗ is that bound |
| 2 | The fix asserts the drift sentence then undo-green | **VERIFIED**, and stronger than claimed — the INDEX probe is the only one of the four whose red is not also produced by the subset test |
| 3 | Dropping `landed` is safe because polarity subsumes it | **HALF TRUE — MEDIUM 1.** Sound for the drift half (measured: unlanded SQL → MUTATION SURVIVED). False for the undo half (measured: ✓ over SQL that never ran) |
| 3 | *failure mode:* `create index` fails silently under `ON_ERROR_STOP=1` | **Fails loud, correctly** — `v3` → ✗. But it reports *MUTATION SURVIVED*, which accuses `check-live-schema.py`, where `landed` said *"DID NOT LAND … treat this bound as NOT RUN"* and accused the SQL. A diagnostic regression, folded into MEDIUM 1 |
| 3 | *failure mode:* index-name collision | **Not reachable.** `${PREFIX}_raw` is a fresh `template` clone per run (`fresh()`, `:155-159`), `PREFIX` is PID-scoped (`:68`), `cleanup()` reaps on EXIT, and the template is built from `m4-base-db.sh`. If it ever did collide, `create` errors → no sentence → ✗ |
| 3 | *failure mode:* `workspace_videos` stops being M4-owned | **Fails loud.** `unexpected()` would skip the entry → no sentence → ✗. The COLUMN mutation at `:268` uses the same relation and would go red in the same run |
| 3 | *failure mode:* the sentence produced by some OTHER object | **Closed by the control chain, with LOW 1's caveat.** `:311-313` asserts the unmutated clone contains no drift sentence, and every probe asserts full-gate green after its undo. `report` does not abort, so once one undo fails every later probe's first half can be earned by the leftover — the general form of LOW 1 |
| 3 | *failure mode:* `db()` itself fails (no container, bad database) | **Fails closed, both halves.** No output of `check-live-schema.py` contains `EXIST ON A RELATION M4 OWNS` except the drift branch (`:1005`, sole occurrence), so a CANNOT-RUN yields ✗; and the undo half reads the exit code, which is non-zero. ⚠ Worth stating: `drift_out` has **no** three-way CANNOT-RUN handling of the kind `anon_ran` (`:111-115`) and `premise_rc` (`:124-129`) carry. Here the conflation errs safe in both directions, so it is not a finding — but it is the reason MEDIUM 1's diagnostic point matters |
| 4 | Removed cleanup is harmless because the probe owns the lifecycle | **LOW 1** — measured path where the undo does not happen and the leftover changes a later assertion's verdict |
| 5 | Substring `"EXIST ON A RELATION M4 OWNS"` names neither kind nor object | **Sound as built, fragile by design.** No earlier probe can leave residue while its own undo assertion passed; I verified the top-of-block control and all three preceding undo assertions exist and are expected-pass. The generic sentence means each probe's discriminating power is on loan from its neighbour — LOW 1 is the one path where that loan is called |
| 6 | Counts, and nothing else pins the total | **VERIFIED BY RUNNING BOTH SIDES** — table below. Also: `mutation N` labels are **29 on both sides**, so `check-schema-gates.sh:130`'s "29 mutations" and `check-catalog-coverage.MOVED_COVERAGE`'s citations (`mutation 10/17/22-26`, `:176-181`) are untouched; the harness is a `.sh`, so `check-selftest-counts.POPULATION` (`:83+`) does not and cannot pin it. Static `report` call sites go 51 → 50 while dynamic assertions go 55 → 56, which is exactly `+2 (a fourth probe_kind) −1 (the deleted bound)` |
| 7 | Backlog row 65 states nothing false | **True on the facts; LOW 2 on the rendering, LOW 3(a) on the enumeration.** The row's live measurement matches mine: 12 `idx:` entries, all with relations; the remaining FOREIGN bound is asserted as a passing case at `:374` |
| 8 | Dashboard: no renumbering, both parse, page regenerates | **VERIFIED.** master has 3 blocks dated 2026-09-12, branch has 5 — a pure append at `docs/dashboard-entries.md:7968+`, so the new ids are `2026-09-12/4` and `/5` and the correction references `/4` correctly. `check-dashboard-entry.py --self-test` 148/148 + 13/13 cannot-run; `check-dashboard-entry.py` → rc=0 *"an entry block was added"*; `gen-dashboard.py` → rc=0, 167 entries, tree still clean. LOW 3(b) on the stated reason only |

---

## Counts — measured on both sides, not inferred

| population | master `a1a5e1bf` | branch `57fd9d17` |
|---|---|---|
| `mutate-live-schema-check.sh` alone | **54 ✓ / 1 ✗**, exit 1 | **56 ✓ / 0 ✗**, exit 0 |
| `M4_PHASE=post scripts/check-schema-gates.sh` | not run — see below | **73 ✓ / 0 ✗**, exit 0, *"✅ all schema gates green"*, 15/15 |

The branch's corrected dashboard entry (2026-09-12/5) claims `54/1 → 56/0` for the harness and
`71/1 → 73/0` for the suite. **Three of those four numbers I reproduced exactly.** The fourth —
the suite on master — I did **NOT RUN**, deliberately: the brief forbids changing the branch, and
running master's suite means running master's `check-schema-gates.sh`, which I can only approximate.
It follows arithmetically (`73 − 56 + 54 = 71`, `0 − 0 + 1 = 1`) and the harness is the only gate the
branch touches, but arithmetic is not a measurement and I am labelling it as such.

**Not run, stated rather than implied:** the live-database sabotage quoted in the backlog row
(`create index m4_triage_idx on public.workspace_videos` against the shared `postgres`). I refused it
on the brief's own advice and used scratch clones. The equivalent measurement on a clone is `v4`
above, which produced the same shape of entry (`idx:workspace_videos.<name>@<digest>`); the live
control half I did reproduce — `check-live-schema.py --database postgres --expect-present` → **rc=0**,
*"checked all 161 objects"*.

---

## What I executed

Run from the branch working tree without ever changing its branch. Variants ran against a symlink
farm at `…/scratchpad/claude-half/fakeroot/` — every repo entry symlinked except `scripts/`, which is
a real directory of symlinks with one file replaced — so `cd "$(dirname "$0")/.."` resolves and the
tracked tree is never written. `git status --porcelain` was clean before and after every step.

| # | Command / variant | Result |
|---|---|---|
| 1 | `./scripts/mutate-live-schema-check.sh` (branch) | 56 ✓ / 0 ✗, exit 0 |
| 2 | `master-harness.sh` via the farm (`git show master:…`) | 54 ✓ / 1 ✗, exit 1 — the one ✗ is the stale bound |
| 3 | `v2-undo-desynced.sh` — branch, INDEX undo desynced | 2 ✗: the undo half **and** the FOREIGN bound → LOW 1 |
| 4 | `v2m-master-leftover.sh` — master, cleanup drop desynced | 1 ✗ only; FOREIGN bound stays ✓ → the control for LOW 1 |
| 5 | `v3-create-fails.sh` — branch, mutate SQL cannot land | drift half ✗ *(sound)*, undo half ✓ *(unguarded)* → MEDIUM 1 |
| 6 | `v4-show-drift.sh` — branch, printing the matched drift lines | `idx:workspace_videos.m4_mut_idx@6277…`, **no `AND ` joiner** |
| 7 | `M4_PHASE=post bash scripts/check-schema-gates.sh` | 73 ✓ / 0 ✗, exit 0, 15/15 green |
| 8 | `check-live-schema.py --self-test` | 119/119, matching its declared `--self-test  # 119 cases` |
| 9 | `check-live-schema.py --database postgres --expect-present` | rc=0, 161 objects |
| 10 | `check-docs.py`, `check-review-rounds.py`, `check-backlog-closure.py`, `check-dashboard-entry.py`, `check-anchors.py`, `check-guard-coverage.py` | all rc=0 |
| 11 | `check-dashboard-entry.py --self-test`; `check-review-rounds.py --self-test` | 148/148 + 13/13; 29/29 |
| 12 | `gen-dashboard.py`; `gen-backlog-page.py` | rc=0 each; tree clean |
| 13 | `page_markup.render_inline` on backlog row 65, both sides | master 0 stray `**`, branch 1 → LOW 2 |

⚠ One process-note on my own measurement, because this repo bills "cannot run" as a failure: my first
attempt at step 10 piped each gate into `tail` and read `$?`, which reported **rc=0 for every gate
including the ones that had not run** (`timeout` does not exist on this machine, so nothing executed).
Re-run capturing the gate's own status. The rc values above are the corrected ones.

---

## Recommendation

**Fix MEDIUM 1 and LOW 2 before merge; LOW 1 and LOW 3 are the coordinator's call.**

* MEDIUM 1 — one edit closes it either way: fold a `landed`-style postcondition into `probe_kind`
  (which also retires `landed`'s special case), or narrow the sentence at `:341-346` to the drift
  half and say the undo half is unguarded. The second is a two-word change and is honest.
* LOW 2 — one character pair; it is visibly wrong on a generated page.
* LOW 1 — moving `probe_kind "INDEX"` below the FOREIGN bound costs nothing and restores master's
  ordering property. Declining is defensible given how narrow the path is; declining *silently* is
  not, because the comment at `:395-398` currently reads as if the hazard were reasoned away.
* LOW 3 — prose only.

None of these is a reason to keep the suite red for a sixteenth day.

---

# Coordinator response — all four findings ACCEPTED, all four fixed, one proposed fix REFUTED

Every finding here was reproduced before it was fixed, and every fix was proved by re-running the
reviewer's own falsifier. The control (`./scripts/mutate-live-schema-check.sh`, unmodified) stays
**56 ✓ / 0 ✗, exit 0** throughout, so none of this is paid for by moving the happy path.

## MEDIUM 1 — fixed at the MECHANISM, not at the sentence

The reviewer offered two fixes and called narrowing the comment *"a two-word change and honest"*.
Narrowing was declined: the comment is not the defect. The unguarded expected-pass is, and it has sat
on POLICY, CONSTRAINT and TRIGGER since backlog 65 — the branch's sentence merely claimed it away.

`probe_kind` now carries **two** guards, generically, so no kind needs a hand-written predicate:

* **(a) did the SQL execute?** psql's own exit status under `ON_ERROR_STOP=1`. This also restores the
  diagnostic the first fix lost — the reviewer noted that an unlandable mutation reported *MUTATION
  SURVIVED*, accusing `check-live-schema.py` where `landed` had accused the SQL.
* **(b) was the mutation OBSERVED as drift?** If not, the undo assertion is **NOT RUN**, never a tick.

| falsifier | before | after |
|---|---|---|
| (a) mutate SQL cannot land (`no_such_column`) | `✗ … MUTATION SURVIVED` + **`✓ …undoing … goes GREEN again`** | `✗ the INDEX mutation DID NOT LAND (psql exit 3) — treat this probe as NOT RUN`, and **no second assertion at all** |
| (b) SQL lands but produces no drift (index on FOREIGN `videos(position)`) | — | `✗ … names DRIFT — MUTATION SURVIVED` (correct accusation) + `⚠ …undoing the INDEX — NOT RUN: the INDEX was never observed as drift` |

Finding (b) is new here: it separates *the gate failed to detect* from *the SQL failed to run*, which
the single exit-status guard alone would still have conflated.

## LOW 1 — accepted, and **the reviewer's second fix option does not work**

> *"Fix. Either move `probe_kind "INDEX"` below the FOREIGN bound, or restore
> `drop index if exists m4_mut_idx;` to the `:399` cleanup block."*

I restored the cleanup drop first, re-ran `v2-undo-desynced`, and got **two reds again**. That block
executes *after* the FOREIGN bound, so the leftover has already corrupted the assertion it was meant
to protect. ⭐ A filed finding's proposed fix is a hypothesis; this one was refuted by running it.

Fixed generically instead: a failed undo sets `residue=1`, and a downstream expected-pass reports
**NOT RUN** rather than a red it did not earn — the rule this file already applies everywhere else.

    branch, undo desynced:   ✗ …and undoing the INDEX goes GREEN again — MUTATION SURVIVED
                             ⚠ BOUND: a new column on a FOREIGN relation (videos) — NOT RUN: a
                               probe's undo failed above, so the clone is known dirty

One red, correctly attributed — master's property, with the reason stated instead of implied. The
`drop index if exists` was **kept** as well: the reviewer is right that `if exists` cannot disagree
with the probe, only absorb what it missed, so the deletion's stated rationale was wrong even though
the deletion was not what broke anything.

## LOW 2 — fixed and verified through the project's own renderer

`page_markup.render_inline(branch row 65).count("**")` → **0**, using the reviewer's falsifier verbatim.

## LOW 3 — both accepted

**(a)** The enumeration was short by one: `docs/reviews/backlog-65-live-schema-drift-claude.md:54-57`
also carries the old world in the present tense. Same class, same disposition — a dated review record,
correctly left alone. The PR body is corrected to name both.

**(b)** Accepted as written. The appended entry's stated reason ("rewriting would renumber ids") is
false for a pure text edit; only inserting, deleting or reordering blocks renumbers. The append was
still mandatory — `.claude/skills/dashboard/SKILL.md` forbids editing an existing block outright — and
the loose reasoning is inherited from that skill's own wording. Corrected in this round's entry rather
than by editing the old one.

## On the independence disclosure

Worth recording, because it is a structural fact and not a lapse: filing the Codex half **on the
branch under review** put its verdict in `git log` and its grade in the diff. Any second half that
reads the diff learns the first half's result. If true independence is wanted, the second half must be
dispatched before the first is committed, or from a tree that does not contain it.

## What I executed after fixing

    ./scripts/mutate-live-schema-check.sh                     56 ✓ / 0 ✗, exit 0   (control, unchanged)
    falsifier (a) unlandable SQL                              DID NOT LAND / NOT RUN, no tick
    falsifier (b) landed but undetected                       MUTATION SURVIVED + undo NOT RUN
    falsifier (c) undo desynced                               1 ✗, downstream bound NOT RUN
    M4_PHASE=post bash scripts/check-schema-gates.sh          73 ✓ / 0 ✗, exit 0, 15/15 green
    page_markup.render_inline on backlog row 65               0 stray `**`
    check-review-rounds.py                                    rc=0, 0 silent gaps
