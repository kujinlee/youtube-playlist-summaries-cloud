# Round 16 — Claude half — `record-review-topology` (FINAL round)

Subject: `/Users/kujinlee/code/agentic-ai-docs/.yps-worktrees/review-topology`, branch
`record-review-topology`, HEAD `dc9fe107` **plus the uncommitted delta**, reviewed from an isolated
copy at `<scratch>/iso` whose `.git` pointer file (109 bytes) was deleted and asserted gone
(`git rev-parse --show-toplevel` → `fatal: not a git repository`). No mutating git was run anywhere.
Only read-only `git ls-files` / `git diff` / `git status` were run in the worktree itself.

**One High. It is a fail-open in the deliverable, it is the same class as r14's and r15's, and it is
in the mechanism this round built to prevent exactly that recurrence.**

---

## H1 — The anti-drift falsifier for `CODE_UNDER_PROSE` cannot see the drift it names, and r15's High recurs verbatim

**Claim.** `prose_exceptions_cover()` is ships-justification for the duplicated path set, but its
only inputs are three hardcoded glob lists inside the self-test. Nothing reads
`.github/workflows/schema-gates.yml`. So when the workflow gains a `docs/` gate directory — the
one drift the comment at `scripts/check-review-recorded.py:174-179` explicitly names — every gate
stays green and both halves of this gate go silent over CI gate code.

`scripts/check-review-recorded.py:209-226` (rule), `:941-948` (its only callers),
`:174-179` (the claim it is supposed to support).

### (a) The input is a third copy, so drift is invisible — MEASURED

Every caller, repository-wide:

```
$ grep -rn "prose_exceptions_cover" --include=*.py --include=*.sh --include=*.yml --include=*.json .
scripts/check-review-recorded.py:209:def prose_exceptions_cover(workflow_globs: list[str]) -> list[str]:
scripts/check-review-recorded.py:941:         prose_exceptions_cover(["docs/superpowers/specs/2026-08-03-stable-blob-addressing/**",
scripts/check-review-recorded.py:945:         prose_exceptions_cover(["docs/superpowers/specs/m5/**"]),
scripts/check-review-recorded.py:948:         prose_exceptions_cover(["supabase/migrations/**"]), [])
```

Three literal lists. The docstring at `:939` says the case is *"fed the REAL globs from
schema-gates.yml"* — it is fed a **transcription** of them, typed into the test, one file away from
the tuple it is checking. Copy #1 is the workflow, copy #2 is `CODE_UNDER_PROSE`, copy #3 is the
case. The falsifier compares #3 against #2. Neither is the authority.

The drift, caused in the isolated copy (workflow only; the script untouched):

```
$ # added "- 'docs/superpowers/specs/m5-newgate/**'" under BOTH paths: filters in schema-gates.yml
$ grep -n "m5-newgate" .github/workflows/schema-gates.yml
82:      - 'docs/superpowers/specs/m5-newgate/**'
106:      - 'docs/superpowers/specs/m5-newgate/**'

$ python3 scripts/check-review-recorded.py --self-test
134/134 passed                                    rc=0

$ # and the classifier's answer for the new gate's code:
is_prose(docs/superpowers/specs/m5-newgate/verify-schema.sh) = True
guarded_changes([p]) = []
verdict(...)         = 0 | no guarded path changed — a review round is not required
second_question(...) = (False, None)
```

That is r15 H1's measured output, line for line — `is_prose` True, `guarded_changes` `[]`, the
"no guarded path changed" verdict, `second_question` returning `(False, None)`. A branch weakening
the new gate merges with no review round and no declaration. The workflow was restored afterwards
(`m5-newgate remaining: 0`).

`m5` is not a hypothetical: `docs/superpowers/specs/m4/` exists, and the self-test's own
anti-drift case at `:945` uses `docs/superpowers/specs/m5/**` as its example of the next one.

### (b) Even fed the real globs, a BROADER glob is silently cleared — and that clause is unfalsifiable

`:224` — `if not any(prefix.startswith(e) or e.startswith(prefix) for e in CODE_UNDER_PROSE)`.
The second disjunct clears any workflow glob that is a **parent** of an exemption:

```
docs/superpowers/specs/m4              -> missing=[]     (correct — trailing-slash tolerance)
docs/superpowers/specs/m4/**           -> missing=[]     (correct)
docs/superpowers/specs/m40/**          -> missing=['docs/superpowers/specs/m40/**']   (correct)
docs/superpowers/specs/**              -> missing=[]     ⛔ WRONG
docs/superpowers/**                    -> missing=[]     ⛔ WRONG
docs/**                                -> missing=[]     ⛔ WRONG
```

With `docs/**` in the path filter, CI treats all of `docs/` as gate subjects and the falsifier
reports full coverage, while `is_prose("docs/gate.sh")` is `True`. Broadening a path filter to a
parent directory is the *ordinary* way that file grows.

The clause is not reachable from any case — deleting it changes nothing:

```
$ # removed "or e.startswith(prefix)"
$ python3 scripts/check-review-recorded.py --self-test
134/134 passed                                    rc=0
```

So the one clause that creates the hole is the one clause no case can break. The three cases at
`:941-948` all feed globs that equal or sit under an exemption, which only ever exercises
`prefix.startswith(e)`. This is the repo's own recorded shape — *fixing a premise is not covering
the branch*.

Note the clause is not merely wrong: it legitimately absorbs a glob written without its trailing
slash (`docs/superpowers/specs/m4`). A fix has to keep that and drop the rest.

### Why High rather than Medium

The brief's *known, not to be re-filed* list excuses the duplicated path set **"stated, with
`prose_exceptions_cover` as its falsifier"**. This finding is not the duplication; it is that the
named falsifier is vacuous in the one direction it was built for. The failure it permits is a
literal recurrence of the High this round exists to fix, and it fails **open** — green, silent,
on executable CI gate code.

### Suggested fix — an existing idiom, not a new mechanism

The comment at `:174-179` argues the tuple ships as a copy because deriving it *"needs a YAML read
inside a pure classifier, i.e. a new mechanism invented during a convergence round."* That is a
false dichotomy, and this file already refutes it twice: `readable_docs(docs, read)` and
`first_codex_gap(docs, parse)` are impure-reader-plus-pure-rule seams, and a sibling guard already
reads a workflow file as plain text — `scripts/check-ratchet-contract.py:818`,
`ci_path = ROOT / ".github/workflows/ci.yml"`, with an explicit NOT RUN when it is missing. PyYAML
is not installed here (`import yaml` → ImportError), so a line scan for `- 'docs/...'` entries under
`paths:` is both sufficient and the established precedent.

1. Add a thin impure reader that extracts the `paths:` globs from `schema-gates.yml` and hand them
   to the existing pure `prose_exceptions_cover`. A missing workflow, or a read yielding **zero**
   globs, is **CANNOT RUN (2)** — a zero over nothing is not a finding.
2. Call it from `main` (or from `check-schema-gates.sh`, whichever the coordinator prefers) so a
   non-empty return is a **red**, not a return value nobody reads.
3. Tighten `:224` to keep only the slash tolerance:
   `if not any(prefix.startswith(e) or e == prefix.rstrip("/") + "/" for e in CODE_UNDER_PROSE)`.
4. Cases for the broadening direction (`docs/**`, `docs/superpowers/**` must be REPORTED) plus the
   trailing-slash case that pins the surviving tolerance, and a mutation entry for the new clause so
   it is falsifiable.

---

## M1 — The `.md` carve-out is justified by a benefit that does not exist

`scripts/check-review-recorded.py:190-200`. The comment states the carve-out was measured because
*"the spec's own prose lives beside its gate scripts"* and that obliging a round for a design-doc
edit is how backlog #56 measured a gate being switched off.

Re-derived: **zero `.md` files are tracked under either exempted directory.**

```
$ ls docs/superpowers/specs/2026-08-03-stable-blob-addressing/
mutate-schema.py   schema/   verify-schema.sh
$ ls docs/superpowers/specs/m4/
accepted-additions.txt  live-manifest.txt  seed-assertion-corpus.sql  t1-blast-radius.sql
$ # tracked .md under either prefix: 0
```

The case that pins it (`:936`, `guarded_changes([_SPEC + "spec.md"]) == []`) uses a path that is not
in the repository. So the carve-out currently protects nothing, while leaving live the fail-open the
comment itself names two lines later: *"a `.md` in one of these directories that LATER becomes a
gate input would be wrongly prose again."* Today it is all cost and no benefit.

I am **not** proposing to remove it — removing it would oblige a round for the first `.md` anyone
writes there, which is the #56 risk the author correctly identified. The defect is the recorded
justification asserting a present-tense fact that is false, in a file whose signature failure is
comments claiming properties the code lacks. Correct the comment to say the carve-out is
*prospective* (there is no `.md` there today; this is the policy for when one appears), and either
drop the fabricated fixture or say in the case name that it is hypothetical.

Verified while re-deriving: the gate-input enumeration itself is **accurate**.
`scripts/check-schema-gates.sh:19,30,33,185` consume `$SPEC/verify-schema.sh`,
`$SPEC/mutate-schema.py`, `$SPEC/schema/05_assert.sql`; `scripts/check-anon-exposure.py:148` and
`scripts/check-live-schema.py:55,58` consume `live-manifest.txt` and `accepted-additions.txt`. No
`.md` is read by any gate.

---

## M2 — `.gitignore` is classified prose, against the gate's own cited scope authority

`scripts/check-review-recorded.py:146` — `.gitignore` is in `PROSE_FILES`. The module docstring at
`:28-31` says *"SCOPE IS BLAST RADIUS ... the same axis `docs/dev-process.md` already uses to decide
branch-plus-PR."* That table, `docs/dev-process.md:97-98`, reads:

```
| `lib/` `app/` ... `scripts/` `tests/`, or any config | **Branch + PR, always.** No size exemption |
| Docs                                                 | Branch + PR, **batched**                     |
```

`.gitignore` is config, not docs, so the classifier and its stated authority disagree about it. The
blast radius is real in one direction: a `.gitignore` edit cannot untrack an existing file, but it
can silently keep a *future* class of artifact out of version control, which turns a downstream gate
that reads tracked artifacts from checking into vacuous. This repo has already paid for that shape
once — backlog #86, a `.gitignore` of bare `*` under `.claude/commands/` making `git status` answer
"clean" about files it could not see.

Medium, not High: I could construct no escape that is live today, and moving `.gitignore` out of
`PROSE_FILES` is a policy change (every `.gitignore` edit then owes a round), which is the
coordinator's call rather than a mechanical fix. Backlog is the right home if it is not taken here.

---

## L1 — Three of the four "generated documentation artifacts" are authored, not generated

The r15 coordinator clears the classifier's remaining non-`.md` prose as *96 review verdicts,
`.gitignore`, and four generated documentation artifacts.* The count reproduces exactly (below), but
"generated" is wrong for three of the four:

| Path | Actually |
|---|---|
| `docs/architecture.html` | **Authored.** `scripts/publish-arch-page.sh:6` — *"master's `docs/architecture.html` is the source of truth; gh-pages is a"* … it is the published source, and holds 2 `<script>` blocks |
| `docs/available-skills-print.tex` | **Authored build INPUT** — a LaTeX header include (`\usepackage{longtable}` …). No producer anywhere in the repo |
| `docs/available-skills-print.css` | **Authored build INPUT** — a print stylesheet (`@page { … size: letter landscape }`). No producer anywhere in the repo |
| `docs/available-skills.pdf` | Genuinely an output |

Classifying all four as prose is still defensible on the blast-radius axis — nothing executes them
in CI — so I am not asking for a behaviour change. The finding is that the *reason recorded* for
clearing them is false, and the next person re-deriving this list will find "generated" and stop.
Say "not read by any gate" (true, and the property that matters) instead of "generated".

---

## What I verified clean

Everything below was **executed**, in the isolated copy, not read.

**All seven declared commands, green.**

```
check-review-recorded.py --self-test   134/134 passed      rc=0
codex-review.py --self-test             85/85  passed      rc=0
check-plan-code.py --self-test         128/128 passed      rc=0
check-ratchet-contract.py --self-test    41/41 passed      rc=0
check-fixture-variation.py   fixture variation OK — 514 parameters, 50 files            rc=0
check-selftest-counts.py     38 scripts declare a count, every one verified by running   rc=0
check-review-rounds.py       235 parsed, 18 exemptions, 0 silent gaps, 101 verdicts read rc=0
```

**Counts, recomputed independently (not read off the subject's tally).** Parsed
`EXPECTED_MUTATIONS` out of `check-plan-code.py` by `ast`, counted the manifests on disk:
declared total **626**, on-disk total **626**, 44 files each, **key sets identical, zero
mismatches**; `check-review-recorded.py` 40 = 40, `codex-review.py` 12 = 12.

**Anchors — all 40 in `check-review-recorded.json`.** Each `edits` anchor resolves to **exactly one**
site in the delivered file (no zero-match orphans, no multi-match ambiguity); **no duplicate entry
names**; **no anchor text shared between entries**.

**The re-anchored r12 mutation.** `"the second question is switched off entirely"` now anchors on
`if not guarded_changes(changed):\n        return False, None` alone, which resolves uniquely inside
`second_question` (`verdict` spells its equivalent as `if not obliged:`, so there is no collision),
and still kills through the case it names — `second_question(["lib/x.ts"], None) == (True, None)`.
It is still about the rule its name claims.

**The waiver fix agrees with `verdict()` in every reachable state.** Driven through the *shared*
parser rather than by reading it:

```
bare marker            reason_of -> ''             verdict=1  second_question asks=True
marker + spaces        reason_of -> ''             verdict=1  second_question asks=True
marker + tab           reason_of -> ''             verdict=1  second_question asks=True
marker + spaces + NL   reason_of -> ''             verdict=1  second_question asks=True
marker + real reason   reason_of -> 'master moved' verdict=0  second_question asks=False
absent                 reason_of -> None           verdict=1  second_question asks=True
```

I specifically looked for the mirror defect — `verdict` uses truthiness (`if reason:`) while
`second_question` now uses `.strip()`, so a whitespace-only reason would pass one and fail the
other. It cannot arise: `exemption_reason` strips, so `reason_of` never returns whitespace-only.
The `.strip()` is defence in depth, not a disagreement.

**No third consumer of `NO-REVIEW:`.** Grepped `*.py *.sh *.yml *.md *.json`: outside
`check-review-recorded.py`, every hit is prose (dashboard entries, review documents). Nothing else
parses the marker.

**Ordering in `is_prose` (`:186-206`).** No path can match `CODE_UNDER_PROSE` and also
`PROSE_FILES` or the root-`.md` rule: the exemptions are all `docs/…/` prefixes, `PROSE_FILES` are
all root basenames, and the root-`.md` rule requires `"/" not in path`. The early return is safe.
`PROSE_DIRS` is deliberately shadowed for the two prefixes, which is the fix.

**The classifier enumeration, re-derived rather than inherited.** `git ls-files -z` → **2,213**
tracked files (matches). Applied `is_prose` to all of them: 1,347 prose / 866 guarded; **101**
non-`.md` paths classified prose = 96 `docs/reviews/verdicts/*.json` + `.gitignore` + the four
artifacts above. Nothing else. And from the other direction: of the 110 tracked non-`.md` files
under `docs/`, the 14 that are not verdicts are the 4 artifacts plus **10 gate files, all 10 inside
the two exemptions** (`mutate-schema.py`, `verify-schema.sh`, 4 `schema/*.sql`,
`live-manifest.txt`, `accepted-additions.txt`, `seed-assertion-corpus.sql`, `t1-blast-radius.sql`).
`CODE_UNDER_PROSE` is **correct and complete for the tree as it stands today** — H1 is about
tomorrow, which is precisely what an anti-drift falsifier is for.

**The gate has a caller, and it is not path-filtered.** `.github/workflows/ci.yml:130` runs the
self-test; `:419-426` runs it for real on `pull_request` with
`--base "origin/$GITHUB_BASE_REF" --pr-body-file /tmp/review-pr-body.md` (its own body file, not the
sibling step's). `ci.yml` declares `on: pull_request: branches: [master]` with **no `paths:`
filter**, so the step runs on every PR — including a PR that touches only `docs/`. This matters for
H1: the gate does run, it just answers wrongly.

**Regression — everything r14/r15 cleared is untouched.** The uncommitted delta to
`check-review-recorded.py` is confined to the docstring count, `CODE_UNDER_PROSE`, `is_prose`,
`prose_exceptions_cover`, `second_question`, the three `git diff` call sites plus the new
`diff_argv`, `main`'s body-file read, and the self-test. `case_line`, `_load_fail_parser`,
`reviewed_state`, `unredirected`, `verdict_record`, `tail_candidates`, `classify_verdict`,
`round_tail` and `tail_verdict` are not modified by this delta.

---

## What I did NOT reach — treat as NOT CHECKED

* **The full `--mutate .` at 626 entries.** The coordinator is running it; I deliberately did not
  duplicate it. I verified the manifest *statically* (anchor resolution, uniqueness, counts) but
  have **not** observed 626 kills attributed to their named cases. My anchor check proves each
  mutation will *apply*; it does not prove each goes red via the case it names.
* `test:integration`, `test:e2e`, anything needing a live Supabase or Postgres. Not run.
* The `docs/plugins.md`, `codex-review.py` and `codex-review.json` portions of the delta were read
  in outline only; my effort went where the brief directed it, into the deliverable's own logic.
  `codex-review.py --self-test` is green at 85 and its 12 manifest entries are in the anchor and
  count checks above, but I did not attack its rules.

---

## Verdict

H1 is a fail-open in the deliverable, in the mechanism built this round to prevent this exact
recurrence, and it is measured end to end with a control. It should be fixed before merge; the fix
is small and uses a seam this file and a sibling guard already use. M1, M2 and L1 are corrections to
recorded reasoning rather than to behaviour, and are backlog-shaped if the coordinator prefers.

I could not break `is_prose` against today's tree, the waiver arms, the re-anchored mutation, the
anchor set, or the counts — all re-derived rather than inherited, and all clean.

VERDICT: NOT CONVERGED
