# Claude falsehood audit — branch `goal-page-mutations`, round 4

PROOF OF SUBJECT

```
$ git rev-parse HEAD
a0d977bb1e902cc2f29a990c8229df565adac0e7

$ python3 -c "import json;d=json.load(open('scripts/mutations/gen-goals-page.json'));print(len(d));print(d[-1]['expect'])"
25
front matter is NOT counted as an amendment
```

Working tree clean (`git status --short` empty); every review half and verdict for rounds 1–3 is
tracked, not untracked. All measurements below were taken at that SHA.

STATUS: COMPLETE

---

## Falsehoods found

### 1 — "the shape ADR-0006 actually had"

**Where:** `scripts/check-plan-code.py:2956`, verbatim:

```
    #     `⟳ SUPERSEDED` line inside the front matter — the shape ADR-0006 actually had.
```

Same sentence in the PR #293 body (*"The fixture now carries `⟳ SUPERSEDED` inside the front
matter — the shape ADR-0006 actually had — and entry 25 pins it."*) and in commit `8d67e55b`'s
message (*"the shape ADR-0006 actually had"*).

**Contradicted by:** `docs/adr/0006-stable-blob-addressing.md`. ADR-0006 has **never** carried a
`⟳` inside its front matter, in any of its four committed versions. Both of its `⟳` lines are in
the **body** — `:61` (`⟳ SUPERSEDED 2026-08-06`) and `:76` (`⟳ CORRECTED 2026-08-06`).

The branch's own source says so four lines from the fixture. `parse_adr`'s docstring, unchanged by
this branch:

> The amendment count is the point: **ADR-0006 sat at `status: proposed` while its body recorded two
> corrections.** Front matter alone is a claim about the day it was written.

That is exactly right and exactly the opposite of the provenance sentence: the front matter said
`proposed`, the *body* held the corrections, and that asymmetry is **why** the front-matter/in-body
split is load-bearing at all. The fixture text was lifted from ADR-0006 — `⟳ SUPERSEDED 2026-08-06`
matches `:61` verbatim up to the tail — and then attributed to the wrong half of the document.

**Command:**

```bash
$ grep -n "⟳" docs/adr/0006-stable-blob-addressing.md
61:- **⟳ SUPERSEDED 2026-08-06 — the segment is a `workspaceId`, resolved through a workspace row rather
76:  **⟳ CORRECTED 2026-08-06 (round 4, Codex #11) — `id` is NOT an independent UUID in this slice; it

# every committed version, front matter isolated the way parse_adr splits it
$ for c in $(git log --format=%h -- docs/adr/0006-stable-blob-addressing.md); do … ; done
61d91c0d fm_lines=8 ⟳ in front matter: False | ⟳ anywhere: True
a4a410be fm_lines=1 ⟳ in front matter: False | ⟳ anywhere: True
d6247fb9 fm_lines=1 ⟳ in front matter: False | ⟳ anywhere: False
f8703bcf fm_lines=1 ⟳ in front matter: False | ⟳ anywhere: False

# and the status line, confirming the docstring's account
$ git show a4a410be:docs/adr/0006-stable-blob-addressing.md | grep -m1 '^status:'
status: proposed — supersedes ADR-0002 if accepted
```

⚠ **The fixture and entry 25 are CORRECT — do not "fix" them.** The rule (a `⟳` in front matter
must not count as an amendment) is real, the fixture now reaches it, and entry 25 dies via
`front matter is NOT counted as an amendment` (measured below, §*attribution*). The false statement
is only the sentence claiming a real ADR had that shape. This is the same species as the round-1/2/3
provenance defect: a true engineering fact wrapped in a historical claim written from recollection.

⚠ `scripts/gen-goals-page.py:830-831` (*"ADR-0006 is the shape that matters: a ⟳ line INSIDE front
matter is a claim about the day it was written, not a recorded correction"*) reads as a statement of
the **rule** rather than of ADR-0006's shape, and is defensible. `:2956` and the PR body are not.

---

### 2 — "`git_pr_history` returning None … THREE manifest entries defend what happens DOWNSTREAM of it"

**Where:** `scripts/gen-goals-page.py:927-928`, verbatim:

```
    # ⛔ `git_pr_history` returning None is the ONLY thing in this file that can ever set
    # `pr_error`, and THREE manifest entries defend what happens DOWNSTREAM of it.
```

and `scripts/check-plan-code.py:585-586` in the same binding, verbatim:

```
    # and `git_pr_history` returning None is the ONLY thing in that file that can set
    # `pr_error`, which three of those fourteen entries already defended DOWNSTREAM of.
```

**Contradicted by:** `scripts/mutations/gen-goals-page.json`. Exactly **two** of the original
fourteen sit downstream of `git_pr_history` returning `None`:

| # | name | edit site |
|---|---|---|
| 5 | thread_prs stops recording that a document could not be read | `thread_prs`, deletes `error = True` |
| 11 | render_threads lets CANNOT RUN read as an honest absence | `render_threads`, `if t["pr_error"]` → `if False` |

The third entry being counted can only be **4** — *"annotate_code collapses CANNOT RUN into
documentation"*, whose edit is `cache[sha] = None if files is None else files_are_code(files)`.
That `None` comes from **`git_show_files`**, not `git_pr_history` (`annotate_code(prs,
show=git_show_files)`, `scripts/gen-goals-page.py:371`), and it never touches `pr_error`. When
`git_pr_history` returns `None`, `thread_prs` `continue`s — `annotate_code` is not on that path at
all.

**The first half of the sentence is TRUE**: `error = True` occurs exactly once in the file
(`:276`), reachable only from `got = history(d["rel"]); if got is None`.

**Command:**

```bash
$ python3 -c "import json;d=json.load(open('scripts/mutations/gen-goals-page.json'));
  print([i for i,e in enumerate(d,1) if 'pr_error' in json.dumps(e['edits'])])"
[11]
$ grep -n "error = True" scripts/gen-goals-page.py
276:            error = True
$ grep -n "def annotate_code" scripts/gen-goals-page.py
371:def annotate_code(prs: list[dict], show=git_show_files) -> list[dict]:
```

**Stated fairly, because this round has a record of over-claiming.** The *dashboard* and the *PR
body* phrase it as *"**None IS NOT []** is the property this file argues hardest for … three of the
original fourteen entries defended **its** downstream consumers"*, where *its* reads as the
None-sentinel property rather than `pr_error`. Under **that** reading three is right (4, 5, 11), and
those two sites are not false. The two sites quoted above bind the count to `pr_error` explicitly,
and under their own grammar the number is two. The cheap fix is to make the source sites say what
the dashboard says — the discipline, not the sentinel — rather than to move the number.

---

### 3 — "The canonical form named at `check-plan-code.py:1395`"

**Where:** `scripts/gen-goals-page.py:792-794`, verbatim:

```
        # is a THIRD producer shape and a reader is owed the reason. The canonical form
        # named at `check-plan-code.py:1395` is the single line `[FAIL] {name}: got {got!r}
        # want {want!r}`, and it parses because `parse_fail_names` truncates at the LAST
```

**Contradicted by:** `scripts/check-plan-code.py:1395` at this HEAD, which is about
`sys.stderr.line_buffering` and has nothing to do with the failure-line contract:

```
1395:        `capture_output=True`, as it has been since 3.9. Killing an unflushed process mid-write
```

The canonical form is named at `:1149`, `:1421` (the `parse_fail_names` docstring) and `:1440`.
`parse_fail_names` itself is at `:1410`.

**This branch broke its own citation.** It was accurate when written and went stale two commits
later, inside the same branch:

```bash
$ for c in e3e44637 8d67e55b a0d977bb; do git show $c:scripts/check-plan-code.py | sed -n '1395p'; done
def parse_fail_names(out: str) -> list[str]:                                      # e3e44637 — correct
    every `redirect_stderr` is inside `_self_test`, and the real `--mutate` path writes to the   # 8d67e55b
        `capture_output=True`, as it has been since 3.9. Killing an unflushed process mid-write   # a0d977bb
$ git blame -L 793,793 scripts/gen-goals-page.py
e3e446371 (Kujin Lee 2026-09-12 793)         # named at `check-plan-code.py:1395` is …
```

It is the only `<file>.py:<line>` citation this branch adds to `scripts/`
(`git diff 58d82658..HEAD -- scripts/ | grep '^+' | grep -oE '[a-z_-]+\.py:[0-9]+'` → one hit), so
this is an instance, not a class. The durable form is the symbol name (`parse_fail_names`), which
this repo already records as *"anchors bind by TEXT, so improving code breaks them"*.

---

## Claims checked and found TRUE

**Ratchets and counts, all measured at HEAD**

* `EXPECTED_MUTATIONS["scripts/gen-goals-page.py"] == 25`; `sum(EXPECTED_MUTATIONS.values()) == 549`; 41 keys; 41 files in `scripts/mutations/`; `len(gen-goals-page.json) == 25`.
* `524 → 549` across the branch: base `58d82658` computes `sum == 524`, 40 keys, no `gen-goals-page.py` key.
* The pinned membership list at `scripts/check-plan-code.py:2499` contains `"scripts/gen-goals-page.py"`.
* `# 75 cases` at `gen-goals-page.py:6`, and `--self-test` prints `75/75`. At `2246ed6d` the same suite printed `65/65`, so "65 → 75" holds.
* `14 → 25` and "+11" decompose as the source states (6 seam + 2 unfalsifiable fixtures + 2 argv + 1 `parse_adr`). The manifest at `2246ed6d` has exactly 14.
* `check-plan-code.py --self-test` → `128/128 passed`.

**The mutation claims, re-measured independently rather than read**

Each of the 25 entries applied to a `git archive HEAD` copy under a redirected `$HOME`, suite run,
red case names parsed with the consumer's own rule (`startswith("[FAIL] ")`, `[7:]`,
`rsplit(": got ", 1)[0]`), file restored between entries:

```
CONTROL rc=0 reds=0
25 killed, 25 attributed, 0 survivors
entries reddening EXACTLY ONE case: 21 of 25 — the four that redden two are 8, 9, 10, 11
```

* All 25 `before` anchors occur **exactly once** in the source; zero duplicate names; every `expect` string is present in the source.
* "Every new entry fails by REPORTING, not by crashing" — TRUE: every one exits rc=1 with at least one parseable `[FAIL]` line; a crash would have yielded zero.
* "every one attributes to the case it names, **ten of them to exactly one case**" (of the fourteen) — TRUE: entries 1–7, 12, 13, 14 redden one; 8, 9, 10, 11 redden two.
* "every new one reddening exactly one case" (the ten added in round 1, entries 15–24) — TRUE.

**CI**

* `CI on 8d67e55b` is real and green (`run 34704786388`, conclusion `success`), and its log contains the quoted line **verbatim**: `delivered scripts mutated: 41 file(s), 549 mutation(s), 549 killed, 549 attributed to the case each names, 0 survivor(s)`.
* `Follow-up to #292 (merged, master green on 58d82658)` — PR #292 is `MERGED` with merge commit `58d82658`, and master's CI run for that SHA is `success`.

**The provenance record**

* **No site states a count of files that paid the failure-line trap.** `grep -rn "NINE FILES|ninth|THIRD file|TWO BRANCHES|paid 8|brief-compose.py (8)|~540"` over `scripts/` and `docs/dashboard-entries.md` returns only *retractions* — every hit is a sentence saying the number was wrong and is deliberately absent.
* **The derivation command works as written.** `git log -S'[FAIL] ' --reverse --format='%h %as %s' -- scripts/<file>` ran against six files and returned dated commits for each (`-S` treats `[FAIL] ` as a literal, not a regex). ⚠ It is a *starting point*, not an oracle: on `check-gate-falsifiability.py` its first hit `9681aa61` is the commit that **added** the marker as a fix, not a payment. The comment's framing ("how often is a question for the command above") survives that; a future reader promoting its raw output to a count would not.
* **"`check-gate-falsifiability.py` never had this printer (it printed `FAIL`)" — TRUE.** `git show 9681aa61^` shows `print(f"  FAIL {name}\n       expected …")` — no bracket, and never the `  ✗ {label}` shape.
* **"§22 was introduced BY the commit that fixed `gen-backlog-page.py` (`050913f6`)" — TRUE, and it is the one kept historical claim.** `git log -S'A kill that attributes to nothing is a pass' -- docs/portable-practices.md` → `050913f6`, and that same commit is `868/36` on `scripts/gen-backlog-page.py` and `91/0` on `docs/portable-practices.md`.
* **"532 insertions, 8 deletions", and 540 being `--stat`'s changed-line total — TRUE, verbatim from git:**
  ```
  $ git show --numstat --format='' 58d82658 -- scripts/gen-goals-page.py
  532  8  scripts/gen-goals-page.py
  $ git show --stat --format='' 58d82658 -- scripts/gen-goals-page.py | tail -2
   scripts/gen-goals-page.py | 540 ++++++…
   1 file changed, 532 insertions(+), 8 deletions(-)
  ```
* **"`git log -S` finds no commit where this dict said 8" (brief-compose) — TRUE.** `git log -S'"scripts/brief-compose.py": 8' -- scripts/check-plan-code.py` returns nothing; walking every commit that touched the file, the key has only ever held `16`, and the manifest has held 16 since `f6c03fd8`.
* **"`gen-backlog-page.py` paid 5 entries on 2026-09-10, and `brief-compose.py` paid the same day" — TRUE** (`050913f6` and `f6c03fd8`, both `2026-09-10`; `EXPECTED_MUTATIONS["scripts/gen-backlog-page.py"] == 5`).
* Three surviving `eight`s in `check-plan-code.py` (`:790`, `:1212`, `:2889`) were checked and are **not** the retracted number: `:790` is `check-selftest-counts.py`'s 8 (correct), and `:1212`/`:2889` are `f6c03fd8`'s own prose, predating this branch, which the branch makes no claim about.

**The overwrite account**

* `docs/reviews/claude/goal-page-mutations-r1-claude.md` contains **no** "24 candidate weakenings" and **no** "11 SURVIVING" — 0 matches. Every occurrence of that phrase in `docs/reviews/` is a *quotation of the fabrication* inside r2-claude, r3-claude or r3-codex.
* Its **High is `parse_adr`** — `:70`, *"the file's most emphatically documented rule has a case that cannot fail for it"*, body explicitly `parse_adr`'s front-matter/in-body split.
* It contains **no numbered findings at all** — `grep "LOW-|HIGH-|MEDIUM-|BLOCKING-"` returns nothing. Its four Lows are unnumbered. So the retired PR-body attribution of `LOW-7 … LOW-11` had no source, as `a0d977bb` says.
* `8d67e55b` did fix three sites and not the fourth: its numstat is `gen-goals-page.py`, `check-plan-code.py`, `dashboard-entries.md` — no PR body. `e3e44637`'s message does say **FOUR PLACES**; `8d67e55b`'s does say **"Both sites"**. The escalation in `a0d977bb` is accurate.
* "`check-plan-code.attribute` … fixed at all four sites" — TRUE **for source**: `git diff 2246ed6d..e3e44637` removes the stale name at 3 sites in `check-plan-code.py` (including the user-facing diagnostic) and 1 in `gen-goals-page.py`. A fifth, in `docs/dashboard-entries.md`, was fixed in the same commit; the only surviving mention is `brief-compose.py:953`'s deliberate historical note.

**The severity table, against the filed documents**

| cell | claim | filed artifact |
|---|---|---|
| r1 Codex | High: the CANNOT-RUN producer is unmutated | `r1-codex.md:21` — *NOT-CONVERGED — 1 High, 3 Medium, 2 Low*; the High is `git_pr_history`'s CANNOT-RUN predicate ✓ |
| r1 Claude | High: `parse_adr`'s split has a case that cannot fail | `r1-claude.md:70`, `:345` NOT-CONVERGED ✓ |
| r2 Codex | **Blocking**: the new argv cases cannot fail | `r2-codex.md:12` — *NOT-CONVERGED — 1 Blocking, 1 Medium* ✓ |
| r3 Codex | 0 Blocking, 0 High (stale prose) | `r3-codex.md` — *"Verdict: NOT-CONVERGED — but with NO Blocking and NO High"*; `Blocking: none. High: none.` ✓ |
| r3 Claude | **Blocking**: this PR body was still the uncorrected r1 record | `r3-claude.md:36`, `:365` — *1 Blocking, 1 High, 2 Low* ✓ |

* **"Round 3's Codex half found no Blocking and no High" — TRUE**, and independently: the Codex verdict testimony `docs/reviews/verdicts/goal-page-mutations-r{1,2,3}-codex.verdict.json` all carry `gate_ran: true`, `exit_code: 0`, `model: gpt-5.5`, so the round-3 clean sheet is a gate that ran, not a gate that was skipped.

**Scope and "left open"**

* **"the last PAGE-PRODUCING generator with no manifest" — TRUE.** The generator-shaped scripts are `brief-compose.py`, `gen-backlog-page.py`, `gen-dashboard.py`, `gen-goals-page.py`, `gen-m4-manifest.py`, `page_chrome.py`, `page_markup.py`, `publish-arch-page.sh`. All have manifests except `gen-m4-manifest.py` (writes an object manifest, not a page) and `publish-arch-page.sh` (bash; copies an existing `docs/architecture.html` to `gh-pages` — it generates no page).
* **"`gen-m4-manifest.py` has none either, and is still outside `scripts/mutations/`" — TRUE**, and still true at HEAD.
* **"the round-1 Lows about entries that redden two cases while naming one are disclosed in the filed reviews and not closed here" — TRUE**, and correctly left without a number. ⚠ The filed r1-claude Low says *"three entries kill two cases each"* (8, 9, 11); measurement gives **four** (8, 9, 10, 11). That undercount lives only inside the filed review — a verbatim testimony artifact — and was **not** propagated to any source comment, dashboard entry or PR-body sentence (`grep "three entries|redden two|two cases each"` over `scripts/` and `docs/dashboard-entries.md` finds nothing about this). Recorded so round 5 does not re-derive it; not a finding, because reviews are filed as written.

**Behaviour and gates**

* **The seam changes no production behaviour.** `collect(DOCS, gen-backlog-page.py text)` run against the real repository at HEAD: **11 anchors, 41 threads, 96 PRs, 0 `pr_error`** — identical to the figures the PR body and dashboard quote from round 2.
* All nine gates `a0d977bb` claims green are green, run at HEAD: `check-plan-code --self-test` 128/128, `check-selftest-counts` (36 scripts), `check-anchors` (11 registered, floor 22 held), `check-docs`, `check-ratchet-contract`, `check-review-rounds`, `check-dashboard-entry`, `check-gate-falsifiability`, `check-fixture-variation` (453 parameters / 49 files). All rc=0.
* **"No code changed in this commit"** (`a0d977bb`) — TRUE: its `scripts/check-plan-code.py` diff is `21/6` and **every** added and removed line is a `#` comment.
* Round 3 added **zero** mutation entries — `a0d977bb` touches no manifest and no `gen-goals-page.py`. This makes the dashboard's *"+11 across review rounds 1 and 2"* the precise statement; the PR body's *"+11 across three review rounds"* is looser but reads as a span, and its own table and narrative attribute entry 25 to round 2. **Not filed as a falsehood.**

**Not re-measured, and said so rather than implied**

Three PR-body claims restate measurements taken in earlier rounds and are neither confirmed nor
refuted here: *"the `tag` CLASS repair kills four weakenings, including ones weaker than the shipped
entry"*; *"the dead-`or` fixture repair measured on both arms: red at `2246ed6d`, green at HEAD"*;
and the round-2 `--follow` probe returning `['101','100']` / `['101']`. Each is documented with its
method in the filed review it came from. The round-3 six-way argv re-probe **is** corroborated —
`r3-codex.md` names all six variants and their verdicts.

---

## Verdict

**NOT-CONVERGED.** Three claims are contradicted by artifacts: the ADR-0006 front-matter shape
(three sites, one of them the PR body), the "three downstream entries" count (two source sites,
measured two), and a stale `check-plan-code.py:1395` citation this branch broke itself.

None of them is a code defect. The 25 entries kill and attribute 25/25 over a control proved green
first, with zero survivors, re-measured here independently of CI; the seam changes no production
behaviour; every ratchet, sum, manifest length, case count and CI tally the branch states is exactly
right. **The code has been clean since round 2 and remains clean. The record is wrong for the fourth
consecutive round, and finding 1 is the same failure mode as v1/v2/v3 — a historical shape written
from recollection, contradicted by the file it names and by this branch's own docstring four lines
away.**
