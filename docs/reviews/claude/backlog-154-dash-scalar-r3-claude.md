# backlog #154 — a block scalar opened on the DASH line — review round 3, Claude half

**REVIEW GAP:** codex — not invoked for this round, by design. Rounds 2+ alternate
(`docs/review-method.md`, Round topology), and Codex authored round 2 — the round whose repair
this reviews.

**Subject:** branch `backlog-154-dash-block-scalar` @ `5380f6d9`, off master `b184bbbc`, PR #331 (OPEN).
**Reviewing:** the repair of **round 2 (Codex, 1 Blocking)**, which this half did not author.
**Oracle:** libyaml via ruby Psych (`/usr/bin/ruby`, 2.6.10); PyYAML is not installed here.
**Method:** everything measured on temp copies under a redirected `HOME`. No repository file other
than this one was modified.
**Subject re-verified after the branch moved:** the head is now `64d0cae8`, and
`git diff --name-only 5380f6d9..64d0cae8 -- scripts/ docs/backlog.md docs/roadmap-to-launch.md
docs/dashboard-entries.md CONTEXT.md` is **empty** — the only change is a `REVIEW GAP:` line added to
the round-2 file. Every finding below stands against `64d0cae8` unchanged.

## VERDICT: NOT CONVERGED — 2 Blocking, 1 High, 3 Medium, 2 Low.

**The short version.** The half-closure Codex named is genuinely half-repaired: the two spellings the
commit message quotes (`- "my run": |`, `- "a:b": |`) are closed, verified against libyaml over a
7,200-fixture generated space, and the two new cases are non-ambient. But **the third spelling named
in round 2's own Blocking evidence — the explicit-key form — was not addressed and is not mentioned
anywhere in the tree**, and the comment's claim that *"a quoted key may hold any character; the class
is closed by matching quote-to-quote"* is **false on its own terms**: `- "a\"b": |` and `- 'a''b': |`
are quoted keys that still false-green to `rc 0, "python pin OK"`.

**And the standing question has a measured answer, which is the most useful thing in this document.**
Over one fixed generated space the false-green rate went **100% (master) → 76.7% (r1) → 36.7%
(HEAD)** — real improvement, halving each round, converging on a non-zero floor. It is *not* the case
that every remaining shape needs its own special case: **one generic key alternation closes 13 of the
14 residue shapes I found, keeps the suite at 92/92, and changes no masking decision on the real
corpus.** But the 14th — the explicit-key form — survives *any* per-line regex by construction,
because its key and its indicator are on different lines. That is the PR #329 conclusion
demonstrated rather than asserted. A **REFUSE** reaches all 14 and, measured over every YAML file in
the repo (7,623 structural lines), would fire **zero** times inside the guard's own corpus.

---

## Was round 2 actually repaired?

| r2 finding | Status | Evidence |
|---|---:|---|
| **Blocking** — `_BLOCK_SCALAR` still not class-closed: quoted key with a SPACE, quoted key with a COLON, **explicit key** | **PARTIAL** | The two quoted spellings are closed (verified, §S1). The **explicit key is untouched, still false-green end-to-end, and appears nowhere in the tree** — B2 |
| r2's note on the Codex Low: duplicate anchor 39/42, deliberately not changed as pre-existing | **SOUND — confirmed** | `master:scripts/mutations/check-python-pin.json` has 39 entries and the same duplication at **35/38**; HEAD has it at 39/42, no *new* duplication, and no duplicate full anchor tuple anywhere (§S3) |
| r2 PARTIAL — inverted causal story survives at `check-python-pin.py:924-926` and `docs/backlog.md:182` | **PARTIAL** | Both named sites are fixed. A **third** copy is live at `CONTEXT.md:131`, and the commit's claim *"`grep` confirms zero remain"* is false — M1 |
| r2 note on Claude L2 — *"backlog still has stale final counts"* | **NOT FIXED** | `docs/backlog.md:182` still says `declared sum 868 → 869; harness 869/869 killed`. Truth: **868 → 872, harness 872**. It also carries `suite 84 → 86; suite 84 → **92**` in one sentence — M2 |
| All other r2 rows (FIXED ones) | **SOUND** | Spot-checked; no regression. The list-`expect` mechanism r1-M4 asked for now also protects the two NEW cases (§S4) |

---

## Findings

### B1 — Blocking. The quoted-key class the comment declares closed is **not** closed

`scripts/check-python-pin.py:326-329` (the `_BLOCK_SCALAR` comment's quoted-key bullet) states the
rule this round shipped:

> `- "run": |` a quoted key. ⛔ r2: MY FIRST CLOSURE OF THIS WAS HALF-DONE — it allowed the QUOTES
> but still required `[\w.\-]+` INSIDE them … **A quoted key may hold any character; the class is
> closed by matching quote-to-quote.**

A quoted key may hold any character — including the quote character itself, which YAML spells `\"`
in a double-quoted scalar and `''` in a single-quoted one. `"[^"]*"` and `'[^']*'` cannot span
either, so the sentence is false for the two remaining members of the very class it declares closed.

Measured. libyaml parse tree first, so there is no argument about what the YAML means:

```text
--- dq ESCAPED quote  (- "a\"b": |)
    step is a Hash, keys = ["a\"b"]
      key "a\"b" -> value "uses: actions/setup-python@v5\nwith:\n  python-version: '9.9'\n"
    has a 'uses' key? false    (if false, the lines below are CONTENT)
--- sq DOUBLED quote  (- 'a''b': |)
    step is a Hash, keys = ["a'b"]
      key "a'b" -> value "uses: actions/setup-python@v5\nwith:\n  python-version: '9.9'\n"
    has a 'uses' key? false    (if false, the lines below are CONTENT)
```

Then the guard, at HEAD (`5380f6d9`), end to end — **not** just `declared_pins`:

```text
--- - 'a''b': |   (sq DOUBLED quote)
    declared_pins: ['9.9']
    unpinned_jobs: []
    verdict rc=0  python pin OK — every job pins 9.9, and this interpreter is 9.9, from /usr/bin/python3
--- - "a\"b": |   (dq ESCAPED quote)
    declared_pins: ['9.9']
    unpinned_jobs: []
    verdict rc=0  python pin OK — every job pins 9.9, and this interpreter is 9.9, from /usr/bin/python3
--- - run: |      (the #154 shape, FIXED — control)
    declared_pins: []
    unpinned_jobs: ['w.yml:verify']
    verdict rc=2  CANNOT RUN — no `python-version:` was found in any workflow, so the interpreter
```

`rc 0, "python pin OK"` over a job with **no `setup-python` step at all** is verbatim the #154
defect, and the control on the same run proves the fixture shape is the one the branch fixed.

**Two more members of the same class, not named by any round so far, and this one is not exotic:**
a space before the colon. YAML permits `key : value`; the regex requires `:` to touch the key.

```text
FALSE_GREEN   padded colon, plain   (- run : |)   oracle=[] valid=True guard=['9.9']
FALSE_GREEN   padded colon, quoted  (- "run" : |) oracle=[] valid=True guard=['9.9']
```

`- run : |` is an ordinary key with one stray space — a human can type it by accident, unlike an
anchor or an explicit key. **Severity note, stated because it matters for the fix:** the padded-colon
and plain-key members are **not a regression of this branch** — master false-greens on them too, in
the dash-less spelling (§S2). What *is* this round's is the sentence claiming the class is closed.

---

### B2 — Blocking. The explicit-key spelling named in round 2's Blocking was silently dropped

Round 2's Blocking named **three** shapes and pasted its own output for all three
(`docs/reviews/codex/backlog-154-dash-scalar-r2-codex.md:31`, `:45-47`):

```text
quoted key with space: oracle=[] declared=['9.9'] DISAGREE FALSE_GREEN
quoted key with colon: oracle=[] declared=['9.9'] DISAGREE FALSE_GREEN
explicit key: oracle=[] declared=['9.9'] DISAGREE FALSE_GREEN
```

Two were fixed. The third is **not fixed, not refused, and not recorded**:

```text
$ grep -rn "explicit key\|explicit-key\|? run" scripts/ docs/backlog.md \
      docs/roadmap-to-launch.md docs/dashboard-entries.md
(no matches)
```

It is absent from `_BLOCK_SCALAR`'s comment, from `_structural`'s **KNOWN BOUND** list
(`check-python-pin.py:361-365`, which exists precisely so an unstated bound does not travel — it
names only flow mappings and escaped newlines), from the backlog row, the roadmap and
the dashboard entry. The commit message's closing matrix — *"agrees with libyaml 8 for 8 — plain
dash, anchor, tag, quoted key, quoted+space, quoted+colon, single-quoted, nested sequence"* — omits
it without saying so. A three-item finding was closed as if it had two items.

It is live. libyaml:

```text
--- EXPLICIT KEY  (? run / : |)
    step is a Hash, keys = ["run"]
      key "run" -> value "uses: actions/setup-python@v5\nwith:\n  python-version: '9.9'\n"
    has a 'uses' key? false    (if false, the lines below are CONTENT)
```

The guard, at HEAD:

```text
--- ? run / : |   (EXPLICIT KEY)
    declared_pins: ['9.9']
    unpinned_jobs: []
    verdict rc=0  python pin OK — every job pins 9.9, and this interpreter is 9.9, from /usr/bin/python3
```

Fixture (indent is load-bearing, so it is given in full):

```yaml
jobs:
  verify:
    steps:
      - ? run
        : |
            uses: actions/setup-python@v5
            with:
              python-version: '9.9'
```

Again **not a regression** — master false-greens here too. It is Blocking because it is *unrepaired
round-2 material still in the false-green direction*, and because dropping an item from a finding
without recording the decision is the failure mode the KNOWN BOUND list was built for. Either close
it, refuse on it, or write it down — but it must stop being invisible.

---

### H1 — High. Nine more valid spellings false-green, and the stated-bound list does not mention the class

A generated differential space — 30 key shapes × 5 node-property forms × 6 block indicators ×
{no comment, trailing comment} × {1, 2} dash levels × {6, 8} base indents = **7,200 fixtures**, every
one checked against libyaml:

```text
cases=7200 invalid_yaml=0 valid=7200 agree=4560 FALSE_GREEN=2640 MISS=0
disagreement rate over valid YAML = 36.7%

--- FALSE-GREEN key classes (guard invents a pin YAML does not have) ---
  key=dq_ESCQUOTE             240 fixtures  e.g. key=dq_ESCQUOTE prop=none ind=| cmt=none dashes=1 base=6
  key=plain_SPACE             240 fixtures  e.g. key=plain_SPACE prop=none ind=| cmt=none dashes=1 base=6
  key=plain_at                240 fixtures
  key=plain_dollar            240 fixtures
  key=plain_equals            240 fixtures
  key=plain_hash              240 fixtures
  key=plain_paren             240 fixtures
  key=plain_plus              240 fixtures
  key=plain_slash             240 fixtures
  key=plain_squote            240 fixtures
  key=sq_DOUBLED              240 fixtures

--- MISS key classes (guard loses a pin YAML does have) ---
  (none)
```

Eleven key classes; with the explicit key and the two padded-colon shapes that is **14 distinct
residue shapes**. **`MISS=0` is a genuinely good result and is reported as such** — the new
alternation does not mask anything it shouldn't, which was r2-H1's failure mode.

Every one of the plain-key members is a valid YAML plain scalar: `run/it`, `run@it`, `run+it`,
`run(it)`, `run#it` (`#` only opens a comment after whitespace), `run$it`, `run=it`, `it's`,
`my run`. `[\w.\-]+` is far narrower than a YAML plain key, and always has been.

**Why this is High rather than Low.** `_structural`'s docstring keeps an explicit KNOWN BOUND list —
flow mappings, escaped newlines (`check-python-pin.py:361-365`) — with the file's own justification:
*"that is exactly the kind of
sentence that has been wrong twice on this branch, so it is written as a KNOWN BOUND, not as a
guarantee."* The key-shape class is a strictly larger hole than either listed bound and is **not on
the list**. Backlog #155 promotes this reader into `scripts/workflow_structure.py` and two more
guards, so an unstated bound travels — which is the argument the branch itself uses for sequencing
#154 ahead of #155.

---

### M1 — the inverted causal story survives a **third** time, in `CONTEXT.md`, and is now also stale

The commit message asserts: *"Both copies are now corrected and `grep` confirms zero remain."* The
two named copies are indeed corrected. A third is live, in the project's canonical vocabulary file —
`CONTEXT.md:131`, inside the definition of the term **Structural line**:

> ⚠ **Structural-ness is relative to the LEVEL a reader is applied at, and this is the trap, not a
> nicety:** `_structural()` is correct about a step's lines and silently weaker about a whole file's,
> because a block scalar opened on a `- ` dash line is masked in the first case and not the second
> (backlog #154). A reader that is sound one level down is not sound one level up.

It is wrong **twice over**:

1. **Same inversion r1-M1 and the Codex Low corrected.** `_structural` has one call site —
   `check-python-pin.py:232`, on the whole file — and the dash-blanking at `:264` runs after it.
   There is no consumer that applies `_structural` to a step's lines, so "correct about a step's
   lines" describes a level that exists only in prose.
2. **It is now stale in the present tense.** Post-fix the dash line *is* masked at file level.
   Measured: `declared_pins` on the #154 fixture returns `[]` at HEAD (control in B1).

**Provenance, stated because it changes who owns it:** `git diff --name-only b184bbbc..5380f6d9 --
CONTEXT.md` is empty, and `git log -S` attributes the sentence to `5ffe6017` (PR #329, the #153
architecture review) on master. **This branch did not write it.** But it is the same class the commit
claims to have swept, the sweep's `grep` was evidently narrower than the claim, and `CONTEXT.md` is
the file `docs/dev-process.md` Phase 6 tells every architecture review to read first. Three rounds
have each found a surviving copy; this is the fourth site.

`docs/reviews/architecture-review-2026-09-21-workflow-readers.md:93-95` carries the same wording. That
is a historical review document and should be left alone — noted so the next reader does not "fix"
the record.

---

### M2 — round 2 explicitly flagged the stale counts in the backlog row; they are still stale

Codex's r2 table, on Claude L2: *"FIXED for the named arithmetic … note backlog still has stale final
counts."* `docs/backlog.md:182` today:

> …declared sum 868 → 869; harness 869/869 killed, 0 survivors

Re-derived:

```text
master declared sum: 868          master check-python-pin key: 39
HEAD  declared sum: 872 over 52 files   HEAD check-python-pin key: 43
actual manifest total across all files: 872
```

So the sentence should read `868 → 872; harness 872/872`. The same row also contains, in one
sentence, **two contradictory suite figures**: *"Suite 84 → 86; suite 84 → **92**"* — the `→ 86`
clause is r1-era residue left beside its own correction. A row a #155 implementer is told to follow
should not state its predecessor's numbers and its own at once.

---

### M3 — the dashboard entry says the class is closed; it is the reader-facing artifact

`docs/dashboard-entries.md:11209-11212` was written at r1 and not touched by the r2 repair commit
(`git show 5380f6d9 --stat` lists five files; `docs/dashboard-entries.md` is not among them):

> The second is that the first fix closed one of four ways to write the same thing. Reviewers found
> three more … **All four are closed now**, and each is held by a test that fails if the fix is
> removed.

Six spellings are closed as of this commit, and 14 measured shapes of the same class are open. The
"each is held by a test" half is true and verified (§S1, §S4). The "all four are closed" half reads
as *the class is closed*, which is the one claim this round's evidence contradicts. The entry is the
artifact a person who was away actually reads.

---

### L1 — the backlog row describes a quantifier the code does not have

`docs/backlog.md:182`: *"`_BLOCK_SCALAR` now accepts an optional `(?:-\s+)?` before the key."* The
shipped regex is `(?:-\s+)*` — a star, widened in r1 for the nested-sequence spelling. `?` would
reopen `- - run: |`.

### L2 — a comment states a suite size two rounds out of date, describing a world its own case ended

`check-python-pin.py:936`: *"a REAL pin is lost — and the suite stayed 86/86 green under it."* The
suite is 92, and under that variant it would now go red, because the very next line adds the case
that makes it so. The past tense is defensible as a record of the r1 measurement, and the following
sentence (*"this case and its mutation now hold it"*) resolves it — but a bare `86/86` in a file whose
declared count is pinned by `check-selftest-counts.py` reads as a live figure. Suggest *"the suite of
the day stayed green under it (86 cases, r1)"* or dropping the number.

---

## The standing question: converged, or the pattern PR #329 diagnosed?

**Answer: not converged, and it is the diagnosed pattern — but the honest form of that verdict is
narrower than "stop widening regexes", and the evidence says which part is which.**

**1. The widening is genuinely working, and the trajectory is measurable.** Same 7,200-fixture space,
three versions of the same function:

| version | agree | FALSE_GREEN | MISS | rate |
|---|---:|---:|---:|---:|
| `master` (`b184bbbc`) | 0 | 7,200 | 0 | **100.0%** |
| r1 (`648c93a0`) | 1,680 | 5,520 | 0 | **76.7%** |
| **HEAD (`5380f6d9`)** | 4,560 | 2,640 | 0 | **36.7%** |

⚠ **The RATE is not a population estimate and must not be quoted as one** — every fixture in this
space is dash-opened, which is the shape master could not parse at all, so master's 100% is an
artefact of an adversarial corpus. The *trajectory within one fixed space* is the meaningful part,
and the class counts (11 → 14 shapes) are the durable figure.

**2. The residue is NOT "one special case per shape". Thirteen of fourteen fall to one generic
alternation.** Measured on a temp copy, replacing the key alternation with a quote-aware,
colon-terminated one (`"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^\s:][^:]*?` plus `\s*:\s*`):

```text
--- existing suite under the generic variant ---
92/92 passed

--- generated space under the generic variant ---
cases=7200 invalid_yaml=0 valid=7200 agree=7200 FALSE_GREEN=0 MISS=0
disagreement rate over valid YAML = 0.0%

### generic variant (the hand-picked extras)
  OK           padded colon, plain   (- run : |)      oracle=[] guard=[]
  OK           padded colon, quoted  (- "run" : |)    oracle=[] guard=[]
  OK           dq ESCAPED quote      (- "a\"b": |)    oracle=[] guard=[]
  OK           sq DOUBLED quote      (- 'a''b': |)    oracle=[] guard=[]
  OK           plain key with SPACE  (- my run: |)    oracle=[] guard=[]
  FALSE_GREEN  EXPLICIT KEY          (? run / : |)    oracle=[] guard=['9.9']
  OK           CONTROL real pin      (- uses: setup-python)  oracle=['3.12'] guard=['3.12']
```

…and it changes **no** masking decision on the real corpus (282 structural lines in
`.github/workflows/`, 5 recognised openers before and after). So *this* residue is closable, and by a
class rule rather than a fifth, sixth and seventh special case. **UNVERIFIED and deliberately not
claimed:** I did not mutation-test that variant or check it against `check-plan-code.py --mutate .`.
It is offered as a feasibility measurement, not a patch.

**3. And there is a hard floor that no per-line regex reaches.** The explicit-key form survives the
generic variant, and it survives every possible variant of it, because the key (`? run`) and the
indicator (`: |`) are on **different lines** — a line-local matcher cannot see the key it needs. That
is precisely PR #329's conclusion: you cannot reach a language by adding alternation to a regular
expression. It is not an argument about taste; it is the one shape that proves the boundary.

**4. Therefore REFUSE is the honest terminal move, and it is measurably quiet.** A refusal predicate
needs no YAML knowledge at all — *this line ends in a block indicator, and `_BLOCK_SCALAR` did not
match it* — i.e. "something opens a scalar here and I cannot classify its key". Measured:

* It catches **14 of 14** residue shapes, the explicit key included:

```text
REFUSES  '      - my run: |'        REFUSES  '      - run$it: |'
REFUSES  '      - run/it: |'        REFUSES  '      - run=it: |'
REFUSES  '      - run@it: |'        REFUSES  "      - it's: |"
REFUSES  '      - run+it: |'        REFUSES  '      - "a\\"b": |'
REFUSES  '      - run(it): |'       REFUSES  "      - 'a''b': |"
REFUSES  '      - run#it: |'        REFUSES  '        : |'
```

* It is silent on the corpus the guard reads, and nearly silent on every YAML file in the repo:

```text
corpus: 2 workflow file(s)
structural lines scanned=282  strict openers=5  loose hits=5  WOULD REFUSE=0

files=18  structural lines=7623  recognised openers=5  WOULD REFUSE=3
   .playwright-mcp/page-2026-08-28T04-50-26-527Z.yml: '      - code [ref=e391]: <owner_id>/<playlist_key>/<key>'
   .playwright-mcp/page-2026-08-28T04-52-14-550Z.yml: '      - code [ref=f2e391]: <owner_id>/<playlist_key>/<key>'
   .playwright-mcp/page-2026-08-28T04-52-26-431Z.yml: '      - code [ref=f2e391]: <owner_id>/<playlist_key>/<key>'
```

All three are Playwright page-snapshot artefacts the guard never opens. ⚠ **Its bound:** my predicate
is crude (ends-with-indicator, unscoped); a real one would fire only inside a `steps:` block, which
can only reduce the count. And `refuse` is the right *direction* for this guard — `rc 2` / CANNOT RUN
is what the file already returns when it cannot see what it needs, and `check-merge-ready`'s
`unaccounted_mentions` (backlog #157) is the existing mechanism.

**Recommendation, in the order I would do it:** (a) close B1 and the 13 closable shapes with the one
generic alternation rather than three more alternatives; (b) refuse on what remains, which makes B2's
explicit key a loud `rc 2` instead of a silent `rc 0`; (c) if (b) is out of scope for this PR, then B2
must at minimum be written into the KNOWN BOUND list and the backlog row, because #155 copies this
reader into two more guards. **This is not a "diminishing returns" call** — the rate is still
halving each round and each round's fix has been correct. It is a *wrong-instrument* call: the
remaining shapes are found by an oracle in seconds and by review rounds one at a time.

---

## What I checked and found SOUND

**S1 — the two new cases are not ambient, and they red for their own reason.** Reverting *only* the
r2 key alternation to r1's spelling on a temp copy:

```text
--- control (HEAD copy) ---
92/92 passed
--- r1-reverted ---
  [FAIL] ...nor does one behind a quoted key containing a SPACE: got ['9.9'] want []
  [FAIL] ...nor does one behind a quoted key containing a COLON: got ['9.9'] want []
90/92 passed
```

Exactly two reds, exactly the two new cases, nothing else moves. The quoted-space and quoted-colon
closure is real, and it is the *whole* `[^"]*` / `[^']*` widening that carries it.

**S2 — the plain-key residue is INHERITED, not a regression.** Same shapes written without a dash —
the spelling master's `^(\s*)[\w.\-]+:` was built for:

```text
### master                                    ### head
  OK           plain                            OK           plain
  FALSE_GREEN  SPACE                            FALSE_GREEN  SPACE
  FALSE_GREEN  SLASH                            FALSE_GREEN  SLASH
  FALSE_GREEN  APOSTROPHE                       FALSE_GREEN  APOSTROPHE
  FALSE_GREEN  dq_ESCQUOTE                      FALSE_GREEN  dq_ESCQUOTE
  FALSE_GREEN  sq_DOUBLED                       FALSE_GREEN  sq_DOUBLED
```

Identical. H1 and the non-explicit half of B1 are bounds this branch inherited and did not widen.
Stated so the severity is not read as "the fix broke something".

**S3 — the manifest's anchor hygiene.** Exactly one duplicated individual anchor, the known
pre-existing one; **no** duplicated full anchor tuple; all 43 anchors match exactly once in the
source:

```text
=== duplicate full anchor TUPLES ===
(none)
=== duplicate INDIVIDUAL anchors (1-based entry numbers) ===
  [39, 42] -> '        if (opens_steps and len(opens_steps.group(1)) == job_steps_indent\n      '
=== anchor uniqueness in the SOURCE ===
 anchors not matching exactly once: none
```

And it is genuinely pre-existing, at different ordinals: `master` has 39 entries with the same
duplication at **35/38**.

**S4 — the merged mutation reddens all three names, and the vacuity defence now covers the new
cases.** Entry 32 (1-based; index 31) applied to a temp copy:

```text
  [FAIL] ...nor does one behind a quoted key containing a SPACE: got ['9.9'] want []
  [FAIL] ...nor does one behind a quoted key containing a COLON: got ['9.9'] want []
  [FAIL] ...nor does one behind a QUOTED key: got ['9.9'] want []
89/92 passed
```

Three names, three reds, no collateral. Matching is exact equality (`check-plan-code.py:1443`,
`[(w, [f for f in fails if w == f]) for w in wants]`), so the uppercase/lowercase pair
(`QUOTED key` vs `quoted key containing a …`) cannot collide. **And the r1-M4 mechanism now protects
the new material too** — dropping the `uses:` line from the SPACE case (making it vacuous exactly as
the original `:880-882` case was) leaves the suite green at 92/92, but under the mutation only two of
the three named cases go red, so `expect` resolves to 0 matches for the third and the harness reports
it unattributed:

```text
--- suite with the vacuous case (unmutated) ---     92/92 passed
--- now ALSO apply mutation entry 31 on top ---
  [FAIL] ...nor does one behind a quoted key containing a COLON: got ['9.9'] want []
  [FAIL] ...nor does one behind a QUOTED key: got ['9.9'] want []
90/92 passed
```

**S5 — counts reconcile.** Suite **92** (`92/92 passed`, and the docstring says 92). Manifest for this
file **43**; `EXPECTED_MUTATIONS["scripts/check-python-pin.py"]` **43**; declared sum **872** = actual
total across all manifests **872**. `check-selftest-counts.py` → `45 script(s) declare a count, every
one verified by running it`, rc 0.

**S6 — no MISS-direction regression.** `MISS=0` across all 7,200 fixtures, and a real pinned step
survives beside a dash-opened scalar in the same job list (positive control:
`pos_scalar_then_real oracle=['3.12'] guard=['3.12']`). The r2-H1 failure mode is not present.

**S7 — the two corrected comments are factually right, checked against the tree rather than read.**
`grep -n "_structural(" scripts/check-python-pin.py` → `232` (the only call) and `336` (the def);
`sed -n 232p` → `structural = _structural(text.split("\n"))`; `sed -n 264p` →
`cur = Step(len(m.group(1)), [" " + m.group(2)])`. So the corrected story — one call site on the whole
file, dash-blanking strictly after it, the defect going through `_steps` — is accurate, and both
locators in the new self-test comment (`:232`, `:264`) still resolve at HEAD.

**S8 — every named probe from the round's mandate that came back clean.** All against libyaml, all
part of the 7,200-fixture space:

| probe | result |
|---|---|
| a key with a backslash — `- "a\\b": \|` | **OK** — matched; libyaml key is `a\b`, guard masks |
| an empty quoted key — `- "": \|`, `- '': \|` | **OK** — both masked |
| the other quote kind inside — `- "it's": \|`, `- 'a"b': \|` | **OK** — both masked |
| leading/trailing spaces inside quotes — `- " run ": \|` | **OK** — masked |
| a quoted key followed by a comment — `… : \|  # note` | **OK** — every key class × `# note` behaves as without it |
| a unicode plain key — `- rün: \|` | **OK** — Python's `\w` is unicode-aware, so this one is closed by accident rather than by design |
| node properties — `&x`, `!!str`, `!!str &x`, `&x !!str` | **OK** — all four, across every key class and indicator |
| indicators — `\|`, `>`, `\|-`, `\|+`, `>-`, `>+` | **OK** — no indicator is a discriminator; the residue is purely the key |

**S9 — `--mutate .` reproduced independently, and the first attempt at it was a CANNOT RUN that
reported success.** The full harness, re-run by me rather than relayed:

```text
OK — delivered scripts mutated: 52 file(s), 872 mutation(s), 872 killed, 872 attributed to the case each names, 0 survivor(s)
EXIT=0
```

`grep -cE "SURVIVED|matched 0 red|matched [2-9] red|NOT COMPLETE|report-format defect"` → **0**, and
`git status --porcelain` after it lists only this review file, so the harness left the tree alone.
⚠ **Worth recording because it is this project's own most-cited failure mode, and it caught me:** my
first invocation wrapped the command in `timeout 3000 …`, which does not exist on macOS. It died at
`EXIT=127` having run nothing — and the background-task notification reported *"completed (exit code
0)"*, because the exit code it saw was the wrapper's, not the harness's. Had I read the notification
instead of the log, I would have recorded a green harness run that never happened.

**S10 — the oracle itself was controlled in both directions**, because a differential harness whose
oracle can only return `[]` manufactures agreement:

```text
pos_ordinary           oracle(valid=True)=['3.12']  guard=['3.12']
pos_name_first         oracle(valid=True)=['3.12']  guard=['3.12']
pos_scalar_then_real   oracle(valid=True)=['3.12']  guard=['3.12']
neg_154_fixed          oracle(valid=True)=[]        guard=[]
```

---

## CANNOT VERIFY

* **Nothing outstanding on the harness — I re-ran it rather than relaying it** (see S9).
* **The generic-alternation variant in §2 of the standing question is a feasibility measurement, not
  a reviewed patch.** It is green on the 92-case suite and on 7,200 fixtures; it has not been
  mutation-tested, and its `[^:]*?` branch has not been attacked for catastrophic backtracking or for
  YAML shapes outside my space.
* **Everything here was measured on Python 3.14.4; CI runs 3.12, and this file exists because those
  two disagreed once.** The guard itself says so on every local run
  (`⚠ ADVISORY — this machine runs Python 3.14; CI runs 3.12`). The residue is pure `re` matching, and
  the matcher's verdict on the residue shapes is reproduced standalone below, so a 3.12 divergence
  would have to be a change in `re`'s alternation or `[^"]*` semantics — I am not aware of one, but I
  did not run it on 3.12, so it is UNVERIFIED there:

  ```text
  NO     '      - my run: |'        match  '      - run: |'
  NO     '      - "a\\"b": |'      match  '      - "my run": |'
  NO     "      - 'a''b': |"       match  '      - rün: |'
  NO     '      - run : |'
  NO     '        : |'
  ```

  The live guard is green on the real corpus at HEAD: `LIVE GUARD rc=0`.
* **My REFUSE predicate is a probe, not a design.** "Ends in a block indicator" is deliberately crude;
  a real one belongs inside `_structural` and scoped to a `steps:` block. The 0-and-3 prevalence
  figures bound *that* predicate over *this* repo's 18 YAML files, and nothing wider.
