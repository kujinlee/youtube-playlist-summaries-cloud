# Claude adversarial review — round 1 — the workflow-readers architecture review

**Subject:** `docs/reviews/architecture-review-2026-09-21-workflow-readers.md` (untracked, branch
`arch-review-153-workflow-readers`). A Phase 6 architecture review document paying off backlog
**#153**.

**Reviewer:** Claude half, dual adversarial review, round 1.
**Method:** every load-bearing number in the document was re-derived by running the shipped code,
not by reading it. Where I ran something, the transcript is pasted. Where I did not, it is labelled
UNVERIFIED. Scratch scripts lived outside the repo; no repository file other than this one was
modified.

**Verdict: DO NOT CLOSE #153 AS WRITTEN.** The diagnosis is right and most of the measurement
reproduces exactly. Two Blocking defects sit in the *recommendation's* numbers and in its
characterisation of the reader it promotes — both of which the implementer would act on directly.

| Severity | Count | Ids |
|---|---|---|
| Blocking | 2 | B1, B2 |
| High | 2 | H1, H2 |
| Medium | 5 | M1–M5 |
| Low | 6 | L1–L6 |
| Checked and SOUND | 14 | S1–S14 |

---

## Findings

### B1 — Blocking. The mutation transfer is **12 anchors, not 8**, and the numbers as written red-line `check-plan-code.py`

The document, line 146:

> | Mutation entries | `check-python-pin.py` **39 → 31**, new key `workflow_structure.py` **= 8** | Measured: 8 of `check-python-pin.json`'s 39 anchors bind to the moving code. **The sum is preserved at 39 — this is a TRANSFER, not a ratchet fall** |

Re-derived by resolving every manifest entry's `edits[0][0]` anchor to a line number in
`scripts/check-python-pin.py`, then to its owning `ast` node. The symbols that must move are
`_steps` (`:106-282`), `_structural` (`:301-357`), `Step` (`:86-103`), and the two module constants
they are the **only** consumers of — `_STEPS_KEY` (`:295`, used at `:244` and `:253`, both inside
`_steps`) and `_BLOCK_SCALAR` (`:298`, used at `:351`, inside `_structural`).

Twelve manifest entries bind there. Entry index, resolved line, anchor:

```
#26 :264  cur = Step(len(m.group(1)), [" " + m.group(2)])                     (_steps)
#27 :232  structural = _structural(text.split("\n"))                          (_steps)
#28 :298  _BLOCK_SCALAR = re.compile(...)                                     (_BLOCK_SCALAR)
#29 :263  if m and (cur is None or len(m.group(1)) <= cur.indent):            (_steps)
#30 :278  if line.strip() and indent <= cur.indent:                           (_steps)
#31 :349  if line.lstrip().startswith("#"):                                   (_structural)
#32 :249  steps_indent: int | None = None                                     (_steps)
#33 :245  job_steps_indent = min(depths) if depths else None                  (_steps)
#34 :254  if (opens_steps and len(opens_steps.group(1)) == job_steps_indent   (_steps)
#35 :260  if line.strip() and indent <= steps_indent and not m:               (_steps)
#36 :295  _STEPS_KEY = re.compile(...)                                        (_STEPS_KEY)
#37 :244  + :254  (two edits, both inside _steps)                             (_steps)
```

No entry among the twelve has any edit outside the moving code, so there is no partial-move
ambiguity. The narrowest defensible reading — "only the two function bodies and `Step`" — still
gives **10**, and it is not a reading that compiles: the functions reference both constants. There
is no reading of the shipped manifest that yields 8.

**Why this is Blocking rather than a wrong number.** `scripts/check-plan-code.py:1212-1218` compares
each target's declared count against the manifest's actual count by equality and fails on drift:

```python
for target, want in sorted(EXPECTED_MUTATIONS.items()):
    got = counts.get(target, 0)
    if got != want:
        drift.append(f"{target}: manifest holds {got} mutation(s), expected {want}. ...")
```

`EXPECTED_MUTATIONS["scripts/check-python-pin.py"]` is `39` today
(`scripts/check-plan-code.py:813`). An implementer who follows line 146 writes `31` and `8`, while
the manifests on disk hold `27` and `12` — **two simultaneous drift failures**, on the gate that
CI runs as `--mutate .`. The correct transfer is **39 → 27**, new key **= 12**; the sum is still
preserved, so the document's *framing* survives — only its arithmetic does not.

---

### B2 — Blocking. `_structural()` carries a **live false green** the document does not know about, inside the very section that promises the bounds are stated

The document, lines 149-163, under the heading *"What this does NOT do — stated, not implied"*,
names exactly one surviving bound (the flow mapping) and characterises it:

> The guard reports the **absence of a thing that is present**. Fail-closed, so not a false green

There is a second bound, it is **not** fail-closed, and it is the same fixture the document quotes
as the fourth `declared_pins` defect with one cosmetic change. `_BLOCK_SCALAR`
(`scripts/check-python-pin.py:298`) is

```python
re.compile(r"^(\s*)[\w.\-]+:\s*[|>][-+0-9]*\s*(#.*)?$")
```

`[\w.\-]+` cannot span the space in `- run:`, so a block scalar **opened on the dash line** never
matches and its body is never masked. Measured minimal pair — identical fixtures, differing only in
whether `run: |` sits under a `name:` or on the dash:

```
masked form  (- name: seed / run: |)  -> declared_pins []      unpinned_jobs ['w.yml:verify']  rc 2
dash form    (- run: |)               -> declared_pins ['9.9'] unpinned_jobs []                rc 0
```

The `rc 0` message is `python pin OK — every job pins 9.9, and this interpreter is 9.9`, for a job
whose only real step is `- run: python3 -V` and which contains **no `setup-python` step at all**.
That is a false green — "the direction this guard must never fail in", by `declared_pins`' own
docstring at `:362-366`.

Two things make this worse than an ordinary missed shape:

1. **The suite appears to cover it and does not.** `scripts/check-python-pin.py:880-882`:

   ```python
   case("...and a job holding only those still reports as unpinned",
        unpinned_jobs({"w.yml": "jobs:\n  verify:\n    steps:\n      - run: |\n"
                                "          python-version: '3.12'\n"}, {}), ["w.yml:verify"])
   ```

   It passes, but not because the mask worked — the fixture's step contains no
   `uses: actions/setup-python`, so `declared_pins` skips it at `:381` before the masking is ever
   load-bearing. Add the `uses:` line inside the same heredoc and the case inverts. This is the
   "passing for an ambient reason" shape the repo has recorded four times on one file.

2. **`- run: |` is the ordinary short form.** It is absent from this repository's two workflows
   today (`grep -nE "^\s*-\s+[-\w.]+:\s*[|>]" .github/workflows/*.yml` → no matches), so the defect
   is **latent, not live** — stated in the document's own honest phrasing. But the recommendation's
   whole premise is that `_structural()` is the best-paid-for of the three readers and should
   become the shared one. Promoting it without this in the bounds list ships a false green into
   three guards at once, and the section that would have caught it is the one titled *stated, not
   implied*.

**What this does not invalidate:** the R3 sweep (S5) is unaffected, because ci.yml contains no
dash-opened block scalar. The instrument was right; the reader it validates has a hole.

---

### H1 — High. The recommendation fixes **two of the three** defective shapes. `if: false` survives, and the document does not say so

The document's transcript, lines 68-73:

```
R3 SATISFIED  <- a YAML COMMENT describing a REMOVED step
R3 SATISFIED  <- text inside a `run: |` block scalar (a heredoc writing a fixture)
R3 SATISFIED  <- a step disabled by `if: false`
R3 SATISFIED  <- a genuine step                              (the control)
```

I reproduced this exactly (S4). I then re-ran it with the blob passed through `_structural()` —
i.e. the state the recommendation delivers:

```
                             before      after _structural
check-gone.py      (comment)  SATISFIED -> VIOLATION
check-heredoc.py   (scalar)   SATISFIED -> VIOLATION
check-disabled.py  (if:false) SATISFIED -> SATISFIED     <-- unchanged
check-real.py      (control)  SATISFIED -> SATISFIED     <-- correct
```

`if: false` is *structure*, so a masking primitive is definitionally unable to see it. The document
knows this ("`_structural()` masks comments and block scalars") but never joins the two facts, and
its own *"What this does NOT do — stated, not implied"* list omits the case. Backlog row **#154**
as drafted — *"wire `check-ratchet-contract.py`'s R3 to it"* — would therefore be ticked with one
of the three shapes it was opened for still green.

Closing it needs `_steps()` used for real (find the step that owns the invocation, reject the step
if it carries a falsy `if:`), which is a different and larger change than the one recommended. The
minimum acceptable repair to the *document* is to state the residue and file it.

**Fair to the document:** the gap is latent, and I checked. Walking all 57 steps of the real
`ci.yml` and intersecting each step's `if:` lines with every guard basename under
`invocation_re`, **no guard invocation lives inside a conditional step**, and `ci.yml` has no
job-level `if:` either. So `if: false` is no more live than the other two shapes were.

---

### H2 — High. The extraction cannot be executed from this document: the self-test cases must move too, and nothing in it says so

`scripts/check-plan-code.py:500`:

```python
r = subprocess.run([sys.executable, name, "--self-test"], cwd=d, ...)
```

The harness runs **only the mutated file's own suite**, and `check-plan-code.py:669-670` states the
consequence in its own words:

> the same reason #71 held its sum at 73. `run_suite(d, fname)` runs only the mutated file's suite,
> so the killing cases moved too.

So a mutation whose `"file"` becomes `scripts/workflow_structure.py` can only be attributed if
`workflow_structure.py` has its **own `--self-test`** containing the case named in `expect` — and
`expect` is matched by **exact equality** against a parsed case name (`:1412-1425`, `:1481-1483`).
The document's bookkeeping table has one row for mutation entries and one for discovery, and names
none of the following, all of which the transfer forces:

* the 12 killing cases move out of `check-python-pin.py`'s suite into the library's;
* `check-python-pin.py`'s docstring line 5 declares `--self-test  # 84 cases` and the suite prints
  `84/84 passed` today — that number falls and must be re-declared;
* `check-python-pin.py` is pinned in `scripts/check-selftest-counts.py:84`'s `POPULATION`, so the
  declared count is externally verified and a stale one fails;
* if `workflow_structure.py` declares a count it must join `POPULATION` too — and note the trap
  that file records at `:95-97`: **bare names in `POPULATION`, full paths in
  `check-plan-code.EXPECTED_MUTATIONS`**.

This is not pedantry about a table: #154 is sized **M**, and the unnamed work is most of what makes
it M rather than S.

---

### M1 — Medium. "Extract `_structural()` + `_steps()`" over-frames what is shared. Only `_structural()` is

R3 is a substring scan over a concatenated blob (`check-ratchet-contract.py:181`). What it needs is
*which lines of `ci.yml` are structure* — `_structural()`. It has no use for step boundaries:
`_steps()` returns `Step(indent, body)` tuples scoped to the shallowest `steps:` key, which is
meaningless applied to a blob that is 81 shell and Python files joined to one workflow.

`_steps()` moves for a different reason — it is `_structural()`'s only in-file consumer and owns
the mask by design (`:225-232`). That is a fine reason to move it, but it is not sharing, and
stating it as sharing makes the extraction look like it delivers more reuse than it does. The
honest framing is: *`_structural()` becomes shared; `_steps()` and `Step` move with it because the
layering says the mask belongs to the splitter.* (If H1 were addressed, `_steps()` would genuinely
become shared — which is an argument for doing H1 inside #154 rather than after it.)

---

### M2 — Medium. The "Discovery" row names the wrong mechanism, and the reason it gives is not the reason

The document, line 147:

> | Discovery | Add to `check-plan-code.py`'s self-tested-non-guard list (`:2745-2754`) | `GUARD_PATH_RE` is `scripts/check-[\w.-]+\.py`, so a library is **not** a guard and R1–R3 never see it. That list is then the only place naming it |

Three corrections:

* **`:2745-2754` is not a self-tested-non-guard list.** It is the tail of a `--self-test` case
  asserting `sorted(EXPECTED_MUTATIONS)` — `case("the declared counts name every manifest that
  ships", ...)` at `:2687`. It contains 40+ `check-*` guards alongside the libraries. The reason
  `workflow_structure.py` must be added there is that it **ships a manifest**, not that it is a
  non-guard.
* **The self-tested-non-guard population lives in a different file and is computed, not listed.**
  `scripts/check-ratchet-contract.py:402-409`:

  ```python
  def discover_self_tested_nonguards(script_paths, texts):
      guards = set(discover_guards(script_paths))
      return sorted(p for p in script_paths
                    if p not in guards and SELF_TEST_RE.search(texts.get(p, "")))
  ```

  `workflow_structure.py` joins it automatically the moment it has a `--self-test`. There is
  nothing to add.
* The document does not mention `WIDENED_MANIFEST_DEBT` (`check-ratchet-contract.py:372-398`),
  which is the frozen set a self-tested non-guard *without* a manifest must be pinned in, checked
  by identity in both directions (`widened_debt_drift`, `:414`). With a manifest the library
  correctly stays out of it — so this is a no-op, but a reader following the table has no way to
  know that, and the two most recent entries in that comment (`codex-review.py`,
  `explainer-serve.py`) are exactly this transaction.

The `GUARD_PATH_RE` claim itself is SOUND — see S10.

---

### M3 — Medium. The reason for not migrating `check-merge-ready.py` does not hold. The decision may still be right

The document, lines 169-172:

> **`check-merge-ready.py` is NOT migrated by this recommendation.** Its reader answers a different
> question (*which steps are gated on `pull_request`*)…

Its *guard* answers a different question. Its *reader* does not. `pr_only_steps` hand-rolls a step
splitter — `scripts/check-merge-ready.py`, inside `pr_only_steps`:

```python
step_indent: int | None = None
key_indent: int | None = None
...
if re.match(r"\s*-\s", line) and (step_indent is None or indent <= step_indent):
    flush()
    step_indent, key_indent = indent, indent + 2
elif step_indent is not None and indent <= step_indent:
    flush()
    step_indent = key_indent = None
```

Sibling-dash detection, dedent-closes-the-step, and an ownership indent. That is `_steps()`'s
subject, arrived at independently — which is precisely the document's own verdict, *"the defect is
not in any of the three; it is that there are three"*, applied to the third one. A justification
that rests on the guard's question rather than the reader's cannot distinguish this case from the
two being merged.

The *decision* is still defensible, and the document has the material for a better argument two
lines later: `check-merge-ready.py` is the only one of the three with a soundness check, so
migrating it trades a proven falsifier for an unproven shared reader. Say that instead. (Verified
the falsifier works — S9.)

---

### M4 — Medium. The instrument behind the document's most dangerous claim is not in the repository

"Swept across all 40 guards on disk: 0 currently depend on it" is a negative, and the document's
defence is that "the sweep's instrument was validated with two controls first". Both controls are
*described*; neither is committed. `git status` on this branch shows one untracked file, the review
document itself. A reader cannot re-run the sweep, and the next person to change `caller_sources`
or `invocation_re` has nothing that would tell them the zero has expired.

I rebuilt the sweep independently and it holds (S5), including both controls (S6) — so the number
is right. But the document as filed asks to be believed, and this project's standing rule is that a
green check is only worth more than a claim when it reads the thing the claim is about. Either
commit the sweep as a throwaway under `scripts/` with a `NO-CALLER:` reason, or state in the
document that the figure is a point-in-time measurement with no owner.

---

### M5 — Medium. A fourth divergence between the three readers, unnamed: the **corpus**

The document's table has columns for what each guard built, what it cost, and how it fails. It has
no column for *which workflow files it reads*, and the three disagree:

| Guard | Corpus |
|---|---|
| `check-python-pin.py` | `WORKFLOW_DIR` glob `("*.yml", "*.yaml")` — `:70`, `:76` |
| `check-merge-ready.py` | `workflow_files(directory)` → `*.yml` ∪ `*.yaml` — `:282` |
| `check-ratchet-contract.py` | **`ci.yml` alone** — `caller_sources: list[Path] = [ci_path]`, `:868` |

`check-python-pin.py:72-76` records paying for exactly this lesson ("a guard that reads only what
its own corpus happens to contain is the shape this work has already paid for twice"), and
`check-merge-ready.py:271-276` records paying for it again (`.yaml` is a workflow too). R3 has not
had that round. A shared *reader* does not fix a divergent *corpus* — the recommendation would
route `ci.yml` through `workflow_structure.py` and leave `schema-gates.yml` unread by R3.

Direction of failure is safe (a caller in an unread workflow reads as no caller → violation), so
this is not a false green. But it belongs in the population section, and it is the shape #153 was
opened about.

---

### L1 — Low. Internal inconsistency: "shared by three guards" vs a recommendation that wires two

Line 166: *"One reader shared by three guards means a future defect in it is a defect in three
guards at once."* Three lines later the document declines to migrate the third. The risk paragraph
should say two — and the understatement runs the wrong way for a concentration argument.

### L2 — Low. `_structural`'s docstring is already stale, and the extraction is the moment to fix it

`:301` — *"PURE. The lines of a **step** that are YAML STRUCTURE"*. The shipped code applies it to a
whole file at `:232` (`_structural(text.split("\n"))`), and the recommendation applies it to a whole
file again. Whole-file application is correct and already precedented; the docstring is the only
thing saying otherwise, and a promoted library carrying a docstring that contradicts both its
callers is a trap for the next reader.

### L3 — Low. "284 of `ci.yml`'s 480 lines (59%)" is exact; its composition is not what the document implies

Reproduced to the line: `len(text.split("\n")) == 480`, `len(_structural(...)) == 196`, removed
**284**, **59.2%**. Instrumenting the two drop branches separately:

```
dropped by the BLOCK-SCALAR branch:  15
dropped by the COMMENT branch:      269
```

The document's phrase ("comment or block-scalar content") is accurate, but its R3 transcript leads
with the heredoc case and the prose leans on block scalars; in the corpus that actually matters the
mechanism is **94.7% comments**. `ci.yml` contains only three block scalars in total, all of them
masked. Worth one clause, because it is the number that tells the implementer where the risk is.

### L4 — Low. `invocation_re`'s docstring does not cite architecture review #7

Document line 75-76: *"`invocation_re`'s docstring says the rule 'must not be satisfiable by prose'
and cites architecture review #7's finding that a `docs/` table row was being read as a caller."*
The first half is verbatim. The docstring (`check-ratchet-contract.py:142-151`) describes the
finding — *"`docs/dev-process.md` lists a script in a table headed What is mechanically enforced and
nothing runs it"* — but never names review #7. The attribution is correct in substance and
UNVERIFIED as a citation; phrase it as *"cites the finding"*.

### L5 — Low. An implementation trap the document should pre-empt: mask `ci.yml`, never the blob

`blob_for[rel]` (`check-ratchet-contract.py:881-885`) joins `ci.yml` with `scripts/*.sh`,
`.claude/hooks/*` and `scripts/*.py` — 82 sources in today's tree. `_structural()` drops every line
whose first non-space character is `#`, so applying it to the *joined* blob would strip every
comment from 81 shell, hook and Python files and silently change R3 across the whole non-workflow
corpus. The masking must happen on `ci_path.read_text()` before the join. One sentence in #154
prevents a plausible wrong turn.

### L6 — Low. The section the document edits contains a stale count it could fix in passing

`CONTEXT.md:118` opens the Verification Stack with *"26 scripts under `scripts/`"*. The shipped tool
prints `guards discovered (40)`, and `ls scripts/*.py` is 63. The document adds two terms to exactly
this section; correcting the preamble is free there and is otherwise nobody's job.

---

## Checked and SOUND

Listed so the reader can tell what was covered, not only what failed.

**S1 — The population correction, both halves.** `check-ci-watched.py` opens no workflow: its only
file handle is `SENTINEL = ROOT / ".claude/ci-watching"` (`:54`), and everything else goes through
`subprocess.run` to `gh` (`:139`). Grepping the whole file for `.yml`/`.yaml`/`workflows` returns
nothing. `check-ratchet-contract.py` does read it — `ci_path = ROOT / ".github/workflows/ci.yml"`
at **`:835`**, exactly as cited. Both corrections stand.

**S2 — Is four complete? Yes, by my own sweep.** `grep -rln ".github/workflows"` across every
`*.py`, `*.sh`, `*.ts`, `*.js`, `*.mjs` outside `node_modules` returns seven files. Four are not
members, each checked by hand:

* `scripts/check-plan-code.py:206` — `".github/workflows"` is a `HARNESS_TREE` **staging** entry, and
  its own comment at `:202` says why: *"the surviving reason is `check-ratchet-contract.py:835`"*. It
  copies the directory; it does not read the YAML.
* `scripts/check-banner-armed.py:1135` and `scripts/check-review-decision.py:462` — the path appears
  only as a **string in a self-test fixture** for path classification.
* `tests/e2e/cloud.setup.ts` — not a guard, does not parse workflow structure.

No `scripts/*.sh` and no `.claude/hooks/*` file mentions `.github` or `workflows` at all (the only
two hits in `scripts/*.sh` are GitHub **Pages** URLs in `publish-arch-page.sh`). The population of
workflow-text readers is the three the document names. The document did not show this sweep; it is
right.

**S3 — The stdlib-only argument, every clause.** `grep -rn "import yaml\|from yaml\|ruamel"` over
`scripts/` and `tests/` → zero (and zero across all **63** `scripts/*.py`, not just the 40 guards).
`python3 -c "import yaml"` → `ModuleNotFoundError: No module named 'yaml'`. No `requirements.txt`,
no `pyproject.toml`, no `setup.py`, no `Pipfile`. No `pip install` in either workflow. An `ast`
walk of every `scripts/*.py` import returns non-stdlib names for 17 files, and **every one is a
local sibling module** (`page_chrome`, `page_markup`, `m4_base_db`, `m4_catalog`, `subject_status`,
`coverage_verdict`) — no third-party package anywhere. `actions/setup-python@v5` is used at
`ci.yml:68` and `schema-gates.yml:201,274`. The conclusion — a real parse means this repo's first
runtime dependency — holds.

**S4 — The R3 four-case transcript.** Reproduced verbatim against `rc.check_caller(path, "'''doc'''",
blob)` with a blob containing a YAML comment, a heredoc inside `run: |`, an `if: false` step and a
genuine step: **all four `R3 SATISFIED`**. (What happens to them under the fix is H1.)

**S5 — "0 of 40 guards currently depend on the R3 false green" — reproduced, and the instrument
survives attack.** I rebuilt `main()`'s corpus line by line rather than trusting the document's:
`texts` from `sorted((ROOT/"scripts").glob("*.py"))`; `ratchets = discover_guards(list(texts))` →
**40**, byte-identical to the shipped tool's printed list; `caller_sources = [ci_path] +
sorted(scripts/*.sh) + sorted(.claude/hooks/*) + sorted(scripts/*.py)` → **82**; per-guard blob
excluding the guard's own path and skipping non-files, exactly as `:881-885`. Then
`check_caller(rel, texts[rel], blob)` with `ci.yml` raw versus `_structural`-masked:

```
guards discovered:                        40
NO-CALLER escapes:                         2  (check-merge-ready.py, check-review-decision.py)
R3 violations today:                       0
guards that FLIP under structural masking: 0
```

The shipped tool agrees: `python3 scripts/check-ratchet-contract.py` → `guards discovered (40)` /
`ratchet contract OK`.

**S6 — The zero is not vacuous, and I tested the two routes it could have been.**
*(a) Controls, run independently of the document's.* A synthetic guard whose only `ci.yml` mention
is a comment flips `SATISFIED → VIOLATION` under masking; one with a genuine `- run:` step stays
`SATISFIED`. So the sweep can both detect a flip and avoid manufacturing one.
*(b) The route the document did not close.* The zero would be empty if nothing depended on `ci.yml`
in the first place. Resolving each guard's R3 evidence to its source file: **21 of the 40 are
satisfied by `ci.yml` and nothing else** — `check-anchors`, `check-arch-findings`,
`check-backlog-closure`, `check-explainer-delivery`, `check-fixture-variation`,
`check-function-revokes`, `check-gate-falsifiability`, `check-group-claims`, `check-plan-code`,
`check-plan-file-tags`, `check-plan-task-order`, `check-producer-enumeration`, `check-python-pin`,
`check-ratchet-contract`, `check-review-rounds`, `check-roadmap-consistency`, `check-selftest-counts`,
`check-storage-grant-pin`, `check-storage-independence`, `check-test-counts`,
`check-theme-token-coverage`. All 21 survive masking. That is a materially stronger result than the
document claims and it should be in the document.
*(c) Zero guards are satisfied only by another `scripts/*.py` file*, so there is no second
prose-satisfies-R3 population hiding behind the first.

**S7 — `_structural` applied to a whole file.** Legitimate, and already shipped:
`check-python-pin.py:232` is `structural = _structural(text.split("\n"))` — the whole workflow, not
a step. (The docstring disagreeing with this is L2.)

**S8 — The flow-mapping transcript, lines 153-158.** Reproduced exactly, including the message:

```
with: {python-version: '3.12'}
    declared_pins  -> []
    unpinned_jobs  -> ['w.yml:verify']
    verdict        -> rc 2, "CANNOT RUN — no `python-version:` was found in any workflow…"
```

Fail-closed, as stated.

**S9 — `check-merge-ready.py` "Refuses — surfaces the unrecognised line".** Verified by running it.
A PR-only condition hidden inside a `run: |` body gives `pr_only_steps -> []` (correctly not
credited) **and** `unaccounted_mentions -> ["ci.yml: echo \"if: github.event_name ==
'pull_request'\""]` — a loud refusal rather than a silent miss. The document's third column is
right, and its quotation of `:130-132` is verbatim.

**S10 — `GUARD_PATH_RE` excludes a library.** `check-ratchet-contract.py:113` is
`re.compile(r"scripts/check-[\w.-]+\.py")`, applied with `fullmatch` at `:164`.
`scripts/workflow_structure.py` does not match, so R1–R3 never see it. SOUND. (Its R4 consequence is
M2.)

**S11 — The naming decision.** `workflow_structure` collides with nothing: no
`scripts/workflow*` file exists, and `importlib.util.find_spec("workflow_structure")` returns
`None`. The underscore/hyphen convention is quoted faithfully from `CONTEXT.md:108-113` and is
broader than the document's single citation suggests — six underscored libraries already exist
(`page_markup`, `page_chrome`, `m4_base_db`, `m4_catalog`, `subject_status`, `coverage_verdict`)
against 57 hyphenated executables. The *"peer, never a gate"* rule and the generator → gate arrow
are quoted correctly from the same lines.

**S12 — "A transfer, not a ratchet fall" is the right framing.** `check-plan-code.py:669-670`
records the precedent in its own words (*"the same reason #71 held its sum at 73"*), and
`EXPECTED_MUTATIONS` is a per-target dict, so a sum-preserving split across two keys is exactly
what the ratchet permits. Only the numbers are wrong (B1) and only the accompanying case move is
missing (H2).

**S13 — Supporting facts spot-checked.** 13 ADRs under `docs/adr/` (+ a README), so "all thirteen"
is right. `check-vocabulary-collisions.py` is schema-scoped by its own docstring (its examples are
`jobs.lease_token` vs `video_artifacts.lease_token`), so "the repo enforces this on schema and has
never applied it to its own guards" is fair. `check-storage-independence.py` does parse with `ast`
(`:60`, `:217`, `:293`); the "grep survived 3 of 5 mutations" half is corroborated by
`docs/dev-process.md` rather than re-measured — UNVERIFIED here. `check-merge-ready.py`'s "4 shapes
/ 3 rounds" matches its docstring's *"FOURTH SHAPE IN THREE ROUNDS"* (`:120`). #153 is the last row
of the Items table; **#154, #155 and #156 are free** — no collision.

**S14 — Baselines are green, so every measurement above is over a clean tree.**
`check-python-pin.py --self-test` → `84/84 passed` (matching its declared `# 84 cases`);
`check-ratchet-contract.py --self-test` → `41/41 passed`; `check-merge-ready.py --self-test` →
`52/52`; `check-ratchet-contract.py` → `ratchet contract OK`. The full `--mutate .` harness was
**not** run (many minutes, out of scope for a round-1 document review) — the B1 conclusion is
derived from `check-plan-code.py:1212-1218` by reading the comparison, and is labelled as such.

---

## What I would require before this closes #153

1. **B1** — 39 → **27**, new key **= 12**, with the twelve entry indices listed so the implementer
   does not re-derive them.
2. **B2** — add the dash-opened block scalar to the bounds section as a **false green**, note that
   `:880-882` passes for an ambient reason, and file it (it is a better #155 than the soundness
   check, because it is a known defect rather than a missing mechanism).
3. **H1** — state that `if: false` survives the fix, and either fold the step-level repair into
   #154 or file it.
4. **H2** — name the self-test case move, the declared-count change, and `POPULATION` in the
   bookkeeping table.
5. **M2** — correct the Discovery row's target and reason.
6. **M3** — replace the migration-decline justification with the one that holds (trading a proven
   falsifier for an unproven shared reader).

M4, M5 and the Lows are improvements, not gates.
