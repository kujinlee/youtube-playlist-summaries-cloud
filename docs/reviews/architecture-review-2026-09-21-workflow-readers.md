# Architecture review — the guards that read workflows as text, 2026-09-21

**Armed by a pre-committed falsifier, not by a schedule and not by the thrashing count.** While
fixing `declared_pins` for the fourth time, the coordinator answered `docs/dev-process.md`'s
THRASHING arming condition by **redesigning instead of convening a review**, and wrote the falsifier
into the code (`scripts/check-python-pin.py:126-128`):

> *if a FOURTH `declared_pins` finding arrives in round 3, the redesign did not dissolve the class
> and Phase 6 fires.*

It arrived. Six more arrived after it — **ten defects in one function across seven rounds**. Codex
reached the same verdict independently and unprompted. Backlog **#153** recorded the debt; this
document pays it.

⚠ **Scope is the component, not the codebase.** `CONTEXT.md` and all thirteen ADRs were read;
**nothing here re-litigates an ADR**, and none of them touches workflow reading.

⚠ **Re-finding the root cause is explicitly NOT owed** (#153's own words). The open question this
document answers is the **MECHANISM**.

**Round 1 was dual-adversarial** (`docs/reviews/codex/arch-review-153-r1-codex.md`,
`docs/reviews/claude/arch-review-153-r1-claude.md`). It returned **2 Blocking, 2 High, 6 Medium,
7 Low** against the first draft of this document, including one defect found by the coordinator
while the halves were in flight. Every number below survived re-derivation by at least two
independent methods; the ones that did not are corrected here and named as corrections.

---

## The verdict, first

**Three guards independently hand-rolled the same missing primitive — *which lines of this workflow
are structure?* — and solved it to three different standards. The defect is not in any of the three;
it is that there are three.**

| Guard | What it built | Cost | On a shape it does not understand | Corpus it reads |
|---|---|---|---|---|
| `check-python-pin.py` | `_structural()` + `_steps()` — comment masking, block-scalar masking, sibling-dash rules, job-key disambiguation | **10 defects / 7 rounds** | **Fail-closed** — *except for the hole in §2, which is a false green* | `*.yml` ∪ `*.yaml` (`:70`, `:76`) |
| `check-merge-ready.py` | A *different* reader, plus `unaccounted_mentions()` — a completeness ratchet over every matching line | **4 shapes / 3 rounds** | **Refuses** — surfaces the unrecognised line | `*.yml` ∪ `*.yaml` (`:282`) |
| `check-ratchet-contract.py` | Nothing. `ci.yml` is read as flat text | — | **Fail-OPEN** | **`ci.yml` alone** (`:868`) |

The knowledge those fourteen findings bought is **private to the file that paid for it**. The sibling
that never asked the question carries the exact false green the other two eliminated — and, §2 shows,
so does the file that paid the most.

⚠ **The corpus column is a fourth divergence, added in round 1 (Claude M5).** A shared *reader* does
not fix a divergent *corpus*: routing `ci.yml` through a shared reader leaves `schema-gates.yml`
unread by R3. Direction of failure is safe (a caller in an unread workflow reads as *no* caller), so
this is not a false green — but `check-python-pin.py:72-76` and `check-merge-ready.py:271-276` each
record paying for this exact lesson, and R3 has not had that round.

This is `CONTEXT.md`'s own doctrine — *one mechanism per concern; duplicate vocabulary is the shadow
of a duplicate protocol* — which the repo enforces on schema (`check-vocabulary-collisions.py`, whose
docstring scopes it to schema) and has never applied to its own guards.

---

## §1 — The population was wrong, and that is a finding

#153 names three guards. Measured against the filesystem rather than recall:

| Guard | #153 says | Measured |
|---|---|---|
| `check-python-pin.py` | reads workflow YAML as text | ✅ `WORKFLOW_DIR:70` |
| `check-merge-ready.py` | reads workflow YAML as text | ✅ `WORKFLOW_DIR:51` |
| `check-ci-watched.py` | "shares the mechanism" | ❌ **FALSE.** Its only file handle is `SENTINEL = ROOT / ".claude/ci-watching"` (`:54`); everything else is `subprocess.run` to `gh` (`:139`) |
| `check-ratchet-contract.py` | *not named* | ✅ **reads `ci.yml:835`** — and it is the one with the fail-open |

**The population of three is complete**, established in round 1 by a sweep this document had not
done: `grep -rln ".github/workflows"` over every `*.py`, `*.sh`, `*.ts`, `*.js`, `*.mjs` outside
`node_modules` returns seven files; the four non-members are `check-plan-code.py:206` (a
`HARNESS_TREE` *staging* entry that copies the directory without reading it), `check-banner-armed.py:1135`
and `check-review-decision.py:462` (the path as a string in a self-test fixture), and
`tests/e2e/cloud.setup.ts`. No `scripts/*.sh` and no `.claude/hooks/*` file mentions workflows at all.

The row was written from the memory of a review round rather than from a sweep, and it named the
wrong sibling while missing the only one with a fail-open.

---

## §2 — A live false green in shipped code, found by reviewing the review

**This is the most consequential finding in the document and it was not in the first draft.** The
coordinator found the shape mid-round; the Claude half independently measured it as a false green;
the coordinator then isolated the path on which every layer of defence passes.

`_BLOCK_SCALAR` (`scripts/check-python-pin.py:298`) is

```python
re.compile(r"^(\s*)[\w.\-]+:\s*[|>][-+0-9]*\s*(#.*)?$")
```

`[\w.\-]+` cannot span the space in `- run:`, so **a block scalar opened on the dash line is never
masked and its body is read as structure.** Inside `_steps()` this never bites, because `Step.body`
blanks the dash before `_structural` sees it (`:264`). The function is correct at the level it was
built for and silently weaker one level up — and its own docstring says *"the lines of a STEP"*,
while the shipped code applies it to a whole file at `:232`.

### The live path, measured

Job A is genuinely pinned — it is where the guard runs, so `pythonLocation` is set. Job B has **no
`setup-python` step at all**; its only `python-version:` is text inside a `- run: |` heredoc.

```
jobs seen     : ['verify', 'schema-gates']
  verify        declared_pins -> ['3.12']     (a genuine setup-python step)
  schema-gates  declared_pins -> ['3.12']     (NO setup-python — heredoc text)
unpinned_jobs : []
VERDICT rc=0  "python pin OK — every job pins 3.12, and this interpreter is 3.12,
               from /opt/hostedtoolcache/Python/3.12.14/x64"
```

**Every layer passes.** `declared_pins` credits the phantom pin; `unpinned_jobs` returns empty;
`pin_took_effect` — the provenance check built specifically to stop a present-but-ineffective pin —
is satisfied by *the other job's* real step, because it speaks only for the job the guard runs in
while `declared_pins` speaks for all jobs. The result is **verbatim the defect #137 and #317 exist to
end**: `schema-gates` running the fifteen gates on the ambient interpreter, reported green.

### Two things make it worse than a missed shape

1. **The suite appears to cover it and does not.** `scripts/check-python-pin.py:880-882` asserts that
   a job holding only heredoc text reports as unpinned. It passes — but not because the mask worked.
   The fixture's step contains no `uses: actions/setup-python`, so `declared_pins` skips it at `:384`
   before masking is ever load-bearing. Add the `uses:` line inside the same heredoc and the case
   inverts. This is the *passing for an ambient reason* shape this project has recorded four times on
   one file.
2. **It is latent, not live — and that is exactly why promotion is dangerous.** `grep -nE "^\s*-\s+[-\w.]+:\s*[|>]" .github/workflows/*.yml`
   returns no matches, so no current workflow uses the shorthand. But the recommendation below
   promotes `_structural()` into other guards **because it is the best-paid-for of the three**.
   Promoting it as written would ship this false green into all of them, and the section that should
   have caught it was the one titled *stated, not implied*.

**This reorders the work: #154 below must land BEFORE the extraction.**

---

## §3 — The fail-open sibling, measured by execution

`check-ratchet-contract.py`'s rule **R3** asks *"does something execute this guard?"* and answers by
substring-scanning a blob that includes `ci.yml`. Run against `check_caller` directly:

```
R3 SATISFIED  <- a YAML COMMENT describing a REMOVED step
R3 SATISFIED  <- text inside a `run: |` block scalar
R3 SATISFIED  <- a step disabled by `if: false`
R3 SATISFIED  <- a genuine step                              (the control)
```

`invocation_re`'s docstring says the rule *"must not be satisfiable by prose"* and cites the finding
that a `docs/` table row was being read as a caller. It excluded `docs/` — **and prose inside
`ci.yml` satisfies it.** The fix went to the directory that had failed, not to the class.

**284 of `ci.yml`'s 480 lines (59%) are masked by `_structural`.** ⚠ The composition is not what the
first draft implied (Claude L3): instrumenting the two branches separately gives **269 comments and
15 block-scalar lines — 94.7% comments**. `ci.yml` contains only three block scalars in total, all
masked. That is the number that tells an implementer where the risk is.

**Swept across all 40 guards: 0 depend on it.** Latent, not live. ⚠ **The zero has no owner** (Claude
M4): the sweep and its controls are a point-in-time measurement, not committed, and nothing will tell
the next person to change `caller_sources` or `invocation_re` that it has expired. It was reproduced
independently in round 1 with a corpus rebuilt line-by-line from `main()` (40 ratchets, 82 caller
sources, `flips []`), and **strengthened**: 21 of the 40 guards are satisfied by `ci.yml` and nothing
else, and all 21 survive masking — so the zero is not the vacuous kind that arises from nothing
depending on `ci.yml` in the first place.

### The asymmetry that names the cause

Inside **one function**, `check_caller` (`:167-187`):

```python
doc = ast.get_docstring(ast.parse(text))          # the PYTHON subject: a real parse
if invocation_re(basename).search(caller_blob):   # the YAML subject:   a substring scan
```

The repo is not confused about which is better. `check-storage-independence.py` parses with `ast`
(`:60`, `:217`, `:293`), having replaced a grep that survived 3 of 5 mutations. The difference is
availability: Python's parser ships in the stdlib and YAML's does not.

---

## §4 — Why "just parse it" is not the answer here

* **No script imports a YAML parser** — zero across all 63 `scripts/*.py`, not just the 40 guards.
* **PyYAML is not installed**: `ModuleNotFoundError: No module named 'yaml'`.
* **No `requirements.txt`, `pyproject.toml`, `setup.py` or `Pipfile`; no `pip install` in either
  workflow.**
* `actions/setup-python@v5` (`ci.yml:68`, `schema-gates.yml:201,274`) provides a clean interpreter, so
  CI would need an install step too.

⚠ **The precise claim is "no third-party dependency", NOT "stdlib-only"** (Codex Low). An `ast` walk
of every `scripts/*.py` finds non-stdlib imports in 17 files and **every one is a local sibling
module** — `page_markup`, `page_chrome`, `m4_base_db`, `m4_catalog`, `subject_status`,
`coverage_verdict`. The imprecise version accidentally argued *against* the recommendation it was
supporting: local helper imports are not an exception to house style, they **are** house style, and
that is the precedent an extracted library needs.

So a real parse means this repo's **first third-party runtime dependency — into the very interpreter
`check-python-pin.py` exists to pin**. A vendored subset parser avoids the dependency by being a
hand-rolled parser again, larger, with no upstream test suite.

`check-merge-ready.py` reached this conclusion first (`:130-132`):

> *this is a hand-rolled YAML parser and the project is stdlib-only, so `yaml` is unavailable. A
> hand-rolled parser CANNOT be made correct. It CAN be made unable to be silently wrong.*

That sentence is right, and it is why the recommendation is about **sharing** rather than
**correctness**.

---

## §5 — Recommendation: extract the reader, wire the fail-open sibling to it

**Decided with the user, 2026-09-21. ⚠ Sequenced after #154 by round 1's B2.**

Promote `_structural()` out of `check-python-pin.py` into an importable library, and make
`check-ratchet-contract.py`'s R3 read `ci.yml` through it.

⚠ **Only `_structural()` is actually shared** (Claude M1). R3 needs *which lines are structure*; it
has no use for step boundaries, since `_steps()` returns tuples scoped to the shallowest `steps:` key
and that is meaningless over a blob of 82 joined sources. `_steps()` and `Step` **move with it**
because `_structural()` is theirs — the mask belongs to the splitter by design (`:147-150`) — not
because they are shared. Framing the move as "extract both, for reuse" overstates the reuse
delivered. *(If #156 is folded in, `_steps()` does become genuinely shared — an argument for doing so.)*

### The worked precedent — this exact move has already been made here once

`scripts/coverage_verdict.py` **is** this extraction, pulled out of `check-plan-code.py`. Its own
comment (`check-plan-code.py:307-314`):

> *"Its three clauses are now `Measured.__post_init__` in scripts/coverage_verdict.py … ⚠ Keeping
> BOTH would be two mechanisms for one concern, which is what check-vocabulary-collisions.py exists
> to catch. **The three mutations that pinned its clauses moved with them, to
> `scripts/mutations/coverage_verdict.json`.**"*

Verified: that manifest holds **6** anchors and `EXPECTED_MUTATIONS["scripts/coverage_verdict.py"]`
is **6** (`check-plan-code.py:827`). The import mechanism is equally settled —
`sys.path.insert(0, parent)` then `import <lib>  # noqa: E402` (`gen-dashboard.py:17-19`,
`check-plan-code.py:86-91`, and three others).

So the recommendation is not a proposal. It is a repeat of a move this repository has already made,
pinned, and given the same reason for.

### Decisions

| Decision | Value | Why |
|---|---|---|
| Name | `scripts/workflow_structure.py` | Underscored = importable library (six exist against 57 hyphenated executables). Named for what it **does**, **not** `workflow_yaml` — it is not a YAML parser and must not claim to be. Verified free: no `scripts/workflow*` exists |
| Role | **Peer, never a gate** | `page_markup.py`'s rule, `CONTEXT.md:108-113`. A reader checks nothing |
| Mutation entries | `check-python-pin.py` **39 → 27**, new key `workflow_structure.py` **= 12** | ⚠ **CORRECTED from 39 → 31 / = 8 by round 1 (both halves, Blocking).** ⚠ **Identified by ANCHOR LINE, not by index — r3 High.** The first version said *"#26–#37"*, which is **0-based**; `#N` in this repo reads as an ordinal, so the natural 1-based reading picks the wrong twelve — dragging a `declared_pins` anchor into a library that has no `declared_pins` and leaving a `_steps` anchor in a file that no longer has `_steps`. Two unbindable anchors, i.e. verbatim the Blocking this number already caused once. **Indices shift when anything is inserted; line anchors do not.** The twelve: `:232`, `:244`, `:245`, `:249`, `:254`, `:260`, `:263`, `:264`, `:278`, `:295`, `:298`, `:349` — ten inside `_steps`/`_structural`/`Step`, plus `_STEPS_KEY` (`:295`) and `_BLOCK_SCALAR` (`:298`), which move because those functions are their only consumers. No entry straddles the boundary. The sum is preserved at 39 — a **TRANSFER, not a ratchet fall**. The wrong numbers would have produced **two simultaneous drift failures** in `check-plan-code.py:1212-1218`, which compares declared against actual by equality |
| **Self-test cases** | The 12 killing cases move too; `check-python-pin.py`'s declared count falls from **84** | ⚠ **Missing from the first draft entirely (Claude H2).** `check-plan-code.py:500` runs **only the mutated file's own suite**, and `expect` is matched by exact equality — so a mutation whose file becomes the library is unattributable unless the library has its own `--self-test` carrying the named case |
| Declared-count bookkeeping | Re-declare in `check-python-pin.py`'s docstring; add the library to `check-selftest-counts.py`'s `POPULATION` | `check-python-pin.py` is already pinned there, so a stale count fails. ⚠ **Bare names in `POPULATION`, full paths in `EXPECTED_MUTATIONS`** — a trap that file records at `:95-97` |
| Discovery | Add to the `EXPECTED_MUTATIONS` self-test case at `check-plan-code.py:2687` | ⚠ **The first draft named the wrong mechanism (Claude M2).** That list is not a "self-tested-non-guard list" — it asserts `sorted(EXPECTED_MUTATIONS)`, and the reason to join it is that the library **ships a manifest**. The self-tested-non-guard population is *computed*, not listed (`check-ratchet-contract.py:402-409`), so the library joins it automatically the moment it has a `--self-test`, and with a manifest it correctly stays out of `WIDENED_MANIFEST_DEBT` |
| **Consumer coverage** | `check-ratchet-contract.py` needs its **own** new self-test cases **and** mutation entries for the wiring — *"`ci.yml` prose no longer satisfies R3"* and the pre-join masking path | ⚠ **Round 2 High, and it is this project's most-repeated lesson.** Its manifest holds **10** entries, none about reading `ci.yml`, and its suite has no case for a comment or block scalar there — so **an implementation could forget the mask entirely and keep every suite green.** Library tests prove the library works; they prove nothing about whether the caller called it. *Unit coverage does not compose — mutate the CALL SITE* |
| **A test seam must be built first** | `check-ratchet-contract.py`'s blob construction has to become a pure, suite-drivable function before the row above can be satisfied at all | ⚠ **r3 High, and it makes the row above unwritable as stated.** The mask must live in `main()` (`:868-885`), which `--self-test` returns before ever reaching (`:832-833`) — so a `CALLER_CASES` case cannot observe it and a mutation anchored there **survives**, which `--mutate .` reports as failure. Measured: all ten existing entries anchor in pure functions or constants, none in `main()`; across the tree, every file carrying a `main()`-anchored mutation has a suite that calls `main()` in-process, and this one cannot (`ROOT` is read at `:40`, `:835`, `:851`). The only way to make a case flip is to mask the **joined** blob — the trap row below, which would strip 163 of 264 lines from `check-schema-gates.sh` alone |
| **A third guard is affected** | `check-fixture-variation.py` goes red on day one, and the public/private naming of the extracted functions decides whether that is a red or a silent hole | ⚠ **r3 High, named by no earlier round.** It runs unconditionally (`ci.yml:333`) and derives its population from disk — any `scripts/*.py` with a `--self-test`, which the library must have. Arrival is a finding, exit 1, until pinned in `EXAMINED_KEYS`. ⭐ **And `analyse()` skips `_`-prefixed functions**, so keeping the names `_structural`/`_steps` pins the library with an **empty key set** — a guard reporting OK over the file that now owns this repo's most defect-prone reader. Renaming them public yields real findings the library's suite must answer. **That is a decision, and it is unbudgeted either way** |
| Implementation trap | Mask `ci_path.read_text()` **before** the join, never the joined blob | `blob_for` (`check-ratchet-contract.py:881-885`) joins `ci.yml` with 81 shell, hook and Python files. `_structural` drops every line whose first non-space character is `#`, so masking the blob would strip comments from all 81 and silently change R3 across the whole non-workflow corpus |

### What this does NOT do — stated, not implied

* **It fixes two of the three shapes in §3. `if: false` survives** (both halves, High):

  ```
                               before      after _structural
  comment                      SATISFIED -> VIOLATION
  block scalar (`- name:` form) SATISFIED -> VIOLATION
  if: false                    SATISFIED -> SATISFIED     <-- unchanged
  control                      SATISFIED -> SATISFIED     <-- correct
  ```

  `if: false` **is** structure, so a masking primitive is definitionally unable to see it. Filed as
  **#156**.

  ⛔ **AND THE FIRST VERSION OF THIS PARAGRAPH ASSERTED SOMETHING FALSE, which is worth recording
  because of HOW.** It said *"no guard invocation lives inside a conditional step"* — taken from
  round 1's Claude half and **propagated into this document and into #156 without being re-run**,
  which is the one thing `docs/dev-process.md` says a Phase 6 must not do: *agent output is a lead,
  not a finding.* Round 2 refuted it in one command, and the coordinator then re-derived it:

  *(summary of a measurement, not a capture)* — two steps in `ci.yml` carry both an `if:` and a
  guard invocation: `check-dashboard-entry.py` (step at `:447`, `if:` at `:448`, invocation at
  `:453`) and `check-review-recorded.py` (step at `:472`, `if:` at `:473`, invocation at `:478`),
  both `if: github.event_name == 'pull_request'`.

  ⛔⛔ **AND THE FIRST REPAIR OF THIS PARAGRAPH MADE THE SAME MISTAKE AGAIN, one round later, inside
  the paragraph whose subject is that mistake.** It argued that rejecting conditional-step
  invocations *"would red-line two guards that genuinely run"*. **False, and never run.** Both guards
  have a **second, unconditional** invocation in the same file — `check-review-recorded.py` at
  `ci.yml:162` and `check-dashboard-entry.py` at `:411`, each a `--self-test` step carrying no
  `if:` — and `invocation_re` matches those. Round 3 excised both conditional steps and re-ran R3:
  **no violation, for either.** The measured cost of the simpler rule is **0 guards**, not two.

  ⭐ **The distinction still stands, but on its own merits and with no cost figure attached:** a
  **statically false** condition (`if: false`) names a step that never executes, so it is genuinely
  not a caller; an **event-scoped** one (`if: github.event_name == …`) names a step that does
  execute, on some events. That argument needs no arithmetic, which is exactly why the arithmetic
  should not have been invented for it.

  ⚠ **Twice now, in this document, a plausible inference has been stated as a measurement** — once
  taken from a reviewer, once my own. Both were caught by the *next* round rather than by the
  author. The durable lesson is not "verify agent output": it is that **a paragraph mixing what was
  measured with what follows from it hides the inference from its own writer**, which is why the
  measurement above is now labelled as a summary and the inference is in a separate sentence.

  ⚠ **The sharper statement of the limit, from round 2:** promoting a structure reader into R3 does
  not answer *"does this guard execute?"* — it answers *"does this text survive workflow-content
  masking?"* Those are different questions, and R3's name claims the first.

* **It does not make the reader correct.** The flow-mapping bound survives and is measured — a
  genuinely pinned job written `with: {python-version: '3.12'}` gives `declared_pins []`,
  `unpinned_jobs ['w.yml:verify']`, `rc 2`. Fail-closed, so not a false green, but the guard reports
  the **absence of a thing that is present** and routes the author toward `EXEMPT_JOBS`, converting a
  fail-closed miss into a permanent exemption. Filed as **#158**.

* **It concentrates risk across two guards, not three** (Claude L1) — `check-merge-ready.py` is not
  migrated, so the concentration argument must say two.

* **`check-merge-ready.py` is not migrated — and the first draft's reason for that was wrong**
  (Claude M3). It said the reader "answers a different question"; its *guard* does, its *reader* does
  not — `pr_only_steps` hand-rolls sibling-dash detection, dedent-closes-the-step and an ownership
  indent, which is `_steps()`'s subject arrived at independently. **The reason that holds:**
  `check-merge-ready.py` is the only one of the three with a working soundness check (verified — a
  PR-only condition hidden in a `run: |` body yields `pr_only_steps -> []` *and* a loud
  `unaccounted_mentions` refusal). Migrating it would trade a **proven falsifier for an unproven
  shared reader**. Revisit once the library has paid for itself.

### The part worth taking from the option not chosen

Sharing a reader gives `check-python-pin.py` no falsifier for shapes the reader cannot see — §2 is
what that costs. `unaccounted_mentions()` is the mechanism that provides one, and
`check-python-pin.py` has its analogue for **job keys only** (`unreadable_jobs:435`). Filed as
**#157**, separately, because bundling it would leave the extraction's own review unable to see
either change cleanly.

---

## §6 — "What did we decide this milestone that isn't written down?"

**`CONTEXT.md` has no term for how a guard reads a workflow.** The Verification Stack section exists
*because* architecture review #7 found seven rounds argued in words the glossary did not contain.
That happened again: three guards built the same primitive and no round could say so.

Two terms are added to `CONTEXT.md` → Verification Stack in the same change:

* **Structural line** — a line of a workflow that is YAML *structure*, as opposed to *content*
  (block-scalar bodies, comments). Text shaped like structure is not structure. Every defect in this
  review is a failure to make this distinction. ⚠ Its correctness is **relative to the level it is
  applied at**: §2 is one function being right about a step and wrong about a file.
* **Soundness check** — a guard's falsifier for its own reader: an enumeration of every line matching
  what it looks for, each of which must be accounted for, so an unrecognised shape becomes a
  **cannot-run** rather than a silent wrong answer.

Two corrections ride along, both found in round 1 and otherwise nobody's job:

* `CONTEXT.md:118` opens the section with *"26 scripts under `scripts/`"*; the shipped tool prints
  `guards discovered (40)` and `ls scripts/*.py` is 63.
* `_structural`'s docstring (`:301`) says *"the lines of a **step**"* while both of its callers pass a
  whole file. Whole-file use is correct and already shipped; the docstring is the only thing saying
  otherwise, and a promoted library must not carry one that contradicts its callers.

---

## §7 — What becomes work

Filed to `docs/backlog.md` and the roadmap in the same turn.

| Row | Subject | Size | Order |
|---|---|---|---|
| **#154** | 🟠 **`_BLOCK_SCALAR` does not mask a dash-opened block scalar → a false green: `rc 0, "every job pins 3.12"` for a job with no `setup-python` at all.** Includes the vacuous case at `:880-882` | S | ⚠ **FIRST — before #155 promotes it** |
| #155 | Extract `workflow_structure.py`; wire R3 to it; transfer 12 anchors **and their killing cases**; re-declare counts | M | after #154 |
| #156 | R3's step-level repair — reject an invocation inside a statically disabled step; and R3's corpus is `ci.yml` alone while its siblings read `*.yml` ∪ `*.yaml` | M | after #155 |
| #157 | A soundness check for `check-python-pin.py`'s pins and steps (the `unaccounted_mentions` analogue) | S | any |
| #158 | The flow-mapping bound — read `{k: v}` or refuse on it | S + decision | any |
| #153 | **CLOSED by this document**, scope corrected: `check-ci-watched.py` is not a member; `check-ratchet-contract.py` is | — | — |

---

## §8 — A note on the round itself

`docs/review-method.md`'s Round topology section records **zero duplicate findings** across three
measured rounds, and uses that to argue the halves do different work. **This round contradicts it**:
both halves independently found the anchor-count Blocking and the `if: false` High, and the
dash-form block scalar was found three times over (coordinator, Codex Medium, Claude Blocking) — at
three *different severities*, which is the interesting part. The coordinator called it a miss, Codex
called it an understated bound, and the Claude half measured it as a false green; the coordinator
then isolated the live path. **Convergent findings were not redundant here — the escalation between
them is what made §2 the headline instead of a footnote.** Worth one line in that section's table
rather than a rewrite: n is now four rounds, not three.
