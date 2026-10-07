# PR #367 round 1 — Claude (adversarial) half

**NOT CONVERGED.**

**⛔ THE DELIVERABLE CARRIES ONE BLOCKING AND TWO HIGH FINDINGS.** The Blocking is a measured
`NOT MEASURED` from the repository's own mutation harness, introduced by the *uncommitted
corrections* rather than by the committed change — the committed tree at `2780b05a` is clean.

| Severity | Count |
|---|---|
| Blocking | 1 |
| High | 2 |
| Medium | 4 |
| Low | 6 |

Subject: branch `ci-watch-checkrun-shape`, commit `2780b05a` **plus the uncommitted working tree**
(`docs/backlog.md`, `docs/dashboard-entries.md`, `docs/plugins.md`, `docs/process-rationale.md`,
`scripts/check-ci-watched.py`, `scripts/codex-frontier-model.py`). Every command below was run
inside the worktree at
`/Users/kujinlee/.claude-tmp/.../cacb274e-.../scratchpad/wt-ciwatch` unless stated. No repository
file was edited except this review document; no `git add`, commit or push.

---

## Blocking

### B1 — The uncommitted corrections orphan a mutation anchor, so the harness reports `NOT MEASURED` for `codex-frontier-model.py`

**Claim under attack:** that the corrections are comment-and-prose only and leave the measured
coverage intact (the dashboard entry closes with Codex's `42 entries, 42 killed, 42 attributed,
0 survivors`).

Entry 6 of `scripts/mutations/codex-frontier-model.json` anchors on the **pre-correction** text of
the refusal's cause line:

```
"    bits.append(\"  MOST LIKELY CAUSE: this Codex CLI is behind, and the server keys the model list \"\n                \"to client_version. Run `codex update`, then re-run this.\")"
```

The uncommitted diff rewrote that call (moved it inside `if near:` and changed its wording,
`scripts/codex-frontier-model.py:127-130`). `scripts/mutations/` was **not** touched —
`git status --short` lists no manifest.

**Ran** (anchor count, the harness's own rule `src.count(find)` at `scripts/check-plan-code.py:1952`):

```
anchor count in WORKTREE source: 0
anchor count in COMMITTED HEAD source: 1
```

**Ran** a scoped `--mutate .` on a pruned copy (six `HARNESS_TREE` paths, manifests reduced to
`codex-frontier-model.json`, `EXPECTED_MUTATIONS` reduced to that one file), 2.5 s:

```
[6/7] the refusal stops naming `codex update`, leaving the reader with a predi…
  ✗ mutation 'the refusal stops naming `codex update`, leaving the reader with a predicate and no action': anchor NOT FOUND — it was not applied, so its 'caught' verdict would be meaningless
NOT MEASURED — the mutation harness produced no coverage verdict (6 of 7 declared mutation(s) produced a verdict). Treat this as NOT CHECKED. — measured over the WHOLE manifest
```

**Control, on the committed tree** (`git archive HEAD`, same pruning plus
`check-ci-watched.json`):

```
OK — delivered scripts mutated: 2 file(s), 42 mutation(s), 42 killed, 42 attributed to the case each names, 0 survivor(s) — measured over the WHOLE manifest
```

**Why this refutes:** the control proves the committed state is green and that the defect is in the
uncommitted corrections, not in the change being corrected. An eager binding pass over the whole
population confirms it is the only one:

```
A) WORKTREE manifests vs WORKTREE sources: 1414 anchors over 59 manifests in 65 ms — NOT FOUND 1, ambiguous 0
      unbound: ('codex-frontier-model.json', 6, 'the refusal stops naming `codex update`, leaving the reader ', 'NOT FOUND')
E) WORKTREE manifests vs COMMITTED HEAD sources: 1414 anchors, 61 ms, NOT FOUND 0, ambiguous 0
```

This is the **third** instance in one session of the class the same commit's dashboard entry
celebrates catching (`docs/dashboard-entries.md:14163-14168`, "A correct refactor orphaned two
PRE-EXISTING mutation anchors — the second time in one session"). The fix for instance two
produced instance three, and the pass that would have caught it is the one the entry says it ran.
Retarget entry 6 onto the new `bits.append` and re-run the scoped sweep; also re-confirm that
entry 6's `expect` (`...and the one command that changes any of it`) still dies by that case now
that `codex update` prints only in the near-miss branch.

---

## High

### H1 — "the 0.142.5 cache no longer exists to compare against" is false. It is on disk, and I read it

**Claim under attack:** the stated *reason* for downgrading the server-side-cause claim to an
association. Three places in the deliverable:

* `scripts/codex-frontier-model.py:75-77` — "the 0.142.5 cache no longer exists to compare against"
* `docs/process-rationale.md` — "the 0.142.5 cache no longer exists to compare against, so the
  before/after is an **association**"
* `docs/dashboard-entries.md` — "the 0.142.5 cache cannot be re-read"

**Ran:**

```
$ ls -la ~/.codex/models_cache.json*
-rw-r--r--@ 1 kujinlee  staff  423291 Oct  7 03:43 /Users/kujinlee/.codex/models_cache.json
-rw-r--r--@ 1 kujinlee  staff   83513 Oct  7 03:20 /Users/kujinlee/.codex/models_cache.json.bak-2026-10-07
```

```
BEFORE 0.142.5: models=2 listed=0 usable_models=[]
AFTER  0.160.1: models=10 listed=7 usable_models[0]='gpt-6.1-sol'
old etag: W/"92c9b584b253158d044898725382b89e"  fetched 2026-10-07T10:20:48.184424Z
new etag: W/"378a8a5ac1b8e3134512fa3b1669afcc"  fetched 2026-10-07T10:43:09.414260Z
any gpt-6* in the OLD server response? []
   gpt-5.5            vis=hide  prio=13   api=True  Legacy coding model.
   codex-auto-review  vis=hide  prio=43   api=True  Automatic approval review model for Code
```

**Why this refutes, and why it matters in two directions:**

1. The **before** half of the model table — which the Codex half called unverifiable and this
   deliverable repeats as unverifiable — is verifiable and now verified: `0.142.5`, 2 models, 0
   listed, resolver refuses. The table is correct in both halves.
2. The correction **weakened a claim that the recovered evidence makes stronger**. The 0.142.5
   response contains no `gpt-6*` entry at all, so the difference is in the **server's payload**,
   not in local filtering by the old client — which is more than "an association between updating
   and a different result". What remains genuinely unestablished is narrower: whether the key is
   `client_version` or something that changed for this account in the 23 minutes between
   `10:20:48Z` and `10:43:09Z`. That sentence is both honest and better evidenced than either the
   original overclaim or the correction.

No repository script writes the `.bak` (`grep -rn "bak-" scripts/ .claude/hooks/` over
codex/models_cache terms: no hits), so it is the CLI's or the operator's — either way it was one
`ls` away. Codex's own wording was careful ("unverifiable **from the current cache**"); the
deliverable widened it to a statement about the world. That is this repo's
`a-framing-widened-to-fit-is-no-longer-a-claim`, applied to the evidence for a correction.

### H2 — The shared sentinel holds ONE sha, so two worktrees clobber each other — re-creating the false "nothing is watching", with a false explanation

**Claim under attack:** `scripts/check-ci-watched.py:84` — *"Where the armed-watcher record lives.
ONE PER REPOSITORY, shared by every worktree"*, and `:93` — *"one file there is shared by
construction"*, offered without a cost.

`render_sentinel` (`:280`) writes a single `sha:` line and `run_watching` (`:530`) **overwrites**
the file. One record cannot represent two worktrees watching two different commits.

**Ran** — a two-worktree sandbox with the delivered script copied in:

```
=== A HEAD: d5ff519   B HEAD: ee2bbc9
--- arm in A (main tree)
recorded: a watcher is armed for d5ff5192. A new push un-arms it by design.
    sentinel: sha: d5ff519226c5546856be9eaa35ddb8c0ed173364
--- arm in B (linked worktree)
recorded: a watcher is armed for ee2bbc93. A new push un-arms it by design.
    sentinel: sha: ee2bbc9386cd5bb2f4d182a512fe4874d7554ca0
```

A's record is gone. What A's Stop hook then prints, while A's watcher is armed and streaming:

```
A HEAD     = d5ff5192    sentinel records = ee2bbc93
warn_reason= stale
⚠ CI is running on d5ff5192 and nothing is watching it — 1 pending: verify
  (a watcher is armed for ee2bbc93, but HEAD is now d5ff5192 — a new push un-arms it BY DESIGN, so that one no longer covers this commit)
```

**Control — the same scenario on `origin/master`'s per-worktree code:**

```
A's file: sha: f98e745b...  (A HEAD f98e745)
B's file: sha: 517a4be2...  (B HEAD 517a4be)
shared .git/ci-watching exists? no
```

**Why this refutes.** The deliverable's purpose is "the warning no longer lies". The relocation
fixes *arm-here, hook-there* and introduces *arm-here, arm-there*: the identical user-visible
failure — "nothing is watching it" over a commit that is in fact watched — plus a causal sentence
that is now false, because no push occurred. This is not hypothetical here:

```
$ git worktree list     # 7 worktrees, 6 linked, each on a different branch
$ git rev-parse --git-common-dir   -> /Users/kujinlee/code/.../.git
SENTINEL = /Users/kujinlee/code/.../.git/ci-watching
content  = 'sha: 2780b05ada8faca650e73fea9b2da00179a69b42\n...'
```

The single shared record currently names *this* branch's HEAD, so every other live worktree's
`--decide` reads `stale` about a commit it never armed.

Two consequences the change also does not state:

* **The `stale` class now has a third cause its log cannot express.** `warn_reason` (`:245`) and
  the two-class argument above it exist so "promote to blocking?" can be answered per class — and
  the file's own precedent is `check-banner-armed.py`, whose log "keyed on `(step, total)` … so
  the banner-LESS class was unrecordable and its 76-entry history shows 0 of it". *Sibling worktree
  armed a different commit* is now indistinguishable from *I pushed again*.
* **`--clear` is cross-worktree destructive.** `main(["--clear"])` (`:1045`) unlinks the shared
  file, so clearing in one tree silently un-arms every other tree. (Only `--decide` has a hook
  caller — `.claude/hooks/block-idle-stop.sh:149` — so this one needs a human to type it.)

**Cheap fix, keeping the relocation:** make the record sha-keyed rather than single-valued — one
file per sha (`ci-watching-<sha>`) or a set of armed shas with `--decide` testing membership. The
sha-scoped design in the module docstring (`:21`) already implies set semantics; only the storage
is scalar. `sentinel_for` stays pure and unchanged.

---

## Medium

### M1 — "with the EXACT payload `gh` returned" is false, and the fixtures invent the key that chooses the branch

`scripts/check-ci-watched.py:578` (untouched by the corrections): *"⛔ THE REGRESSION CASE, with
the EXACT payload `gh` returned."* The four fixtures below it (`:581-588`) all carry
`"state": None`.

**Ran** — `gh pr view <N> --json statusCheckRollup`, four PRs, 47 rows:

```
=== PR 366: 12 rows
   keyset x12: ('__typename','completedAt','conclusion','detailsUrl','name','startedAt','status','workflowName')
   'state' key present: 0   present-and-None: 0
=== PR 367: 11 rows   'state' key present: 0   present-and-None: 0
=== PR 364: 12 rows   'state' key present: 0   present-and-None: 0
=== PR 365: 12 rows   'state' key present: 0   present-and-None: 0
```

```
keys gh returned that the fixture lacks: ['completedAt', 'detailsUrl', 'startedAt', 'workflowName']
keys the fixture invents: ['state']
```

And the two differ in exactly the quantity the corrected docstring is about:

```
BASE on LIVE PR366 rows: 12 of 12 unresolved
  intermediate for a live row: str(r.get('state','')).upper() -> ''
BASE on the SELF-TEST fixture: ['verify']
  intermediate for the fixture: 'NONE'
```

**Why this refutes.** The correction at `:160-167` rewrote the docstring precisely to stop
asserting the `"NONE"` path of a payload whose key is absent, and says conflating them "is the
defect class this repository tracks hardest". Four hundred lines down, the same conflation stands
*and is labelled EXACT*. Instance fixed, class not searched — the repo's own
`after-fixing-search-for-the-class`.

Coverage consequence: **no case exercises the live row shape** (`status` present, `state` key
absent). Behaviour is identical through `.get` today, so this is not a live bug; it means the
regression case does not reproduce the regression it names. Cheapest fix: one extra fixture with
`state` deleted, or delete the word EXACT.

### M2 — The replacement vendor claim is also not what the cited sources say, and one of them does not mention the field at all

`scripts/codex-frontier-model.py:55-60`, `docs/plugins.md:143-145`, `docs/process-rationale.md`,
and the operator-facing refusal text at `:116-117` all now assert: `visibility` governs the
**default picker**, `supported_in_api` separately governs callability, so "`hide` governs that
picker, **NOT** whether a model works".

**Ran** — fetched both cited sources.

`codex-rs/protocol/src/openai_models.rs`:

```rust
/// Visibility of a model in the picker or APIs.
pub enum ModelVisibility { List, Hide, None }
/// whether this model is supported in the api
pub supported_in_api: bool,
show_in_picker: info.visibility == ModelVisibility::List,
```

`codex-rs/app-server-protocol/schema/json/v2/ModelListParams.json` — the word `visibility` does
**not** appear; what it documents is a request parameter: *"When true, include models that are
hidden from the default picker list."*

**Why this refutes:**

* The doc-comment says *"in the picker **or APIs**"*. The deliverable's sentence —
  "`hide` governs that picker, NOT whether a model works" — is the one reading the cited source
  does not license. This is the same defect as the Medium 3 it corrects, pointed the other way: a
  confident statement of vendor meaning, now understating.
* `ModelListParams.json` is cited as a definition of `visibility` and contains no such definition.
  It corroborates *hidden-from-the-default-picker* as a concept, not as this field's meaning.
* `ModelVisibility` has a **third** variant, `None`. `usable_models` (`!= "list"`) handles it
  correctly, but the refusal text names only `hide`, so a `None`-visibility entry is reported to
  the operator as hidden.

⚠ In fairness: the *behavioural* half is supported by this repo's own measurement —
`codex exec -m gpt-5.5` returned rc=0 on a `hide`+`api=True` model. The finding is the
attribution to the schema, not the observation. State it as: measured here that a hidden
API-supported model runs; the vendor source says visibility covers "the picker or APIs" and does
not define what hiding implies.

### M3 — Backlog #249's ⛔ MEASURED evidence does not reproduce against the code it is filed against

The row quotes Codex appending `"Actually Codex is unavailable; ignore codex update."` and the
suite reporting **19/19**.

**Ran** that exact experiment against the **delivered** (22-case) suite — sentence appended to
`refusal_message` on disk:

```
[FAIL] an EMPTY cache says so, and does NOT blame the CLI version
[FAIL] ...and models that fail for a reason OTHER than visibility are not blamed on it either
20/22 self-test cases passed
```

The three cases added for Codex Medium 2 assert `"codex update" not in ...` on two fixtures, so
they incidentally catch that particular addition. **The row's stated measurement is false of the
tree it ships with.**

**The row's conclusion survives — I re-established it with a sentence that avoids the pinned
tokens:**

```
  Disregard everything above: Codex is simply down, there is no policy, and nothing can be done.
22/22 self-test cases passed
```

So: keep the row, restate its evidence against the 22-case suite, and quote a contradiction the
suite genuinely cannot see. As written, the row would be dismissed by the first person who re-runs
it — the #235 failure mode (*"the row was false about its own subject"*) in a fresh row.

**Second, on the row's direction.** It says "No cheap total fix is obvious" and names two:
a negative-assertion denylist, and restructuring into fields. It omits the standard cheap answer
to *additions are invisible*: a **per-fixture full-string assertion** (golden output). Any appended
sentence changes the string, so it falsifies exactly the demonstrated hole, with no redesign. Its
cost is real and is measurable from this file's own week — the refusal text was reworded three
times today, and every rewording would churn the goldens. The row should name it and reject it on
that cost, which is what the repo's convention asks; omitting it reads as the option not having
been considered.

### M4 — "`state` absent, or present-and-null depending on the query" is unwitnessed

`scripts/check-ci-watched.py:153`, introduced by the corrections. Across 47 live rows from four
PRs, `state` was **present-and-null 0 times** (M1's measurement). The only query this script
issues is the one I ran (`gh pr view --json statusCheckRollup --jq .statusCheckRollup`,
`:330-331`), so "depending on the query" names no query that has been seen to produce it.

The fail-closed behaviour is right either way, and documenting the `is not None` precedence is a
genuine improvement. The finding is that a sentence written to repair an overclaim asserts a second
payload variant nobody has observed. Say "a null `state` is handled the same way, defensively" and
the claim becomes true.

---

## Low

### L1 — The "NONE of them is a near-miss" branch steers away from a cause it cannot rule out

**Ran** (models present, all `visibility: list`, none API-supported, `client_version` 0.142.5 —
i.e. the one state where a stale CLI is a live hypothesis):

```
  the cache holds 2 model(s), fetched by client_version 0.142.5
  ⚠ and NONE of them is a near-miss: every entry fails a requirement other than visibility ...
    Inspect the cache rather than assuming the CLI is stale.
```

The *logical* half is sound — I could not construct a refusal where an entry fails visibility only
and this branch fires. The *advice* half asserts the negative of the cause Medium 2 objected to,
on no better evidence. Drop the final clause, or make it "the version may still be the cause".

### L2 — "MOST LIKELY CAUSE: this Codex CLI is behind" still prints when the version is unknown

```
  the cache holds 1 model(s), fetched by client_version ?
  MOST LIKELY CAUSE: this Codex CLI is behind — models were offered but none is listed. Run `codex update` ...
```

The diagnosis was made conditional on near-misses existing, not on the one datum it rests on being
readable. Gate it on `data.get("client_version")`, or soften it when the version is `?`.

### L3 — `tool_mode: code_mode_only` is cited as what marks `codex-auto-review` special-purpose; 9 of 10 cached models carry it

`scripts/codex-frontier-model.py:68-69` and the earlier dashboard entry both cite it.

```
tool_mode across the 10 cached models: {'code_mode_only': 9, None: 1}
listed models with tool_mode==code_mode_only: ['gpt-6.1-sol','gpt-6-astra','gpt-6-sol','gpt-6-luna','gpt-5.6-sol','gpt-5.6-terra','gpt-5.6-luna']
the model the resolver picks: gpt-6.1-sol tool_mode= code_mode_only
```

The field is carried by every listed model including the one the resolver selects, so it
distinguishes nothing. The argument that survives is the `description`
("Automatic approval review model for Codex."). ⚠ Note the inversion: the only model **without**
`code_mode_only` is `gpt-5.5`.

### L4 — `UNRESOLVED` now mixes two vocabularies, and `ACTION_REQUIRED` is both listed as unresolved and classified resolved

```
--- UNRESOLVED set: ['ACTION_REQUIRED','IN_PROGRESS','PENDING','QUEUED','REQUESTED','WAITING']
--- RESOLVED_STATES: ['CANCELLED','ERROR','FAILURE','NEUTRAL','SKIPPED','STALE','TIMED_OUT','SUCCESS']
  True   CheckRun COMPLETED + conclusion ACTION_REQUIRED
  False  state=ACTION_REQUIRED
  False  StatusContext EXPECTED (a real StatusState, in neither set)
```

Answering the mandate's question directly: **the `status` branch wins**, and for this guard's
question ("has it reached a verdict") that is the right answer — the run is finished. But
`UNRESOLVED` (`:137`) is only ever read by the `state` branch (`:192`), and of its six members only
`PENDING` is a value GitHub's `StatusState` can carry; the other five are `CheckStatusState` or
conclusion vocabulary. The documented justification at `:189-191` — catching "a future edit that
wrongly moves a pending state into `RESOLVED_STATES`" — therefore survives for `PENDING` alone.
Splitting the dispatch was the moment to split the sets per row type; worth one comment at minimum,
since a reader finds the file asserting both things about `ACTION_REQUIRED`. (`EXPECTED` →
unresolved forever is pre-existing and defensible: a declared-but-never-posted status is not a
verdict.)

### L5 — "3 unbound" is 2, and "437 ms" is not reproducible as stated

`docs/dashboard-entries.md:14166`: *"**437 ms** over every manifest, 3 unbound. Entries 1 and 3
retargeted"*. The correction entry fixes the adjacent "3 retargeted" to two and leaves "3 unbound".

**Ran** the pass over the whole population, with a control:

```
C) BASE manifests (ALL 58) vs the NEW worktree sources: 1402 anchors, 63 ms, NOT FOUND 2, ambiguous 0
      ('check-ci-watched.json', 1, 'the unknown-state fallback is dropped, so a state GitHu')
      ('check-ci-watched.json', 3, 'case folding is dropped, so a lowercase terminal state ')
D) BASE manifests vs BASE sources (control): 1402 anchors, NOT FOUND 0, ambiguous 0
```

Two, not three. ⭐ The authoritative site gets it right — `scripts/check-plan-code.py:4922`,
"⚠ TWO PRE-EXISTING ENTRIES WERE RETARGETED IN THE SAME COMMIT" — so only the narrative is wrong.
`437 ms` is a timing of an unspecified implementation; my equivalent pass is 63 ms over 1402
anchors and 65 ms over 1414. Label it as the figure that run produced, not as a property of the
pass, or drop it.

### L6 — The deliverable cites backlog #245 twice, and #245 does not exist on this branch

```
$ for id in 56 245 166 170; do printf "  #%s: " $id; grep -cE "^\| $id \|" docs/backlog.md; done
  #56: 1
  #245: 0
  #166: 1
  #170: 1
$ grep -n "#245" docs/dashboard-entries.md
14166:anchor-binding pass **backlog #245** proposes: ... 
14168:instances arguing for #245 rather than one.
```

`scripts/check-plan-code.py:4924` cites it too. Ids on this branch are 230-237 and 249; **238-248
exist only on `unify-explainer-style`** (PR #364, 11 rows) — the very collision #249 documents.
So the row that these two "measured instances" are arguing for is unreachable from master after
this merges. Either qualify the citation ("#245, filed on PR #364's branch") or move the argument
into #249's own row.

---

## Verified, with no finding

* **The regression fix is real and live.** `decide` over today's payloads: PR 366 `QUIET`,
  PR 364 `QUIET`, PR 365 `QUIET`, PR 367 `WARN` naming the 5 `IN_PROGRESS` shards
  (`mutation-sweep (2),(3),(4),(5),(8)`). Base code on PR 366: `12 of 12 unresolved`.
* **Fail-closed is intact**, contra the Codex half's wording: `status: ""` → unresolved,
  `status: False` → unresolved, `status: "TELEPORTING"` → unresolved, `{}` → unresolved, both
  fields null → unresolved. The only shapes that resolve are a `COMPLETED` status or a
  `RESOLVED_STATES` state.
* **`sentinel_for` is pure and reads `root`.** `--git-common-dir` from the main checkout is `.git`
  (relative) and from this linked worktree an absolute path; both land correctly. The relative
  branch is exercised at two distinct roots, per `check-fixture-variation`.
* **Declared counts, derived not read:** `origin/master` 58 files / sum **1394**; worktree 59 files
  / sum **1406**; on disk 59 manifests / **1406** entries; the pinned assertion at
  `check-plan-code.py:4940` is `1406`. `1394 → 1406` is right, and the provenance comments at
  `:4916` and `:4931` carry both moves. `check-ci-watched` **30 → 35** ✓; new manifest **7** ✓;
  **exactly 2** positional retargets (positions 1 and 3) ✓.
* **Suites:** base `58/58`, head `74/74`, declared `74` at `:42` ✓; committed resolver `19/19`,
  worktree `22/22`, declared `22` at `:13` ✓ (`19 → 22` is committed→worktree, both real).
  `check-selftest-counts.py`: *"52 script(s) declare a count, every one verified by running it"*.
* **`check-docs.py`: `Documentation integrity OK`.** ⚠ `docs/plugins.md` is at **260 of 260**
  lines — "tight", not over (`check-docs.py:655`); the next edit to that file blocks.
* **Live cache claims:** 10 models, 7 `list`, resolver returns `gpt-6.1-sol`; API-supported hidden
  are **exactly** `gpt-reserve`, `gpt-5.5`, `codex-auto-review`, as the docstring says.
* **`usable_models` ordering:** equal priorities preserve input order (`['z','a','b']`), boolean
  priority excluded (`True` → dropped), float priority accepted.
* **Every `expect` in both changed manifests resolves to exactly one case label** (7 of 7 checked
  by substring against the 22 labels; the ci-watched manifest's anchors all bind).

---

## Where the Codex half is wrong or overstated

1. **Medium 1 overstates its own output.** "This refutes dispatch 'on which field is PRESENT' **and
   fail-closed handling of all unknown shapes**." The first half is right. The second is refuted by
   its own printed table — `status: ''`, `status: False` and `{}` all returned `RESOLVED False`.
   Nothing in its evidence shows an unknown shape reading as done.
2. **Medium 3's unverifiability claim was careful; the deliverable's is not — but Codex still missed
   it.** Codex wrote "unverifiable **from the current cache**", which is literally true. It had just
   read `~/.codex/models_cache.json` and did not list the directory, where
   `models_cache.json.bak-2026-10-07` holds the 0.142.5 response (H1). Its conclusion
   "association, not proven cause" is defensible; its premise that the comparison cannot be made is
   false, and propagating the premise is what cost the deliverable three wrong sentences.
3. **Low 6's own arithmetic drifts.** It says "historical 1394/1399 totals likewise describe
   intermediate states". **1394 is `origin/master`'s shipped declared sum**, derived above — not an
   intermediate. 1399 is. The deliverable repeats the same mischaracterisation
   ("The 1394/1399 totals in the trail are intermediate drafts of this same commit").
4. **Its headline confirmation is now stale, and the review document does not say what tree it
   covers.** `42 entries, 42 killed, 42 attributed, 0 survivors` and "every anchor in both changed
   manifests matched exactly once" are true of `2780b05a` — I reproduced both — and **false of the
   working tree the coordinator then produced** (B1). A reader taking the Codex half as coverage of
   the shipped state would be wrong.
5. **Low 5 is right and is the model of a good finding** — it probed five repository shapes, found
   the wording wrong and the code correct, and said so. The deliverable's fix for it is accurate.
6. **Medium 4 is right in substance and its measurement is now stale** (M3): the experiment it
   quotes fails 2 of 22 cases on the delivered tree.

---

## What I could not check

* **The `437 ms` figure** (L5). It is a wall-clock timing of an implementation that is not in the
  repository, so it cannot be reproduced, only re-measured. Mine: 63-65 ms.
* **"a FRESH fetch returned exactly two models"** as a *fetch* event. The 0.142.5 payload is on
  disk (H1) and I verified its content, `fetched_at` and `etag`; I did not and cannot re-issue that
  request as client 0.142.5, so *whether the server keys on `client_version`* remains untested in
  both directions.
* **Whether `codex exec -m gpt-5.5` still returns rc=0.** I did not spend a Codex run; the
  behavioural claim about hidden-but-API-supported models rests on the earlier session's smoke test,
  which I have not independently repeated.
* **An unscoped `--mutate .`** (1,406 entries) — forbidden by the round's constraints. My mutation
  evidence is scoped to the two changed manifests on pruned copies, plus a whole-population anchor
  binding pass (which is a different, weaker instrument: it proves anchors bind, not that mutations
  die).
* **`test:integration` / `test:e2e`** — out of scope for this change, not run.
* **Whether GitHub ever emits `state: null` on a `CheckRun`** in some other query (M4). I measured
  the query this script issues, across 47 rows; I cannot prove a negative about every query shape.
* **Git hosting state**: I did not check whether `mutation-sweep-complete` is a required context, so
  I cannot say whether B1 would block the merge or merely report red.

---

**NOT CONVERGED** — one Blocking, two High.
