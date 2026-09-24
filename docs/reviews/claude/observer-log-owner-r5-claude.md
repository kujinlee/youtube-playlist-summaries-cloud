# Adversarial review — `observer-log-owner` (PR #342), round 5, Claude half

**Subject.** Branch `observer-log-owner`, HEAD `17c21ecd`, base `origin/master` (`b493edcc`).
Primary subject: **`6cfae34a`** — round 5's fold of round 4's Codex High, the code no review round
has seen (`scripts/codex-review.py`, `scripts/check-plan-code.py`,
`scripts/mutations/codex-review.json`). Also in range and docs-only: `fedd004e`, `f7164f6d`,
`17c21ecd`.

**Mandate: refute, not confirm.** The brief's instruction was to assume `6cfae34a` put a defect
inside its own fix, because the three commits before it each did. It did, twice: the phrase the
commit says it deleted is **still in the docstring as a positive claim**, beside a paragraph that
now states a different identity than the one the code computes; and claim 4's class was fixed as an
instance while three more instances of it survive in the two files the commit touched.

**Counts:** 0 Blocking · 1 High · 4 Medium · 1 Low

**Verdict: NOT CONVERGED.**

---

## What I verified GREEN, by running it

### The control, and the isolated tree the mutations ran in

A scripts-only copy gives a RED control (1 case of 119), so it is not a faithful staging. Measured,
with the failing case named rather than guessed:

```
$ cp -R $REPO/scripts $ISO/scripts && cd $ISO && python3 scripts/codex-review.py --self-test
  [FAIL] docs/reviews is watched even when --out is outside the repo: got False want True
118/119 passed        control-rc=1

$ mkdir -p $ISO/docs/reviews/verdicts && python3 scripts/codex-review.py --self-test
119/119 passed        control-rc=0
```

`watched_dirs` (`scripts/codex-review.py:633-640`) calls `os.path.isdir`, so `docs/reviews` has to
exist for that case to reach its subject. Every mutation below ran over that **green 119/119
control**, on a copy; the working tree was not modified (`git status --porcelain` empty before and
after — checked).

### Claim 7 — the counts, re-derived by running, never read from a comment

```
$ python3 scripts/codex-review.py --self-test  |  tail -1
119/119 passed                                    rc=0
$ grep -n 'self-test  #' scripts/codex-review.py
45:  scripts/codex-review.py --self-test  # 119 cases
```

`EXPECTED_MUTATIONS` reconciled against the manifests on disk, by loading the module and counting
the JSON rather than reading the constant's comment:

```
declared sum          = 990
declared codex-review = 25
manifest total on disk= 990
manifest codex-review = 25
MISMATCHES: none
files: EM = 53  manifests = 53
```

### Claim 7 — the nine r4+r5 mutations kill AND attribute

Each manifest edit applied to the isolated copy; the failing case names parsed with the harness's
**own** consumer, `check_plan_code.parse_fail_names` (`scripts/check-plan-code.py:1790`), not a
re-typed regex:

```
CONTROL rc=0 119/119 passed
KILL  attr=True  | r4 H1: the allocator is dropped, so the documented mktemp call shape collides again
KILL  attr=True  | r4 H1: the run token ignores the PROMPT, so two different reviews become one run
KILL  attr=True  | r4 H1: the run token ignores the HEAD, which is the r3 incident's own shape
KILL  attr=True  | r4 M5: the refusal testifies to the very path it is protecting, destroying it
KILL  attr=True  | r4 M2: a git that cannot be run is reported as a repository successfully built
KILL  attr=True  | r5: the run token ignores the TREE, so one brief over two trees is one run
KILL  attr=True  | r5: 'could not describe the tree' collapses into 'the tree was clean'
KILL  attr=True  | r5: the tree is hashed in dict order, so one tree can split into two runs
KILL  attr=True  | r5: the run token narrows back to the 32-bit namespace a collision was found over
```

### Claims 1, 2, 3 — driven, not read

`run_token` called directly (`scripts/codex-review.py:224-288`):

```
TOKEN_HEX = 16
len: 16
A!=B: True | A!=clean: True | None!=clean: True
  order probe  same-token: True    [('a','1'),('b','2')] == [('a','1'),('b','2')]
  quote probe  same-token: False   [("a'b",'1')]  vs  [('a"b','1')]
  smuggle      same-token: False   [('a', "1'), ('b")]  vs  [('a','1'),('b','')]
```

- **Claim 1 (the tree is in the token): TRUE.** Two trees at one head and one brief are two tokens.
- **Claim 2 (`None` ≠ `{}`): TRUE.** `_nodesc != _clean`, driven.
- **Claim 3 (`repr(sorted(...))` is a safe canonical form): TRUE for the live type.** The smuggle
  probe — a value containing `'), ('`, which is what would be needed to impersonate a second entry
  — does **not** collide, because `repr` escapes the quote. `repr` of a `list[tuple[str, str]]` is
  injective. The field is also delimited: `head` + `\x00` + marker + `repr` + `\x01` + prompt, and
  `repr` always opens `[`, so no field can bleed into its neighbour.
  Off the annotated type it degrades rather than lying: `{1: "a", "b": "c"}` raises `TypeError` from
  `sorted` (loud), `{"a": 1}` hashes (silent) — neither reachable from `reviewed_state`, which
  builds `dirty[path] = f"{parts[1]} {parts[3]}"` at `scripts/codex-review.py:596`.

### Claim 6 — `main` refuses an empty prompt: TRUE on every path

`scripts/codex-review.py:893-897`:

```python
    prompt = args.prompt
    if args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
    if not prompt:
        ap.error("provide a prompt argument or --prompt-file")
```

The `--prompt-file` read happens **before** the check, so an empty file yields `""` and is refused
there too. (A whitespace-only file is not refused — `"\n"` is truthy. That is not a collision: two
distinct whitespace prompts still hash apart, and it is not a claim `6cfae34a` makes. Noted, not
filed.)

### Claim 5 — the docstring no longer overclaims: **FALSE.** See H1 and M2.

This is the one claim of the seven that measurement refutes outright. Evidence in H1.

### Gates

All run at HEAD `17c21ecd`, live against the repo:

| Gate | Result |
|---|---|
| `codex-review.py --self-test` | rc=0, 119/119 |
| `check-plan-code.py --self-test` | rc=0, 130/130 |
| `check-selftest-counts.py --self-test` / LIVE | rc=0, 18/18 / rc=0, 46 scripts verified by running |
| `check-ratchet-contract.py --self-test` | rc=0, 41/41 |
| `check-review-rounds.py --self-test` / LIVE | rc=0, 29/29 / rc=0, 332 parsed, 0 silent gaps, 183 verdicts |
| `check-docs.py --self-test` / LIVE | rc=0, 22/22 / rc=0 |
| `check-plan-file-tags.py --self-test` / LIVE | rc=0, 44/44 / rc=0, 0 across 1442 documents |
| `check-dashboard-entry.py --self-test` / LIVE | rc=0, 13/13 / rc=0 |
| `check-anchors.py --self-test` | rc=0, 15/15 |
| `check-backlog-closure.py --self-test` | rc=0, 20/20 |
| `check-review-recorded.py` LIVE | **rc=1** — expected: it is the gate that convened this round, and it clears when r5's halves land |

### The `63093d7f` machinery — nothing regressed

`refusal_verdict_path` (`:317`), `verdict_collision` (`:334`) and `path_is_tracked` are untouched by
`6cfae34a` (`git show 6cfae34a -- scripts/codex-review.py` shows edits only in the `TOKEN_HEX`
block, `run_token`, the `main` call site and the self-test). Their five mutations still kill and
attribute — rows 1–5 of the table above.

---

## What I could NOT verify — treat as NOT RUN

- **`check-plan-code.py --mutate .` — 53 files / 990 mutations / 990 killed / 0 survivors, rc=0.**
  The brief forbids the ~14-minute sweep, which the coordinator ran at `6cfae34a`. **I did not run
  it. I have NOT independently verified that figure.** What I did verify independently is the
  *arithmetic* it rests on (990 = 990, 25 = 25, 53 = 53, above) and that the nine new entries kill
  and attribute — not that the other 981 do.
- **Nothing was executed against a live Codex CLI.** Every claim about dispatch behaviour below is
  derived from the code and driven through the pure functions, not from a real run.

---

## Findings

### H1 — High, structural: the docstring now states TWO different identities for one function, and the phrase the commit says it deleted is still there as a positive claim

**Premise.** `6cfae34a`'s claim 5, in its own commit message:

> *"The docstring no longer claims 'cannot collide'. It states the bound: a pure function of
> (head, tree, prompt)…"*

and in the code it added (`scripts/codex-review.py:255-256`):

> *"⛔ **r5 (Codex half) — THE FIRST VERSION OF THIS SAID "cannot collide" AND THAT WAS AN
> OVERCLAIM, IN TWO DIFFERENT WAYS. Both are fixed here; the claim is now bounded rather than
> absolute.**"*

**Measurement.** `grep -n "cannot collide" scripts/codex-review.py` returns four lines. Two are the
note recording that it was the defect (`:214`, `:255`) and one is a case name (`:1423`). The fourth
is a live positive claim, in the same docstring, **twenty-five lines above the paragraph that says
it was removed** — and `git show 6cfae34a` leaves it untouched (the hunk is `@@ -244,12 +251,41 @@`;
these lines are context, not additions):

```
scripts/codex-review.py:246-250
    **What the identity is, stated so a reader can predict it:** the same HEAD and the same prompt
    text yield the SAME token. That is deliberate — re-running one review is the same run and should
    land on its own testimony rather than accumulating debris. Two DIFFERENT reviews, which is the
    H1 scenario, differ in prompt text and so cannot collide however `--out` is named. A review of a
    different commit differs in HEAD, which is the r3 incident that cost a restore.
```

Against `scripts/codex-review.py:274-278`, added by the same commit:

```
    ⚠ **WHAT THIS STILL CANNOT DO, said out loud instead of being discovered later:** it is a pure
    function of `(head, tree, prompt)`. …
```

Three separate defects in that surviving paragraph, each checkable:

1. **"the same HEAD and the same prompt text yield the SAME token" is now FALSE.** Driven:
   `run_token("abc123","same brief",{"scripts/x.py":"M"}) != run_token("abc123","same brief",{"scripts/y.py":"M"})`
   — same head, same prompt, two tokens. This is the sentence explicitly offered *"so a reader can
   predict it"*, and a reader who predicts from it is wrong about the function's headline property.
2. **"cannot collide" is still asserted.** The commit message and the code comment both state that
   the phrase was removed because it was an overclaim. It was removed from one paragraph and left
   standing in another, about the same function, on the same axis.
3. **"re-running one review is the same run and should land on its own testimony rather than
   accumulating debris" no longer describes production.** The token now varies with the whole
   working tree — `reviewed_state` stages `add -A` with no pathspec (`:571-572`), and
   `verdict_record`'s own note at `:459-460` says the entries *"are the whole working tree (`add
   -A`, no pathspec)"* — so any edit
   anywhere in the repo between two dispatches of one brief produces a second verdict path. Debris
   accumulation is now the *normal* outcome of a re-run, and the paragraph still promises the
   opposite.

**Why High, and why that is the branch's own scale rather than mine.** The Codex High this commit
folded was graded High for precisely this: its ⑵ says *"It was never the live hazard. THE DEFECT WAS
THE SENTENCE."* A false sentence in this docstring is, by the branch's own accepted precedent one
round ago, a High. Here there are three, in the function's *predict-it-from-this* paragraph, and one
of them is the literal string the commit claims to have removed. Not Blocking: no gate misreports
and no evidence is destroyed — the executable behaviour is correct (claims 1–3 verified green
above). The failure is that the artefact a reader reasons from now contradicts itself, in the round
convened to stop it overclaiming.

**Proposed fix (structural).** Delete `:246-250` and let `:274-278` be the single statement of
identity — one rule, one place. If the r4 paragraph's *rationale* is worth keeping (why re-running
one review should land on its own testimony), rewrite it under the new identity and say what changed:
a re-run lands on its own testimony **only if the tree has not moved**, which is a different and
weaker promise than the one the paragraph makes. Then add a case that fails when the docstring's
stated tuple and the hashed tuple disagree — e.g. assert `run_token`'s signature parameters against
a literal `("head", "prompt_text", "dirty")`, so adding or dropping an input without updating the
prose goes red.

---

### M1 — Medium, structural: the fix fixed ONE instance of the class it named; `VERDICT_DIR` is the same shape, still live, and it guards a stated safety invariant

**Premise.** `6cfae34a`'s claim 4 is that a case comparing against the constant it checks agrees
with any value that constant takes, and that the width case therefore carries a **literal 16**:

> `scripts/codex-review.py:1433-1437` — *"**A LITERAL 16, NOT `TOKEN_HEX` — AND THE SWEEP IS WHAT
> CAUGHT IT.** Written first as `(False, TOKEN_HEX)`, the width mutation SURVIVED … This literal is
> the OUTSIDE OBSERVER of the width, the same role the declared-sum literal plays in
> `check-plan-code`."*

The file already knew this class before r5. `scripts/codex-review.py:1560-1562`:

> *"r11 Low: `VERDICT_SCHEMA` was stamped into every record and asserted by nothing — deleting … the
> LITERAL is the point: comparing against `VERDICT_SCHEMA` would agree with any value it took."*

So this is the **second** time the class has been named and fixed as an instance.

**Measurement.** I mutated every module-level constant in `scripts/codex-review.py` over the green
119/119 control:

| Constant | Mutation | Result |
|---|---|---|
| `VERDICT_SCHEMA` | `2 → 3` | **KILLED** 118/119 — `the record states which schema it is, as a number a reader can check` |
| `ARTIFACT_ROOTS` | `("docs/reviews",) → ()` | **KILLED** 118/119 — `docs/reviews is watched even when --out is outside the repo` |
| `TOKEN_HEX` | `16 → 8` | **KILLED** (manifest entry, attributed) |
| **`VERDICT_DIR`** | `docs/reviews/verdicts → docs/reviews` | **SURVIVED — 119/119 passed, rc=0** |
| **`MIN_REVIEW_CHARS`** | `200 → 5` | **SURVIVED — 119/119 passed, rc=0** (see M3) |
| `ACCOUNT_FAULT_STATUSES` | drop `429` | **SURVIVED** (see L1) |

The two surviving *self-agreeing* cases are the ones that pass the constant back in as the
expectation:

```
scripts/codex-review.py:1403-1405
    chk("the default verdict lands INSIDE the repo, not beside --out",
        verdict_path("/tmp/anywhere/plan-x-r3-codex.md").startswith(
            os.path.join(REPO_ROOT, VERDICT_DIR)), True)

scripts/codex-review.py:1468
    _prot = os.path.join(REPO_ROOT, VERDICT_DIR, "codex-r3.verdict.json")
```

Both move with the constant. Contrast the case 60 lines earlier, which is correct and is the shape
the fix is imitating:

```
scripts/codex-review.py:1378-1379
    chk("docs/reviews is watched even when --out is outside the repo",
        os.path.join(REPO_ROOT, "docs/reviews") in watched_dirs("/tmp/elsewhere/out.md"), True)
```

**Why this one matters and is not merely a coverage number.** `VERDICT_DIR`'s value carries a
written, previously-paid-for invariant:

```
scripts/codex-review.py:209-211
# It is a subdirectory of `docs/reviews/` on purpose: `dir_snapshot` is non-recursive, so the
# wrapper's own verdict writes cannot register as agent intrusions into the artifact root.
VERDICT_DIR = os.path.join("docs", "reviews", "verdicts")
```

Under the surviving mutation, the wrapper's verdicts land at the top of `docs/reviews/`, which
`ARTIFACT_ROOTS` watches non-recursively. `ours` is `{out_name}` on the success path
(`:1012`) and `set()` on the failure path (`:1037`), and the failure path **`quarantine()`s created
files out of the repository** (`:1064`, and `docs/plugins.md`: *"on the FAILURE path,
`quarantine()` MOVED a concurrent half out of the repo"*). Two concurrent dispatches — the
documented dual-review topology — would then have run B quarantine run A's verdict. That is the
same evidence-destruction class this branch has now paid for three times, and it is asserted by
nothing.

It is worse than a single unasserted constant, because the value is **independently re-implemented
as a string literal in both of its consumers, with no cross-check**:

- `scripts/check-review-recorded.py:117` — `VERDICT_DIR = "docs/reviews/verdicts/"`
- `scripts/check-review-rounds.py:138` — `VERDICT_DIRNAME = "verdicts"`

Neither imports `codex-review`. A drift in any one of the three is silent in all three suites — the
repo's recorded *a second implementation of one rule drifts* shape, on the rule that decides whether
CI can find the testimony at all.

**Why Medium, not High.** The code is CORRECT today; I found no wrong behaviour, and the three
spellings currently agree (verified above). What is missing is the falsifier, on a branch whose
entire subject is making these invariants falsifiable — and the class was named and fixed as an
instance twice (r11, r5) with this occurrence untouched both times. Not High because nothing
misreports now; not Low because the failure mode is destruction of committed testimony.

**Proposed fix (structural).** Two parts, and the second is the class half:

1. Rewrite `:1405` and `:1468` to carry the literal path — `os.path.join(REPO_ROOT, "docs", "reviews", "verdicts")` — so a case is an outside observer of the constant, and add the
   manifest entry `VERDICT_DIR → os.path.join("docs", "reviews")` so `--mutate .` holds it.
2. Add one case that asserts the *invariant* rather than the value: the default verdict path must
   **not** be directly inside any `ARTIFACT_ROOTS` directory — i.e.
   `os.path.dirname(verdict_path(...)) not in watched_dirs(<anything>)`. That is the property
   (`assert the PROPERTY, not the mechanism`), and it survives a future move of the directory.
   Separately, have one of the three spellings import the others' and assert agreement, or state a
   `NO-CALLER:`-style written reason why three copies are acceptable.

---

### M2 — Medium, structural: the replacement for the overclaim is itself an overclaim, and it was introduced by this fix

**Premise.** The Codex High was *"the docstring claims it cannot collide"*. `6cfae34a`'s claim 5 is
that the docstring now *"states a bound … rather than 'cannot collide'"*. The bound it states:

```
scripts/codex-review.py:274-278
    ⚠ **WHAT THIS STILL CANNOT DO, said out loud instead of being discovered later:** it is a pure
    function of `(head, tree, prompt)`. Two dispatches agreeing on all three ARE the same run by
    every property this wrapper can observe, and they share a path deliberately. A caller who needs
    two distinct verdicts from one identity must pass `--verdict`.
```

**Measurement.** *"every property this wrapper can observe"* is false as written. The wrapper parses
and observes `--model`, `--timeout`, `--min-chars` and `--allow-overwrite`
(`scripts/codex-review.py:864-885`); `--model`, `--timeout` and `--min-chars` all change what the
dispatch does and none reaches the identity. Driven:

```
run 1 (gpt-5.5, --timeout 900)  -> reviews/verdicts/obs-r5-codex.2aedfb61514f9c58.verdict.json
run 2 (gpt-5.4, --timeout 1800) -> reviews/verdicts/obs-r5-codex.2aedfb61514f9c58.verdict.json
same path: True
collision refusal when UNTRACKED: None
collision refusal when TRACKED  : ['REFUSED — the verdict path derived from --out is already TRACKED: …']
```

`verdict_collision` refuses only a **tracked** path (`scripts/codex-review.py:358-373`), so the
second run silently replaces the first's untracked verdict.

**Why this is a live path and not a hypothetical.** The re-dispatch this describes is the repo's
*documented* recovery, at `docs/plugins.md:146`:

> *"⛔ EXCEPT a TIMEOUT, usually your own `--timeout`: **DOUBLE IT and re-run once first.**"*

and the same file's `codex … -m "$(python3 scripts/codex-frontier-model.py)"`. Doubling the timeout
or forcing a slug, against the same prompt file at the same head over the same tree, is a
**same-identity re-dispatch by construction**. Its verdict lands on the previous run's path, and the
previous run's testimony — `gate_ran`, the timeout reason, the attempt list — is gone. That is
exactly the indistinguishability the verdict mechanism exists to abolish, re-opened for the one path
the process tells people to take.

**Why Medium, not folded into H1.** H1 is about sentences the fix failed to remove; this is about
the sentence the fix *wrote*, and it has a live consequence H1 does not. The loss is bounded — it
reaches only *untracked* verdicts (a committed one is refused), and the surviving record is usually
the later, more informative one — which is why it is Medium rather than High. But a bound that does
not name what it excludes is not a bound, and this one was introduced by the round convened to stop
this function overclaiming.

**Proposed fix (structural, two options — I recommend (a)).**

- **(a)** Make the sentence true by narrowing it, not by widening the identity: replace *"by every
  property this wrapper can observe"* with *"by `(head, tree, prompt)` — deliberately NOT by
  `--model`, `--timeout` or `--min-chars`, so the documented doubled-timeout retry lands on the same
  path and replaces the earlier verdict"*, and say whether that replacement is intended. A bound is
  only a bound if it names what it excludes.
- **(b)** If replacement is *not* intended, fold `args.model` / `args.timeout` / `args.min_chars`
  into the token — but that changes the retry contract and needs the user's call, so (a) first.

Either way, add a case: two `run_token` calls are equal **because and only because** head, tree and
prompt match — today nothing asserts the exclusion, so (b) could be done silently and no case would
notice.

---

### M3 — Medium, structural: `MIN_REVIEW_CHARS`, the value that decides whether the gate ran, is unpinned over [3, ≥300]

**Premise.** `MIN_REVIEW_CHARS = 200` (`scripts/codex-review.py:68`) is the threshold `classify`
uses to decide whether a final message is a review or a report of one
(`scripts/codex-review.py:747`, `:793`). It is the file's central judgement.

**Measurement.** Binary-searched over the green control:

```
MIN_REVIEW_CHARS=0    rc=1 110/119     MIN_REVIEW_CHARS=150  rc=0 119/119
MIN_REVIEW_CHARS=1    rc=1 118/119     MIN_REVIEW_CHARS=199  rc=0 119/119
MIN_REVIEW_CHARS=2    rc=1 118/119     MIN_REVIEW_CHARS=201  rc=0 119/119
MIN_REVIEW_CHARS=3    rc=0 119/119     MIN_REVIEW_CHARS=300  rc=0 119/119
MIN_REVIEW_CHARS=10   rc=0 119/119
```

The suite is green at **3**. The cause is the same family as claim 4: the helper passes the constant
in as the argument, so the fixtures and the threshold move together —

```
scripts/codex-review.py:1229
        got, reason = classify(code, out, msg, MIN_REVIEW_CHARS, t_out, out_path=OUT)
```

— and no case is an outside observer of the value. At 3, a three-character final message classifies
as a real review and the wrapper writes it to `--out` and reports `gate_ran=true`: the
gate-fails-open condition this whole file exists to prevent.

**The class spans both files `6cfae34a` touched.** Same probe on `scripts/check-plan-code.py`, over
its green 130/130 control (staged with the full `HARNESS_TREE`, six entries, or the control is red):

| Constant | Mutation | Result |
|---|---|---|
| `PROGRESS_WIDTH` | `79 → 20` | KILLED 123/130 |
| `DIAGNOSTIC_WINDOW` | `400 → 40` | KILLED 121/130 |
| `MANIFEST_DIR` | `scripts/mutations → scripts/muts` | KILLED |
| **`SUITE_TIMEOUT`** | `120 → 3` | **SURVIVED — 130/130** |

`SUITE_TIMEOUT` is how long a spawned suite may run before the harness calls it dead; at 3 seconds
the sweep would report CANNOT RUN wholesale, and nothing goes red.

**Why Medium.** Pre-existing, not introduced by `6cfae34a`, and there is no evidence any of these
values is wrong today — which is why it is not High. It is Medium rather than Low because
`MIN_REVIEW_CHARS` is the single value that decides whether a review gate ran, it is the class the
round was convened over, and the round fixed one instance of that class without sweeping for it.

**Proposed fix (structural).** Two cases, both outside observers: one asserting a message of length
`199` is rejected and `200` accepted (literals, not the constant), and one manifest entry
`MIN_REVIEW_CHARS = 200 → MIN_REVIEW_CHARS = 5`. Same for `SUITE_TIMEOUT`. Then do the sweep once,
as a class: mutate every module-level constant in both files and file whatever else survives —
mechanically, in the way this finding was produced, rather than by noticing.

---

### M4 — Medium, structural: the optional `dirty` lets the r4 cases keep asserting the OLD identity, and one of them now asserts a property production no longer has

**Premise.** The fix's own ⑴ is that `dirty is None` and `dirty == {}` are different answers and
must not be collapsed (`scripts/codex-review.py:264-268`; `reviewed_state`'s `:538-540`, where a
null `dirty` routes `classify_verdict` to CANNOT RUN). The new parameter is nonetheless optional:

```
scripts/codex-review.py:224-225
def run_token(head: "str | None", prompt_text: str,
              dirty: "dict[str, str] | None" = None) -> str:
```

**Measurement, part 1 — the conflation is relocated, not removed.** Driven:
`run_token("abc123","same brief") == run_token("abc123","same brief", None)` → **True**. A caller
who omits the argument produces the "git could not describe the tree" token — by this file's own
rule the CANNOT-RUN answer — asserted as a positive fact by omission. The exact shape ⑴ was written
to prevent, moved from the hash body out to the signature.

**Measurement, part 2 — and it is already load-bearing in the suite.** The r4 cases were not
revisited, so they still call the two-argument form and both sides default to `None`:

```
scripts/codex-review.py:1419-1422
    _tokA = run_token("abc123", "review prompt A")
    _tokB = run_token("abc123", "review prompt B")
    _tokA2 = run_token("abc123", "review prompt A")
    _tokC = run_token("deadbee", "review prompt A")

scripts/codex-review.py:1427-1429
    chk("…and the SAME review re-run lands on its own testimony rather than accumulating debris",
        verdict_path("/tmp/one/r.md", run_id=_tokA)
        == verdict_path("/tmp/three/r.md", run_id=_tokA2), True)
```

That case passes because both tokens were taken with **no tree**. At the production call site
(`:939`) a tree is always supplied, and any edit anywhere in the repo between the two dispatches
gives the re-run a different path. So the case asserts "a re-run lands on its own testimony" over a
world the production caller never inhabits — a case passing for an ambient reason (the default
argument), about the very property H1's paragraph 3 shows production has lost.

**Why Medium, not Low.** I first graded this Low on the strength of "there is one production caller
and it passes the tree". Part 2 refutes that framing: the optional parameter is not merely a future
hazard, it is *currently* holding a case green whose stated subject has changed underneath it. It is
not High because no production behaviour is wrong and no gate misreports.

**Proposed fix (structural).** Make `dirty` a required positional parameter; pass it explicitly at
`:1419-1422`, `:1457` and `:1459`. A caller that forgets then gets a `TypeError`, not a wrong
answer — the same *loud rather than silent* principle `build_probe_repo`'s `git` parameter was added
for (`:378-390`). Then re-point the `:1427` case at the property it now means: a re-run at the same
head **over the same tree** lands on its own testimony, and a re-run over a changed tree does not —
two distinct inputs, which is the rule the paragraph at `:1417-1418` already states for this block.

---

### L1 — Low: `ACCOUNT_FAULT_STATUSES` membership is unasserted

**Measurement.** `ACCOUNT_FAULT_STATUSES = {401, 403, 429}` (`scripts/codex-review.py:76`) →
`{401, 403}`: **SURVIVED, 119/119**. The 429 case asserts only the outcome (`try_next`), not the
annotation the set produces at `:783` (*"(account-level — later models will likely fail too)"*),
which is the caller's signal that walking the candidate chain is pointless.

**Why Low.** Cosmetic — only guidance text changes; the control-flow outcome is asserted.
Transitional: fold it into M3's constant sweep rather than treating it separately.

---

## Verdict

**NOT CONVERGED.** 0 Blocking, 1 High, 4 Medium, 1 Low.

**The executable code is sound.** Claims 1, 2, 3, 6 and 7 all hold under measurement: the tree is in
the token, `None` and `{}` hash apart, `repr(sorted(...))` is injective for the live type and
resists the smuggling probe, `main` refuses an empty prompt on the `--prompt-file` path too, and the
counts reconcile (990 = 990, 25 = 25, 53 = 53) with all nine r4+r5 mutations killing and attributing
over a green 119/119 control. Nothing I ran contradicts the commit's description of what the code
does. No Blocking.

**What fails is what `6cfae34a` claims about itself, and it failed in the predicted place.** The
brief said to assume the fix contains a defect, as the three folds before it did. It does:

- **H1** — the docstring was not de-overclaimed. "cannot collide" is still a live positive claim at
  `:249`, twenty-five lines above the note announcing its removal; the paragraph offered *"so a
  reader can predict it"* now states an identity the code does not compute; and its promise that a
  re-run avoids accumulating debris is the opposite of what a tree-sensitive token does. Graded High
  on the branch's own precedent — the finding this commit folded was a High whose whole content was
  *"THE DEFECT WAS THE SENTENCE."*
- **M2** — the replacement bound is false in its own right: `--model`, `--timeout` and
  `--min-chars` are observable and excluded, so `docs/plugins.md`'s documented doubled-timeout retry
  is a same-identity re-dispatch that silently replaces an untracked verdict.
- **M1 + M3** — claim 4 named a class and fixed one instance. Mutating every module-level constant
  in the two files the commit touched finds three more survivors over green controls: `VERDICT_DIR`
  (self-agreeing, and it guards the quarantine invariant this branch has paid for three times),
  `MIN_REVIEW_CHARS` (green at 3 — the value that decides whether the gate ran), `SUITE_TIMEOUT`.
- **M4** — the optional `dirty` relocates ⑴'s conflation to the signature and is currently holding
  an r4 case green over a world production no longer inhabits.

All six findings sit in one component — run identity and verdict naming — and every one of them is
either caused by this round's own fold or is the class this round's own fold named. That is the
thrashing shape for a fourth consecutive round, and it is what the Phase 6 architecture review
already convened on this component exists to answer. **I would not merge on this round**, and I
would treat H1 and M4 as fold-now, M1/M2/M3 as the sweep the architecture review should absorb
rather than another round of instance repairs.

⚠ **Not independently verified by me:** `check-plan-code.py --mutate .` (990/990/0 survivors). Per
the brief I did not run it. Treat the coordinator's figure as the only evidence for it.
