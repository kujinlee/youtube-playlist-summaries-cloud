# Adversarial review — `review-identity-176`, round 1 (Claude half)

**Subject:** commit `4c29fe25` on branch `review-identity-176`, base `origin/master` = `b2e10e39`.
Backlog #176 — the review's testimony gets a supplied identity (`--review-id`), the wrapper performs
the promotion, `--verdict` is retired, and the `--out`-derived verdict namespace and its allocator
are deleted.

**Mandate:** refute, not confirm. The design (settled by the Phase 6 architecture review and three
decisions with the repository owner) is **not** re-litigated here; only the build is.

**Counts:** 1 Blocking · 1 High · 5 Medium · 2 Low

**Verdict: NOT CONVERGED.**

---

## What I verified GREEN, by running it

Every command below was run from the repo root at `4c29fe25` with a clean tree. Exit codes were read
directly, never through a pipe (`cmd | tail; echo $?` reports *tail's* status — the false green this
session has already produced three times).

### The three pre-committed falsifiers, driven against the shipped functions

```
$ python3 - <<'EOF'   # imports scripts/codex-review.py and scripts/check-review-rounds.py
...
EOF
== FALSIFIER 1: two reviews, same documented --out shape ==
  A: .../docs/reviews/verdicts/subject-x-r1-codex.verdict.json
  B: .../docs/reviews/verdicts/subject-y-r1-codex.verdict.json
  distinct: True
  verdict_path signature params: ['review_id']

== FALSIFIER 3: unclassifiable / non-half ids ==
  'plan-x-r3-gpt'              -> who=None refused=True
  'plan-x-codex'               -> who=None refused=True
  'plan-x-r3-coordinator'      -> who=None refused=True
  'plan-x-r3-codex.md'         -> who=None refused=True
  ''                           -> who=None refused=True
  'r'                          -> who=None refused=True
  'plan-x-r3-codex'            -> who='codex' refused=False
  'plan-x-codex-r3'            -> who='codex' refused=False
  'plan-x-r3-claude'           -> who='claude' refused=False
  'plan-x-claude-r3'           -> who='claude' refused=False

== FALSIFIER 2: gate_ran=false, review IS filed ==
  master-shape record review field: r.md
  branch-shape record review field: subject-x-r1-codex.md
  problems under scratch name: 0
  problems under supplied id  : 1
```

Falsifier 2 is the measurement the slice exists for, and it holds: **0 → 1**, driven through the
shipped `check-review-rounds.verdict_problems`, not a copy of it. `verdict_path` takes exactly one
parameter and there is no `--out` and no override left in it.

The refusals name both accepted shapes, are `rc=2`, and no path defaults to a writer — I drove the
CLI too: `--review-id x-r1-gpt` → `rc=2`, message naming `<subject>-r<N>-<writer>` **and**
`<subject>-<writer>-r<N>`; `coordinator` refused separately with its own sentence.

### The import, not a copy

```
$ grep -rn "endswith(\"-codex\|endswith(\"-claude" scripts/     -> no matches
$ grep -rn "codex|claude" scripts/*.py
scripts/check-review-rounds.py:75:    re.compile(r"^(?P<subject>.+)-r(?P<round>\d+)-(?P<who>codex|claude|coordinator)\.md$"),
scripts/check-review-rounds.py:76:    re.compile(r"^(?P<subject>.+)-(?P<who>codex|claude|coordinator)-r(?P<round>\d+)\.md$"),
scripts/check-review-rounds.py:87:    r"^[*_>#\s-]*REVIEW GAP:[*_\s]*(codex|claude)\b[*_\s]*[—–-][*_\s]*(\S.*?)[*_\s]*$",
```

One owner. `codex-review.py:103-104` binds `parse_review_name = _rounds.parse` and
`HALVES = _rounds.HALVES`; there is no private suffix rule anywhere in `scripts/`, inline or
otherwise. This is the single best thing in the change.

### The r7 self-reference guard, re-armed without a measured false positive

`classify` now receives the promotion path. I checked the arming against the real corpus rather than
reasoning about it. Over every filed review whose **first line is the wrapper's own
`<!-- codex-review: model=… -->` marker** — i.e. a verbatim capture, not a hand-assembled document:

```
pure wrapper captures (marker is line 1): 251
of those, body names its own basename:    0
```

So the newly armed guard does not retroactively reject a single real capture. (The 27 review files
in the wider corpus that *do* contain their own basename all carry it in a provenance header a human
added **after** promotion — `**Dispatched with** … --out …/schema-gates-ci-r1-codex.md` — which was
never part of the captured message. I checked that before counting it as a finding, and it is not
one.)

### The promotion does not trip the wrapper's own intrusion detector

Driven in a sandboxed copy of `scripts/` whose `REPO_ROOT` resolves to a scratch tree, under the
**documented** call shape (`--out` in a `mktemp -d`):

```
watched:     ['/var/folders/.../tmpXXXX', '<sandbox>/docs/reviews']
promoted to: <sandbox>/docs/reviews/codex/y-r1-codex.md   exists: True
intrusions:  []
```

`dir_snapshot` uses `os.listdir` + `os.path.isfile`, so neither the promoted file nor the writer
directory created for it can appear. The docstring's claim is true **under the documented shape** —
see M5 for the condition it does not state.

### The ratchet FALL is deliberate and re-derives exactly

Loaded both manifests rather than reading the commit message:

```
manifest entries: base 28 -> head 29
retired: 13   added: 14   kept: 15
```

That is the commit's claim, exactly. Every retired entry mutates `run_token` / `TOKEN_HEX` /
`verdict_collision` / `path_is_tracked` / `refusal_verdict_path` / `build_probe_repo`, all of which
are gone, and the retired/added split is written at **both** sites
(`EXPECTED_MUTATIONS["scripts/codex-review.py"]` and the declared-sum case). The declared sum moves
994 → 995 and `check-plan-code --self-test` passes, so the sum is consistent with the dict.

⚠ One retirement is not as clean as it reads — see **B1**.

### Deleted-symbol sweep

```
$ grep -rn "run_token|TOKEN_HEX|verdict_collision|path_is_tracked|refusal_verdict_path|build_probe_repo" \
    --include=*.py --include=*.sh --include=*.yml .
```

Six hits, all in `scripts/check-plan-code.py` (lines 1071-1074, 3616, 3634-3639), all inside
annotated retirement notes. No stale executable reference, no comment describing deleted machinery
as if it were live. The branch's signature defect did not occur.

### Suites and gates

| Command | rc | Result |
|---|---|---|
| `python3 scripts/codex-review.py --self-test` | 0 | 124/124 |
| `python3 scripts/check-plan-code.py --self-test` | 0 | 131/131 |
| `python3 scripts/check-review-rounds.py --self-test` | 0 | 29/29 |
| `python3 scripts/check-fixture-variation.py --self-test` | 0 | 67/67 |
| `python3 scripts/check-review-rounds.py` | 0 | 333 rounds, 184 verdicts, era caveat printed |
| `python3 scripts/check-fixture-variation.py` | 0 | — |
| `check-ratchet-contract` / `check-selftest-counts` / `check-docs` | 0 | — |
| `check-producer-enumeration` / `check-plan-file-tags` / `check-anchors` | 0 | — |
| `check-gate-falsifiability` / `check-dashboard-entry` | 0 | — |
| `check-guard-coverage` (`PGCONTAINER=m4_schema_gates M4_PHASE=post`) | 0 | real Postgres |
| `check-vocabulary-collisions` (same env) | 0 | real Postgres |

⛔ **`check-plan-code.py --mutate .` was NOT run by me.** The coordinator reports 53 files, 995
mutations, 995 killed, 995 attributed, 0 survivors, rc=0 at this commit. **I have not independently
verified that figure and it should not be read as though I had.**

---

## Findings

### 🔴 BLOCKING — B1. The refusal destroys the committed testimony it exists to protect, and then makes the new join key accuse the review it destroyed the evidence for

**Premise.** `write_verdict` (`scripts/codex-review.py:587-601`) opens the verdict path with `"w"` —
unconditional truncate, no existence check, no policy. `verdict_path(review_id)` is now a pure
function of the id, so a second run with the same id targets the same committed file. And on the
branch, `emit` — which writes that file — is reached **from the refusal path itself**:

```python
# main(), :1002-1015
for _path, _exists, _what in ((args.out, ...), (dest, os.path.exists(dest), "the promoted review")):
    _refusal = overwrite_refusal(...)
    if _refusal:
        print(...)
        return emit(2, gate_ran=False, reason=f"refused: {_what} already exists ...")
```

**Measurement.** Driven end-to-end in a sandboxed copy (`scripts/` copied to a scratch tree so
`REPO_ROOT` resolves there; no model is contacted, because the refusal precedes `resolve_candidates`).
Pre-state: a real filed review `docs/reviews/codex/x-r1-codex.md` and its committed testimony:

```json
{ "gate_ran": true, "exit_code": 0, "review": "x-r1-codex.md",
  "reason": "final message is a real review (4821 chars)", "model": "gpt-5.5", "schema": 2 }
```

Then the same review id is dispatched again — the case the refusal message itself invites
(*"Choose a different --review-id (or --out), or pass --allow-overwrite deliberately"*):

```
$ python3 <sandbox>/scripts/codex-review.py --review-id x-r1-codex --out "$(mktemp -d)/r.md" "review this"
[codex-review] REFUSING — the promoted review already exists: .../docs/reviews/codex/x-r1-codex.md
...
[codex-review] verdict: gate_ran=false -> .../docs/reviews/verdicts/x-r1-codex.verdict.json
rc=2
```

Post-state of the **same committed file**:

```json
{ "gate_ran": false, "exit_code": 2, "review": "x-r1-codex.md",
  "reason": "refused: the promoted review already exists and --allow-overwrite was not given",
  "model": null, "attempts": [], "schema": 2 }
```

The review it was about is untouched on disk. Now the *new* join key, driven through the shipped
consumer:

```
verdicts read: 1   reviews on disk: {'x-r1-codex.md'}
PROBLEM: x-r1-codex.verdict.json: the Codex gate did NOT run (refused: the promoted review already
  exists and --allow-overwrite was not given), yet `x-r1-codex.md` is filed in docs/reviews/. A
  failed gate must not leave an artifact that reads as a completed one — delete it, or if it is a
  Claude review, name it as one and record a `REVIEW GAP:` line
problem count: 1
```

So one accidental re-dispatch (a) destroys committed testimony that a real gate ran, (b) replaces it
with testimony that it did not, and (c) turns `check-review-rounds` — newly able to join, because of
this very slice — into a red CI failure telling the reader to **delete a genuine adversarial review**.
`check-review-recorded.py` cannot see it either: it selects with `--diff-filter=A` (`:1220`), and an
overwritten verdict shows as **M**, not **A**.

**Why this is not a design objection.** Master had *two* independent mechanisms against exactly this,
and both were deleted in this commit as "retired with their subject":

- `verdict_collision(vpath, tracked=…, override_given=…)` refused outright when the verdict path was
  already **tracked** — *"Would writing here destroy COMMITTED testimony about a different run?"* — and
  it ran at `:967`, **before** `emit` was even defined at `:990`.
- `refusal_verdict_path` sent a refusal's own testimony to `<base>.refused.verdict.json`. The retired
  manifest entry names the hazard in one line:

```json
{ "name": "r4 M5: the refusal testifies to the very path it is protecting, destroying it",
  "edits": [["    return f\"{base}.refused.verdict.json\"", "    return vpath"]],
  "expect": "the refusal's testimony is never the path it is protecting" }
```

The retirement argument in `EXPECTED_MUTATIONS` is that these entries "mutated the ALLOCATOR for a
namespace derived from `--out`'s basename" and "that namespace is GONE". That is true of the
*allocator*. It is **not** true of the *hazard*: r4 M5's subject was never the allocator, it was the
invariant *a refusal must not write over the path it is refusing to disturb*. Deleting the id
derivation removed the allocator and left the invariant unguarded — and the branch then added a new
refusal (`dest` exists) that violates it. Two of the thirteen retirements were therefore retirements
of a live subject, which is the one kind of fall the repo's own rule does not sanction.

**Proposed fix (structural).** Give the verdict the same one-policy treatment the review and the
capture got. Either:

1. route the refusal paths' testimony to a path that is *not* the one being protected (restore
   `refusal_verdict_path`'s property, not its allocator); **or**
2. have `emit` call `overwrite_refusal` for `vpath` as well — refuse by default, yield to
   `--allow-overwrite` — so that the run that cannot proceed also cannot overwrite; **or**
3. both: refuse to start at all when `vpath` exists and `--allow-overwrite` was not given, which
   makes the whole re-dispatch a single deliberate decision.

Whichever is chosen, it needs a mutation entry whose `expect` restates r4 M5's sentence, because the
entry that used to carry it is gone. **Label: structural.**

---

### 🟠 HIGH — H1. `--review-id` is validated for its writer and its extension but not for being a single path segment, so a supplied id can file the review at the artifact ROOT, or where nothing can read it

**Premise.** `review_identity` refuses a `.md` suffix, an unparsable id, and a non-half writer. It
does not constrain the *subject*, and `check-review-rounds.PATTERNS` spells the subject `(?P<subject>.+)`
— which matches `/` and `..`. `promotion_path` and `verdict_path` then `os.path.join` that string
straight into a destination.

**Measurement** (driven against the shipped functions):

```
id='docs/reviews/codex/foo-r1-codex'      accepted: True  writer: codex
   dest   : <repo>/docs/reviews/codex/docs/reviews/codex/foo-r1-codex.md
   verdict: <repo>/docs/reviews/verdicts/docs/reviews/codex/foo-r1-codex.verdict.json

id='../foo-r1-codex'                      accepted: True  writer: codex
   dest   : <repo>/docs/reviews/foo-r1-codex.md          <-- THE ARTIFACT ROOT
   verdict: <repo>/docs/reviews/foo-r1-codex.verdict.json

id='../../escape-r1-codex'                accepted: True  writer: codex
   dest   : <repo>/docs/escape-r1-codex.md
```

Consequences, each against a shipped consumer:

- **`../foo-r1-codex` files the half at the top level of `docs/reviews/`** — the location
  `promotion_path`'s own docstring calls mechanically unreachable (*"ONE LEVEL DOWN, NOT THE ARTIFACT
  ROOT … A promotion written there would be indistinguishable from the agent's own guessed write"*),
  which `docs/plugins.md` declares a *"no-legitimate-writes zone while a Codex run is in flight"*, and
  which `quarantine()` moves out of the repository on the failure path. The added mutation entry
  `#176: the promotion writes into the artifact ROOT, where quarantine() moves it back out` guards
  the *code path* to that property; nothing guards the *input*.
- The verdict lands outside `docs/reviews/verdicts/`, where `read_verdicts` globs — so the run leaves
  **no testimony CI can read**, silently, on a run that exits 0.
- **`docs/reviews/codex/foo-r1-codex` files the half two levels down.** `check-review-rounds.review_files`
  reads the flat layout and **one** level of subdirectory (`:231-236`). The half is invisible, the
  round reads as having one reviewer, and the check fails for a review that exists.

**Why High and not Blocking.** It needs a malformed id, and the caller is trusted. But the id is a
*newly required* argument whose documented meaning is *"the filename this wrapper PROMOTES the capture
to under `docs/reviews/<writer>/`"* — and pasting the path you were just told about is the obvious
first mistake. The validator already anticipated the adjacent mistake (a trailing `.md`) and says so
in a full sentence; this one is the same class and is unguarded.

**Proposed fix (structural).** In `review_identity`, refuse any id containing `os.sep`, `/`, or a
`..` segment, with a sentence in the same register as the `.md` refusal (*"--review-id is a NAME, not
a path — the wrapper chooses the directory from the writer"*). Optionally belt-and-braces: assert in
`promotion_path` that `os.path.realpath(dest)` is under `os.path.join(REPO_ROOT, REVIEW_ROOT, who)`.
Add one mutation entry for the refusal.

---

### 🟡 MEDIUM — M1. The slice builds the join key and leaves the direction that needed it unused

**Premise.** `verdict_problems` fires on exactly one shape: `gate_ran == false` **and** the named
review **is** filed. The mirror — `gate_ran == true` and the named review is **not** filed — is
`continue`d at `:174-175`.

Before this change that mirror was unusable: the key was `r.md` for every run, so "not filed" was
true of practically everything. **Measured on the current corpus: 53 of 184 verdicts are in that
shape.** After the cutover it becomes a precise contradiction, and the branch itself creates the path
that produces it — the `perr` branch returns `emit(2, gate_ran=True, reason="…; NOT PROMOTED: …")`,
i.e. testimony that a real review exists under a name that is not on disk.

**Why Medium.** Not a defect in what shipped; a gap in what the shipped thing was for. The failure it
leaves open is a coordinator citing `gate_ran=true` for a round whose review was never filed — the
same species of false green #176 was convened over.

**Proposed fix (structural).** Add the reverse clause to `verdict_problems`, gated on the era (see
M2) so it does not fire on the 53 historical records, plus a mutation entry. The wrapper already
records `exit_code`, so the check can distinguish "gate ran, promotion refused" from "gate ran,
review filed".

---

### 🟡 MEDIUM — M2. The era boundary is prose with no machine representation and no falsifier

**Premise.** The whole correctness story for the 184 pre-existing verdicts is an **era caveat**: a
comment above `VERDICT_DIRNAME` and one `print` in `main`. Nothing in the data marks the era.

**Measurement.**

```
schema distribution across docs/reviews/verdicts: {2: 99, 1: 85}
```

`VERDICT_SCHEMA` is still `2` at `codex-review.py:263` and is unchanged by this commit — so
post-cutover records are indistinguishable from the 99 pre-cutover records that carry the same
number, by any reader and by `verdict_problems` itself. The one field whose *meaning* changed
(`review`, from "basename of a scratch path" to "the review's durable name") changed under a schema
version that says nothing happened.

And the caveat has **no falsifier**. `scripts/mutations/check-review-rounds.json` is byte-identical to
base (12 entries, `EXPECTED_MUTATIONS["scripts/check-review-rounds.py"] = 12`, unchanged), none of
them mentions the caveat, and `self_test` has no case for it — it lives in `main`, which `self_test`
returns before reaching. Deleting both the comment and the `print` goes green everywhere. This is the
shape `CLAUDE.md` names directly: *"Before adding a rule here, ask whether it can be a script."*

**Why Medium.** The caveat is honest and correct today. It is also the only thing standing between a
reader and a green line that means less than it says, and it is the single piece of this change that
nothing can hold in place.

**Proposed fix (structural).** Bump `VERDICT_SCHEMA` to `3` — the join-key semantics changed, which is
what a schema version is for — and have `verdict_problems`/`read_verdicts` treat `schema < 3` as
*not meaningfully checkable*, reporting the count rather than a prose sentence. That turns the caveat
into a derived number (which cannot go stale, cf. M3), makes M1's reverse check safe to add, and gives
the whole thing a mutation entry.

---

### 🟡 MEDIUM — M3. The `183 verdicts / 58 (32%)` measurement is wrong at the denominator and was copied into three more places, two of them shipped scripts

**Premise.** The corpus figure is stated in `scripts/check-review-rounds.py:151`,
`scripts/codex-review.py:430` and `docs/process-rationale.md:743` (and pre-existed in
`docs/backlog.md:204`, which this commit did not touch).

**Measurement.**

```
$ git ls-tree -r --name-only b2e10e39 docs/reviews/verdicts | grep -c '\.json$'   -> 184
$ git ls-tree -r --name-only 4c29fe25 docs/reviews/verdicts | grep -c '\.json$'   -> 184
$ read_verdicts(docs/reviews/verdicts)                                             -> 184 read, 0 unreadable
$ verdicts naming a review NOT filed                                               -> 58  (31%)
```

184 at base **and** at head, so `183` was wrong when it was written, at every site, and it was
propagated rather than re-derived. The `58` is right and the `32%` survives rounding; the denominator
does not. Separately, the denominator **moves on every run** — a verbatim copy inside a shipped
script comment is stale by construction, which is the *"a document inside the corpus it measures"*
shape this repo has already paid for.

**Why Medium and not Low.** The number now lives in the two scripts that are the producer and the
consumer of the join, and it is the stated evidence for the era caveat that M2 shows nothing else
holds up. An argument resting on a figure nobody can re-derive from the file it sits in is the exact
"inference stated as MEASURED" pattern.

**Proposed fix (transitional).** Either state it with its as-of (*"184 verdicts as of 4c29fe25"*), or
better, have `check-review-rounds` **print** the two counts it can compute at run time (verdicts read;
verdicts naming a review not filed) so the caveat carries a live number instead of a frozen one.

---

### 🟡 MEDIUM — M4. `rc=2` now covers two opposite outcomes, and the exit-code legend in `docs/plugins.md` — which `CLAUDE.md` imports — still describes only one

**Premise.** The new promotion-failure path returns `2` with `gate_ran=True`:

```python
# :1064-1069
return emit(2, gate_ran=True, reason=f"{reason}; NOT PROMOTED: {perr.splitlines()[0]}", ...)
```

The legend this commit rewrote says:

```
#   exit 0 = review written AND FILED  exit 1 = gate did NOT run → fall back  exit 2 = REFUSED / CANNOT RUN
```

And `docs/plugins.md`'s fallback rule — a few lines above — instructs a caller who gets CANNOT RUN to
*"immediately run a rigorous Claude adversarial review in Codex's place"* and to record a `REVIEW GAP:`.

**Measurement.** By reading the two together: a run in which a real Codex review **was** captured and
**is** intact at `--out`, but the destination already existed, exits 2. A caller following the
documented legend discards a paid-for Codex review, files a Claude one in its place, and records a
gap that did not happen. The wrapper prints a loud correction to stderr — but the documented contract
is the exit code, and the entire history in this file is of callers reading exit codes and losing
stderr.

**Why Medium.** No data is destroyed and the stderr message is good. The defect is that the contract
the rest of the process is built on no longer partitions the outcomes.

**Proposed fix (transitional).** Give the "gate ran, not filed" case its own exit code (e.g. `3`), or
state it explicitly in the legend and in the fallback rule: *"rc=2 with `gate_ran: true` in the
verdict means the review exists at `--out` — file it, do not fall back."* The verdict already carries
the distinguishing field; the legend just has to name it.

---

### 🟡 MEDIUM — M5. The "layout, not a predicate" argument for `quarantine()` is stated unconditionally but holds only while `--out` is outside `docs/reviews/`, and nothing refuses such an `--out`

**Premise.** Three places now assert the property as a fact of the layout:

- `unexpected_writes` docstring: *"neither the promoted review nor the directory created for it can
  appear here at all"*;
- the failure-path comment: *"review halves now land in `docs/reviews/<writer>/`, which this
  NON-RECURSIVE snapshot cannot see"*;
- `docs/process-rationale.md`: *"`quarantine()` on the failure path cannot reach it."*

But `watched_dirs(out_path)` starts with `os.path.dirname(os.path.abspath(out_path))`. If `--out`
points into a writer subdirectory, that subdirectory becomes watched — recursion has nothing to do
with it, and nothing validates `--out`'s location.

**Measurement.** Driven in the sandbox. A failing run whose `--out` was `docs/reviews/codex/capture-x.md`,
while a concurrent half was promoted into the same directory:

```
failure-path hits: [('concurrent-half-r9-codex.md', 'CREATED during the run (writer unattributed)')]
QUARANTINED: ['<sandbox>/docs/reviews/codex/concurrent-half-r9-codex.md']
victim still in repo? False
```

That is backlog #92's measured disaster — a legitimate concurrent half moved out of the repository by
the fallback path — reproduced against the **new** layout. A second drive showed the milder direction:
with `--out` in `docs/reviews/codex/`, the wrapper's own successful promotion is reported as
`CREATED during the run (writer unattributed)` — the self-accusation the docstring says would only
happen if someone made the snapshot recursive.

**Why Medium.** It needs a non-documented `--out`, so it is not reachable through the prescribed call
shape. It is Medium rather than Low because the change *makes the writer subdirectory the wrapper's
own output location*, which is precisely the argument someone will use for putting `--out` beside it,
and because three separate texts now state the safety property with no condition attached.

**Proposed fix (structural).** Refuse an `--out` whose directory is `REPO_ROOT/docs/reviews` or any
subdirectory of it — the documented shape already puts it outside the repo, so this refuses nothing
legitimate — and reword the three claims to name the condition they actually depend on (*"`--out` is
outside the artifact tree, which the wrapper enforces"*) rather than resting them on non-recursion
alone.

---

### 🟢 LOW — L1. The commit message's line-count claim is false in both magnitude and direction

```
$ git show b2e10e39:scripts/codex-review.py | wc -l   -> 1858
$ git show 4c29fe25:scripts/codex-review.py | wc -l   -> 1869
```

The message states `1858 -> 1755 lines`. The file **grew by 11**. Nothing downstream reads this
number (it did not leak into `docs/` or `scripts/` — I grepped), so it costs nothing mechanically; it
costs the commit message's credibility as a record, in a repo whose own rule is *derive, do not
recall*. **Transitional** — a message amendment.

### 🟢 LOW — L2. "the ERA CAVEAT, printed on EVERY run" is false

Stated in the commit message and again in `docs/process-rationale.md` (*"prints it on every run"*).
The `print` is at `check-review-rounds.py:462`, after both early returns: `main` returns `1` on
`problems` (`:443`) and `2` on `verdicts_bad` (`:452`) without reaching it. It prints on the **rc=0
path only**.

Behaviourally that is the path that needs it most, so the code is defensible and only the claim is
wrong. But the claim is load-bearing for M2's argument that the caveat cannot be missed — and a
reader hitting a red run is exactly the reader most likely to be re-reading the verdict corpus.
**Transitional** — either correct both sentences, or move the `print` above the early returns.

---

## What I could not finish

- **`check-plan-code.py --mutate .` — NOT RUN by me.** Excluded by the brief (~14 min). The
  coordinator's figure (53 files / 995 mutations / 995 killed / 995 attributed / 0 survivors / rc=0)
  is **NOT INDEPENDENTLY VERIFIED** in this review. Everything I say about the manifest comes from
  loading the JSON and from `check-plan-code --self-test` (131/131), not from a mutation run. In
  particular, I did **not** confirm that each of the 14 added entries is killed by the case it names.
- **`test:integration` / `test:e2e` — not run** (need a live Supabase stack). Out of this change's
  blast radius; recorded rather than silently skipped.
- **No live `codex exec` run.** Every drive above uses the shipped pure functions or a sandboxed copy
  of `scripts/` whose `REPO_ROOT` resolves to a scratch tree. The refusal paths I drove end-to-end all
  return before `resolve_candidates()`, so no model was contacted and none was needed; the `perr`
  path (M4) I read rather than executed, because reaching it requires a real capture.
- I did not audit `docs/dashboard-entries.md` (+44) or `docs/roadmap-to-launch.md` (+13) line by line
  beyond confirming `check-dashboard-entry` and `check-docs` are green and that the deleted symbols
  appear there only as retirement notes.

---

## Verdict

**NOT CONVERGED.**

The core of the change is right and I could not break it: the identity is supplied, the grammar is
imported rather than copied, the three falsifiers all drive green against the shipped functions, the
r7 guard is re-armed with zero false positives over 251 real captures, the ratchet fall is deliberate
and re-derives exactly, and the deleted-symbol sweep is clean.

It does not converge on **B1**: the one path that exists to touch nothing is the path that overwrites
committed testimony, and the join key this slice built then turns that overwrite into CI telling a
reader to delete a real review. Master had two guards against precisely that, both retired in this
commit under an argument that covers their allocator and not their subject — and one of the retired
manifest entries states the violated invariant in its own `expect` field. **H1** lets the same
required argument that fixed the identity put the artifact somewhere no consumer can read, including
the one location the change's own docstring says is unreachable.
