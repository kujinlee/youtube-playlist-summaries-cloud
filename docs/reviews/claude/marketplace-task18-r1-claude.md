# Task 18 (PR #617) — adversarial review r1, Claude half

Subject: branch `marketplace-task18` @ `0f8fb5f4`, `git diff origin/master...HEAD` (21 files).
Probes ran in a full clone at `scratchpad/task18/r1-claude-work/repo` (checked out at `0f8fb5f4`), never in the worktree.

## What I tried to refute and could not

- **FAILS IF clauses:** `recall: {"a": false, "b": "unanswered"}`; all six recall rows are `phase: "later"`; `grep -c 1-if-feasible docs/marketplace/inventory.json` → `0`. Both probe records (`probe-results.json`, `probe-results-dirname.json`): there are 7 runs each, and no `opened` path contains `/memory/`.
- **`recall.a = false` is a measured false, not an allow-list artefact.** I reproduced the `dirname` failure (see C4). The SUPPLEMENTARY run, with `dirname` allowed, exercised the hook properly (the unarmed hook opened 45 files, so it reached the matcher). It still produced no output unarmed. Armed, it gave a cwd-relative `--arm` instruction, and `--arm` returned rc 6. The code supports this independently: `recall-llm.py:120-122` keys ROOT, SENTINEL and CACHE_DIR to the install directory, `:417` `memory_dir` keys the slug to ROOT, and the plugin declares no hooks. So a stranger with an empty corpus gets nothing useful on day one, and `false` is honest.
- **rests_on:** I loaded every finding id against `scan-2026-11-17.json`. Every id is under the row's own component. `## 3.`, `### Effort (1) — recall` (spec:370) and `## 4.` (spec:413) all exist. The 23 `memory-corpus` ids are all used in the notes as C2/C3 reasons, grouped by kind (1:1-1:4 hosts and services, 2:1-2:17 out-of-package scripts, 4:2 a doc path, 5:1 a skill), and 4:1 is explicitly excluded. They are grounds, not a dump. The group attributions also check out: 1:1-1:3 and 2:3/2:4 are in `launch-roadmap-state.md` (group A), 1:4 in `reservation-release-slice-state.md` (B), and 2:8 and 5:1 in C files.
- **The 16 excluded files:** `groups()` reads the first table and returns 6/4/6/6. The names match `decision-5-suspect-files.md` lines 13-16. The build wrote 180 = 196 − 16 files, and `launch-roadmap-state.md`, `slice-history.md` and `process-conventions.md` are absent from the output.
- **Mutations:** `check-plan-code.py --mutate . --only scripts/build-shipped-corpus.py` in the full clone, with `node_modules` linked, gave `18 mutation(s), 18 killed, 18 attributed to the case each names, 0 survivor(s)`. Self-tests: build-shipped-corpus 20/20, check-selftest-counts 60/60, check-fixture-variation 67/67, check-shipping-sets 140/140 (pin 358/`f56c5c628641f10d` green).
- **The token: NO.** I compared the token file against `git diff origin/master...HEAD`, `git log -p origin/master..HEAD`, every file in the task18 scratchpad and all three `mkt18.*` run directories, both as the full string and as a 16-character prefix. There were 0 hits. Nothing was printed.

## Findings

### C1 — MAJOR — check 1 misses an original quote when only its punctuation changes (9 of 51 quotes survive whole) — `fix_induced: false`

`norm()` (`scripts/build-shipped-corpus.py:81-84`) removes `*_`\` characters, blockquote markers, case and whitespace, and nothing else. Commas, periods, `?`, `#`, `"`, brackets and apostrophes stay inside fragments and windows. So a quote that is short, or punctuated every few words, can be reproduced word for word with the punctuation changed, and the check passes it.

The experiment used the real D sources and the real built output (`../out`). For each extracted quote I planted `"Lesson: " + quote` into one extra output file and ran `check()`:

```
quotes 51
undetected with punctuation stripped: 9
   how-to-shape-a-message-to-me.md | #297 is NOT ready to merge — no review, `verify` pending.
   how-to-shape-a-message-to-me.md | The one confusion, wearing ten costumes
   how-to-shape-a-message-to-me.md | Merging #297 stays yours
   how-to-shape-a-message-to-me.md | Have you done this too?
   the-user-does-not-follow-in-real-time.md | changed mind. prepend the timestamp. format [mm-dd hh:mm]
   a-budget-stop-is-soft-with-a-reserve.md | do not stop tonight as un-used capacity by the reset time (tomorrow 2am) will be lost
   a-budget-stop-is-soft-with-a-reserve.md | how will you resume by yourself?
   owner-decisions-1113-marketplace-ff-392.md | use my name \"Kujin Lee\"
   route-agents-by-task-model.md | if it is just a win, apply in near term
undetected with curly apostrophe + , . -> ;: 3
   (ten costumes / timestamp format / win-near-term)
```

`use my name Kujin Lee`, the owner's name in the owner's words, passes the check. So does `do not stop tonight as unused capacity by the reset time tomorrow 2am will be lost`, which carries a date-like detail. The docstring's *What this cannot see* (lines 27-29) lists rewording, sub-six-word reuse and sub-three-word fragments. It does not list punctuation, so the stated bound is also wrong. The current paraphrases are clean: I grepped them for the name, dates, `#N`, percentages and model names and found only rule text. The gap is in the guard, not today's output.

**Fix:** in `norm`, map every non-alphanumeric character to a space (`re.sub(r"[^\w]+", " ", …)`) before collapsing, on both sides. Add a self-test case for punctuation and apostrophe variants, with a mutation that removes that normalisation.

### C2 — MINOR — finding no quotes in ONE D file is a silent pass; only finding none in ALL D files is CANNOT RUN — `fix_induced: false`

`check()` (`:146-154`) returns CANNOT RUN only when `frags` is empty across all six files. If one D source's quotes move to a form `quotes()` does not read (a plain `"…"`, or a blockquote that opens with `**"`), that file reports `0 quotes` and its quotes are simply not searched. The run still passes on the other five. The per-file counts are printed (`owner-priority-order-1102.md: 5 quotes`) but never asserted. The `sources.json` sha guard protects `--out` but not `--check DIR`. Today every D file has 5 to 13 quotes, so this does not fire.

**Fix:** treat any D file with 0 quotes as CANNOT RUN.

### C3 — MINOR — the paraphrases remove rule parameters that were never inside a quote — `fix_induced: false`

The owner's answer covers the quotes: *"paraphrase and anonymize the quote. Only convey essence of the example"*. The plan says *"every rule kept and no names, dates, numbers or project details **from the quote**"*. `shipped-corpus/a-budget-stop-is-soft-with-a-reserve.md` also removes numbers from the author's own rule text, which holds no quote:

- `every remaining day keeps ≥ 8% (push-day ceiling = 100 − 8 × days left after it)` became "a fixed minimum reserve";
- `steady ~14%/day`, `A=12 / B=20 %` became "a steady daily share" and "a lower bound A and an upper bound B";
- the cron line `7 0 * * *` and its fixed prompt prefix became a description;
- `~2–3 pt rainy-day reserve` and `~2 pts burned` became "small" and "a few".

The paraphrase points the reader to "the usage-pace script" for the numbers. `check-usage-pace.py` is not in the recall package, so a stranger gets an invariant with no value. 12/20 is defensible, because the owner's own 11-09 quote (`spend 12% to 20% per day`) carries it. 8% and 14.3 are not.

Either restore the non-quote parameters, or record that the owner's "not specifics" was read as covering rule text too, so this becomes a stated decision rather than a silent widening. The other five paraphrases keep their rules. I spot-checked `how-to-shape…` and `owner-priority-order-1102.md` against their sources: four numbered rules, the anti-starvation clause and the order are all present.

### C4 — MINOR — the experiment doc's *Outcome* describes hook behaviour the cited primary run never exercised — `fix_induced: false`

With `dirname` missing, line 41 resolves `REPO_ROOT=/` and the hook exits at line 61 without starting the matcher. I reproduced this in the clone:

```
$ env -i PATH=/nonexistent /bin/bash -x .claude/hooks/surface-recall.sh
.claude/hooks/surface-recall.sh: line 41: dirname: command not found
++ cd /../..
+ REPO_ROOT=/
+ MATCHER=//scripts/recall-llm.py
+ '[' -f //scripts/recall-llm.py ']'
```

The primary record confirms it: both hook runs show `opened` = 0. Even so, *Outcome* says *"the matcher exits 2 … which the hook swallows by design"*, and the table presents the two primary hook rows as results. Only the supplementary run (`mkt18.rc0f4sjc`) measured the hook. Its results file has no `repo_memory_assert` or `a_gate` key, and the doc states the FAILS IF assertion only over "all 7 records" of the primary run. I checked the supplementary records myself and found no `/memory/` path, so the assertion holds.

Separately, the `hook-surface-recall` row's note calls `dirname` "a host-tool gap". Every stranger host has `dirname`. It is a gap in the probe's allow-list, not in the product. The `a = false` verdict itself survives, on the supplementary run.

**Fix:** mark the primary hook rows as not measured (the hook exited before the matcher). Base the hook claims on the supplementary run, and state that the docs/memory assertion was also checked there. Reword "host-tool gap".

### C5 — MINOR — check 2 matches excluded files by NAME only — `fix_induced: false`

`check()` `:158-160` tests `p.name in excluded`. If an excluded file's content is copied into the output under any other name, or concatenated into `MEMORY.md`, check 2 passes. The plan's wording ("any of the 16 excluded files is present in the output") arguably means content. A body hash or a large-window text match against the 16 sources would close this. Low risk today, because `build()` only copies by name.

## Not verified

In the clone, a full `check-selftest-counts.py` live run reported `check-paid-caller-arrival.py` and `check-plan-code.py` self-tests red. I did not trace whether that comes from the clone's environment (a local-path `origin`, no `node_modules`) or from this diff. Neither file's self-test logic is changed by the diff beyond one POPULATION line in `check-plan-code.py`. Worth one CI look.

VERDICT: NOT CONVERGED
