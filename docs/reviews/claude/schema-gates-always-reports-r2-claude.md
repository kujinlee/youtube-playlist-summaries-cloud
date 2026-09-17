# Round 2 — Claude adversarial half, `schema-gates-always-reports` (backlog #137)

## Subject, confirmed by execution

```
$ git log --oneline -6
3e25d630 r2: a child vouched for its parent, and CI caught a crash this machine could not
99f4da56 Dashboard: what round 1 cost and what it caught (backlog #137)
a5a50d8f r1 High 2: make under-coverage LOUD, since measurement says it cannot be made SOUND
b3052e11 r1 Blocking: three mutations shared one anchor and the whole 719-entry harness went dark
3a2fc5e3 Round 1 found the fail-open this branch had only declared, and the fix is a class fix (backlog #137)
839bc738 Fifteen schema gates reported red into a void, and the filter protecting them was buying nothing (backlog #137)

$ git rev-parse HEAD
3e25d630ce510f69cae062eb927afb93b5df4b95
$ git rev-parse --abbrev-ref HEAD
schema-gates-always-reports
$ git status --porcelain
(clean)
$ git diff 93c815c8..3e25d630 --stat | tail -1
 13 files changed, 1700 insertions(+), 176 deletions(-)
```

Reviewed commit: **`3e25d630`**, base `93c815c8`. All evidence below was taken against a copy of the
tracked tree at `/tmp/rr2/repo` (`git ls-files -z | xargs -0 tar cf - | tar xf -` — a COPY, so `ROOT`
resolves to the copy) or read-only against the working tree. No tracked file was modified except
this review document.

---

## Verdict

**NOT CONVERGED** — 1 High, 5 Medium, 3 Low.

⚠ **Read the shape before the count: none of these is a live behavioural defect in the shipped
gate.** Every finding is a *falsifiability* or *claim* defect — a clause that is correct but that
nothing would notice becoming wrong, or a measurement recorded in the repository that is not what
was measured. The High is cheap (one case, one manifest entry). That is a different situation from
a round that finds the gate producing a wrong answer, and the verdict should be read with it.

**Three things the branch gets right, verified rather than assumed, and they are the expensive
half:**

1. **All 56 manifest entries are killed by the case(s) they name, on Python 3.12 AND 3.14, with no
   crashes and no version divergence.** This is the direct re-test of the defect CI found. Evidence
   in *What I tried that produced no finding*, item 1.
2. **The manifest has no anchor collision**, and `load_manifests` accepts exactly the declared
   population: 56 == the pin, 727 == the declared sum, zero refusals across every manifest.
3. **The actual `#137` change — the deleted `paths:` filters — produced no finding in this half
   either.** I attacked it directly (item 5 below). That makes it five halves with zero findings in
   the change the branch is actually for, which corroborates the coordinator's asymmetry claim.

---

## HIGH 1 — the gate's central predicate has no falsifier: any added `.md` would satisfy the recorded-review question

**VERIFIED.** `scripts/check-review-recorded.py:572`

```python
return [p for p in paths if p.startswith(REVIEW_DIR) and p.endswith(".md")]
```

`review_added` is the function that answers *"was a review round recorded?"* — the question this
entire file exists to ask, and the one whose absence let five PRs merge unreviewed in one night.
It has two clauses. **Only one of them is falsified.**

The manifest entry `"any file under docs/reviews/ counts as a review, not just .md"` mutates the
`.endswith(".md")` half, killed by `case("only .md counts as a review document",
review_added(["docs/reviews/verdicts/x.json"]), [])` at `:1460`. **Nothing targets
`p.startswith(REVIEW_DIR)`.** The case that appears to cover it — `case("a code branch that ADDED a
review passes", verdict(CODE, ["docs/reviews/claude/x-r1-claude.md"], …)[0], 0)` at `:1259` — feeds
a path that is *also* a `.md`, so it passes for the suffix reason alone. This is the
"a case can pass for an AMBIENT reason" shape the coordinator asked me to hunt.

**Executed:**

```
$ # in /tmp/rr2/repo, sole edit:
$ #   return [p for p in paths if p.startswith(REVIEW_DIR) and p.endswith(".md")]
$ # -> return [p for p in paths if p.endswith(".md")]
CONTROL: (0, '166/166 passed')
  A  review_added: drop the docs/reviews/ DIRECTORY test
      -> SURVIVED (suite green)  [166/166 passed]
```

**Concrete failure scenario.** `REVIEW_DIR` drifts (a rename to `docs/review/`, a "simplification"
of this comprehension, a refactor that moves the prefix test into a caller). The suite stays at
166/166 and `--mutate .` stays fully attributed. From that moment a branch that changes `lib/x.ts`
and adds *any* Markdown file — `docs/notes.md`, a new `CHANGELOG.md` under a package — records a
review round:

```
real  review_added(['docs/notes.md'])          = []
real  verdict(['lib/x.ts'], ['docs/notes.md'])  = 1     (correct today)
with the clause dropped: review_added -> ['docs/notes.md'] -> verdict 0
```

i.e. the 2026-09-09 night in this file's own WHY THIS EXISTS, reached through the predicate instead
of through the missing gate.

**Observation that proves it fixed:** a case `review_added(["docs/notes.md"]) == []` (a `.md` that
is NOT under `docs/reviews/`), plus a manifest entry dropping `p.startswith(REVIEW_DIR)` that goes
red via that case. `looks_like_path`'s own two entries are the model: one clause, one anchor, one
case.

---

## MEDIUM 2 — a derived bare `docs` is SILENTLY SKIPPED by the coverage falsifier, so a gate at the `docs/` root passes both prongs and is still classified prose

**VERIFIED.** `scripts/check-review-recorded.py:247-248`

```python
prefix = g.split("*")[0]
if not prefix.startswith("docs/"):
    continue
```

That `continue` exists to ignore non-`docs/` entries (`case(prose_exceptions_cover(["supabase/migrations/**"]), [])`
at `:1382`). The exact string `docs` — no trailing slash — **also fails `startswith("docs/")`**, so
it is skipped rather than reported. And `gate_code_dirs` produces exactly that string for any bound
path one level deep: `p.rsplit("/", 1)[0]` of `docs/gate-rules.sql` is `docs`.

**Executed** — real gate sources plus one hypothetical gate binding a non-`.md` file at the `docs/`
root:

```
derived (real gates + one new gate at docs/ root):
  ['docs', 'docs/superpowers/specs/2026-08-03-stable-blob-addressing',
   'docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema',
   'docs/superpowers/specs/m4']
declared_not_derived   -> []          (empty = passes)
prose_exceptions_cover -> []          (empty = reports FULL COVERAGE)
is_prose("docs/gate-rules.sql") -> True   (the branch owes no review round)
```

and the rule in isolation:

```
prose_exceptions_cover(['docs'])         = []            <- skipped, reported as covered
prose_exceptions_cover(['docs/'])        = ['docs/']     <- reported
prose_exceptions_cover(['docs/newgate']) = ['docs/newgate']
```

**Why this is not the residual already filed as backlog #138.** #138 is about a gate directory the
derivation never FINDS. Here the derivation *does* find it — it is in `_dirs` — and the coverage
rule declines to say anything about it. Both prongs report success over a directory neither has
examined, which is the precise shape `prose_exceptions_cover`'s own docstring records as r16 High
(*"`docs/**` in the path filter made this report FULL COVERAGE while `is_prose("docs/gate.sh")` was
still True"*). The r16 fix closed the broader-glob route and left the bare-directory route open.

**Reachability.** Four tracked non-`.md` files sit directly under `docs/` today
(`architecture.html`, `available-skills.pdf`, `available-skills-print.css`, `.tex`). None is
currently bound by a script in `check-schema-gates.sh`'s list, so this is not live — but the
anti-drift pair exists to answer for the future, and this is the direction it calls dangerous.

**Observation that proves it fixed:** `prose_exceptions_cover(["docs"])` returns `["docs"]`, and a
case pins it. (The exemption tuple can never legitimately contain `docs/`, so reporting it is the
correct outcome — it turns a silent pass into a human decision.)

---

## MEDIUM 3 — the retired suffix allow-list left a third clause behind, and it is both unfalsified and a silent under-coverage rule

**VERIFIED.** `scripts/check-review-recorded.py:441-442`

```python
if not suffix:
    return False
```

r1's codex High replaced the `(".sql", ".txt")` allow-list, and the fix is described as closing the
finding *"as a CLASS rather than by adding `.json` and waiting for the next suffix"*: `.md` answers
*is it prose*, existence answers *is it a path*. **A third suffix rule survived that split** — *no
extension at all means not gate data* — and it is an allow-list by another name, because it decides
membership on the shape of the filename rather than on a property that is true.

**Executed** (both halves):

```
  C  is_gate_data: delete the `no suffix -> not gate data` rule
      -> SURVIVED (suite green)  [166/166 passed]

is_gate_data('docs/superpowers/specs/m4/live-manifest',  is_file=True) = False
is_gate_data('docs/superpowers/specs/newgate/Makefile',  is_file=True) = False
is_gate_data('docs/superpowers/specs/m4/live-manifest.txt', is_file=True) = True

gate_code_dirs("", {"scripts/g.py": 'M = "docs/superpowers/specs/newgate/live-manifest"'},
               is_file=lambda rel: True)   ->   []
```

So the clause has no mutation and no case (unfalsified), **and** it rejects a real extension-less
file *before* `is_file` is ever consulted — exactly the reviewer-reproduced shape from r1 codex
High, one suffix convention over. A gate reading `docs/superpowers/specs/<new>/manifest` (no
extension), or a `Makefile`, or a `Dockerfile`, is invisible; the existing gates keep the result
non-empty so the CANNOT-RUN guard is satisfied; a later PR editing that file classifies as PROSE.

**Observation that proves it fixed:** either (a) delete the clause and let `is_file` answer —
`is_gate_data("docs/superpowers/specs/m4/live-manifest", <exists>)` returns True — or (b) keep it
with a case and a manifest entry pinning the exclusion deliberately. Silence is the one option that
is not available, because this repository already paid for the identical shape one round ago.

---

## MEDIUM 4 — `looks_like_path` bounds the COMPONENT and not the TOTAL, so `Path.is_file()` can still raise on the CI Python

**VERIFIED for the errno behaviour; REASONED for reachability.**
`scripts/check-review-recorded.py:479-483`, `COMPONENT_LIMIT` at `:282`.

The commit and the docstring state an absolute contract: *"Verified structural — the longest string
now reaching `is_file` is 38 bytes, mutated or not, so no python version can crash it."* The guard
bounds each `/`-component at 255 bytes and does not bound the path.

**`Path.is_file()` raises ENAMETOOLONG for an over-`PATH_MAX` path whose every component is legal.**
Executed on both interpreters (`schema-gates.yml:238` pins `python-version: '3.12'`; `ci.yml` uses
the runner default; this machine is 3.14):

```
=== 3.14 ===
  long component (1450 bytes):              returned False
  total 12060 bytes, all components 200:    returned False
  total 1200 bytes, components 100:         returned False
=== 3.12 ===
  long component (1450 bytes):              RAISED OSError errno=63 [Errno 63] File name too long
  component exactly 256:                    RAISED OSError errno=63
  component 255:                            returned False
  total 12060 bytes, all components 200:    RAISED OSError errno=63
  total 4200 bytes, components 100:         RAISED OSError errno=63
  total 1200 bytes, components 100:         RAISED OSError errno=63     <- every component <= 255
```

`ENAMETOOLONG` is raised for `strlen(path) > PATH_MAX` as well as for `component > NAME_MAX`, and
`PATH_MAX` is 1024 on macOS / 4096 on Linux. Nothing in `looks_like_path` sees the total. (`ValueError`
paths — embedded NUL, lone surrogate — are swallowed on both versions; I checked those too, and they
are not a live route.)

**The supporting measurement is also imprecise in the same direction, and that is the interesting
part.** *"The longest string now reaching `is_file` is 38 bytes"* is the longest **component**; the
longest **string** is 77 bytes:

```
survive looks_like_path: 17 of 18 bound docs/ strings
max component among survivors: 38
max total     among survivors: 77
```

Conflating component with string is precisely the conflation that leaves total length unbounded.

**Reachability, measured rather than asserted.** I applied all 56 manifest mutations and, for each,
measured the longest string that reaches `is_file` over the real gate sources:

```
CONTROL max total reaching is_file: 77
mutations producing >900-byte totals reaching is_file: 0
```

So no current mutation reaches it. The finding is that the guard's contract is stated as structural
and absolute (*"no python version can crash it"*) while it bounds one of the two limits — in a file
whose entire reason for existing this round is a CI-only crash of exactly this kind.

**Observation that proves it fixed:** a `PATH_LIMIT` clause (own line, own anchor, own case)
rejecting a path over 4096 bytes, pinned by `looks_like_path("docs/" + "/".join(["a"*100]*50))
== False`; or the claim in the docstring narrowed from *"no python version can crash it"* to what
was actually measured.

---

## MEDIUM 5 — backlog #138's measured "no content rule separates them" is refuted by the non-recursive form of the very rule it names

**VERIFIED.** `docs/backlog.md:166` (row 138).

The row states, as a measurement:

> ⛔ **No content rule separates them either**, because `docs/superpowers` CONTAINS the gate
> directories, so *holds a non-`.md` file* is true of the prose parent and the gate directory alike.

That is true of the **recursive** reading and false of the **non-recursive** one. Asked of a
directory's own *direct* tracked children, the rule separates them 6 of 7:

```
RULE: does the directory's own DIRECT children include a tracked non-.md file?

  docs                                                children= 26 non-md=  4 -> GATE   (truth: prose)  ✘
      non-md: ['architecture.html','available-skills-print.css','available-skills-print.tex','available-skills.pdf']
  docs/adr                                            children= 14 non-md=  0 -> prose  (truth: prose)  ✔
  docs/reviews                                        children=864 non-md=  0 -> prose  (truth: prose)  ✔
  docs/superpowers                                    children=  0 non-md=  0 -> prose  (truth: prose)  ✔
  docs/superpowers/specs                              children= 95 non-md=  0 -> prose  (truth: prose)  ✔
  docs/superpowers/specs/m4                           children=  4 non-md=  4 -> GATE   (truth: GATE)   ✔
  docs/superpowers/specs/2026-08-03-stable-blob-...   children=  2 non-md=  2 -> GATE   (truth: GATE)   ✔
```

`docs/superpowers` — the "prose parent" the row's sentence rests on — has **zero direct children of
any kind**, so the premise does not hold for it.

Composed with the shape #138 says is fatal (accepting bound DIRECTORIES), it cuts the false
positives from four to one:

```
bound docs/ DIRECTORIES (the 'dominant shape' #138 names):
    docs                                                          direct-non-md -> True
    docs/adr                                                      direct-non-md -> False
    docs/reviews                                                  direct-non-md -> False
    docs/superpowers                                              direct-non-md -> False
    docs/superpowers/specs/2026-08-03-stable-blob-addressing       direct-non-md -> True
    docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema direct-non-md -> True
    docs/superpowers/specs/m4                                     direct-non-md -> True

after the NON-RECURSIVE content rule: ['docs', '…/stable-blob-addressing', '…/schema', '…/m4']
CODE_UNDER_PROSE                     : ['…/stable-blob-addressing', '…/m4']
```

`…/schema` is a genuine gate subdirectory (its `.sql` files are read by `run-schema-assertions.sh`)
and is covered by the exemption's prefix anyway; `docs` is the documentation root, trivially
excludable.

**This does NOT change the deferral verdict, and I want that stated plainly.** The rule is fragile
in the noisy direction — one `.svg` added to `docs/adr` flips it, which is the same objection that
correctly killed the inverted allow-list — so filing rather than patching is still right. The
finding is that the *reason* recorded in the row is not what was measured. A future implementer
reading #138 will take the sentence at face value and never re-derive it, which is this project's
recorded "a filed finding's proposed FIX is a hypothesis" / "check the assumption, not just the
code".

**Observation that proves it fixed:** the row's sentence either narrows to *"no recursive content
rule"*, or records the non-recursive result and the reason it was still rejected (fragility, not
impossibility).

---

## MEDIUM 6 — the anti-drift CALL SITE has zero mutation entries; r1 High 2's ordering is unfalsified

**VERIFIED.** `scripts/check-review-recorded.py:1167-1204`.

r16 High is recorded at `:1163` as *"`prose_exceptions_cover` existed and was returned to nobody; a
rule whose result no one reads is not a gate"*, and r1 High 2 added `declared_not_derived` with an
explicitly load-bearing ORDER (`:1185`: *"COMPLETENESS BEFORE COVERAGE … This question has to come
first"*). Both the calls and the order can be removed with the suite fully green.

**Executed:**

```
CONTROL: (0, '166/166 passed')
  F1 main: delete the declared_not_derived CALL SITE (r1 High 2 fix)   -> SURVIVED  [166/166 passed]
  F2 main: delete the prose_exceptions_cover CALL SITE (r16 High fix)  -> SURVIVED  [166/166 passed]
  F3 main: neuter the completeness question (pass an empty declaration)-> SURVIVED  [166/166 passed]
  F4 main: remove the CANNOT-RUN-on-empty-derivation guard             -> SURVIVED  [166/166 passed]
```

An exhaustive `if`-condition sweep over `main` agrees — every one of `_gs is None`, `not _dirs`,
`_undiscovered`, `_uncovered`, `code`, `not ask`, `waived` can be forced to either constant with the
suite at 166/166 (18 survivors). And the manifest confirms it structurally:

```
$ # manifest entries mapped to the function containing each anchor
entries anchored in main(): 0
```

The pure rules are well covered (`declared_not_derived` 2 entries, `prose_exceptions_cover` 2). The
wiring is not covered at all — so r16's finding is half-closed: the rule is now read, and nothing
can report if it stops being read, which is the same class of gap one layer out.

**Honest limit on this one:** `check-plan-code --mutate .` attributes kills through the target's
`--self-test`, and `main` is not reachable from a pure-rule suite, so a manifest entry alone cannot
fix it. The fix is a thin seam — extract the anti-drift sequence into a pure
`antidrift_verdict(dirs, declared) -> (rc, message)` that `main` calls — after which order,
both calls and all three exit codes are casable in the existing suite. That is the same shape as
`second_question`, whose docstring at `:1223` records that `if True:` there once left the suite
green for exactly this reason.

---

## LOW 7 — `is_prose`'s `PROSE_FILES` branch is unfalsified; `.gitignore` is its only real member

**VERIFIED.** `scripts/check-review-recorded.py:216-217`, tuple at `:149`.

```
  B  is_prose: delete the PROSE_FILES branch entirely  -> SURVIVED (suite green)  [166/166 passed]
```

Because four of the five members are also caught by the root-`.md` fallback at `:221`:

```
  README.md    tuple-> True   root-.md fallback -> True
  CLAUDE.md    tuple-> True   root-.md fallback -> True
  AGENTS.md    tuple-> True   root-.md fallback -> True
  CONTEXT.md   tuple-> True   root-.md fallback -> True
  .gitignore   tuple-> True   root-.md fallback -> False   <-- ONLY this one needs the tuple
```

The five cases at `:1279-1281` use `README.md`, `CLAUDE.md`, `AGENTS.md` — all of which pass for the
fallback reason. `.gitignore` appears exactly once in the file: in the constant. Direction of failure
is noisy (a `.gitignore` one-liner would demand a review round), which is why this is Low.

**Observation that proves it fixed:** `case("a .gitignore edit is prose", guarded_changes([".gitignore"]), [])`.

---

## LOW 8 — the component-limit clause did not prevent the CI crash the docstring credits it with, and a mutation NAME asserts otherwise

**VERIFIED.** `scripts/check-review-recorded.py:458-470`; manifest entry *"the component limit is
widened, re-admitting the shape that RAISED in CI"*.

The docstring presents the byte limit as the answer to the measured CI failure. Measured over the
real corpus:

```
docs/ string constants ANYWHERE in gate .py sources: 27
  ...with NO whitespace: 17
  longest no-whitespace: 63 bytes  ('docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema')
  max component among no-whitespace: 38
max component overall: 1450  (in scripts/check-live-schema.py)
   does that string contain whitespace? True
```

and over the strings the live derivation actually produces:

```
total bound docs/ strings reaching is_gate_data: 18
with whitespace: 1
with a component > 255 bytes: 0
```

**The 1450-byte component that raised in CI contains whitespace**, so the whitespace clause alone
rejects it, and no string in the corpus has an over-255-byte component without whitespace. Defence
in depth is fine — the clause has a case and a mutation and I am not asking for its removal. What
is wrong is the attribution: the manifest entry setting `COMPONENT_LIMIT = 4096` is named *"re-admitting
the shape that RAISED in CI"*, and it does not re-admit that shape (whitespace still rejects it).
It is killed by its named case because the case is synthetic (`looks_like_path("docs/" + "a"*256)`),
which is legitimate — but the sentence is a claim about the real world that the real world does not
support, and this repository treats those as findings.

**Observation that proves it fixed:** the entry name and the docstring say the whitespace rule is
what rejects the measured blob and the byte rule is prospective cover for a no-whitespace long
component.

---

## LOW 9 — the count narrative in `check-plan-code.py` stopped at an intermediate value while the pinned numbers moved on

**VERIFIED.** `scripts/check-plan-code.py:3231-3237`.

```python
# ⟳ 2026-09-16: 714 -> 718, backlog #137. `check-review-recorded.py` 43 -> 47: …
case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 727)
```

The pinned values are **727** and **56**; the prose beside them says **718** and **43 -> 47**, which
is where the branch stood three commits ago. The per-file comment block above does carry the full
chain to 56, so the two narratives disagree with each other as well as with the code. The numbers
that a gate can check are right — I verified them:

```
refusals/errors: []
ACCEPTED for check-review-recorded.py: 56
PIN                                 : 56
total accepted: 727 | declared sum: 727
files where accepted != pin: []
```

so this is prose-only. It is Low and it is filed anyway because `docs/plugins.md` already records
the r13 Medium where a count in prose went on being wrong *inside the sentence promising the next
drift would fail a gate* — same shape, same file family.

---

## What I tried that produced NO finding

1. **The whole manifest, on the CI Python.** The most direct re-test of the defect CI caught. All 56
   entries applied to the delivered script, self-test run under 3.12 and 3.14, kill attributed by
   matching the `[FAIL] <case>` contract (`:1805`) against each entry's `expect` (which may be a
   **list**; my first pass mishandled that and produced 17 false alarms):
   ```
   CONTROL 3.14: rc=0 166/166 passed
   CONTROL 3.12: rc=0 166/166 passed
   not-clean / version-divergent: 0 of 56
   ```
   **No crash, no unattributed kill, no divergence between the two interpreters.** The ENAMETOOLONG
   class is closed for the current manifest; Medium 4 is about the contract, not about a live case.
2. **Anchor uniqueness, both directions.** 56 entries, 56 unique names, 56 unique `old` anchors, and
   every anchor occurs **exactly once** in the delivered file (`edits whose anchor does NOT occur
   exactly once: 0`). `load_manifests` returned zero refusals across every manifest in
   `scripts/mutations/`, so the r1 Blocking cannot recur from this file — and could not recur from
   any other either.
3. **A redundant or mis-expecting entry.** I looked for an entry subsumed by another and for one
   whose `expect` names a case it does not kill. Found neither; item 1 is the evidence for the
   second half.
4. **`looks_like_path` as a too-strict gatekeeper (attack 1).** No live false rejection.
   `docs/spéc/x.sql` ✓, `docs/ünïcode/rules.json` ✓, `./docs/spec/x.sql` ✓ (the reader slices from
   `index("docs/")`, so the `./` never arrives), `docs/spec/` ✓ shape-wise and then correctly
   rejected by the suffix rule exactly as `docs/spec` is. A path with a **space** is rejected — but
   zero tracked files in this repository contain one (`git ls-files | grep -c ' '` → 0) and the
   shell reader's `[\w./-]+` cannot produce one, so it is not reachable. `docs/` + 128 × `é` is
   rejected at 256 bytes, which is **correct**: that exceeds `NAME_MAX`, and the case asserting it
   is asserting the right thing.
5. **The `#137` change itself — the deleted `paths:` filters (attack 7).** Attacked and found
   nothing. `prod-drift` is correctly gated `if: github.event_name == 'schedule' || … 'workflow_dispatch'`
   (`:209`), so removing the filter does not expose it to `pull_request` where fork PRs get no
   `CLAUDE_RO_DATABASE_URL`; `schema-gates` is gated `!= 'schedule'` (`:163`) so the context does
   report on every PR, which is the point; the `concurrency` key still carries `github.event_name`,
   so the push/cron collision r1 Medium 5 found stays fixed; `permissions: contents: read` is
   unchanged. The one doc asserting the filter still exists (`docs/dev-process.md:161`) was updated
   in the same commit. The only surviving mention outside review documents is
   `docs/dashboard-entries.md:8654`, an append-only historical entry describing past work — correct
   to leave.
6. **`declared_not_derived`'s exact match as too strict (attack 3).** Trailing slashes are symmetric
   — both sides `rstrip("/")` — verified in both directions:
   ```
   declared=("docs/a/",) derived=["docs/a"]   -> []
   declared=("docs/a",)  derived=["docs/a/"]  -> []
   declared=("docs/a/",) derived=["docs/a/b"] -> ['docs/a/']   (correctly REPORTED — the r2 fix)
   ```
   A declared directory that becomes legitimately derivable only as a child now yields rc=2
   CANNOT RUN rather than a silent pass. That is loud and, for this rule, correct.
7. **The ORDER in `main` (attack 4) as a live incoherence.** I could not construct a state where
   both prongs pass over a *derived* directory that the classifier mishandles — except the bare-`docs`
   case, which is Medium 2 and is a hole in the coverage rule rather than in the order. The order
   itself is right; it is merely unfalsified (Medium 6).
8. **The repository's own gates against the branch**, run in the working tree:
   `check-docs` rc=0, `check-gate-falsifiability` rc=0, `check-ratchet-contract` rc=0,
   `check-anchors` rc=0, `check-plan-file-tags` rc=0, `check-selftest-counts` rc=0,
   `check-plan-code --self-test` 128/128 rc=0. `check-review-rounds` is red for one reason only —
   *"schema-gates-always-reports round 2: only codex — claude neither ran nor recorded a REVIEW
   GAP:"* — which this document closes. (`check-selftest-counts` and `check-backlog-closure` report
   red/rc=2 inside my `/tmp` copy; both are artefacts of the copy not being a git repository, and
   both are green in the working tree.)
9. **Exhaustive clause sweep.** 88 generated mutations (force each `if` condition to both constants,
   neutralise each `and`/`or` operand, flip each comparison) across `_joined_path`,
   `bound_docs_paths`, `gate_code_dirs`, `is_gate_data`, `looks_like_path`, `declared_not_derived`,
   `prose_exceptions_cover`, `is_prose`, `_gate_sources`, `review_added`, `guarded_changes`,
   `is_absent`, `main`. 27 survivors. After discounting `main` (Medium 6), the two clauses this file
   already documents as inert (`_joined_path`'s `len(parts) > 1` at `:292`, and `is_absent`'s
   `bool(parts[1])`), and environment-dependent `_gate_sources` probes, the residue is Findings 1, 3
   and 7. **`looks_like_path` itself survived nothing** — deleting the whole component loop goes red
   via both of its named cases.

---

## ⟳ Thrashing classification — my own answer, not an inheritance

The coordinator asserts round 2 is the **first** round whose findings came from the previous round's
own fix. **I agree, and my half sharpens it rather than softening it.** Of my nine findings:

| Finding | Origin |
|---|---|
| Medium 3 (`not suffix`) | **r1 codex's fix** — the clause the allow-list split left behind |
| Medium 4 (PATH_MAX) | **r2's own fix** — a gap in `looks_like_path` as delivered |
| Medium 6 (call site) | **r1 High 2's fix** — the call it added |
| Low 8 (attribution) | **r2's own fix** — the docstring and entry name it wrote |
| High 1, Medium 2, Low 7 | pre-existing, untouched by either round |
| Medium 5 | the backlog row r1 produced, not the code |
| Low 9 | this branch's bookkeeping |

Four of nine are inside the previous rounds' repairs, and all four are in **one component** — the
gate-code derivation. So round 2 is confirmed as the first such round from both halves independently.

⚠ **Round 3 is the decision point, and the pre-committed retreat should be read before round 3
starts, not after it.** I record one asymmetry the coordinator's note does not: the four findings
above are *falsifiability* defects in the repairs, not wrong answers produced by them. If round 3's
findings are of the same kind — "this fix is correct and nothing would notice it breaking" — that is
evidence for the prose-floor reading rather than the thrashing reading, because a coverage gap does
not regenerate when you close it. If round 3 finds a repair that produces a **wrong answer**, that is
thrashing and the retreat should fire.

I also confirm the asymmetry the retreat rests on: **the deleted `paths:` filters produced zero
findings in this half too** (item 5 above), making it five halves. The collateral derivation has now
produced every finding in both rounds.

---

## Verdict

**NOT CONVERGED** — 1 High, 5 Medium, 3 Low.

The High is one case plus one manifest entry. Mediums 2 and 3 are each a clause change plus a case.
Medium 6 needs a small pure seam. Mediums 4 and 5 can be closed by narrowing two written claims to
what was measured, if the code changes are judged not worth it — but they must be closed one way or
the other, because both are currently recorded in the repository as measurements that do not hold.
