# closing-table — round 9 — independent Claude half (Tier 1 of #149)

**Verdict: the central claim SURVIVES a serious attempt to refute it — but it is DEFENDED BY
NOTHING. 1 High, 1 Medium, 1 Low, plus three confirmations.** NOT CLOSED pending R9-1, which is a
one-line assertion and one manifest entry.

Subject: branch `fix/closing-table-log-turn-identity` (PR #328), +163/−8, read from
`git diff master...fix/closing-table-log-turn-identity`. Base is `master` `fab6f655` (#327).
F7 is mine, so this round was run to refute rather than confirm.

Constraints honoured: read-only git; every experiment on `cp -R scripts` in `mktemp -d`;
`check-plan-code.py --mutate .` never run against the working tree (I imported `run_mutations` and
ran only the three new entries against a copy); `docs/reviews/` top level untouched; this file is
the only write in the repo.

⚠ **Build attribution, so the numbers are not misread.** Warned-turn counts fell 744 → 315 between
r7 and now. That is #327's marker widening, merged as `fab6f655`, **not** anything in this PR.
Every figure below is measured against the PR's own build over **767** transcripts.

---

## Item 1 — "does `cut -f4 | sort -u | wc -l` yield a true turn count?" — CONFIRMED, refutation failed

I computed a ground-truth subject identity **independently of the column under test** (the uuid of
the first `assistant` record in the judged window's body), then compared:

| measurement, 767 transcripts, this build | value |
|---|---|
| judged windows encountered | 2,290 |
| … with `opener=None` (degenerate) | **0** |
| … opener present but no usable uuid | **0** |
| warning emissions (log lines) | 630 |
| **TRUE distinct warned turns** (ground truth) | **315** |
| **`cut -f4 \| sort -u \| wc -l`** | **315** — exact |
| subjects whose id CHANGED across consecutive stops | **0** |
| ids shared by TWO different subjects | **0** |
| `-` lines in the simulated log | **0** |

So the id is stable as the live window grows, the coalesced window's opener is not the wrong
fragment's, and the column is not decorative. This also independently replicates the docstring's
own table (315 / 630 / 2.00 mean / 71 worst).

**And it is retrievable**, which is the part that makes the column useful rather than merely
unique. Taking a real emission's id and grepping its transcript:

```
simulated line:  <when>	<session>	a commit	bf0db8ca-0d93-455d-8c17-762648997210
grep for that id in its own transcript → 4 records
the first is:    type=user, content "file it on #90 and finish the PR"
```

— the human message that opened the judged turn. Column 2 narrows the file, column 4 finds the
turn inside it.

I could not refute this. **CLOSED.**

---

## R9-1 — High — the wiring has NO falsifier: `run_decide` can log a constant and the suite stays green

All 13 new cases exercise `turn_id_of` and `log_line` **in isolation**. Nothing asserts that the
line actually written carries the **judged** turn's id. Two mutations on a copy of `scripts/`:

| mutation at the call site | result |
|---|---|
| `log_line(acts, when, session_id, turn_id_of(judged))` → `log_line(acts, when, session_id, "-")` | **SURVIVED — 151/151, rc=0** |
| → `log_line(acts, when, session_id, session_id)` | **SURVIVED — 151/151, rc=0** |

The first mutation **is this entire PR reverted at the only place it takes effect**: every line's
4th column becomes `-`, and `cut -f4 | sort -u | wc -l` returns `1` for any log, forever. The suite
does not notice. The second is subtler and worse for a reader: the column becomes one value per
*session*, so the count looks plausible and is wrong by the number of warned turns per session.

You wrote that you "verified one end-to-end case". That verification is not in the suite, and it is
the only claim the PR makes.

**Fix, and it is small.** The end-to-end case already exists and already reads the log file back:

```python
check("run: the warning was logged",
      (tmp / "warnings.log").exists() and "a push" in (tmp / "warnings.log").read_text(), True)
```

`prose.jsonl` is built from records whose opener is a known `user` record, so give that record a
`"uuid"` and assert the 4th field of the written line equals it (through `_safe`, per this file's
own rule). Then mutation `turn_id_of(judged) → "-"` dies via a case that names it, and the PR's
claim acquires a falsifier. One manifest entry alongside it.

⚠ Note the shape, because it is the one this subject keeps producing: the *unit* is thoroughly
tested — `turn_id_of` has six cases and every one of them kills a real mutation (I checked all six:
`getattr` → attribute access, dropping `isinstance(opener, dict)`, dropping `isinstance(uuid, str)`,
dropping the empty-uuid test, reading the wrong key — each went red via the case naming it) — while
the *composition* is untested. r7 F6, r8 R8-4, and now this: three rounds, three times the gap was
between two tested pieces rather than inside one.

---

## R9-2 — Medium — the `-` branch is unreachable from `run_decide`, so the docstring's justification is wrong and a real `-` would be a bug signal, not a value

`turn_id_of`'s docstring: *"`-` is returned for the DEGENERATE window — `windows()` returns a single
`opener=None` window when a transcript has no real-user boundary at all, which is reachable and
load-bearing (see its docstring)"*.

That is true of `windows()` and **false of the judged window**, which is the only thing
`turn_id_of` is ever called with:

```python
def judged_window(wins):
    for window in reversed(wins[:-1]):   # the degenerate case yields EXACTLY ONE window,
        ...                              # so wins[:-1] is empty
    return None
```

A degenerate transcript has no boundary → one window → `wins[:-1] == []` → `judged_window` returns
`None` → `run_decide` returns QUIET **before** reaching `log_line`. Measured: **0 of 2,290** judged
windows had `opener=None`, and **0 of 2,290** lacked a usable uuid.

Keep the defensive branch — a Stop hook must not raise, and mutation B proves the branch is live in
the suite. But two things should change:

1. the sentence. "Reachable and load-bearing" is inherited from `windows()`'s docstring and does not
   survive the move to this call site.
2. the reader's instruction. Since neither route to `-` can occur, **a `-` in column 4 means the
   guard is wrong about something** — it should be documented as an anomaly to investigate, not as
   "no id available".

That matters because `-` currently encodes **five** distinct conditions (no `opener` attribute /
`opener is None` / non-dict opener / no `uuid` key / empty `uuid`) plus `log_line`'s own
`turn or '-'`. `sort -u` collapses every one of them into a single line, so if the assumption ever
breaks the undercount is silent — the exact rule `check-sentinel-meanings.py` enforces elsewhere in
this repo: one value, one meaning; a conjunction in the meaning is the tell.

---

## R9-3 — Low — two survivors that are dead weight, both inside the new code

| mutation | result | why |
|---|---|---|
| `getattr(window, "opener", None) or {}` → `getattr(window, "opener", None)` | **SURVIVED** | the `isinstance(opener, dict)` guard already turns `None` into `uuid = None` → `"-"`. `or {}` cannot change any outcome |
| `def log_line(..., turn: str = "-")` → `turn: str = "X"` | **SURVIVED** | every case and the only caller pass `turn` explicitly; the default is dead |

Neither is a bug. Both are the *unfalsifiable guard* class already filed as #151 — code whose
removal no test can detect, in a file whose review history is largely about that class. The honest
options are to delete them (making `turn` a required argument is strictly better: it removes the
shape where a caller silently logs the default) or to give each a case. Not worth a round on its
own; worth not accumulating.

---

## R9-4 — the three errors you asked me to check are fixed

| your item | verified how | verdict |
|---|---|---|
| positional `split("\t")[3]` raised → unattributable | ran the "drop the turn column" mutation: **4 red cases, all with `[FAIL]` lines**, attributed via `log: the line carries FOUR tab-separated fields` | ✅ fixed |
| `check-fixture-variation` on identical `when`/`session` | ran it on the branch: `fixture variation OK — 592 parameter(s) examined across 56 file(s)`, rc=0. `when`, `session` and `turn` differ at every call site; `session or '-'` has its own case **and** its own mutation (`I` → 1 red, attributed) | ✅ fixed |
| two manifest entries sharing an edit anchor | 45 entries / **45 unique anchors** / 45 unique names; real `run_mutations` on the three new entries: `ok = True`, `survivors = []`, all three `attributed=True` | ✅ fixed |

⚠ One observation on the third, offered rather than filed: entry I clears the anchor-identity rule
by anchoring the **same physical line** with a longer prefix (`"""\n` + the return line). That is
the hole documented at the rule itself — *"r12 Low … two entries aimed at the SAME behaviour clear
this rule simply by shortening one"*. Benign here, because G and I genuinely test different
behaviours and both attribute. But what is protecting those two entries is your judgement, not the
gate.

---

## Item 5 — the Tier 2 deferral: SOUND, and I tested the premise rather than the argument

The deferral rests on *"the live log has recorded zero firings"*. The failure mode that would make
that rationalisation rather than reasoning is **the log being empty because the guard is broken** —
in which case the deferral rests on a dead instrument. So I replayed the current code over the
**9 transcripts touched since the guard merged** (`371d6fdb`, 2026-09-20 22:44:41 −0700):

| since the guard merged | value |
|---|---|
| judged turns with a closing act | **8** |
| of those, turns that WOULD warn | **0** |
| emissions that would have been logged | **0** |

The empty log is empty for the right reason. Against 94.6% of closing turns warning across history
(r7), 0 of 8 is a real change, not a broken path.

**Caveat, stated because n=8 is small:** all eight fall in the window where you are actively
working on this guard, which is maximum observer effect. It is evidence the mechanism is not dead;
it is not yet evidence about steady state.

And there is a second reason for the deferral that the docstring does not give, which I think is
the stronger one: **Tier 2 is unfalsifiable until the log has data.** An anti-nag journal cannot be
shown to work without a nag to suppress, and the Tier 1 column is exactly what will make the first
real measurement readable. Building them in this order is right, not merely cheaper.

⚠ The one thing I would add to #149: say what number would *trigger* Tier 2, now, while it is a
prediction rather than a judgement made after seeing the log. On replayed history the mean is 2.00
emissions per turn and 41% of emissions come from turns warned more than 3×; a trigger such as
*"Tier 2 when the live log shows mean > 1.5 or any single turn > 5"* turns the deferral into a gate
with a falsifier instead of a decision to revisit.

---

## Verdict, per item

| item | verdict | evidence |
|---|---|---|
| 1 — `cut -f4 \| sort -u \| wc -l` is a true turn count | **CLOSED** | 630 emissions → 315 ids → 315 ground-truth turns; 0 id changes across stops; 0 collisions; id greps back to the opening user message |
| 2 — the id is the judged turn's in every path | **CLOSED by measurement, NOT DEFENDED** | 0 anomalies in 2,290 judged windows — but see **R9-1**: the call site can log a constant and the suite stays green |
| 3 — degenerate window does not raise | **CLOSED (behaviour), NEW DEFECT (justification)** | mutation B kills the removal; but the `-` branch is unreachable from `run_decide` and the docstring says otherwise — **R9-2** |
| 4 — the 13 new cases held to the F6 standard | **NEW DEFECT** | 6 of 6 `turn_id_of` cases kill real mutations; the wiring has none (**R9-1**) and two new guards are unfalsifiable (**R9-3**) |
| 5 — the Tier 2 deferral | **SOUND** | premise independently verified: 8 acts-bearing turns since the merge, 0 would warn |
| self-test on the branch | ✅ | 151/151, rc=0; 151 static `check(` calls = the derived count |
| new manifest entries | ✅ | 3/3 caught and attributed, `ok = True` |

**Not mergeable-as-is only on R9-1**, and only because it is cheap: the PR's single claim should
not be the one thing in the file with no falsifier. Everything else here is a comment fix or an
accumulation note.

**REVIEW GAP: codex — not run for round 9.** This is the independent Claude half only.

---

**Coordinator correction, appended (not rewritten) — the `REVIEW GAP:` line above is now FALSE.**
The Codex half DID run for round 9, concurrently with this one: `scripts/codex-review.py` via
`gpt-5.5`, filed at `docs/reviews/coordinator/closing-table-r9-codex.md`, with
`docs/reviews/verdicts/r9-codex.verdict.json` recording `gate_ran=true`. The reviewer wrote its gap
line correctly on the evidence it had — it could not see a run that had not yet returned.

**Codex independently replicated this half's Item 1** over 773 transcripts / 3,267 boundaries: 630
emissions collapsing to 315 unique judged-turn uuids, 0 `-` ids, and the 71-emission worst turn
sharing one uuid. Three independent measurements of the load-bearing claim now agree.

Its one finding (Low) was stale counts in the dashboard entry, and it was right. ⚠ Those numbers
drifted AGAIN between Codex reading them and the fix landing, so they were DELETED rather than
corrected — the owners are the script's own declaration and `EXPECTED_MUTATIONS`, both gate-checked.

⚠ Codex states it did **not** run `check-plan-code.py --mutate .` to completion — interrupted at
223/827. Treat its mutation coverage as PARTIAL. The coordinator's own full run of that gate
returned `827/827 killed, 827 attributed, 0 survivors` on the pre-R9-fix tree; CI is the authority
for the current one.
