# Architecture review — the observer family, 2026-09-22

**Armed by THRASHING, on two slices independently, and both arms were pre-committed in writing
before the round that would have been accused of softening them.**

| Slice | Evidence | Confirmed by |
|---|---|---|
| banner / `unheralded` (PR #332) | rounds 3, 4 and 5 each carried findings caused by the previous round's fix | pre-committed **by round 4, in writing**, before round 5 ran |
| Stop-observer (PR #333) | r3's Medium came from r2's fix; 2 of r4's 5 came from r3's fix | **both review halves independently**; r5 re-derived the arming rule from `dev-process.md`'s own text |

⚠ **Scope is the family, not the codebase.** `CONTEXT.md` was read in full (140 lines);
`docs/adr/README.md`'s index — which carries a one-to-three-sentence statement of every ADR's
decision — was read in full, and **ADR-0010 alone was read in full as a document**, because the
index shows it is the only one whose subject is repo tooling. The other twelve are product schema,
cost, storage and job-queue decisions. **Nothing here re-litigates an ADR**, and ADR-0010 is leaned
on rather than reopened.

⚠ This document carries **no `Anchor:` header, deliberately.** ADR-0010's own scope table
(`0010:108`) says documents under `docs/reviews/` get one **never** — they are point-in-time
artifacts, not living ones. An earlier draft of this file had one, with a slug absent from
`docs/anchors.md`; it is recorded here rather than silently removed, because inventing an anchor is
exactly the drift R2 exists to catch.

It inherits three framed questions — backlog **#164**, **#165**, **#166** — and is expected to answer
them *together*. §4 does, and **refutes part of the framing it inherited**: two of the three are one
class; the third is not, and folding it in would be the error.

---

## §0 — What this review must NOT do, because it was done yesterday

**Architecture review #153 (`docs/reviews/architecture-review-2026-09-21-workflow-readers.md`,
2026-09-21) already named this class**, in its own closing sentence:

> *"This is `CONTEXT.md`'s own doctrine — one mechanism per concern; duplicate vocabulary is the
> shadow of a duplicate protocol — which the repo enforces on schema
> (`check-vocabulary-collisions.py`, whose docstring scopes it to schema) and **has never applied to
> its own guards**."*

Re-deriving that would be this document's own worst failure mode, and the repo has a memory note for
it (*"it exists under a name I didn't search"* — three times in one day).

**So the question here is different, and it is the one #153 did not ask:**

> The class was named on 2026-09-21. On 2026-09-22 a fourth duplicate shipped, in a different
> family, carrying a docstring that names the problem in capitals. **Why did naming it not stop it?**

Measured, not recalled:

| Fact | Evidence |
|---|---|
| `check-ci-watched.log_line` is the newest duplicate | first appears in `ebfb74f1`, **dated 2026-09-22** (`git log -S "def log_line"`) |
| Its author knew | `check-ci-watched.py:160-168` — *"⚠ THIS IS THE THIRD `log_line` IN `scripts/`… `check-vocabulary-collisions.py` exists on the principle that duplicate coordination vocabulary is the shadow of a duplicate protocol"* |
| …and shipped it anyway, with a stated reason | same docstring, `:165` — *"⭐ SO THIS ONE DOES NOT INVENT A FOURTH GRAMMAR. Matching the closest sibling is the cheapest thing that does not make the problem worse"* |

That reason is **correct at slice time**, which is exactly why prose cannot fix this. The author
faced a real choice between two costs and took the smaller one. Nothing made the duplicate cost
anything at the moment it was written.

---

## §1 — The verdict, first

**The repo makes claims about two substrates. For one it built a cross-member instrument, at
considerable cost, after a duplicated protocol survived six adversarial rounds. For the other —
which is where all recent work happens — every instrument it owns is per-member.**

| | **Product schema** | **Repo tooling (`scripts/`)** |
|---|---|---|
| Enumerated whole | `pg_catalog` / `information_schema` | the filesystem (`check-ratchet-contract.py`) |
| Per-member instruments | many | 6 guards take `scripts/` as subject |
| **Cross-member instrument** | **`check-vocabulary-collisions.py`** | **none** |
| Shared modules | `m4_base_db` (6 importers), `m4_catalog` (5), `subject_status` (3) | — |

`check-vocabulary-collisions.py`'s own founding paragraph states the principle this review applies
to it:

> *"Nothing caught it, because every gate this project owns asks 'is this correct?', which is a
> LOCAL question and can always be answered yes by patching. **A duplicated mechanism is never
> locally incorrect.**"* (`:12-14`)

### The six guards whose subject is `scripts/`, and what each asks

Measured by reading each one, not by grepping for a word:

| Guard | Question it asks | Span |
|---|---|---|
| `check-ratchet-contract.py` | does **this file** have a self-test / no fail-open / a caller / mutations? | one file |
| `check-selftest-counts.py` | does **this file's** declared count match what its suite printed? | one file |
| `check-plan-code.py` | does **this mutation** redden the case it names? | one entry |
| `check-fixture-variation.py` | do these cases vary **this parameter**? | one suite |
| `check-storage-independence.py` | does **this file** read `storage.*`? | one file |
| `check-review-recorded.py` | did **this branch** record a round? | one branch |

**Every one is answerable by looking at a single member.** Not one asks a property that holds over
the *set*. That is the absence, stated as an enumerated whole rather than as an impression.

### The extraction idiom exists here, works, and this family has never used it

This is **not** "the repo doesn't factor code out". It does, twice, at family scale:

| Family | Shared module | Importers |
|---|---|---|
| Page generation | `page_chrome` | 6 |
| Page generation | `page_markup` | 5 |
| Schema gates | `m4_base_db` | 6 |
| Schema gates | `m4_catalog` | 5 |
| Schema gates | `subject_status` | 3 |
| Mutation harness | `coverage_verdict` | 1 (the extraction #155 cites as precedent) |

And the observer family:

| File | Lines | Local modules imported |
|---|---:|---|
| `check-banner-armed.py` | 2,545 | **none** |
| `check-closing-table.py` | 1,655 | **none** |
| `begin-plan.py` | 1,025 | **none** |
| `check-ci-watched.py` | 890 | **none** |
| `check-plan-progress.py` | 606 | **none** |
| **total** | **6,721** | **none** |

### How the duplication is actually transmitted

**The sibling is the specification, and it is consulted by reading rather than by importing.**
`check-ci-watched.py` cites "the sibling" at six separate decision points (`:64`, `:163`, `:466`,
`:592`, `:616`, `:660`) and imports nothing but the standard library. Across the 40 guards the word
appears **82 times in 17 files** — `check-python-pin.py` 21, `check-banner-armed.py` 16,
`check-plan-code.py` 10.

That is a working knowledge-transfer mechanism with one property that matters: **it copies the
answer and not the obligation.** When the sibling is later fixed, the copy is not.

---

## §2 — The instrument already fits, and two things stop it

The recommendation this section builds toward is **not** "write a new guard". It is: the guard
exists, its rule is already substrate-neutral, and it has one adapter where it needs two.

### 2.1 — `evaluate()` is already substrate-neutral, and that was deliberate

`check-vocabulary-collisions.evaluate()` (`:120`) takes `cols: list[tuple[str, str]]` and does
nothing to them but string work: `f"{t}.{c}"`, `stem in c`, `h.split(".")[0]`. **It does not know it
is looking at a database.** It was split out of `main()` on 2026-08-19 for a related reason, stated
in its own docstring (`:127-129`):

> *"Split out of main() 2026-08-19 so `--self-test` can drive the RULE without a live Postgres…
> The rule and the fetch are different things, and only one of them needed the container."*

In this skill's language: **the seam already exists.** `columns()` (`:97`) is its one adapter. One
adapter is a hypothetical seam; two make it real.

### 2.2 — Measured: the rule fires correctly on `scripts/`, unchanged

A throwaway adapter — `ast`-parse every `scripts/*.py`, emit `(filename, module-level symbol)` — was
fed to `evaluate()` **with no modification to `evaluate()` and no modification to the script**.
Population: **1,382 module-level symbols across 63 files.**

| stem | files | which |
|---|---:|---|
| `decide` | **5** | `check-banner-armed`, `check-ci-watched`, `check-closing-table`, `check-plan-progress`, `check-review-decision` |
| `SENTINEL` | **4** | `begin-plan`, `check-banner-armed`, `check-ci-watched`, `check-plan-progress` |
| `log_line` | 3 | `check-banner-armed`, `check-ci-watched`, `check-closing-table` |
| `WARN_LOG` | 3 | `check-banner-armed`, `check-ci-watched`, `check-closing-table` |
| `parse_sentinel` | 2 | `check-ci-watched`, `check-plan-progress` |
| `render_sentinel` | 2 | `begin-plan`, `check-ci-watched` |

**Backlog #166 names one of these six.** It is not the largest.

⚠ **Two of the six are probably `ALLOWED` entries, not defects, and that is the mechanism working
rather than a false-positive rate.** `decide` across five files is a shared verb for *"this guard's
verdict function"* — shared identity, the same category as `created_at` in the schema substrate,
which `check-vocabulary-collisions.py:28-32` already carves out by curating the stem list.
`SENTINEL` names **two different files** — `.claude/ci-watching` in one, `.claude/executing-plan` in
the other three — which is the *different concepts sharing a word* case `ALLOWED` exists for.
Reporting them and making someone write down which, is the designed behaviour.

### 2.3 — The `h.split(".")[0]` round-trip is safe here, measured rather than assumed

`evaluate()` joins the pair into `"{t}.{c}"` and re-splits on the **first** dot to recover the
container. That is lossy for any container or symbol containing a dot, and a filename has one by
construction. Measured over the live population:

- symbols containing a dot: **0**
- files sharing a stem before the extension (e.g. a `.py`/`.sh` pair): **none**

So it works today — but **by luck, not by contract**. A `check-ci-watched.sh` added beside
`check-ci-watched.py` would silently collapse two containers into one and suppress a real collision.
That is a fix to make while extracting, not a reason not to extract.

### 2.4 — ⛔ The first thing that stops it: the stem match is case-sensitive, and that is a FALSE GREEN

`:134` is `stem in c`. Every entry in `MECHANISM_STEMS` is lowercase, because Postgres column names
are lowercase by convention. Python module-level constants are UPPERCASE by convention. Measured:

```
stem='warn_log'   -> 0 hit(s)
stem='WARN_LOG'   -> 3 hit(s)
```

Three files declare `WARN_LOG`. **A second adapter written by someone carrying the schema substrate's
habits would report zero collisions and pass.** That is a false green in the one guard whose entire
reason for existing is catching what every other gate structurally cannot — and this project has a
standing note that a vocabulary which silently stops matching is worse than no check at all
(ADR-0010 §2, rejecting free-text tags on exactly this ground).

### 2.45 — The family has FOUR log files, 131 live records, and **zero parsers** — measured across all four

Each producer's docstring claims its own log has no consumer. Taken together and verified as one
sweep (every `*.py`, `*.sh`, `*.ts`, `*.js`, `*.yml`, `*.md` under `scripts/`, `.claude/`,
`.github/`, `docs/`):

| Log file | Lines on disk | Code that reads it |
|---|---:|---|
| `.claude/banner-warnings.log` | 76 | **none** — only `check-banner-armed.py` itself |
| `.claude/banner-flush-observations.log` | 45 | **none** — only `check-banner-armed.py` itself |
| `.claude/ci-unwatched.log` | 5 | **none** — only `check-ci-watched.py` itself |
| `.claude/closing-table-warnings.log` | 5 | **none** — only `check-closing-table.py` itself |

Every other reference in the repo is prose — designs, backlog rows, review documents.

⭐ **This matters for §6's ordering, in the honest direction: it LOWERS the urgency of the log work
and raises the urgency of the instrument.** Three injectable producers with no parser cannot corrupt
a consumer that does not exist; the hole is a contract hole, exactly as #166 says. The logs exist to
*become* a denominator later — `check-ci-watched.log_line:170` says so outright (*"it exists so the
promote-to-blocking decision has a denominator"*). **So work 3 is cheap insurance on a grammar
nothing yet depends on, and work 1 is what stops the family growing a fifth member meanwhile.**

⚠ **One stale claim found while verifying this.** `check-banner-armed.py:633` reads: *"Nothing parses
this file (searched 2026-09-04: only this module, its self-test, **a comment in block-idle-stop.sh**,
and prose in docs/dashboard-entries.md)."* Measured — `.claude/hooks/block-idle-stop.sh` contains no
reference to `banner-warnings.log` or `WARN_LOG` at all; it references the **script**
`check-banner-armed.py` (`:11`, `:75`), which is a different thing. The load-bearing half of the
sentence (*nothing parses this file*) is **true and now verified family-wide**; its enumeration of
referrers has expired. Same class as F6 — an evidence list that is not re-derived when it moves, in
a file whose own hook records at `:156` having *"measured the check-banner-armed line reference as
already pointing at unrelated prose."*

### 2.5 — ⛔ The second thing that stops it, and it is the important one: **a renamed duplicate is invisible**

This is a limitation of the proposed fix, found by testing the fix rather than the finding, and it
decides how much of the inherited brief the fix can actually close.

A collision check keys on a **name**. It sees a duplicate that kept its name and is blind to one that
did not. Measured — **three readers of one `key: value` sentinel grammar, under two names**:

| Reader | Where | Name | Seen by a name check? |
|---|---|---|---|
| `parse_sentinel` | `check-plan-progress.py:106` | same | ✅ |
| `parse_sentinel` | `check-ci-watched.py:206` | same | ✅ |
| `_armed_from_text` | `check-banner-armed.py:651` | **different** | ❌ **invisible** |

All three iterate `text.splitlines()`, skip lines without `":"`, and split on the first colon. The
third is the one whose agreement with the others is load-bearing — its own docstring says so
(`:654-656`): *"the two must agree about what 'armed' means, or this guard's principal firing state
becomes the one documented escape."* `check-plan-progress.strip_field` (`:116-120`) says the same
thing from the other side: *"THE POINT IS THE AGREEMENT, NOT THE STRING SURGERY."*

**So the instrument in §2.2 catches backlog #166 and misses the heart of #165.** Recommending it as
the answer to both would be this review asserting a fix it had not tested. The consequence is §4's.

---

## §3 — The sentinel grammar: backlog #100 is right, and bounded to one file too few

Backlog **#165** says *"backlog #100 owns the sentinel grammar"*, and it does. #100 is a thorough
row and this review does not improve on its diagnosis:

> *"the file is a schema-less `key: value` store whose WRITERS (`begin-plan.py` — `_arm`,
> `cmd_pause`, `cmd_resume`) validate against hand-written rules, while its READERS
> (`check-plan-progress.parse_sentinel` / `strip_field`, `check-banner-armed._armed_from_text`)
> parse with `str.splitlines()`. Two grammars for one file."*

Its candidate **(a)** — *"one owner for the sentinel — a small module that reads, writes and
validates it, which both guards and `begin-plan.py` import"* — is the right answer, and §1's
evidence says why: that is exactly the `page_markup` / `m4_base_db` move, already proven twice here.

**The contribution of this review is one correction, and it changes the scope of the fix.**

### 3.1 — The grammar was already in TWO files when #100 was filed

| Sentinel file | Declared at | Readers |
|---|---|---|
| `.claude/executing-plan` | `begin-plan.py:81`, `check-banner-armed.py:143`, `check-plan-progress.py:88` | `parse_sentinel` (`check-plan-progress.py:106`), `strip_field` (`:116`), `_armed_from_text` (`check-banner-armed.py:651`) |
| **`.claude/ci-watching`** | **`check-ci-watched.py:60`** | **`parse_sentinel` (`check-ci-watched.py:206`)** |

#100 lists only the first row. Measured — and this refutes the obvious explanation:

- `check-ci-watched.py` and its `parse_sentinel` were **both created in `632a60f4`, 2026-09-04**;
- **#100 was filed 2026-09-06.**

So the second implementation is **not** a later replication that #100 could not have seen. It
existed, with the same function name, over the same grammar, two days before #100 was written.
**#100 scoped itself to a FILE when the subject was a GRAMMAR**, and the grammar already had two.

⚠ **This review states that as a correction to a row's scope, not as a criticism of the row.** #100's
own falsifier — *"add a writer that puts any new field into the sentinel, or a reader that asks a
question about it, without touching both `begin-plan.py` and `check-plan-progress.py`"* — is
excellent and is preserved below with one clause widened.

### 3.2 — The two `parse_sentinel`s share a name and return different types

This is worse than a plain duplicate, and it is the concrete reason the scope matters:

| | `check-plan-progress.py:106` | `check-ci-watched.py:206` |
|---|---|---|
| Signature | `(text: str) -> dict[str, str]` | `(text: str) -> str \| None` |
| Returns | every key | the `sha` value only |
| On a line with no colon | skips | skips |
| Split | `line.split(":", 1)`, both sides `.strip()` | identical |

Same name, same grammar, same skip rule, **different return type**. A reader who has learned one
will misread the other — and `check-banner-armed._armed_from_text:670-675` records that the
colon-skip rule is *load-bearing* and that a divergence between readers already cost a measured
defect on 2026-09-04.

#### ⛔ 3.2a — They do not merely differ in type. On a DUPLICATE KEY they give OPPOSITE answers.

Measured by driving all three readers over sixteen adversarial sentinel texts. Fifteen agree. One
does not, and it is the one that matters:

```
input:  "sha: first\nsha: second\n"

  check-plan-progress.parse_sentinel  ->  'second'     LAST wins
  check-ci-watched.parse_sentinel     ->  'first'      FIRST wins
```

The mechanism, quoted rather than characterised — both loop `for line in text.splitlines()` and both
guard on `if ":" in line`, and then:

```python
# check-plan-progress.py:112     accumulates, so a later line OVERWRITES
out[k.strip()] = v.strip()

# check-ci-watched.py:211-212    returns on the first match, so a later line is UNREACHABLE
if k.strip() == "sha" and v.strip():
    return v.strip()
```

⭐ **Why this is the important finding in §3, and not a curiosity.** Backlog #100's instance (2) is
*exactly* a duplicate-key event: `--pause` wrote free text into the `key: value` file and **a
newline injected a live second `plan:` field**, so the Stop guard supervised a DIFFERENT plan. Which
field wins is therefore not academic — it decides which plan is supervised. **The two readers of
this grammar answer that question in opposite directions**, and nothing anywhere states which is
correct, because no document says the grammar permits a duplicate key at all.

⚠ **Honest bound: this is not a live defect today — and that is now verified at the WRITER, not
assumed.** `begin-plan.cmd_pause` strips before it appends (`:521`), and measured,
`strip_field(stack, "paused")` removes **every** occurrence, so a restatement cannot leave a second
`paused:` line. The two readers are also pointed at *different* sentinel files, so no single input
reaches both. It is a latent divergence that becomes live the moment §3.3's shared owner is written.

⭐ **But the duplicate-key shape is NOT hypothetical — this repo has already had it, and already
measured why nobody noticed.** `begin-plan.py:518-520`, in its own words:

> *"STRIP BEFORE APPEND, so a restatement leaves ONE pair rather than a growing stack. **Last-wins
> parsing made the stack harmless to READ, which is exactly why it went unnoticed for as long as it
> did** — the file was wrong in a way no reader complained about."*

⛔ **Correction to this review's own first draft of F12.** It said *"nothing anywhere states which
[rule] is correct."* **Too strong.** There is recorded evidence, and it points one way — measured
against the exact stack that comment describes:

```
"plan: p\narmed: t\npaused: first reason\npaused: second reason\npaused: third reason\n"

  check-plan-progress (LAST wins)  -> 'third reason'   newest — why the defect READ as fine
  check-ci-watched    (FIRST wins) -> 'first reason'   oldest — a stale reason, silently
```

So the two rules do not merely differ: **each has a known failure mode in this codebase.** Last-wins
*masked a writer defect* — recorded, not speculative. First-wins would not have masked it but would
have pinned the *stale* value, reporting a pause reason three restatements out of date. **Whoever
writes the shared owner is choosing between two failure modes, not between a right and a wrong
answer** — which is a stronger argument for #100's candidate *(b)* (enumerate the legal states, so
*duplicate key* is decided rather than discovered) than "no basis for choosing" was.

**The other fifteen cases agree**, and are recorded so the claim is falsifiable rather than a
sample: plain, key-with-inner-space, leading whitespace, trailing whitespace on the key, a value
containing a colon, empty value, a bare `":"` line, an uppercase key, `**paused**` with no colon,
`paused:` with a colon, CRLF, ` `, and form feed.

### 3.3 — What the fix must therefore be

**#100 candidate (a), with its population taken as the GRAMMAR rather than one file.** One module
that reads, writes and validates the `key: value` sentinel grammar, imported by `begin-plan.py`,
`check-plan-progress.py`, `check-banner-armed.py` **and `check-ci-watched.py`**. The projections stay
per-caller (one wants a dict, one wants a `sha`); the *parse* is one implementation.

⚠ **Widened falsifier**, extending #100's: *add a writer that puts a new field into **either**
sentinel, or a reader that asks a question about **either**, without touching the shared module.*
Today that is possible in both files and nothing notices.

---

## §4 — The three inherited questions, answered together — and the framing partly refuted

The brief says the three rows *"converge on one thing: duplicated mechanisms no guard can see"* and
asks that they be answered together. **Two of them do. The third does not, and folding it in would
be the error.**

| Row | Class | Answer |
|---|---|---|
| **#166** — three `log_line` producers | **cross-member** | A second adapter to `evaluate()` (F2) + hoist `_col`. Closed by §2. |
| **#165** — what "paused" means | **cross-member** | It is **backlog #100**, candidate **(a)**, with the population widened from one FILE to the GRAMMAR (§3). |
| **#164** — derived values at two inputs | **per-member** | **A different class.** Extend `check-fixture-variation.analyse`; do NOT build a sibling guard (§4.2). |

### 4.1 — Why #165 and #166 are one class and one decision

Both are *"N files independently implement one mechanism"*. Both are invisible to every instrument
the repo owns over `scripts/`, for the reason F1 gives. Both have the same shape of fix — the
extraction this repo has already performed twice (`page_markup`, `m4_base_db`) — and **they should be
decided together**, because the observer family would otherwise get a shared *sentinel* module and a
shared *log* module by two separate decisions, which is how a third arrives.

⭐ **They are also not equally closed by the same instrument, and that asymmetry is the finding.**
The collision adapter (F2) sees #166 because its duplicates kept the name `log_line`. It does **not**
see #165's third reader, because `_armed_from_text` was renamed (F4). So:

- the **instrument** (F2, F3, F9) makes the *next* duplicate expensive to write;
- the **extraction** (§3.3) removes the *existing* one that the instrument cannot see.

Neither substitutes for the other. Doing only the instrument leaves #165 open and reports success.

### 4.2 — Why #164 is NOT that class, measured

#164's property — *a case asserting a derived value must exercise its producer at two DISTINCT
inputs* — is a property of **one case**. It is not "two files implement one mechanism". Answering it
alongside the other two, as the brief asks, produces the wrong fix: a **new sibling guard**, which
would be a *second independent reader of the same test suites* — a fresh instance of exactly the
class #165 and #166 are instances of.

**The row's conclusion is right, and so is its worked example** — ⟳ this sentence is a correction;
an earlier draft of this section, and of backlog #164, claimed the example was wrong. It was
refuted by an adversarial check and the retraction is §4.3. What follows is a **second, more
general** demonstration of the same gap, not a replacement for the row's.

Measured by running `check-fixture-variation.analyse` on a miniature of
`begin-plan.render_banner` (`:222`, whose banner is
`f"## ▶ STEP {index + 1} of {len(steps)} — {s.title}"` at `:230`):

```python
# BOTH parameters vary in source text; len(steps) is 3 in BOTH.
case("a", render_banner(["a","b","c"], 0), "STEP 1 of 3")
case("b", render_banner(["x","y","z"], 1), "STEP 2 of 3")
#   -> analyse() returns []          PASSES

# control: `steps` frozen in source text too
case("a", render_banner(["a","b","c"], 0), "STEP 1 of 3")
case("b", render_banner(["a","b","c"], 1), "STEP 2 of 3")
#   -> "`render_banner(steps=…)` is passed the SAME value at every call site"   FLAGGED
```

The guard's own docstring states the cause without drawing this conclusion from it (`:52-56`):

> *"It compares the SOURCE TEXT of arguments… So it is a floor — it proves a parameter was
> *thought about*, never that the values chosen are good ones."*

**Therefore the work belongs inside `check-fixture-variation.py`, as an extension of `analyse` from
argument source text to derived components — not as a sibling.** That also answers the row's own open
question (*"decide whether the property is mechanisable"*): the machinery is `ast`, the guard already
has it, and the extension has a natural home with one owner.

### ⟳ 4.3 — RETRACTION: this review claimed #164's worked example was wrong. It is not.

**What was published and is now withdrawn.** §4.2 and F11 asserted that #164's distinguishing
example — `STEP 2 of 5` and `STEP 2 of 3` in two cases — *"would be caught, because a frozen `index`
is an unvaried parameter"*, and a correction saying so was appended to backlog **#164**.

**The refutation.** Raised by an adversarial check on this review's own finding, then re-measured
here. The claim rests on `step` being a **parameter**. In the real subject it is not:

```python
# scripts/check-banner-armed.py:503
def decide(texts: list[str] | None, armed: bool,
           steps=_UNSET, edited: bool = False,
           tool_uses: int = 0, paused: bool = False) -> tuple[int, str, str]:
```

The banner — and therefore the step number — rides **inside `texts`**. There is no `decide.step`.
Two cases passing `["…STEP 2 of 5…"]` and `["…STEP 2 of 3…"]` vary `texts` in source text while the
step stays frozen at 2, and `analyse` has nothing to flag.

Measured against that signature, with **every other parameter varied** so nothing else can account
for the verdict:

```
findings : []
examined : ['decide.armed', 'decide.edited', 'decide.steps', 'decide.texts']
```

Non-vacuous (all four parameters discovered and judged) and **zero findings**. **#164's example is a
genuine miss in situ.**

⛔ **The error, named, because it is one this project has a standing note about.** I measured a
*synthetic* signature — `render_banner(steps, index)`, where `index` genuinely is a parameter — and
generalised the result to a subject with a different shape. That is *measure the population the code
actually sees*, failed at the point of drawing the conclusion rather than at the point of running the
code. My run was correct about `render_banner` and silent about `decide`.

**What survives, and it is the more useful framing.** There are **two distinct ways** a quantity can
be frozen and invisible to `analyse`, and the row and this review each found one:

| | Frozen quantity | Why `analyse` cannot see it | Example |
|---|---|---|---|
| **#164's** | a component of a **composite parameter** | the parameter's text varies; the component inside it does not | `texts=["…STEP 2 of 5…"]` vs `["…STEP 2 of 3…"]` |
| **this review's** | a value **derived** from a parameter | the parameter's text varies; `len()` of it does not | `len(steps)` = 3 for `["a","b","c"]` and `["x","y","z"]` |

Both are real. This review's is **more general** — it holds for any signature, because the frozen
quantity is computed inside the producer and never appears at a call site at all — so it is the
better example to build the extension against. **But #164's evidence is not wrong, and the backlog
row's correction has been rewritten to say so.**

⭐ **One thing the adversarial check established that this review had not:** `analyse` returns
`(findings, examined_keys)` — a *set*, not a count — deliberately, because *"'this entry did not
fire' and 'this parameter is no longer examined at all' are the same observation"* (`:703-708`).
That second value is what separates a real pass from a vacuous one, and every `PASSES` claimed in
§4.2 and here is now reported with its non-empty `examined` set. A private function or an uncalled
one yields `examined=[]` and would have passed for an unrelated reason.

---

## §4.5 — How this review was conducted, stated because a gate depends on it

⚠ **Three `Explore` agents were dispatched** (the observer-log family, the sentinel grammar,
`check-fixture-variation`'s real scope). **None returned before §1–§6 were written**, and a
partial-results request to each went unanswered; the agent later reported its replies had been
plain text that never routed. Every measurement in §1–§6 was produced by the coordinator running
the code, and the runs are reproduced inline.

⟳ **CORRECTION, after §1–§6 were committed: `observer-logs` DID eventually deliver**, and F13–F15
below originate as **leads from it**. Each was re-measured by the coordinator before being written
down — the file bytes opened, the producing lines read — and the runs are shown. So the skill's rule
holds in its usual direction here rather than being moot, and this paragraph is corrected rather
than left standing, because a claim about how a review was conducted is exactly the kind that gets
believed without checking.

⛔ **And the agent's own summary contradicted its own data, which is the rule working.** Its §2
concluded that `check-banner-armed.py:633`'s referrer list is *"still accurate"* — including *"a
comment in block-idle-stop.sh"* — while the 19-file table in its §1 **omits that hook entirely**.
Re-measured: `grep -c "banner-warnings\|ci-unwatched\|closing-table-warnings\|banner-flush"
.claude/hooks/block-idle-stop.sh` → **0**. The hook invokes the *scripts* and never names a log. The
finding in §2.45 stands; the agent's prose summary was wrong where its table was right.

---

## §5 — Findings

Every finding below was measured by the coordinator by hand, by running the code. Agent output was
used to generate candidates and is marked where any survives into a claim. **Structural** means the
shape is wrong; **transitional** means the choice was right for its moment and has expired.

### F1 — No instrument over `scripts/` asks a question that spans two files — **High, structural**

Six guards take `scripts/` as their subject; all six ask a per-member question (§1). The repo built
the cross-member instrument for the *schema* substrate, at the cost of six adversarial rounds, and
has never had one for its own tooling — which is now where essentially all work happens.

**Falsifier:** name a guard in `scripts/` whose verdict changes when a *second* file changes and the
first does not. If one exists, this finding is wrong.

⭐ **The evidence that this is structural rather than an oversight**: architecture review #153 named
the class on 2026-09-21; on 2026-09-22 `check-ci-watched.log_line` shipped as the fourth duplicate,
in a docstring that names the problem in capitals and explains — correctly — why copying was the
cheaper move at slice time. **Naming the class did not stop it. Prose is not the missing mechanism.**

### F2 — `evaluate()` needs a second adapter, not a new guard — **Medium, structural**

`check-vocabulary-collisions.evaluate()` (`:120`) is already substrate-neutral and was deliberately
split from its fetch (`:127-129`). Run over the live `scripts/` population unchanged, it reports
**six** collisions (§2.2) where backlog #166 names one. The seam exists with one adapter.

### F3 — A second adapter would go **silently green**: the stem match is case-sensitive — **Medium, false green**

`:134` is `stem in c`; `MECHANISM_STEMS` is all-lowercase because Postgres columns are. Python
constants are UPPERCASE. `warn_log` → 0 hits, `WARN_LOG` → 3 (§2.4). A false green in the one guard
whose purpose is catching what other gates structurally cannot.

### F4 — A name-based check cannot see a **renamed** duplicate, and that is #165's core — **Medium, structural**

Three readers of one `key: value` sentinel grammar under two names; `_armed_from_text`
(`check-banner-armed.py:651`) is invisible to a name check (§2.5). **This bounds F2:** the adapter
closes #166 and does not close #165. Recommending it for both would assert an untested fix.

### F5 — Three of four log producers are field-injectable, not two — **Medium, structural**

Backlog #166 says "the two that ship". Measured by running all four with `session = "sess\tinjected"`
and `"sess\nsecond"`, against the expected shape of 4 columns / 1 record:

| Producer | cols | records | verdict |
|---|---:|---:|---|
| `check-banner-armed.log_line` (`:626`) | 5 | 2 | **INJECTABLE** |
| `check-banner-armed.flush_line` (`:639`) | 5 | 2 | **INJECTABLE** |
| `check-ci-watched.log_line` (`:156`) | 4 | 1 | SAFE (`_col`, `:177`) |
| `check-closing-table.log_line` (`:841`) | 5 | 2 | **INJECTABLE** |

`flush_line` is a **fourth producer the row does not count** — same two leading columns, a third
grammar, its own file (`FLUSH_LOG`, `:150`). Exploitability remains nil (`session_id` is a
harness-generated UUID); this is a contract hole, as #166 says. The correction is to the *count*.

⭐ `_col` (`:177`) is the right thing to hoist: it asks `splitlines()` — the consumer's own rule —
rather than enumerating separators, so it also covers `\v`, `\f`, ` `. The producer is stricter
than any consumer, which is the safe direction.

### F6 — The comment documenting the injection fix has an unverified number — **Low**

`check-ci-watched.py:183` states that the pre-fix producer, given
`log_line("unwatched", "d", "T", "s\tinjected")`, yields *"SIX columns, not four"*. Measured against
`check-banner-armed.log_line`, which `:194` calls byte-identical to the pre-fix form:

```
'T\ts\tinjected\tunwatched\td\n'  ->  ['T','s','injected','unwatched','d']  ->  5
```

**Five.** Worth a line because of where it sits: an unprovenanced number inside the evidence for a
review finding, in a repo whose own memory records that class as costly and recurring.

### F7 — The dashboard-entry ratchet lacks the frozen-payload warning its sibling carries — **Medium, structural**

`ci.yml:465-471` records, in detail and with a measurement (PR #322, 2026-09-18, two rerun cycles),
that `github.event.pull_request.body` is read from the **frozen event payload**, so editing a PR body
does not re-arm the gate and `gh run rerun` replays the stale payload. That comment sits on
`check-review-recorded` (`:472`). The `dashboard entry ratchet` (`:447`) has the identical
`BODY: ${{ github.event.pull_request.body }}` property, **no warning**, and a refusal message that
tells the reader to *"put 'NO-ENTRY: <reason>' in the PR body"* — an instruction that cannot, by
itself, make the gate pass.

⭐ **Measured on this review's own branch, today.** PR #336 refused; the body was edited exactly as
instructed; a rerun was spent; the cause was the documented one, found by reading the *sibling's*
comment. **The same class as F1 at a different scale** — one rule, two sites, the knowledge on one
of them. Two sites is the whole population (`grep 'github.event.pull_request.body' .github/workflows/`).

### F8 — An external `session_id` is used as a path component, unvalidated — **Low, structural**

`check-banner-armed.py` reads `session_id` from the Stop payload (`:958`) and interpolates it into
filenames: `JOURNAL_DIR / f"{session_id}.json"` (`:903`), `f".{session_id}.tmp"` (`:920`), and the
`replace` target (`:924`). No validation. A `/` or `..` escapes `JOURNAL_DIR`.

⚠ **Honest severity: this is a contract hole, not a live defect**, for the same reason F5 is —
`session_id` is a harness-generated UUID. It is recorded because it is the *same class* as F5 in a
more consequential position: the failure is caught by `except OSError` (`:926`) and degrades to
`return False`, which the caller reports as CANNOT RUN — fail-closed, and therefore silent.

### F10 — Backlog #100 is scoped to a FILE when its subject is a GRAMMAR — **Medium, structural**

#100 names `.claude/executing-plan` and its three readers. The same `key: value` grammar is also
parsed by `check-ci-watched.parse_sentinel` (`:206`) over `.claude/ci-watching` (`:60`) — created
`632a60f4`, **2026-09-04, two days BEFORE #100 was filed** (§3.1). So this is not a later
replication #100 could not have seen; the population was already two when it was written.

**Consequence:** #100's candidate *(a)* — *"one owner for the sentinel"* — is under-scoped as
written. Executed literally it gives one sentinel an owner and leaves the second with its own copy.
The two `parse_sentinel`s additionally **share a name and return different types**
(`dict[str, str]` vs `str | None`), which is worse than a plain duplicate: a reader who learns one
will misread the other (§3.2).

### F13 — ⭐ The record grammar ALREADY DRIFTED, silently, and nothing could have caught it — **High, structural**

*Lead from `observer-logs`; re-measured by opening the files.* Columns 3 and 4 of the banner warning
log **swapped meaning** between 2026-09-04 and 2026-09-05, with no version marker in any generation:

| File | First record's cols 3, 4 | Meaning |
|---|---|---|
| `.claude/banner-warnings.pre-backlog96.log` (2026-09-04) | `STEP 4 of 5`, `unarmed` | **detail, reason** |
| `.claude/banner-warnings-archived-2026-09-06.log` (2026-09-05) | `unarmed`, `STEP 3 of 4` | **reason, detail** |
| `.claude/banner-warnings.log` (live, 2026-09-06→) | `unarmed`, `STEP 2 of 5` | reason, detail |

⭐ **This is the thesis of the whole review, already having happened once and gone unnoticed.** §2.45
establishes the family has four writers and zero readers; F13 is what that costs. A grammar with no
consumer has no falsifier, so its columns can invert between two generations of the same file and
**no test, no guard and no reviewer can observe it**. The 76 live records and the 6 pre-backlog96
records are not comparable, and nothing anywhere says so.

⚠ **The consequence for the promote-to-blocking decision these logs exist to inform**
(`check-ci-watched.py:170`): any future analysis that concatenates generations of `banner-warnings*`
silently mixes two column orders. **A shared record owner (§6 work 3) must carry a version marker**,
which none of the four producers has today. That raises work 3 above the "cheap insurance" framing
§2.45 gave it — the risk is not injection, it is that the denominator is already unsound.

### F14 — Two timestamp grammars across three writers of one record shape — **Low, structural**

*Lead from `observer-logs`; re-measured from the live files and the producing lines.*

| Log | First field | Producer |
|---|---|---|
| `banner-warnings.log` | `2026-09-06T07:27:10-07:00` | `.isoformat()` (`check-banner-armed.py:1162`) |
| `banner-flush-observations.log` | `2026-09-06T12:39:58-07:00` | `.isoformat()` (`:942`) |
| `ci-unwatched.log` | `2026-09-22T20:33:31-07:00` | `.isoformat()` (`check-ci-watched.py:411`) |
| **`closing-table-warnings.log`** | **`2026-09-22T17:10:57-0700`** | **`strftime("%Y-%m-%dT%H:%M:%S%z")`** (`check-closing-table.py:926`) |

Three writers agree; the fourth omits the colon in the UTC offset. Both are valid ISO 8601, and
`datetime.fromisoformat` accepts both on Python ≥ 3.11 — so this is a latent inconsistency, not a
parse failure. It belongs to work 3: a single owner emits one.

### F15 — The documented human reader of a log does not exist in the file it is cited from — **Low**

*Lead from `observer-logs`; re-measured.* `check-closing-table.py:846` opens its justification with
*"`docs/dev-process.md` tells the reader to 'read the log in a few weeks' to answer *does this guard
cry wolf?*"* — and that is the argument for the whole `turn` column. Measured:

```
grep -c "closing-table\|closing table" docs/dev-process.md   ->  0
grep -c "in a few weeks"               docs/dev-process.md   ->  0
```

The cited instruction is not in the cited file. `docs/backlog.md` row **#149** repeats the same
citation as its severity justification, so a second row now rests on it. ⚠ **The `turn` column is
still right** — its own measurement over 767 transcripts (`:848-854`) is independent of who reads
the log. What has expired is the *reason given for collecting it at all*, which is the same class as
F6 and §2.45: an evidence citation that is not re-derived when its subject moves.

### F12 — The two `parse_sentinel`s resolve a DUPLICATE KEY in opposite directions — **Medium, structural, latent**

Measured over sixteen adversarial sentinel texts; fifteen agree, one does not (§3.2a):

```
"sha: first\nsha: second\n"   ->  check-plan-progress: 'second' (LAST wins)
                                  check-ci-watched:    'first'  (FIRST wins)
```

`check-plan-progress.py:112` accumulates into a dict so a later line overwrites;
`check-ci-watched.py:211-212` returns on the first match so a later line is unreachable.

⭐ **Backlog #100's own instance (2) is a duplicate-key event** — `--pause` free text with a newline
injected a live second `plan:` field and the Stop guard supervised a different plan. Which field
wins decides which plan is supervised, and the two readers of this grammar answer oppositely.

⚠ **Not live today, verified at the WRITER** — `cmd_pause` strips before appending (`:521`) and
`strip_field` removes every occurrence (measured), so a restatement cannot stack; and the readers
are pointed at different sentinel files. It becomes live when §3.3's shared owner is written.

⟳ **F12's first draft said *"nothing states which rule is correct."* Corrected — there is evidence,
and it indicts both.** `begin-plan.py:518-520` records that a growing stack of `paused:` lines
actually occurred and that **last-wins parsing is why it went unnoticed** (*"the file was wrong in a
way no reader complained about"*). Measured on that exact stack: last-wins returns the newest
reason (hiding the defect), first-wins returns a **stale** one three restatements old. The choice is
between two known failure modes — a stronger case for #100's candidate *(b)* (enumerate the legal
states, so *duplicate key* is decided rather than discovered) than the original wording made.

### F11 — ⟳ RETRACTED AND REPLACED: #164's example is RIGHT; this review found a SECOND, more general one — **Medium**

⛔ **As first published, F11 read *"#164's conclusion is right; its worked example is wrong"*. That
is withdrawn.** The example rests on `step` being a parameter of `check-banner-armed.decide`; it is
not — the banner rides inside `texts` (`:503`). Re-measured with every other parameter varied:
`findings=[]`, `examined=['decide.armed','decide.edited','decide.steps','decide.texts']`. **#164's
example is a genuine miss in situ.** The error was generalising a run against a *synthetic*
signature to a subject with a different shape. Full retraction and the two-mechanism table: §4.3.

**What stands:** `analyse` compares `ast.unparse`-normalised argument text and is blind to any
frozen quantity that is not itself a parameter — whether it is a *component of a composite
parameter* (#164's case) or a *value derived from one* (this review's, `len(steps)`). The second is
more general and is the better target to build against. The fix still belongs **inside**
`check-fixture-variation.py`, not in a sibling guard.

Measured by running `check-fixture-variation.analyse` (§4.2). The row's example
(`STEP 2 of 5` / `STEP 2 of 3` in two cases) **would be caught** — a frozen `index` is an unvaried
parameter, which is exactly what the guard flags. The real gap is a frozen **derived component**
(`len(steps)`) whose **source parameter varies in text**; that passes with an empty problem list.

**The conclusion survives, the evidence is replaced, and the fix moves:** because the gap is in
`analyse`'s source-text comparison, the work belongs **inside `check-fixture-variation.py`** as an
extension, not in the sibling guard the row proposes. A sibling would be a second independent reader
of the same suites — a new instance of F1's class.

### F9 — `evaluate()`'s container round-trip is safe by luck, not by contract — **Low, structural**

`f"{t}.{c}"` then `h.split(".")[0]` recovers the container from the **first** dot. Measured over the
live population: 0 symbols contain a dot, and no two files share a stem before the extension — so it
is correct today. A `check-ci-watched.sh` beside `check-ci-watched.py` would collapse two containers
into one and suppress a real collision. Fix while extracting, not a reason not to extract.

---

## §6 — Recommendation, in the order that makes each step cheap

**Three pieces of work, and the order matters** — the instrument makes the *next* duplicate
expensive, the extractions remove the *existing* ones it cannot see.

| # | Work | Closes | Size |
|---|---|---|---|
| 1 | **Second adapter for `check-vocabulary-collisions`** — an `ast` reader emitting `(file, module-level symbol)` pairs over `scripts/*.py`, plus a curated observer stem list and its own `ALLOWED`. Fix F3 (case) and F9 (dot round-trip) while extracting. | F1 partly, F2, F3, F9 | **M** |
| 2 | **One owner for the sentinel grammar** — #100 candidate (a), population = the GRAMMAR. Imported by `begin-plan.py`, `check-plan-progress.py`, `check-banner-armed.py`, `check-ci-watched.py`. | #165, #100, F4, F10 | **M** |
| 3 | **One owner for the observer-log record** — hoist `_col`, the `when\tsession\t…` prefix, **and a VERSION MARKER**. Closes the injection hole in all three producers at once. | #166, F5, F8, **F13**, F14 | **S** |

⟳ **Work 3's justification CHANGED after F13, and the table above already reflects it.** §2.45
argued work 3 was cheap insurance on a grammar nothing depends on — true as far as it went, and
based on the correct observation that the family has zero parsers. **F13 then measured that the
grammar has ALREADY inverted its columns once, between two generations of the same file, unnoticed.**
So the case for work 3 is not the injection hole (contract-only, exploitability nil) and not a
future parser: it is that **the denominator these logs exist to provide is already unsound**, and no
producer carries a version marker that would let a reader tell the generations apart. A shared owner
that emits a version is what makes the 76 live records mean something.

⚠ **1 before 2 and 3, and not for tidiness.** The adapter is what makes the extractions *stay*
extracted: without it, the fourth `log_line` costs nothing to write again, which is precisely what
§0 measured happening within 24 hours of the class being named.

⚠ **2 and 3 are one decision, taken together** (§4.1). Taken separately, the observer family gets a
shared sentinel module and a shared log module by two independent choices — which is how a third
arrives.

**Do NOT do** — a sibling guard for backlog #164. Extend `check-fixture-variation.analyse` instead
(F11). And do not treat work 1 as closing #165: it cannot see `_armed_from_text` (F4).

**Two small fixes that ride along, neither worth its own slice:**
`ci.yml`'s dashboard-entry step gets the frozen-payload comment its sibling carries (F7); and
`check-ci-watched.py:183` says five, not six (F6).

---

## §7 — What we decided this milestone that is not written down

`docs/dev-process.md` requires this question of every architecture review, calling it *"the one
failure no tool can see."* Three answers, each now recorded somewhere it can be found:

1. **"Match the closest sibling rather than invent a fourth grammar" is a real decision rule this
   repo follows**, and it is nowhere written down. It is *correct at slice time* and produced four
   duplicate producers and 82 sibling references across 17 guards. It needs either a written home or
   a mechanism that prices it (§6 work 1). Recorded here; belongs in `process-checklists.md`.
2. **`docs/reviews/` documents carry no `Anchor:` header, deliberately.** ADR-0010's scope table says
   so (`:108`) and nothing else does; an earlier draft of *this* document invented one.
3. **A gate whose remedy lives in the PR body cannot be satisfied by editing the PR body.** Known,
   measured twice (PR #322, PR #336), and written on exactly one of the two steps it applies to (F7).

---

## §8 — Status: nothing here is filed yet, and that is deliberate

⛔ **No backlog row and no roadmap edit has been made for any finding in §5.** `docs/dev-process.md`
says findings that become work go to `docs/backlog.md` **and** the roadmap in the same turn; that is
held pending the user's sign-off, because the standing instruction from 2026-07-31 is that
**investigating and filing are separate steps, and filing is the user's**:

> *"we were discussing the nature of the issue and you just file the ticket. I think you need to
> agree with me before file the tickets."*

The precedent is this exact artifact — an architecture review document plus roadmap rows, filed
without asking, where several framings then needed correction during the discussion that followed.

**So §5 is eleven PROPOSED findings pending sign-off, not eleven filed ones**, and §6 is a proposed
sequence. What would be filed, if agreed:

| Proposed | From | Touches |
|---|---|---|
| one new row — the cross-member instrument over `scripts/` | F1, F2, F3, F9 | new |
| widen **#100**'s population from one file to the grammar | F4, F10 | edits #100 |
| widen **#165** to point at #100 as answered, not open | §3 | edits #165 |
| ⟳ move #164's fix inside `check-fixture-variation.py` — its example is RIGHT, see §4.3 | F11 | edits #164 |
| correct **#166**'s producer count from two to three | F5 | edits #166 |
| two ride-alongs — `ci.yml` comment (F7), `:183` five-not-six (F6) | F6, F7 | new, small |

⚠ **Three of those are EDITS to rows that already exist**, which is worth flagging before anyone
agrees to them: #100, #164, #165 and #166 are all rows whose *conclusions* this review supports and
whose *evidence or scope* it corrects. Editing a row to say something its author did not measure is
a different act from adding a row, and it is the user's call which of the two happens.
