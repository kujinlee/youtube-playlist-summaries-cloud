# Claude adversarial review — branch `goal-page-mutations`, round 3

**Subject:** `git diff e3e44637..HEAD` (the round-2 fixes, commit `8d67e55b`), with
`git diff 58d82658..HEAD` for context. Base `58d82658`.

PROOF OF SUBJECT

1. The `expect` of the **LAST** entry in `scripts/mutations/gen-goals-page.json`, verbatim:

       front matter is NOT counted as an amendment

2. The entry count: **25**.

3. The current fixture string passed to `parse_adr` in the case named
   `"front matter is NOT counted as an amendment"` (`scripts/gen-goals-page.py:833-834`), verbatim:

   ```python
       eq("front matter is NOT counted as an amendment",
          parse_adr("---\nstatus: accepted\n⟳ SUPERSEDED 2026-08-06 by ADR-0009\n---\n\nbody\n"
                    )["amendments"], [])
   ```

STATUS: COMPLETE

⚠ **Working-tree note, recorded rather than hidden.** While I reviewed, the coordinator was applying
round-3 fixes in this checkout in response to the Codex half. At the time of writing,
`git status` shows `M docs/dashboard-entries.md` and `M scripts/check-plan-code.py`. **My findings
are against HEAD (`8d67e55b`), the stated subject**, and I verified each one is *also* still present
in the working tree — none of them is closed by the in-flight edits. Where an in-flight edit is
relevant I say so explicitly.

---

## Findings

### Blocking — PR #293's body is the uncorrected round-1 record, and "both sites" is the same undercount that produced "TWO BRANCHES"

**Where:** the body of PR #293 (`gh pr view 293`). Compare `scripts/check-plan-code.py:571-587`,
`scripts/gen-goals-page.py:769-789`, `docs/dashboard-entries.md:7735-7749`.

**What:** the round-2 commit message states the fix as *"both sites now carry the derivation
instead."* There are not two sites. Round 1's own commit message says
*"THE PROVENANCE CLAIM WAS WRONG AND IS CORRECTED IN **FOUR** PLACES"*, and round 1's dashboard
entry carried the heading *"## ⟳ The provenance claim was wrong, and is corrected in four places"*.
Round 2 corrected three of them — `gen-goals-page.py`, `check-plan-code.py`,
`docs/dashboard-entries.md` — and left the fourth, **the PR body**, entirely untouched.

The PR body is not a stale copy of something harmless. It is the verbatim round-1 record, including
every sentence round 2 identified as fabricated:

```text
:27  They reached it from opposite directions. Codex read the manifest and saw the CANNOT-RUN
     producer was not on it. Claude staged the tree, applied **24 candidate weakenings and
     measured 11 SURVIVING**.
```

That is the exact sentence `check-plan-code.py:572-574` now flags as
*"A MEASUREMENT NO COMMITTED ARTIFACT CONTAINS"*. I re-verified the artifact:
`grep -n "24 candidate\|11 SURVIV\|SURVIVING\|staged the tree" docs/reviews/claude/goal-page-mutations-r1-claude.md`
returns **nothing** (356 lines). It is still presented in the PR as the justification for the
ratchet move.

It also still carries, uncorrected:

```text
:3   `gen-goals-page.py` was the **one sibling generator nothing mutated**
:5   ## 24 entries (14, then +10 from review round 1)
:45  Left open and said so: r1's LOW-7 (the sort *key* …), LOW-8 (`a.get("fanout", {})` …),
     LOW-9, LOW-10, LOW-11 — all disclosed in the r1 review with measurements.
:51  It said this was the **THIRD** file … it is the **NINTH** since 2026-09-06:
:58  | `check-gate-falsifiability.py` | **`  ✗ {label}`** | 2026-09-07 |
:68  **A convention did not hold nine times** …
:74  `EXPECTED_MUTATIONS` sum **524 → 548** (`gen-goals-page.py` 14 → 24)
:76  **24/24 kill via the case each names**
:82  Nine files have now paid; the tenth is only a matter of time.
```

Line 45 is a second fabricated attribution, independent of the first and not previously filed.
`grep -n "LOW-7\|LOW-8\|LOW-9\|LOW-10\|LOW-11\|sort key\|fanout\", {}"` over **both** committed
round-1 halves returns nothing. The committed `goal-page-mutations-r1-claude.md` has exactly four
Lows, none of them numbered and none of them those:

```text
209:### Low — `brief-compose.py (8)` is not supported by any committed artifact
231:### Low — "~540 lines of new rules" overstates the measured delta
241:### Low — entry 9's `expect` names a case whose title claims crash-safety …
259:### Low — three entries kill two cases each and name only one
```

So the PR tells a reader that five specific findings were *"all disclosed in the r1 review with
measurements"* when no filed review discloses any of them. Line 58 is the enumeration row round 2
identified as false (`check-gate-falsifiability.py` printed `FAIL`, never `  ✗ {label}`) — the row
that is the stated reason the whole enumeration was deleted rather than corrected a third time.

**Failing scenario:** merging is the human gate, and the PR body is the text at that gate. A
reviewer opening PR #293 to decide whether the `524 → 549` ratchet move is justified reads
*"Claude staged the tree, applied 24 candidate weakenings and measured 11 SURVIVING"*, goes to
`docs/reviews/claude/goal-page-mutations-r1-claude.md` to check it, and finds a document that says
nothing of the kind — which is precisely the experience round 2 says this branch exists to prevent.
The repo now contains three corrected accounts and one uncorrected one, and the uncorrected one is
the only artifact outside the repository.

**Evidence:**

```console
$ gh pr view 293 --json body -q .body | grep -c "24 candidate weakenings and measured 11 SURVIVING"
1
$ grep -c "24 candidate\|11 SURVIV" docs/reviews/claude/goal-page-mutations-r1-claude.md
0
$ grep -c "LOW-7\|LOW-8\|LOW-9\|LOW-10\|LOW-11" docs/reviews/claude/goal-page-mutations-r1-claude.md docs/reviews/codex/goal-page-mutations-r1-codex.md
docs/reviews/claude/goal-page-mutations-r1-claude.md:0
docs/reviews/codex/goal-page-mutations-r1-codex.md:0
```

⚠ The generalisable shape, which is why this is Blocking and not Medium: **round 2 fixed the
instance and re-made the counting error in the sentence describing the fix.** "TWO BRANCHES
undercounts" was the round-1 finding; "both sites" is the round-2 undercount of the same class, in
the commit message that announces the correction. The number of sites fell from four to two with
nothing retired. This is the branch's signature failure — a corrected account written the same
careless way — occurring inside the correction.

---

### High — `check-plan-code.py:2966` still asserts "HAS NOW COST NINE FILES", four lines above the paragraph that deletes the number and calls "ninth" wrong

**Where:** `scripts/check-plan-code.py:2966` (present at HEAD **and** in the working tree).

**What:** round 2's fix rewrote the `⟳` paragraph in this comment block to say the count is
deliberately not stored. It did not touch the block's **headline sentence**, which is the sentence
that states the count. The two now sit in one comment, contradicting each other:

```python
2966:    # ⛔ THE PROBLEM IS REAL AND HAS NOW COST NINE FILES. `parse_fail_names` reads a red case
…
2974:    # ⟳ 2026-09-12. "TWO BRANCHES" UNDERCOUNTS, AND THE REPLACEMENT COUNT IS DELIBERATELY
2975:    # NOT WRITTEN HERE. Three hand-written enumerations were attempted in one day — "third
2976:    # file", then "ninth, third with this shape" — and each was wrong in a new way …
```

"NINE FILES" *is* the "ninth" figure. It was introduced by round 1's own fix — `git show
2246ed6d:scripts/check-plan-code.py` has `COST TWO BRANCHES` at `:2919`; `git show
e3e44637:scripts/check-plan-code.py` has `COST NINE FILES` at `:2947` — and it is derived from the
enumeration four lines below now calls wrong on two counts (a file named that never had the printer,
a file omitted that did).

**Failing scenario:** a reader lands on line 2966 — the `⛔` headline, the line written to be read —
and takes NINE as the figure. If they read nine lines further they are told that figure was wrong
and is not recorded here. The comment's own stated policy ("the number is DERIVED, never stored") is
falsified by its first sentence. The claim in the round-2 commit message that the enumeration was
*"DELETED rather than corrected a third time"* is true of the file list and false of the count: at
this site the count survived the deletion of its own evidence.

**Evidence:**

```console
$ git show HEAD:scripts/check-plan-code.py | grep -n "NINE FILES"
2966:    # ⛔ THE PROBLEM IS REAL AND HAS NOW COST NINE FILES. `parse_fail_names` reads a red case
$ grep -n "NINE FILES" scripts/check-plan-code.py        # working tree, still present
2966:    # ⛔ THE PROBLEM IS REAL AND HAS NOW COST NINE FILES. `parse_fail_names` reads a red case
```

The sibling site was done correctly and is the model: `gen-goals-page.py:769` opens with
*"THE COUNT THAT BELONGS HERE IS NOT WRITTEN DOWN, ON PURPOSE"* — headline and body agree. Only
`check-plan-code.py` had its body rewritten and its headline left.

---

### Low — `brief-compose.py (8)` survives at `check-plan-code.py:1226`; the in-flight fix removed only the other instance

**Where:** `scripts/check-plan-code.py:1226`.

**What:** the working tree closes the `:2970` instance of this round-2 Low with an explicit
removal note. It leaves the second occurrence, in the diagnostic comment for the report-format
branch:

```python
1226:            # `gen-backlog-page.py` (5 entries) and `brief-compose.py` (8) — and BOTH times
```

The observable counts disagree with 8 exactly as round 1 said: `len(scripts/mutations/brief-compose.json)`
is **16** and `EXPECTED_MUTATIONS["scripts/brief-compose.py"]` is **16** (`:608`). The removal note
now added at `:2972` says the number *"is removed"* — singular, and not true of the file.

**Failing scenario:** instance-not-class. The next reader greps `brief-compose` and finds the number
the adjacent note says was withdrawn for being unsupported, with no withdrawal attached to it.

**Evidence:**

```console
$ grep -n "brief-compose.py\` (8)\|paid 8" scripts/check-plan-code.py
1226:            # `gen-backlog-page.py` (5 entries) and `brief-compose.py` (8) — and BOTH times
$ python3 -c "import json;print(len(json.load(open('scripts/mutations/brief-compose.json'))))"
16
```

⚠ A second, smaller problem in the new note itself: it says *"`git log -S` finds no commit where
this dict ever said 8."* Unqualified, that is now false — `git log -S'"scripts/brief-compose.py": 8'`
returns `8d67e55b` and `e3e44637`, because the round-1 and round-2 **review documents** quote the
query string. It is true only with `-- scripts/check-plan-code.py`, which is how Codex r3 ran it.
Add the pathspec to the comment or the next person re-running it gets two hits and concludes the
opposite.

---

### Low — "~540 lines of new rules" survives at two sites after three rounds

**Where:** `scripts/check-plan-code.py:569` and `scripts/check-plan-code.py:2921` (both at HEAD and
in the working tree).

**What:** filed as a Low by r1-claude (`:231`) and again by r2-claude (`:386`, second bullet), and
both lines are inside comment blocks the round-2 fix edited — they were on screen. The measured
delta:

```console
$ git show --numstat 58d82658 -- scripts/gen-goals-page.py
532	8	scripts/gen-goals-page.py
```

532 added, 8 removed, **net 524**. "~540" overstates both the net and the gross.

**Failing scenario:** minor on its own. It is filed because of what it is an instance of: this is the
third round in which a number in this branch's record is wrong in the direction that makes the work
look larger, and the sentence containing it is the sizing argument for the manifest.

Codex r3 classified this *"OPEN but not escalated here; it is old and not made worse by the round-2
fix."* I agree it is not made worse and I file it at the same severity r1 and r2 did — a Low that
three rounds have now named is a Low that should be closed or explicitly declined, not carried a
fourth time.

---

## Round 2 findings — closed or not

| # | Round-2 finding | Verdict | Evidence |
|---|---|---|---|
| 1 | **Blocking** — argv cases compared one call to one literal | **CLOSED** | I built 9 hardcoding mutants and every one dies via the case it names: hardcode path to fixture #1, to fixture #2, to `docs/x.md`, to `path.name`, to `str(ROOT / path)`; hardcode sha to `abc1234`, `0ff9911`, `HEAD`, `sha[:4]`. All `rc=1`, killed by **reporting**, attributed. Table below |
| 2 | **High** — r1's `parse_adr` High still open | **CLOSED** | `text.split("---", 2)` does treat the new fixture as front matter: `split` yields `['', '\nstatus: accepted\n⟳ SUPERSEDED…\n', '\n\nbody\n']`, `[-1]` is the body. Entry 25 (`body = text`) → `rc=1`, **no traceback**, red set is exactly `['front matter is NOT counted as an amendment']`. Killed by reporting |
| 3 | Provenance enumeration **deleted** rather than corrected a third time | **NOT CLOSED** | Correct in `gen-goals-page.py` and `docs/dashboard-entries.md`. `check-plan-code.py` kept the count in its headline (**High** above), and the fourth site — the PR body — was never touched (**Blocking** above) |
| 4 | `check-fixture-variation`'s credit corrected | **CLOSED** in source | `gen-goals-page.py:955-964` and `check-plan-code.py:2936-2947` both now state the anti-correlation. ⚠ `docs/dashboard-entries.md:7765` still reads *"⭐ The last two entries came from `check-fixture-variation.py`, not from either reviewer"*, but the corrected prose sits above it in the same entry, so I do not file it separately |
| 5 | `--follow` "impossibility" replaced with the real constraint | **CLOSED** | `gen-goals-page.py:988-996` now cites line 6, and line 6 verbatim is `python3 scripts/gen-goals-page.py --self-test  # 75 cases, pure functions only`. The citation resolves |
| 6 | "the ONE sibling generator with no manifest" narrowed | **CLOSED** in source | `check-plan-code.py:563-568` names `gen-m4-manifest.py`; `scripts/mutations/gen-m4-manifest.json` does not exist. ⚠ Still false in the PR body (`:3`), folded into the Blocking |
| 7 | Five comments citing nonexistent r1 finding IDs | **CLOSED, and the restatements are TRUE** | See below — I re-measured all three, rather than accepting them |
| 8 | **Low** — `brief-compose.py paid 8` | **PARTIALLY OPEN** | one of two instances closed in the working tree; see Low above |
| 9 | **Low** — two untouched r1 items | **SPLIT** — "ONE sibling generator" closed; "~540 lines" **OPEN** | see Low above |

**On item 7 — I did not take the restatements on trust, because a restatement that keeps the
attribution keeps the defect.** The comments no longer cite `MEDIUM-2/3/5`; they now say *"round 1
measured this as a SURVIVING weakening"*. Neither filed r1 half records those measurements, so I
reproduced them against the pre-branch file (`git archive 2246ed6d`, control **65/65** green):

```text
the unknown CSS class is dropped …        rc=0  SURVIVED   → claim CONFIRMED
the fan-out threshold slips to >2 …       rc=0  SURVIVED   → claim CONFIRMED
delete ONLY the dead `or` fallback  →     rc=1, red = ["a thread's PRs are the union over its
                                          documents, deduped, NEWEST FIRST",
                                          "one unreadable document poisons the thread's verdict"]
                                          → "reddened both of them" CONFIRMED, exactly both
```

All three restated claims are true. The finding-ID citations were the only defective part and they
are gone.

**On the new account of the overwrite incident (attack item 3) — it is accurate.** I checked each
assertion against the committed artifact:

* *"its High is `parse_adr`, not the seam"* — **true**. `goal-page-mutations-r1-claude.md:70`:
  *"High — the file's most emphatically documented rule has a case that cannot fail for it"*, and
  `:72` names `scripts/gen-goals-page.py:111` (the split) and `:69` (`AMENDMENT`).
* *"says nothing of the kind"* re "24 candidate weakenings / 11 SURVIVING" — **true**, 0 matches.
* *"the CANNOT-RUN producer being unnamed is CODEX's round-1 High"* — **true**;
  `goal-page-mutations-r1-codex.md` files it as its High.
* `gen-goals-page.py:955` attributes the seam to *"(round 1, both halves)"*, which looked like an
  overreach. It is **defensible**: r1-claude records it at `:332-339` under *Checked and found
  sound* — *"The genuinely untestable surface at HEAD is real … a mutation on them would have
  SURVIVED … it is a true positive"* — explicitly logged as confirmed-and-in-flight rather than as
  a finding. Not a finding.

Nothing is attributed to the surviving r1-claude review that it does not say. The corrected account
is the one part of this round's record that was written from the artifact.

---

## Checked and found sound

**The argv tracking assertions (attack item 1), probed nine ways.** All against a scratch copy,
control green at 75/75 first. `KILLED-reporting` means `rc=1` with the named case parsed out of the
output by the consumer's own `parse_fail_names` — not a crash:

```text
A1 path -> "docs/superpowers/specs/a-design.md"  (fixture #1)  rc=1 KILLED-reporting  attributed
A2 path -> "docs/superpowers/plans/z-plan.md"    (fixture #2)  rc=1 KILLED-reporting  attributed
A3 path -> "docs/x.md"       (the pre-r2 manifest value)       rc=1 KILLED-reporting  attributed
A4 path -> path.name         (derived, not the parameter)      rc=1 KILLED-reporting  attributed
A5 path -> str(ROOT / path)  (derived from a global)           rc=1 KILLED-reporting  attributed
B1 sha  -> "abc1234"         (fixture #1)                      rc=1 KILLED-reporting  attributed
B2 sha  -> "0ff9911"         (fixture #2)                      rc=1 KILLED-reporting  attributed
B3 sha  -> "HEAD"            (the pre-r2 manifest value)       rc=1 KILLED-reporting  attributed
B4 sha  -> sha[:4]           (derived from the parameter)      rc=1 KILLED-reporting  attributed
```

A2 is the case the brief asked about specifically — hardcoding to the **second** fixture value —
and it dies, because `[c[-1] for c in _argv[-2:]]` becomes `[z-plan, z-plan]`. A4 and A5 are the
"derives from something other than the parameter" probes; both die because the assertion pins the
**values**, not merely that they differ. The window `_argv[-2:]` is correct: the earlier
`"a readable git log becomes PRs"` call leaves `_argv == [a, a, z]`, and `_run_rc1` / `_run_boom`
(which record nothing) run *after* the assertion, so nothing displaces the window.

**All 25 entries, run by me rather than inherited.** Control green first, each entry applied to a
pristine copy:

```text
CONTROL rc=0  75/75 self-test cases passed
25/25 rc=1, zero tracebacks, every entry attributed to the case its `expect` names
  (entries 7, 8, 9, 10 redden two cases each — both disclosed in r1-claude's fourth Low; all
   others redden exactly one)
```

**Anchors (attack item 5).** All 25 `before` strings occur **exactly once** in
`scripts/gen-goals-page.py` — I counted every one, not a sample; no duplicate `before` strings and
no duplicate `name`s. Four containment pairs exist (entry 1 ⊂ 2, 18 ⊂ 17, 21 ⊂ 9, and the pair the
brief asked about, **22 ⊂ 16** — `"--follow", "--", str(path)]` inside entry 16's full `git log`
argv). All are safe: each entry has exactly one edit (25 edits / 25 entries) and `run_mutations`
restores the file between entries, so no two anchors are ever live together. Entry 23's
`"-1", sha]` is inside entry 17's `git show` anchor and is safe for the same reason.

**Ratchets and counts (attack item 4).** `EXPECTED_MUTATIONS["scripts/gen-goals-page.py"] == 25`
(`:587`); `sum(EXPECTED_MUTATIONS.values()) == 549` and the pinned case at `:2954` asserts 549;
manifest length 25; `# 75 cases` at line 6 matches the executed suite. The breakdown comment at the
sum site enumerates `6 + 2 + 2 + 1 = 11`, and 14 → 25 is eleven — **it adds up**. I verified the
composition independently by diffing entry names against `2246ed6d`: exactly 11 added, 0 removed,
and they partition as 6 seam / 2 unfalsifiable fixtures / 2 argv / 1 `parse_adr`, matching the
comment's four bullets.

**Gates.** `gen-goals-page.py --self-test` 75/75 · `check-plan-code.py --self-test` 128/128 ·
`check-selftest-counts.py` (36 scripts, every declared count verified by running it) ·
`check-fixture-variation.py` (453 parameters / 49 files) · `check-anchors` · `check-docs` ·
`check-ratchet-contract` · `check-dashboard-entry` — all rc=0.
`check-review-rounds.py` correctly reports round 3 as half-filed while this file is unwritten.

**`parse_adr`'s `maxsplit` is load-bearing and covered.** Dropping to `split("---", 1)` dies via the
named case. This matters over the real corpus: 8 of 13 ADRs contain more than two `---`
(ADR-0013 has 8), so `maxsplit=2` is what keeps the body intact rather than truncating at the first
in-body rule.

**One surviving weakening, and why it is not a finding.** Deleting the `startswith` guard —
`body = text.split("---", 2)[-1]` with no conditional — leaves the suite 75/75 green. It is **not a
live defect**: `parse_adr`'s only production caller globs `docs/adr/[0-9][0-9][0-9][0-9]-*.md`
(`:394`), all 13 matches start with `---`, and `docs/adr/README.md` — the one file that does not —
is excluded by the glob. `"x".split("---", 2)[-1] == "x"`, so the guard is behaviour-preserving over
every input the function can receive. Recording it rather than filing it: a manifest entry here
would pin a branch nothing can reach, which is the defect class rounds 1 and 2 were about.

**The seam still changes no production behaviour.** Production calls `git_pr_history(ROOT / rel)`
and `git_show_files(sha)` with no `run=`; the parameter defaults to `subprocess.run`. Only the
self-test passes a stand-in.

**The dated historical count at `gen-goals-page.py:767` is correct as written.**
*"paid all 14 of its manifest entries for it on 2026-09-12"* is a claim about a past event and the
manifest held 14 then. It should **not** be updated to 25 — that is the pinned-to-a-past-event case.

---

## Verdict

**NOT-CONVERGED.** 1 Blocking, 1 High, 2 Low.

The code is in good shape and I want to be unambiguous about that: round 2's two substantive fixes
both hold under adversarial probing that is strictly stronger than the mutations that ship — nine
hand-built hardcodings against the argv assertions, all killed by reporting; `parse_adr`'s split now
has a fixture that can fail for the rule it names; 25/25 entries attribute over a control I proved
green myself. Round 1 found rules nothing could reach, round 2 found cases that could not fail, and
round 3 found **none of either**. On the code, this branch has converged.

What has not converged is the record, and it has now failed in the same direction three rounds
running. The Blocking is not "a doc is stale". It is that the sentence announcing the correction —
*"both sites"* — is itself an undercount of exactly the kind it was correcting, dropping four sites
to two; and the site it dropped is the PR body, the only artifact outside the repository, the text a
human reads at the merge gate, and the one that still presents a fabricated measurement as the
justification for the ratchet move, plus a second fabricated attribution (LOW-7 … LOW-11) that no
round has previously caught.

Both remaining defects are edits to prose, and both are mechanical:

1. Rewrite the PR #293 body from the corrected account (`--body-file`, per `docs/dev-process.md` —
   the enumeration is full of backticks).
2. Delete "NINE FILES" from `check-plan-code.py:2966`, matching the headline to the body the way
   `gen-goals-page.py:769` already does.

I expect round 4 to converge. ⚠ Before it does, answer the question this round is the third instance
of: **the four sites were enumerated once, in round 1, and nothing holds that list.** Every
subsequent round has re-derived it from memory and got a smaller number. If "the record of this
class" is going to keep being corrected, the set of places it lives needs to be written down
somewhere a grep can reach — or the next correction will miss a fifth site nobody has thought of.
