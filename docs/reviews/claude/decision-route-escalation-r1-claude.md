# decision-route-escalation — round 1 — CLAUDE half (adversarial)

**Subject:** `git diff baseline-surveys...HEAD` (16 files). Stacked on `baseline-surveys`; the
previous slice is excluded.

**I executed.** Every finding below was produced by running code, not by reading it.
`python3 scripts/check-decision-scheme.py --self-test` → **64/64**, rc=0.
`python3 scripts/check-review-decision.py --self-test` → **91/91**, rc=0.
`--rederive` → rc=0, no material drift. `check-plan-code.py --self-test` → 178/178.
`check-selftest-counts` rc=0 (55 scripts, each verified by running it). `check-fixture-variation`
rc=0 (914 parameters, 69 files, 0 findings). `check-docs` rc=0. `check-review-rounds` rc=1 only
because this half was not yet filed. The full `--mutate .` was not run (CI is its authority, per the
brief); I verified the two rejected mutations by hand instead.

⚠ **No git writes were made.** All constructions were built in throwaway repositories under the
scratchpad. **Provenance disclosure:** a repo-wide `grep` for `route_next` returned one line of the
concurrently-running Codex half, which had independently found an adjacent shape of B3. My
construction for B3 is my own (`routes_tried` that never grows); I note the corroboration rather
than hide that I saw the line.

---

## Blocking

### B1 — The slice's headline measurement is refuted by running it: relocation gains ZERO subjects, not 97%

**Where:** `scripts/check-review-decision.py:rounds_for` (docstring), `docs/round-header-template.md`
(the ⭐ MEASURED paragraph), `docs/dashboard-entries.md`, `scripts/mutations/check-review-decision.json`
(the entry named *"relocation reads only the coordinator, restoring the 35% ceiling"*).

**The claim.** *"at least one HALF (codex|claude) …. 254 of 261 = 97% / a COORDINATOR document ……
91 of 261 = 35% … Reading only `coordinator/` capped feedability at 35% of rounds."* The 97% is
placed immediately after the 35% as the delta this change buys.

**The input.** Run the shipped `rounds_for` over all 57 subjects where the procedure applies, once
with `writers=("coordinator",)` (the old behaviour) and once with the new default.

**What is observed:**

| | readable with ≥2 rounds | raises (→ CANNOT RUN) | subjects whose round count changed |
|---|---|---|---|
| OLD (`coordinator` only) | **10** | 14 | — |
| NEW (`coordinator`,`codex`,`claude`) | **10** | 14 | **0** |

**Why.** Of **435 half documents** in `docs/reviews/{codex,claude}/`, **0 carry a parseable yaml
header** (measured by calling `parse_header` on each). They are all skipped by the `continue`, which
is exactly what the docstring's own ⚠ paragraph promises ("254 existing halves stay silent instead
of going red from birth"). So 254/261 = 97% is the rate at which half *documents exist*, and it is
presented as the rate at which *rounds become readable*. Today the second number is **0% of the 251
rounds that were previously unreadable**, and `rounds=0 on 81% of subjects` is unchanged. The live
run proves it: `check-review-decision.py` on this very branch prints `rounds=0` while
`docs/reviews/codex/decision-route-escalation-r1-codex.md` exists.

This is the defect class the repository's own memory calls *"an inference stated as MEASURED"* and
*"a measurement is only as good as its corpus"*, landing in the three artifacts a human reads to
decide the merge.

**The code is fine** — reading the halves is strictly additive and harmless. What must change is the
claim: 97% is a **ceiling for future rounds**, conditional on H4 below being solved, and the measured
delta today is zero. The mutation entry's wording ("restoring the 35% ceiling") should not imply the
ceiling moved.

### B2 — A corpus that cannot be read exits 0 and prints "all triggers quiet"; the comment asserting otherwise is false

**Where:** `scripts/check-decision-scheme.py:_corpus_now` (the `except (OSError, AttributeError,
ImportError)` handler, and its claim *"⛔ NOT a fail-open: the caller prints these as `None` and
trigger 6 is skipped, which is visible in the output line"*) and `main()`.

**The input.** Drive `main([])` with `corpus=lambda: {"median": None, "mean": None, "error": "SHAPES
went away"}` — the exact dict `_corpus_now` returns — over an armed baseline and an empty log.

**What is observed:**

```
rc = 0
decision-scheme: 0 row(s), 0 scored; pinned median 4 vs now None
  all triggers quiet
```

`'CANNOT RUN' in output: False`. `'SHAPES went away' in output: False`.
`'all triggers quiet' in output: True`.

**Why the comment is wrong in the decisive respect.** The `error` string is read on **exactly one
path** — `--rederive`, which prints it and returns 2 (`:362-364`). The default path, which is the one
CI runs, never looks at `now["error"]`. It prints `now=None`, which is *indistinguishable from an
empty corpus*, and then makes the positive assertion **"all triggers quiet"** — a claim that all
seven triggers were evaluated, when trigger 6 was not evaluated at all. Per this repository's
standing rule, *"'Cannot run' is a FAILURE, never a pass … Silence there is indistinguishable from
success and gets believed."* This is that, inside the guard whose stated purpose is refusing silent
passes, and it is the first thing a reader of the comment would believe is impossible.

**Reachability is not exotic.** `_corpus_now` resolves `SHAPES` from `check-review-rounds.py` by
`importlib`; any rename of that symbol, any move of that file, or any `docs/reviews` relocation
reaches this handler. It is also reached with **no exception at all** — see L1.

**Falsifier for a fix:** `main()` must treat `now.get("error")` as CANNOT RUN (rc=2) on the default
path too, or at minimum refuse to print `all triggers quiet` when any trigger was skipped. There is
no case and no manifest entry over either the handler or the `--rederive` error return, so neither
would redden today.

### B3 — "Escalation terminates" is enforced only by a function with no caller; a log that retries one route forever passes clean

**Where:** `scripts/check-decision-scheme.py:route_next` (the carrier of the termination guarantee),
`validate_row`, `t2_non_termination`.

**The input** (five rows, all individually valid):

```json
{"subject":"s","unit":"u","route":"accrete","routes_tried":["accrete"],"outcome":"continued","ranker_hit":true}   x4
{"subject":"t","unit":"v","route":"redesign","routes_tried":["accrete","redesign"],"outcome":"stopped","rounds_at_termination":3,"ranker_hit":true}
```

**What is observed:** `rc = 0`, `decision-scheme: 5 row(s), 5 scored`, **`all triggers quiet`**.
`validate_row` returns `None` on the retried row. `route_next(["accrete"])` returns `"redesign"` —
the row's own `route` contradicts it, and nothing compares the two.

**Why.** `route_next` has **no caller anywhere outside this file's self-test** (grepped across
`*.py`, `*.md`, `*.yml`, `*.json`). The ladder's no-retry rule is therefore asserted in a pure
function that nothing in the log, the validator, the triggers, or CI ever invokes:

* `validate_row` checks `routes_tried` *internally* (prefix, no dupes) but never relates it to
  `route`. A row betting on `accrete` while declaring `accrete` already tried validates.
* `t2_non_termination` reads **one row at a time** and needs `len(set(routes_tried)) >= 4`. If the
  author never grows `routes_tried`, exhaustion is invisible — and `routes_tried` is author-supplied.
* **No trigger ever groups rows by `(subject, unit)`.** The one trigger that could notice a conveyor,
  `t3_routes_collapsed`, is defeated by a single second unit on a different route, as above.

So the stated figure of merit — rounds-to-termination — has no mechanism behind it. The docstring's
"a route is never retried on the same unit … which is what stops the loop running forever" is true of
`route_next` and false of the artifact the guard reads.

**Falsifier for a fix:** `validate_row` (or a new per-unit trigger) must refuse a row whose `route`
is not `route_next(routes_tried)`, and must refuse a `(subject, unit)` whose `routes_tried` does not
grow between rows. Observation that would make it fail: the input above exiting 0.

⚠ A separate adjacent shape (an explicit retry recorded *after* exhaustion) was found independently
by the Codex half; the two findings share a cause and should be fixed together.

---

## High

### H1 — An `armed_at` that git parses differently silently disables trigger 1, the loudest trigger, with no CANNOT RUN

**Where:** `scripts/check-decision-scheme.py:paths_added_since` (`git log --since={since}`),
`subjects_starved`, `main()` (which only tests `if not armed`).

**The inputs and what is observed**, run against this repository:

| `armed_at` | `paths_added_since` returns | `subjects_starved` |
|---|---|---|
| `2026-10-20T10:00:00-07:00` (shipped) | 6 paths | `[]` |
| `2026-10-20` — **bare date** | **0 paths** | `[]` |
| `on merge` | 0 paths | `[]` |
| `""` | 0 paths | `[]` |
| `2026-13-45T99:00:00` | — (`git log` returns **35 commits**, rc=0) | `[]` |

`git log --since=2026-10-20 --oneline` returns **0** commits in this repo while
`--since=2026-10-19` returns **30** and `--since="2026-10-20 00:00"` returns all three of today's.
git 2.49.0, rc=0 in every case: approxidate never refuses.

**Why it matters, and why the bare-date form is the likely one.** `baseline.json` already mixes
formats — `"derived_at": "2026-10-20"` is a bare date two lines above `"armed_at"`. A maintainer
re-arming the ratchet will copy the neighbouring style, get an empty `added` set, and trigger 1 — the
trigger the docstring calls "THE LOUDEST … because it is how the predecessor died" — goes permanently
and silently quiet while the run reports `all triggers quiet`, rc=0. Nothing validates the field's
format, no case covers it, and no manifest entry targets `paths_added_since` at all.

**Falsifier for a fix:** parse `armed_at` with `datetime.fromisoformat` and exit 2 if it does not
parse, or pass git an unambiguous `--since=@<epoch>`. The observation that would make it fail: a
baseline whose `armed_at` is `2026-10-20` producing rc=0 with no complaint.

### H2 — The ratchet names HISTORICAL subjects via two measured doors, which is the backlog #56 shape it exists to avoid

**Where:** `subjects_starved` + `paths_added_since` (`--diff-filter=A`).

The `--diff-filter=A` choice survives a **pure** relocation: measured, `git mv` of a round document
is reported `R100` and does not appear in the added set. Two doors defeat it.

**Door 1 — a SHORT document relocated with a header added is an `A`.** Measured in a throwaway repo:
a 300-line half moved into `docs/reviews/claude/` with a yaml header prepended is `R099` (safe); a
3-line half through the identical commit is **`A`** plus a `D`. This slice's own
`round-header-template.md` invites exactly that commit shape ("a HALF may carry it instead").
Observation: `subjects_starved` then names a subject whose second round landed months ago, trigger 1
FAILs, rc=1, and the only way to make it green is to author a log row about ancient history — a gate
red from birth.

**Door 2 — `--since` filters on COMMITTER date, not author date.** Measured in the same fixture: a
commit whose author date is `2026-01-01` and whose committer date is today had **all four** of its
files reported by `git log --since=2026-06-01 --diff-filter=A --name-only`. This repository squash-
merges and rebases constantly; a squash merge produces one commit with today's committer date
carrying every file added on the branch. Any round document for a pre-arming subject that rides in on
such a commit is reported as added after `armed_at`.

**Scope:** 294 flat round documents are candidates for door 1 (see M1), and every open branch is a
candidate for door 2.

**Falsifier for a fix:** key the ratchet on something that is not a commit date — e.g. record the
starved population at arming time in `baseline.json` and subtract it — or use `--diff-filter=AR` with
`--follow`-equivalent handling plus author dates. Observation: relocating a short historical half and
re-running must not name its subject.

### H3 — `rounds_for` reads ONE document per round and silently discards the other half, in 66% of rounds

**Where:** `scripts/check-review-decision.py:rounds_for` — `if h["round"] in by_round: continue`,
with `writers` as the outer loop.

**The input.** A tree with both halves carrying a header for round 1:
`codex/s-r1-codex.md` with one Low finding on `codex-only`; `claude/s-r1-claude.md` with **two
Blocking** findings on `claude-only` and `claude-two`.

**What is observed:**

```
rounds read:     [(1, 'codex/s-r1-codex.md')]
components seen: {'codex-only': 1}
with writers reversed (claude first): [(1, 'claude/s-r1-claude.md')]
```

The claude half's two Blocking findings are invisible to `scope_tally`, `review_scope`, `scope_lead`,
`thrashing_component` and `converged`. Swapping `("coordinator","claude","codex")` changes the answer
and **nothing notices** — no self-test case constructs two headered halves for one round, and the
manifest's `"a HALF outranks the coordinator"` entry only exercises coordinator-vs-half, so a mutation
of the half ordering would survive.

**Why this is not covered by the docstring's reasoning.** The ⚠ paragraph justifies precedence as
"a coordinator … adjudicates the two halves and a half speaks only for its own reviewer." That
argument says the two halves should be **merged**, not that codex should silently beat claude. And by
this slice's own measurement **171 of 261 rounds (66%) have both halves** — so under the new reading,
in the majority of rounds the decision is computed from one reviewer's unadjudicated findings with the
other reviewer's discarded. `review-method.md` elsewhere records that the halves are *not* redundant.

**Falsifier for a fix:** union the findings of all half documents for a round (deduplicating by `id`),
keeping coordinator precedence; add the two-headered-halves case and a manifest entry that reddens on
the writer order.

### H4 — A half document structurally CANNOT carry the required header, which is why 0 of 435 do — and the 97% ceiling is unreachable without a grammar change

**Where:** `docs/round-header-template.md` (the new "a HALF may carry it instead"), the `REQUIRED`
enum enforced by `scripts/check-review-decision.py:_validate`.

`_validate` raises unless every finding carries `severity`, `aim`, `fix_induced` **and
`disposition`**, and `disposition`'s allowed set is `{fixed, filed, declined}` — the template defines
it as *"what Q3 decided"*. `fixes_nontrivial` is likewise required per round and defined as *"were
this round's fixes more than a reworded line?"*.

**Both are post-fold facts.** A half is written before the coordinator adjudicates and before any fix
exists, so a reviewer filling in `disposition` at authoring time is guessing at a decision that has
not been made, and `fixes_nontrivial` refers to fixes that have not been written. (This review is the
worked example: I deliberately did not attach a header, because I cannot honestly state either field.)

This is the mechanism behind B1 — it explains both the measured 0/435 and why the 97% will not arrive
by relocation alone. The relocation needs either (a) a half-flavoured header whose required set omits
the post-fold fields, or (b) an explicit amend-after-the-fold step. Neither is in this slice, and the
template asserts the relocation is complete ("The grammar is unchanged … so this is relocation, not a
second format").

**Falsifier:** author a half header honestly at review time. If `disposition` cannot be filled without
inventing a value, the claim is unfixed.

### H5 — The dashboard entry — the artifact the human reads to decide the merge — states case counts that are wrong

**Where:** `docs/dashboard-entries.md`, the `2026-10-20 [needs-you]` `<!--tech-->` block.

**It says:** *"New `scripts/check-decision-scheme.py` — **51 cases**, 11 mutations, 0 survivors"* and
*"Suites **87/87** and **51/51**"*.

**Measured:** `check-decision-scheme.py --self-test` → **64/64**; `check-review-decision.py
--self-test` → **91/91**. The docstrings declare 64 and 91 and `check-selftest-counts` verifies both
by running them — so the file that is machine-checked is right and the prose a human reads is stale by
13 and 4. `.remember/remember.md:35` also says "91 cases, 21 mutations", i.e. the correct figures were
available when the entry was written.

Nothing checks counts in `dashboard-entries.md` (`check-test-counts.py` reads the roadmap). The
mutation figure in the same paragraph — "1573 → 1595 declared" — **is** correct; see M2 for the one
that is not.

---

## Medium

### M1 — The corpus excludes 294 flat round documents, so three of the pinned rates are wrong as stated

**Where:** `check-decision-scheme.py:_round_docs` and `_corpus_now` (`if path.parent.name not in
("codex","claude","coordinator"): continue`), `docs/reviews/decision-scheme/baseline.json`.

`check-review-rounds.py` — whose `SHAPES` this slice deliberately imports rather than retypes — reads
**both** layouts and "refus[es] a basename filed in both", so the flat layout is a legitimate
location, not dead data. Measured at the pinned commit `5d957db8`:

| | writer subdirectories | flat `docs/reviews/` | combined |
|---|---|---|---|
| subjects with any round | 63 | 41 | 104 |
| subjects with ≥2 rounds | **57** | 24 | **81** |
| rounds | **261** | 131 | **392** |
| median rounds/subject | 4 | — | **4** |
| mean | 4.58 | — | 4.84 |
| at least one half | 97.3% | — | 98.2% |
| **both halves** | **65.5%** | — | **71.4%** |
| **coordinator document** | **34.9%** | — | **29.3%** |
| **over four rounds** | **33.3%** | — | **38.3%** |

The **median 4 survives** — the number the baseline calls "the number that matters" is robust, which
is worth saying. Three others do not: the coordinator rate the relocation argument rests on is 29.3%,
not 35%; both-halves is 71.4%, not 66%; and the tail the scheme promises to shrink is 38.3%, not 33%.
`baseline.json`'s `derivation` field honestly names its file set, so this is a scoping choice stated in
one place and over-generalised in three others (`rounds_for`'s docstring, `round-header-template.md`,
`review-method.md` all say "over the 57 subjects where the procedure applies"). The 81%-starvation
figure is also computed over 57 rather than 81 subjects.

Note the same filter makes trigger 1 **blind** to a flat-filed second round — consistent with
`rounds_for`, but it means the ratchet's promise is vacuous over 24 ≥2-round subjects.

### M2 — The mutation manifest's own accounting comment says 17 and 1580; the code says 21 and 1595

**Where:** `scripts/check-plan-code.py:1104` and the second `⟳ 2026-10-20` block.

The comment: *"⟳ 2026-10-20: 10 -> **17**. SEVEN added for `scope_lead`/`scope_tally`/
`scope_lead_lines`"* and *"check-review-decision 10 -> **17**, declared sum 1573 -> **1580**"*.
The code: `"scripts/check-review-decision.py": 21` and
`case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 1595)`.

**The code is right** — I counted the manifests: `check-decision-scheme.json` has **11** entries and
`check-review-decision.json` has **21**, and `1573 + 11 + 11 = 1595`, with `--self-test` green at
178/178. The comment counted the 7 ranker mutations and omitted the **4 relocation** ones
(*"relocation reads only the coordinator"*, *"a HALF outranks the coordinator"*, *"a malformed header
is swallowed for the coordinator too"*, *"every writer is strict"*). So the four mutations that cover
the slice's riskiest change are undeclared in the narrative that exists to declare them — in the file
whose comment header warns that stale counts here are the recurring defect.

### M3 — Nothing validates `baseline.json`'s shape; the literal-4 default makes the guard attribute a figure to a baseline that does not contain it

**Where:** `main()` — `pinned_rounds = pinned.get("rounds_to_termination", {})`,
`t4_no_improvement(rows, pinned_rounds.get("median", 4))`.

**The input.** A baseline with `armed_at` but no `rounds_to_termination` block, and five stopped rows
at 99 rounds.

**What is observed:**

```
decision-scheme: 5 row(s), 5 scored; pinned median None vs now 99
  FAIL  trigger 4 NO IMPROVEMENT: median rounds-to-termination over the last 5 subjects is 99,
        against a pinned pre-scheme median of 4 — …
```

The summary line says the pinned median is `None` and the finding one line below says it is 4. The 4
is a literal in the call site. Trigger 6 goes silently quiet in the same state (both keys absent →
`t6` skips). A baseline that is valid JSON but the wrong shape also reaches `.get` on a non-dict and
raises an uncaught `AttributeError`; a baseline that is *invalid* JSON raises an uncaught
`JSONDecodeError`, exiting **1** (a FAIL) rather than **2** (CANNOT RUN), which the project
distinguishes deliberately. Per the repo's rule, *hardcode only what fails loudly* — this default
fails quietly and then speaks in the baseline's name.

### M4 — `review_scope` STILL has no non-test caller, and it is the symbol both process docs name

**Where:** `main()`'s new reader calls `scope_lead_lines(scope_lead(rounds))`.
`docs/dev-process.md:121` — *"`check-review-decision.py:review_scope` computes it"*;
`docs/review-method.md:247` — *"Computed by `scripts/check-review-decision.py:review_scope`."*

Grepped: after this slice `review_scope` is referenced from its own definition, its own self-test
cases, `check-fixture-variation`'s key list, and prose. **No caller.** The commit's own comment
states the defect — *"⛔ THE RANKER HAD NO READER. Until 2026-10-20 `review_scope` was called only by
this file's own self-test, while `dev-process.md` said running this script computes it"* — and then
gives a reader to a different function. In the lead case the practical information arrives (the same
winner is named); in the abstention case the ordered list is deliberately not printed, so the two
process docs now point at a symbol that computes something the tool declines to report. Either make
`main()` print `review_scope`'s order alongside the lead, or repoint both docs at `scope_lead`.

### M5 — `rounds_for`'s docstring says a document with no header block is "skipped"; for the coordinator it raises, and 14 subjects hit it

**Where:** `rounds_for`'s ⚠ paragraph: *"A header that is present but MALFORMED propagates its
ValueError … A document with NO header block is skipped, which is how 254 existing halves stay
silent."*

**The input.** `coordinator/s-r1-coordinator.md` containing `# r1\n\nno header at all\n`, plus a
headered `codex/s-r2-codex.md`.

**What is observed:** `RAISED ValueError: no ```yaml header block`. The halves are never reached.

The code's actual distinction is the **writer**, not header presence — which the inline comment states
correctly (*"PRECEDENCE DECIDES STRICTNESS"*), so the docstring contradicts both the code and the
comment eight lines below it. Measured over the real corpus, **14 of 57 subjects raise** for exactly
this reason (`adopt-90`, `banner-unheralded`, `chrome-bar-reachable`, `clickable-dashboard-asks`,
`describe-twelve`, `harness-progress`, `main-drivable`, `plan-coverage-verdict-union`, …). That count
is unchanged from the old behaviour, so it is not a regression — but the relocation is **not additive
for those 14**: one unheadered coordinator document still poisons the subject before any half is read,
which `docs/backlog.md` #318 (filed in this slice) describes without noting that the new reading
cannot route around it.

### M6 — `paths_added_since` has no shallow-clone refusal, and a shallow clone makes every tracked round document look new

**Where:** `paths_added_since`.

**The input.** `git clone --depth 1`, then the same `git log --since=… --diff-filter=A --name-only`.

**What is observed:** the graft commit has no parent, so git reports **every tracked file as added**.
In this repository that makes all 57 ≥2-round subjects starved → trigger 1 FAILs → rc=1, with no
CANNOT RUN and nothing saying history was unavailable.

The new steps live in the `verify` job, which takes `fetch-depth: 0`, so **this is latent today** — I
checked. It matters because (a) `scripts/check-backlog-closure.py` exits **2** on a shallow clone for
precisely this reason, so the precedent and the mechanism already exist in this repo and were not
reused, and (b) `docs/portable-practices.md` is a stated deliverable, i.e. this guard is meant to be
copied into repositories whose checkout nobody has audited.

---

## Low

* **L1 — a second, exception-free door into B2.** `_corpus_now` returns the identical
  `{"median": None, "mean": None, "error": …}` dict when `counts` is empty, with no exception
  involved: measured, pointing `REPO` at a tree whose `docs/reviews` is empty returns
  `error: 'no subject has >=2 rounds'`. That reaches `main()`'s default path and prints
  **all triggers quiet**, rc=0. So the fail-open does not require the handler at all — a mislocated
  or renamed `docs/reviews` is enough. Also: the handler catches `(OSError, AttributeError,
  ImportError)` but not `SyntaxError`, so a syntax error in `check-review-rounds.py` exits 1 by
  traceback rather than either 0 or 2 — three different outcomes for three flavours of the same
  "could not read the corpus".
* **L2 — `scope_lead` reports "leads by 1" for a component with a single appearance.** `scope_lead([_r(1,"only")])`
  → `margin=1, abstain=False, "only leads by 1 (n1=1 n2=0)"` — the same phrasing the real
  `seed-explainer-serve-manifest` (n1=3 n2=2) gets. `n1` is printed so the reader *can* see the
  difference, but the sentence does not distinguish "won by one appearance out of five" from "is the
  only thing that ever appeared".
* **L3 — the `_five` fixture's component names are invented, in the case whose comment says they are
  not.** The comment reads *"⭐ THE IDENTITY CASE, and it is the MEASURED shape, not a constructed
  one"*, and the **shape is real** (I reproduced the 5-way tie at one appearance). But
  `arm-prod-drift-cron`'s actual components are `cron-comment, drift-interpretation,
  failure-visibility, merge-readiness, schedule-durability`; the fixture uses `drift-window` and
  `doc-row`, which do not exist in that subject. Two of five names are reviewer-invented — the same
  class the slice's own docstring complains about ("19 of 27 cited locations were reviewer-invented
  fixtures").
* **L4 — `t5_ranker_miss`'s message says "of {len(marks)} scored"**, but `marks` is built from
  `"ranker_hit" in r` with no `outcome` filter, unlike `t3`/`t7` which both filter on `OUTCOMES`. The
  figure the message calls "scored" counts pending rows.
* **L5 — `baseline.json`'s `_what` labels itself "the PRE-SCHEME baseline for … trigger 3 (\"no better
  than doing nothing\")"**. That is trigger **4** (`t4_no_improvement`); trigger 3 is
  `t3_routes_collapsed`. The pinned comparator misnames the trigger it exists for.
* **L6 — `t6_denominator_moved`'s `or not b` zero-guard has no case.** No fixture passes a pinned value
  of 0, so removing the guard (→ `ZeroDivisionError`) reddens nothing. The adjacent `median: None`
  case covers a different branch.
* **L7 — the new `⟳ 2026-10-20` comment block in `check-plan-code.py` is inserted mid-sentence**, between
  *"then r2 CLAUDE's six over the"* and *"# facts/render REDESIGN (22 -> 28 …)"*, breaking a
  pre-existing clause in a comment that is already the hardest thing in the file to read.

---

## Verified correct — reported, not filed

I re-derived every number the brief listed. Unless named above, each reproduces:

| claim | re-derived | source |
|---|---|---|
| 261 rounds, 57 subjects ≥2 rounds, 63 any round | **261 / 57 / 63** at `5d957db8` | `git ls-tree` + `check-review-rounds.SHAPES` |
| median 4, mean 4.58, min 2, max 17 | **4 / 4.58 / 2 / 17** | same |
| over-four share 0.333 (19 subjects) | **19, 0.333** | same |
| capture 97.3% / 65.5% / 34.9% | **254 / 171 / 91 of 261** | same (but see B1 — existence, not readability; and M1 — corpus) |
| 13.8 mean distinct components, median 11 | **13.8 / 11.0** over the 10 readable subjects | `scope_tally` per subject |
| "a coin is right about 7%" | **1/13.8 = 7.25%** | arithmetic |
| 37% / 55% / 74% one-sided 95% bounds from 3/3, 5/5, 10/10 | **0.05^(1/n) = 0.368 / 0.549 / 0.741** | arithmetic |
| 5 of 10 readable subjects have no lead | **5 of 10** abstain (`arm-prod-drift-cron`, `decision-card-soundness`, `explainer-src-root-self-configures`, `fix-src-viewer-escaping`, `peer-sites`) | shipped `scope_lead` |
| `arm-prod-drift-cron` is five components at one appearance each | **n1=1, n2=1, tied=5** | shipped `scope_lead` |
| 10 readable subjects | **10** | shipped `rounds_for` |
| mutation manifest sum 1595 | **11 + 21 entries, sum 1595, 178/178 green** | manifest JSON + `--self-test` |

**The two rejected mutations — both reasons are correct.**
`if v == n1` → `if v >= n1` in `scope_lead`: unkillable, because `n1 = counts[0]` is the maximum of
`tally.values()` by construction, so no `v > n1` exists and the selected set is identical.
`len(rounds) < 2` → `< 1` in `subjects_starved`: a 1-round subject then reaches `sorted(rounds)[1]`
and raises `IndexError` inside `_self_test`, killing the suite with zero `[FAIL]` lines — and the
`_docs["one"]` fixture guarantees it. Rejecting it costs nothing, because the *tightening* direction
of the same clause is covered by manifest entry 2 ("the ratchet excludes TWO-round subjects").

**Clauses no manifest entry would redden** (the brief's item 7): `_corpus_now` entirely (handler,
empty-`counts` path, and the `except` tuple), `main()`'s `--rederive` `now.get("error")` return,
`paths_added_since` entirely, `_round_docs` entirely, `t6`'s `not b` guard, and the codex-vs-claude
half ordering in `rounds_for`. Every `main()` case injects `corpus=` and `starved=`, so the three
functions that decide what the live CI run actually measures have neither a case nor a mutation.

**Attacking the "unavoidable" claim, as the brief invites.** The docstring's position — every row is
authored, nothing verifies it, and that is the consequence of causation not being observable — is
sound for `fix_induced`. It does **not** extend to the two fields the triggers actually turn on.
`routes_tried` is derivable from the log's own earlier rows for the same unit, and `outcome:
continued` is derivable from whether the next round's half named the same component (which
`scope_tally` already computes). B3 is the cost of not deriving them: the unverifiability that is
genuinely structural has been used to justify leaving verifiable fields unverified.

**One thing I could not verify:** the full `python3 scripts/check-plan-code.py --mutate .` — the brief
states CI is its authority and a scoped local run is not available (round-robin sharding cannot
isolate a file). I verified the manifest's arithmetic, its entry counts, and both rejection reasons by
hand instead; the claim "11 mutations, 0 survivors" and "21, 0 survivors" is **unmeasured here**.

---

**VERDICT: NOT CONVERGED** — 3 Blocking, 5 High, 6 Medium, 7 Low.
