# R3 becomes "something USES it" (backlog #196) — Claude half, round 1

Subject: branch `r3-something-uses-it`. **The subject is NOT one commit.** `778fd822` off `master`
`446025ab` changes four files; the working tree carries three more modified files that hold every
coverage artefact the brief claims. See **B1**.

**Verdict: NOT CONVERGED** — 1 Blocking, 3 High, 4 Medium, 6 Low.

What I confirmed of the author's own claims, before the findings: the seven mutation entries all
kill and all attribute to the case they name over a green 52/52 control; R2 is genuinely 0
violations across the widened population; `import_re` genuinely agrees with an AST import graph on
every library in the population (0 regex-only, 0 AST-only, checked on six not four); `evaluate` and
`caller_blob_targets` provably cannot disagree; and deleting the R1 case was right. The defects are
elsewhere.

---

## BLOCKING

### B1 · The reviewed commit contains the rule change and none of its coverage — three of the six changed files are uncommitted

`git status --porcelain`:

```
 M scripts/check-plan-code.py
 M scripts/check-ratchet-contract.py
 M scripts/mutations/check-ratchet-contract.json
```

The brief says "four files", "one commit `778fd822`", and claims `52/52`, `1041 mutations`,
`EXPECTED_MUTATIONS 10 -> 17`. Every one of those is a property of the **working tree**. I extracted
the commit in isolation and measured it:

```
$ git archive HEAD | tar -x -C <tmp> && cd <tmp>
$ python3 scripts/check-ratchet-contract.py --self-test
self-test: 49/49 passed                       rc=0
$ grep -n "self-test  #" scripts/check-ratchet-contract.py
30:    python3 scripts/check-ratchet-contract.py --self-test  # 49 cases
$ python3 -c "import json;print(len(json.load(open('scripts/mutations/check-ratchet-contract.json'))))"
10
$ grep -n '"scripts/check-ratchet-contract.py":' scripts/check-plan-code.py
824:    "scripts/check-ratchet-contract.py": 10,
```

HEAD is *internally consistent and green*, which is what makes this dangerous rather than obvious.
At HEAD the seven new discriminators — the import arm, `_LINE_START`, `_OPT_INDENT`, the identifier
guard, widened R2, widened R3, and the caller-blob population — have **zero** mutation entries, and
`check-plan-code.py --mutate .` would pass at 1034 declaring full coverage. `caller_blob_targets`
does not exist at HEAD either; the blob union is still inline in `main()`, so the defect the author
describes as fixed by extraction is only patched, not covered.

This also defeats the merge gate rather than tripping it: `check-merge-ready.py` reads the
**committed** diff, so it cannot see any of the three modified files.

**Fix:** commit the three files (or amend `778fd822`) and re-run the gates against the committed
tree before claiming them.

**What would prove this wrong:** `git status --porcelain` returning empty, with `git show --stat
HEAD` listing six files.

---

## HIGH

### H1 · The newly-applied R3 reports GREEN for `scripts/explainer-serve.py`, which nothing executes — it is satisfied entirely by `print()` strings

R3 was never asked of `explainer-serve.py` before this change. It is now, and it passes with **zero
executable callers**. All seven matches are inside string literals in other `.py` files:

`scripts/brief-compose.py:914`
```python
    print("    serve: python3 scripts/explainer-serve.py   then open http://127.0.0.1:7391/latest")
```
`scripts/check-explainer-delivery.py:102`
```python
SHARED_BODY = "run python3 scripts/explainer-serve.py\n"
```
plus four more `print("… (start: python3 scripts/explainer-serve.py)")` lines in
`gen-backlog-page.py:3385`, `gen-dashboard.py:3542`, `gen-features-page.py:706`,
`gen-goals-page.py:1247`, and one fixture in `check-explainer-delivery.py:153`.

This is the defect the rule exists to catch, restated. `invocation_re`'s own docstring
(`scripts/check-ratchet-contract.py:143-148`) says the rule "must not be satisfiable by prose", and
`main()`'s caller-source comment says `docs/` is excluded because "a row in a table headed *What is
mechanically enforced* is a CLAIM about a caller, not one". A `print()` telling a human how to start
a server is the same claim; it simply lives in a `.py` file, and `.py` files are in
`caller_sources`.

`explainer-serve.py` is a human-run local server — exactly the class the author correctly declared
`NO-CALLER:` for on `codex-review.py`, `peer-sites.py` and `prior-art.py`. It is missing from that
set, and the reason it looks like it does not belong there is a false green.

**Reproduction** (classifies every `invocation_re` hit by whether its line is inside an `ast`
string-literal span):

```
⛔ PROSE-ONLY   scripts/explainer-serve.py   real=0 prose=7
```

**Fix:** either declare `NO-CALLER:` on `explainer-serve.py` (cheap, honest, consistent with the
other three), or — the class fix — exclude string-literal and comment lines from the `.py` half of
the caller blob before searching it.

**What would prove this wrong:** a `.sh`, hook, or `ci.yml` line that actually executes
`scripts/explainer-serve.py`. I grepped `.github/`, `.claude/` and `scripts/` for `explainer-serve`
outside string literals and found only two prose mentions in `.claude/hooks/regen-backlog-page.sh:113`
and `regen-features-page.sh:15`, neither of which invokes it.

### H2 · For `begin-plan.py` and `gen-m4-manifest.py` the widened R3 has no falsifier — delete their only real caller and it stays green

Same root cause as H1, measured as the question that matters: *would this gate notice its subject's
caller being deleted?* I deleted every non-string, non-comment line matching `invocation_re` from
the caller blob and re-ran `check_caller`:

```
⛔ STILL GREEN  scripts/begin-plan.py           real caller lines deleted=1
red (good)      scripts/brief-compose.py        real caller lines deleted=1
red (good)      scripts/build-m4-schema.py      real caller lines deleted=3
red (good)      scripts/gen-backlog-page.py     real caller lines deleted=1
red (good)      scripts/gen-dashboard.py        real caller lines deleted=2
red (good)      scripts/gen-features-page.py    real caller lines deleted=1
red (good)      scripts/gen-goals-page.py       real caller lines deleted=1
⛔ STILL GREEN  scripts/gen-m4-manifest.py      real caller lines deleted=1
   (page_chrome.py / page_markup.py also stay green, correctly — the IMPORT arm holds them)
```

`begin-plan.py`'s sole real caller is `.github/workflows/ci.yml:303`; `gen-m4-manifest.py`'s is
`scripts/check-schema-gates.sh:100`. Both stems are hyphenated, so the import arm is inert for them
— the green after deletion is prose alone. Together with H1 that is **3 of 19** widened files on
which the new rule is either wrong today or unable to go wrong.

This is what the payoff claim in `evaluate`'s comment asserts for `recall-llm.py` ("MEASURED both
ways … reports `R3_no_caller` with the hook removed"). That measurement holds for `recall-llm.py`
because its caller is a hook and nothing prints its name; it does not generalise, and the comment
presents it as if it does.

**What would prove this wrong:** the two files going red in the run above — i.e. their names
appearing only outside string literals.

### H3 · R2's new application to the widened population raises an unhandled `SyntaxError`; `master` handled the same input

`scripts/check-ratchet-contract.py:321`
```python
        for line in fail_open_handlers(texts[rel]):
```

`fail_open_handlers` calls `ast.parse` with no handler. The widened population is discovered by a
**regex** (`SELF_TEST_RE` over the raw text), not by parseability, so an unparseable `scripts/*.py`
that mentions `--self-test` enters the population and then crashes the guard.

The two sibling rules in this same file both handle it deliberately: `check_caller:250-256` catches
`SyntaxError` ("an escape we could not read is not an escape") and `check_manifest` does the same.
`CALLER_CASES` even carries a case named *"an UNPARSEABLE file does not exempt"*. The class was
known; the handling was applied to one arm and not the new one.

**Reproduction** (branch vs `master`, same input):

```python
bad = '"""A tool.\n\nRun with --self-test.\n"""\ndef broken(\n'
texts = {"scripts/check-w.py": SELF_TEST_OK, "scripts/tool.py": bad}
evaluate(texts, {"scripts/check-w.py": "python3 scripts/check-w.py"}, set())
```
```
BRANCH: !! UNHANDLED SyntaxError from evaluate(): '(' was never closed (<unknown>, line 5)
MASTER: [('scripts/check-w.py','R4_no_mutation_manifest'), ('scripts/tool.py','R4W_no_mutation_manifest')]
```

The crash aborts before any violation is printed, so a run that would have reported real violations
dies with a traceback instead, and `widened_debt_drift` — which needs `examined` to avoid reporting
unexamined debt as paid — never runs. This is a realistic input, not a contrived one: the repo pins
its interpreter precisely because `ast.parse` behaviour differs between versions
(`scripts/check-python-pin.py`), so a file using syntax newer than the pinned Python is unparseable
in CI while parsing fine locally.

**Fix:** wrap the widened R2 arm the way `check_caller` wraps its parse, and add a case (the R3
unparseable case shows the shape).

**What would prove this wrong:** `evaluate` returning a violation list rather than raising on that
input. (Note the unparseable-*guard* path raises on `master` too — that half is pre-existing; the
widened population is new exposure.)

---

## MEDIUM

### M1 · `import_re`'s stated soundness argument is false for multi-line strings and for docstring prose

`scripts/check-ratchet-contract.py:159`
```python
_LINE_START = r"^"        # excludes `# import x` and an import inside a string literal
```

and `:176-181` of the docstring: *"The anchor is required: `check-storage-independence.py:398`
carries `"from m4_catalog import CATALOG_SQL\n…"` as a test FIXTURE inside a string literal, and a
pattern without the anchor counts it."*

The cited evidence is real — I read `check-storage-independence.py:398` and it is a string that
*starts mid-line*, after an open paren. But the claim generalises to "an import inside a string
literal", and that is false for the triple-quoted form, which is the dominant fixture idiom in this
very repo (`SELF_TEST_OK`, `FAIL_OPEN`, `HAS_CALLER_STUB` are all `'''…'''`):

```
no     single-line string (the case in the suite):  '    x = "from m4_catalog import CONST"\n'
MATCH  TRIPLE-QUOTED fixture, import at line start: 'FIX = """\nimport m4_catalog\n"""\n'
MATCH  triple-quoted, indented:                     'FIX = """\n    import m4_catalog as c\n"""\n'
MATCH  docstring prose example:                     'def f():\n    """Example:\n\n    import m4_catalog\n    """\n'
```

The docstring-prose row is the same class as H1 arriving through the new arm: a docstring saying
`import m4_catalog` as an example satisfies R3.

The suite's negative case is labelled *"an import inside a STRING LITERAL is not a use — the
measured fixture shape"* and pins only the shape that happens to be excluded. There is **no live
instance** — I compared `import_re` against an `ast` import graph across all caller sources for all
six library-stem members of the population (`coverage_verdict`, `m4_catalog`, `observer_log`,
`subject_status`, `page_chrome`, `page_markup`): 0 regex-only, 0 AST-only, so the author's
measurement is correct as stated. The defect is the argument, not today's answer — and this is the
repo's *framing widened to fit* shape: the comment should say *a string literal that does not begin
a line*, and a triple-quoted case should be added (it goes red under the current code).

**What would prove this wrong:** `import_re("m4_catalog.py")` failing to match
`'FIX = """\nimport m4_catalog\n"""\n'`.

### M2 · The blob-population fix has no falsifier at the site where the defect happened, and the harness cannot give it one

`scripts/check-ratchet-contract.py:1105`
```python
    for rel in caller_blob_targets(texts):
```

`caller_blob_targets` is a pure function with three cases and a mutation entry — but the cases drive
the **function**, and the mutation entry mutates the **function body**. Nothing covers `main()`'s
use of it, which is where the live defect was. Reverting exactly the defect:

```
$ # in a copy of scripts/ + .claude/hooks/ + ci.yml, replace the line above with `for rel in ratchets:`
$ python3 scripts/check-ratchet-contract.py --self-test
self-test: 52/52 passed        rc=0
$ python3 scripts/check-ratchet-contract.py
summary: 16 violation(s), baseline 0
RATCHET FAILED: a ratchet was added or changed without following the contract.
live rc=1
```

So the suite is blind to the reverted fix and the **live run** is what catches it. The live run is in
CI (`.github/workflows/ci.yml:239`), so this is not an undetected defect — but the docstring at
`:219-236` claims more than was achieved:

> *"Keeping it a pure function with a case is the difference between having fixed the instance and
> having covered the class."*

It is not: CI's live run covers the class; the case covers the function. And a manifest entry cannot
close the gap, because the mutation oracle is the target's `--self-test` alone —
`scripts/check-plan-code.py:500`:

```python
        r = subprocess.run([sys.executable, name, "--self-test"], cwd=d,
```

A mutation at `main()`'s call site would therefore be **unkillable** and refused. Either say so in
the docstring, or give the suite a case that drives `main()` (e.g. a tiny fixture tree plus
`main([])`, which is what would make the claim true).

Incidentally, the `16` above resolves the arithmetic in `main()`'s comment: it says *"R3 fired for
all 19 of them. Measured: 19 violations where 3 were expected"*, but with the three `NO-CALLER:`
declarations in place the empty-blob run produces 19 − 3 = 16. The `19` is only reproducible against
a state where the declarations did not yet exist, which the comment does not say.

**What would prove this wrong:** `--self-test` going red after that one-line revert.

### M3 · `check-dashboard-entry.py` is RED on this branch and the brief's gate list omits it

```
$ python3 scripts/check-dashboard-entry.py
REFUSED — 4 tracked file(s) changed and no entry was added to docs/dashboard-entries.md.
rc=1
```

The brief lists five gates and claims all green; this one is not in the list and is not green. Per
`docs/dev-process.md` it blocks a branch that changes tracked files. It needs an entry or a written
`NO-ENTRY:` declaration. (Note it counts 4 — the committed files only — which is B1 again from the
other side.)

**What would prove this wrong:** rc=0 from that command.

### M4 · Four comments in three other files assert that this guard's population excludes files it now applies R2 and R3 to

None of these is edited by this change, and all four are now wrong in the direction the change moves:

- `.github/workflows/ci.yml:386` — `# library, not a guard, so \`check-ratchet-contract.py\` neither sees it nor should:` (about `page_markup.py`)
- `.github/workflows/ci.yml:395` — same sentence, about `page_chrome.py`
- `.github/workflows/ci.yml:157` — `# (30 guards, all check-*) does not see it` (about `brief-compose.py`; the count is also 40 now, not 30)
- `scripts/check-plan-code.py:3020` — `# \`check-ratchet-contract\`'s population never sees it;` (about `observer_log.py`) — in a file **this change edits**
- `scripts/check-selftest-counts.py:107` — `# LIBRARY: \`check-ratchet-contract\`'s population is \`check-*\` guards, so nothing else observes`

All five named files are in the widened population (measured below), so "neither sees it nor should"
is contradicted by the code as of this commit. `nor should` is a design assertion, not just a stale
count — it says the opposite of what this change decides, and the change does not answer it.

**What would prove this wrong:** `discover_self_tested_nonguards` omitting `page_markup.py`,
`page_chrome.py`, `brief-compose.py` and `observer_log.py`. Measured population (19):

```
begin-plan brief-compose build-m4-schema codex-review coverage_verdict explainer-serve
gen-backlog-page gen-dashboard gen-features-page gen-goals-page gen-m4-manifest m4_catalog
observer_log page_chrome page_markup peer-sites prior-art subject_status verify-exclusion-reasons
```

---

## LOW

### L1 · `evaluate`'s R2 measurement cites a denominator of 20; the population is 19

`scripts/check-ratchet-contract.py:310`
```python
    #      Measured 2026-09-30 across all 20 files: 0 violations. Free, so it is taken.
```

Measured: `len(discover_self_tested_nonguards(...)) == 19`, and 0 R2 violations across it — so the
verdict is right and the corpus size is not. The same file says `19` twice (`:1098`, `:1101`), so it
disagrees with itself, and the brief repeats the 20.

### L2 · The identifier guard is provably inert — its only falsifier is a fixture that is not valid Python

`scripts/check-ratchet-contract.py:195`
```python
    if not stem.isidentifier():
```

Measured across the full population (guards + widened, 59 files, 53 with non-identifier stems):
**0** files whose R3 answer changes if the guard is removed. That is not an accident of today's
corpus — a hyphenated stem can only satisfy the unguarded pattern via text that is not valid Python
(`import exec-tool`), which is precisely the suite's fixture. So the mutation entry *"the identifier
guard is bypassed"* is killed by a case over a branch production cannot reach.

Answering the brief's question directly: the rule has no *hole*. Keywords pass `isidentifier()` but
no valid text matches them; dotted names are non-identifiers; non-ASCII identifiers work through
`re.escape`. It is simply not the discriminator that is doing the work — the concatenated-blob regex
is, and its weakness is prose (H1/H2/M1), not the filename convention. Keeping the guard as
defence-in-depth is fine; describing it as *the* discriminator overstates it.

### L3 · `import_re` never checks that the import resolves to the file — a stdlib-shadowing stem passes R3 from unrelated imports

Measured against the real caller blob:

```
a hypothetical scripts/subprocess.py would pass R3 via the import arm: True
a hypothetical scripts/json.py       …                                : True
a hypothetical scripts/re.py         …                                : True
a hypothetical scripts/pathlib.py    …                                : True
a hypothetical scripts/dataclasses.py …                               : True
```

Not live — no current member shadows a stdlib name. But the population already contains
underscore-named libraries, so `scripts/logging.py` or `scripts/types.py` with a `--self-test` is a
plausible future member, and R3 would be green on it from day one.

### L4 · Real import forms `import_re` misses (all false REDs, none live)

```
no  import os, m4_catalog          (second name on a multi-name import)
no  from . import m4_catalog       (relative)
no  from m4_catalog.sub import X   (submodule)
no  if True: import m4_catalog     (compound statement)
no  from \<newline>    m4_catalog import A   (backslash continuation)
```

These fail *loud* (a false red), which is the safe direction, and none occurs today. Worth a line in
the docstring's stated bound, which currently names only the string-literal risk.

### L5 · `docs/dev-process.md:147` declares "`--self-test`: 21 cases" for this guard; the actual count is 52

Unpoliced: `check-selftest-counts.py` reads declared counts from the scripts, not from
`docs/dev-process.md` (`rc=0`, "46 script(s) declare a count"). The drift predates this change
(41 → 52 now) but this change is the one that moves it, and the spine row also still describes R3 as
"**a caller**", which the rename to "uses" has widened.

### L6 · `total`'s group list is still hand-maintained — verified complete today, and machine-covered by accident

`self_test`'s `total` sums twelve `len(...)` terms. I enumerated every case collection in the file:
`CASES, DISCOVERY_CASES, CALLER_CASES, POPULATION_CASES, WIDENED_POP_CASES, ESCAPE_CASES,
WIDENED_DRIFT_CASES, wiring, SELF_EXEMPTION_CASES, SCOPE_CASES, MANIFEST_BRANCH_CASES,
BLOB_TARGET_CASES` — all twelve appear. So the answer to the brief's question is **no other group is
missing**, and each term is derived (`len(...)`) rather than typed.

The class is not closed, as the author's own comment concedes, but it is *incidentally* covered:
`check-selftest-counts.py:103` lists `check-ratchet-contract.py`, and it compares the docstring's
declared count to the count the suite prints. A group dropped from `total` lowers the printed number
while the docstring stays, so that guard reddens. Worth recording, because the comment implies
nothing catches it.

---

## Answers to the six things you asked me to attack

1. **Is `import_re` sound?** Its answers are correct on today's corpus — I reproduced the AST
   comparison on six library stems, not four: 0 regex-only, 0 AST-only. Its *stated* soundness
   argument is false for multi-line strings and docstring prose (**M1**), and it misses five real
   import forms in the safe direction (**L4**). The dangerous weakness is not in `import_re` at all
   — it is in `invocation_re` over a blob that includes `.py` string literals (**H1**, **H2**).
2. **Is the identifier guard the right discriminator?** It has no hole, and it is inert on every
   valid input (**L2**). It is not what discriminates library from executable in practice.
3. **Did you widen the right rules, and was deleting the R1 case right?** Yes to both. R1's
   predicate and the population's predicate are the *same symbol* — `check_contract` tests
   `SELF_TEST_RE`, `discover_self_tested_nonguards` filters on `SELF_TEST_RE` — so R1 cannot fire on
   a widened member and the deleted case genuinely could not fail. One rule, one place; the coupling
   is enforced by the shared constant, which is the right mechanism, and the comment is the right
   place for the decision. R2 was free and correct (0 violations, verified). Its **exception
   handling** was not widened with it (**H3**).
4. **Another population mismatch of the same shape?** No. `caller_blob_targets:238` returns
   `sorted(set(discover_guards(list(texts))) | set(discover_self_tested_nonguards(list(texts), texts)))`
   and `evaluate:290,318` iterate `discover_guards(list(texts))` and
   `discover_self_tested_nonguards(list(texts), texts)` over the same `texts` — the same two
   expressions, so they cannot disagree. But the *repair* is uncovered at the site that broke
   (**M2**).
5. **Are the three `NO-CALLER:` reasons legitimate?** Yes, all three. Each names a real reason no
   executable caller *should* exist — a paid human-gated operation (`codex-review.py`), a
   previously-recorded design decision (`peer-sites.py`, #134/#313), a research tool with no
   pass/fail (`prior-art.py`) — and I confirmed no invocation exists for any of them. The defect is
   that the **set is incomplete**: `explainer-serve.py` is the same class and was let through by a
   false green (**H1**).
6. **The mutation entries.** All seven verified by hand against a green 52/52 control, each
   reddening the case it names. Every anchor binds exactly once in the delivered file.

```
CONTROL: rc=0 self-test: 52/52 passed fails=[]
KILLED attributed=True 49/52  the import arm is neutered            → an IMPORTED library is USED…
KILLED attributed=True 50/52  the line-start anchor is dropped      → an import inside a STRING LITERAL…
KILLED attributed=True 51/52  the optional indent is dropped        → …the import may be INDENTED…
KILLED attributed=True 51/52  the identifier guard is bypassed      → …HYPHENATED executable…
KILLED attributed=True 51/52  R2 stops being applied                → evaluate APPLIES R2 to a NON-guard
KILLED attributed=True 51/52  R3 stops being applied                → evaluate APPLIES R3 to a NON-guard…
KILLED attributed=True 51/52  the blob is built for guards only     → a SELF-TESTED NON-GUARD gets one too…
```

Two entries redden a second case as well (the import-arm entry also reddens the indent and wiring
cases; the anchor entry also reddens the commented-out case). Neither is vacuous — attribution to
the named case holds in both — but note that *"a COMMENTED-OUT import is not a use"* has no entry of
its own and is defended only by `_LINE_START`, i.e. the same constant as the string-literal case.

---

## Areas I could NOT establish

- Nothing on the gate results — the full sweep landed before I filed. `check-plan-code.py --mutate .`
  finished at exit 0 with **`53 file(s), 1041 mutation(s), 1041 killed, 1041 attributed to the case
  each names, 0 survivor(s)`**, matching the brief exactly. ⚠ It ran against the **working tree**,
  so it verifies the uncommitted state, not `778fd822` — B1 stands. I had separately verified the
  seven new entries by hand against a green 52/52 control before this arrived; the two agree.
- **The `recall-llm.py` payoff.** As the brief states, the file is not on this branch. I could not
  re-measure "R3 goes red if `.claude/hooks/surface-recall.sh` is deleted", and H2 shows that
  measurement does not generalise across the population even though it is presented as the rule's
  justification.
- **Whether `explainer-serve.py` is intended to have a caller.** I established that it has none and
  that R3 passes on prose; whether the right fix is a declaration or a CI step is a decision for
  you, not a finding.
- **`check-guard-coverage.py`'s SHAPE/SEQUENCE classification of the new import arm.** The guard
  runs green (rc=0) but its subject is the blob-addressing schema guards, so it says nothing about
  whether the new arm needs a SEQUENCE reconciliation.

---

## Verified — every command I ran

```
$ git log --oneline -3
778fd822 R3 asks whether anything USES a file, not whether anything invokes it
446025ab Retire PR #295: …

$ git diff --stat master...HEAD
 scripts/check-ratchet-contract.py | 194 ++++++++++++-, scripts/codex-review.py | 7 +,
 scripts/peer-sites.py | 7 +, scripts/prior-art.py | 6 +      4 files changed, 204 insertions(+), 10 deletions(-)

$ git status --porcelain
 M scripts/check-plan-code.py
 M scripts/check-ratchet-contract.py
 M scripts/mutations/check-ratchet-contract.json

$ python3 scripts/check-ratchet-contract.py --self-test
self-test: 52/52 passed                  rc=0

$ python3 scripts/check-ratchet-contract.py
guards discovered (40): …
ratchet contract OK                      rc=0

$ python3 scripts/check-plan-code.py --self-test
131/131 passed

$ python3 scripts/check-selftest-counts.py
self-test counts: 46 script(s) declare a count, every one verified by running it   rc=0

$ python3 scripts/check-plan-code.py --mutate .            # ~30 min, against the WORKING TREE
OK — delivered scripts mutated: 53 file(s), 1041 mutation(s), 1041 killed,
     1041 attributed to the case each names, 0 survivor(s)                         rc=0

$ python3 scripts/check-docs.py             rc=0  Documentation integrity OK
$ python3 scripts/check-anchors.py          rc=0  anchors: 13 registered, all claimed…
$ python3 scripts/check-guard-coverage.py   rc=0  ✅ every BLOB-ADDRESSING SCHEMA guard classified…
$ python3 scripts/check-dashboard-entry.py  rc=1  REFUSED — 4 tracked file(s) changed and no entry…   ← M3

# B1 — the committed tree in isolation
$ git archive HEAD | tar -x -C <tmp>; cd <tmp>
$ python3 scripts/check-ratchet-contract.py --self-test    self-test: 49/49 passed  rc=0
$ grep -n "self-test  #" scripts/check-ratchet-contract.py 30: … # 49 cases
$ python3 -c "import json;print(len(json.load(open('scripts/mutations/check-ratchet-contract.json'))))"   10
$ grep -n '"scripts/check-ratchet-contract.py":' scripts/check-plan-code.py                824:  … : 10,
  (its 3 --self-test failures in <tmp> are environmental — node_modules/typescript absent, HARNESS_TREE)

# population + R3 arms, per widened file
widened population: 19
begin-plan inv=1 imp=0 NOCALLER=0 … codex-review inv=0 imp=0 NOCALLER=1 … coverage_verdict inv=0 imp=1
explainer-serve inv=1 imp=0 NOCALLER=0 … m4_catalog inv=0 imp=1 … observer_log inv=0 imp=1
page_chrome inv=1 imp=1 … page_markup inv=1 imp=1 … peer-sites inv=0 imp=0 NOCALLER=1
prior-art inv=0 imp=0 NOCALLER=1 … subject_status inv=0 imp=1 … verify-exclusion-reasons inv=1 imp=0

# import_re vs an ast import graph, all six library stems
coverage_verdict: regex 1 / AST 1, regex-only [] AST-only []
m4_catalog:       regex 6 / AST 6, regex-only [] AST-only []
observer_log:     regex 3 / AST 3, regex-only [] AST-only []
subject_status:   regex 3 / AST 3, regex-only [] AST-only []
page_chrome:      regex 6 / AST 6, regex-only [] AST-only []
page_markup:      regex 5 / AST 5, regex-only [] AST-only []
  (cited evidence checked by hand: check-storage-independence.py:398 is a mid-line string —
   the anchor does exclude it; verify-exclusion-reasons.py:388 is a real in-function import)

# import_re adversarial probe (M1, L4)
no MATCH: single-line string / import os,m4_catalog / from . import / from m4_catalog.sub /
          if True: import / backslash continuation / prefix collision (m4_catalogue)
MATCH:    triple-quoted fixture / triple-quoted indented / docstring prose example /
          parenthesised from-import / trailing-comment import

# H1/H2 — invocation matches classified by ast string-literal span, then the deletion falsifier
⛔ PROSE-ONLY  scripts/explainer-serve.py  real=0 prose=7
⛔ STILL GREEN scripts/begin-plan.py       (only real caller ci.yml:303 deleted)
⛔ STILL GREEN scripts/gen-m4-manifest.py  (only real caller check-schema-gates.sh:100 deleted)

# H3
BRANCH evaluate(unparseable self-tested non-guard): !! UNHANDLED SyntaxError '(' was never closed
MASTER evaluate(same input):                        [R4_no_mutation_manifest, R4W_no_mutation_manifest]

# M2
revert main():1105 to `for rel in ratchets:`  →  --self-test 52/52 passed rc=0 ; live run rc=1, 16 violations
scripts/check-plan-code.py:500  subprocess.run([sys.executable, name, "--self-test"], …)   ← the only oracle
.github/workflows/ci.yml:239    run: python3 scripts/check-ratchet-contract.py             ← what does catch it

# L1, L2, L3
R2 violations across widened population: 0        declared denominator in the file: "all 20 files"
non-identifier stems in the full population: 53 of 59; answers changed if the guard is removed: 0
hypothetical scripts/{subprocess,json,re,pathlib,dataclasses}.py pass R3 via the import arm: True ×5

# mutation entries — anchors bind once each, all seven
1 1 1 1 1 1 1   (src.count(old) for each of the 7 new entries)
CONTROL 52/52 → all 7 KILLED, all 7 attributed to the case they name
```
