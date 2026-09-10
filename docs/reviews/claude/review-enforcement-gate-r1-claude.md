# Adversarial review r1 — `check-review-recorded.py`, the zero-round gate (Claude)

## PROOF OF SUBJECT

Branch `review-enforcement-gate`, tip **`c1bb6b1c`** (`wip: the zero-round gate`), pinned outside the
repo with `git archive review-enforcement-gate | tar -x -C <scratch>/reg`:

```
scripts/check-review-recorded.py               b522d57af16acc1c  b522d57af16acc1c  MATCH
scripts/check-dashboard-entry.py               32acfa227452c52f  32acfa227452c52f  MATCH
.github/workflows/ci.yml                       1c222ed19288363a  1c222ed19288363a  MATCH
scripts/mutations/check-review-recorded.json   d9ab6d4b1a998f0b  d9ab6d4b1a998f0b  MATCH

$ git log --oneline origin/master..review-enforcement-gate
c1bb6b1c wip: the zero-round gate          (single commit, based directly on master)
$ python3 scripts/check-review-recorded.py --self-test    14/14 passed
$ python3 scripts/check-dashboard-entry.py --self-test   146/146 passed
```

I did not re-run the measurements already reported (the six-PR replay, the four manifest mutations).
Everything below is a fresh measurement against the pinned tree.

---

# R1 — HIGH. `GUARDED` misses `middleware.ts` and `.claude/settings.json`. The second one is the file that decides whether this project's hooks run at all.

**file:line** — `scripts/check-review-recorded.py`, `GUARDED` / `GUARDED_FILES`.

I enumerated every tracked file on the branch and asked the gate about each:

```
tracked files: 2030   unguarded: 1241
UNGUARDED files that are CODE/CONFIG by extension (14):
   <root>    12       .claude   1       types   1

   .claude/settings.json          middleware.ts             package-lock.json
   jest.config.ts                 jest.setup.ts             jest.integration.config.ts
   playwright.config.ts           playwright.cloud.config.ts playwright.prod.config.ts
   postcss.config.mjs             tsconfig.worker.json      types/index.ts
   settings.json                  skills-lock.json
```

Two of these are not edge cases.

**`middleware.ts` — 60 lines, and it runs on every request:**

```ts
export async function middleware(request: NextRequest) {
  if ((process.env.STORAGE_BACKEND ?? 'local') !== 'supabase') return NextResponse.next({ request });
  const supabase = createServerClient(url, anonKey, { cookies: {...} });
  const { data: { user } } = await supabase.auth.getUser();     // refreshes the session
  const pathname = request.nextUrl.pathname;
```

Session refresh, route classification, anon provisioning. `lib/` and `app/` are guarded; the file
that gates access to both is not.

**`.claude/settings.json` — 89 lines, and it is *entirely* hooks:**

```
top-level keys: ['hooks']
hook events:    ['PreToolUse', 'PostToolUse', 'Stop']
```

The gate guards `.claude/hooks/` — the shell scripts — and not the file that registers them. A
branch that unregisters `block-default-branch-push.sh`, `check-plan-gate.sh` and every other row of
`dev-process.md`'s *"What is mechanically enforced"* table changes exactly one path, and this gate
answers **"no guarded path changed — a review round is not required"**. That is a hole in the
enforcement layer this gate was written to complete.

Note also `tsconfig.json` is guarded and `tsconfig.worker.json` is not, and no `jest.*` or
`playwright.*` config is guarded while `tests/` is — the list is a hand-kept enumeration of a set
that has members it does not know about, which is the failure mode its own docstring diagnoses in
`GROUPS` two files away. `dev-process.md`'s axis, which the docstring cites, says *"…or any config"*.

**Fix shape:** add `types/`, `middleware.ts`, `.claude/`, and a suffix rule for `*.config.*` /
`tsconfig*.json` / lockfiles. Better, invert it: guard everything **except** a short exempt list
(`docs/`, `*.md` at root, `.screenshots/`), so the next new top-level directory is guarded by
default rather than by remembering.

---

# R2 — HIGH. A stacked branch inherits its parent's review document and passes.

**file:line** — `added_paths(base)` → `git diff --diff-filter=A $(merge-base base HEAD) HEAD`.

Measured with real git in a throwaway clone:

```
=== branch A: changes code AND adds a review doc ===
ok — review recorded: docs/reviews/claude/a-r1-claude.md

=== branch B: STACKED on A, changes code, adds NO review of its own ===
  files B added itself: lib/bbb.ts
  gate says (--base master_sim):
ok — review recorded: docs/reviews/claude/a-r1-claude.md
  ...and against its ACTUAL base feat-a:
FAILED — 1 guarded path(s) changed and no review round was recorded:
    lib/bbb.ts
```

Branch B changed `lib/bbb.ts`, reviewed nothing, and is cleared by a document that reviews A.

CI passes `--base "origin/$GITHUB_BASE_REF"`, so this is **correct whenever the PR targets its true
parent**. The reachable case is a PR based on another feature branch but opened against `master` —
which this project has already had happen once and recorded (*"a PR silently carried a whole other
PR"*, hence the `git log --oneline origin/master..HEAD` habit). In that configuration
`GITHUB_BASE_REF` is `master`, the merge base is `master`, and the parent's review doc satisfies
the child.

It also means the gate's honest contract is *"someone added a review document somewhere in this
range"*, not *"this branch was reviewed"*. The docstring's argument for not keying on the branch
name is sound — a subject name drifts — but "added in the range" is weaker than it reads, and the
range is not always the branch.

**Fix shape:** cheapest is to compare against `HEAD^` for the added-docs question as well as the
base, or to report which commits in the range contributed the review doc so a stacked pass is
visible rather than silent.

---

# R3 — MEDIUM. Every documented CANNOT RUN path exits **1**, not **2**. The sibling it copies exits 2.

**file:line** — `main()` has no exception handler; `changed_paths` / `added_paths` `raise
RuntimeError(...)`, and `--pr-body-file` is read with a bare `read_text`.

The docstring is explicit:

> *FAILS IF … git is absent, the base cannot be resolved, or the clone is SHALLOW -> exit **2**,
> CANNOT RUN. A shallow clone sees fewer commits and would report a confident, smaller diff.*

Measured:

```
  bad base                        rc=1   (expected 2)
  missing --pr-body-file          rc=1   (expected 2)  + FileNotFoundError traceback
  grep 'return 2|except' in check-review-recorded.py:  NONE
```

The sibling whose posture it copies:

```
  check-dashboard-entry bad base       rc=2
  check-dashboard-entry missing body   rc=2
```

So in CI a genuine violation and a gate that could not run are the same red, distinguished only by
whether a stack trace happens to appear in the log. `CLAUDE.md`: *"'Cannot run' is a FAILURE, never
a pass… it must fail loudly and say treat this as NOT RUN. Silence there is indistinguishable from
success and gets believed."* Here it is indistinguishable from *failure*, which is the less
dangerous direction but still leaves the shallow-clone case reporting a wrong reason.

There is no self-test case for any CANNOT RUN path.

**Fix shape:** wrap `main`'s body in `except RuntimeError as exc: print(exc, file=sys.stderr); return 2`,
and give `--pr-body-file` the same treatment.

---

# R4 — MEDIUM. The shared parser's `head` scan point is unpinned for the new marker. Reverting it leaves both suites fully green.

**file:line** — `scripts/check-dashboard-entry.py`, `exemption_reason`, the two call sites.

**Answering item 5 directly: no existing behaviour changed.** Both call sites are threaded, the
default is `NO_ENTRY`, and `check-dashboard-entry --self-test` is 146/146 with `gen-dashboard.py`
untouched. The design is right.

But only one of the two scan points is covered with the new marker. Mutating the *other* one back to
a hardcoded `NO_ENTRY`:

| mutation | check-dashboard-entry | check-review-recorded |
|---|---|---|
| **MD1 revert the HEAD scan point** (line carrying an HTML comment) | **146/146** | **14/14** |
| MD2 revert the PROBE scan point (normal path) | 146/146 | 12/14 — killed |
| MD3 ignore the `marker` argument entirely | 146/146 | 12/14 — killed |

MD1 is behaviourally live, not dead code:

```
current code:
   NO-REVIEW plain                -> 'docs only'
   NO-REVIEW + trailing <!-- -->  -> 'docs only'

under MD1:
   NO-REVIEW plain                -> 'docs only'
   NO-REVIEW + trailing <!-- -->  -> None          <-- declaration silently ignored
   NO-ENTRY  + trailing <!-- -->  -> 'docs only'   <-- sibling marker still works
```

A PR body reading `NO-REVIEW: docs only <!-- agreed with the lead -->` would have its declaration
dropped and the branch refused, with a message telling the author to write the marker they already
wrote — and the asymmetry with `NO-ENTRY:` would be baffling. The three new cases exercise the plain
path, the fenced path and marker discrimination; none puts a comment on the line.

**Fix:** one case — `_reason_of("NO-REVIEW: docs only <!-- x -->", NO_REVIEW) == "docs only"`.

---

# R5 — MEDIUM. `GUARDED`'s coverage is pinned for `scripts/` and nothing else, because the case that looks like it covers the list iterates the list.

**file:line** — the case:

```python
    case("every guarded prefix is recognised",
         all(guarded_changes([g + "f.ts"]) for g in GUARDED), True)
```

It iterates `GUARDED` to test `GUARDED`. Delete an entry and the loop is shorter and still true — it
cannot observe a deletion, only a broken prefix match.

Mutations, control `14/14 passed`:

| mutation | result |
|---|---|
| **G1 drop `.agents/`** | **14/14 passed** |
| **G2 drop `tests/`** | **14/14 passed** |
| **G3 drop four of five `GUARDED_FILES`** | **14/14 passed** |
| G4 `review_added` drops the `.md` requirement | 13/14 — killed |
| G7 review doc checked against `changed` not `added` | 13/14 — killed |
| G8 prefix match → exact match | 9/14 — killed |
| G9 empty declaration passes | 13/14 — killed |

Only `scripts/` survives deletion-detection, and only because other cases use `CODE = ["scripts/x.py"]`
— incidentally, not by design. The shipped manifest's first entry pins that same one path. So the
gate's entire subject — the guarded set — can shrink to `scripts/` plus `package.json` with every
gate green, which is the *"a hand-kept list disagreeing with the table"* failure this repository has
now paid for in `GROUPS`, `KNOWN_GAP` and `LINK_SURFACES`.

**Fix shape:** name the paths explicitly rather than deriving them from the constant —
`guarded_changes(["tests/a.ts"]) == ["tests/a.ts"]`, one line per entry — or assert `len(GUARDED)`
alongside, so a deletion is a visible act. R1's inversion would make most of this moot.

---

# R6 — LOW. The empty-declaration refusal is pinned by exit code only, so its message can vanish silently.

**file:line** — `verdict`, `if reason is not None: return 1, f"{NO_REVIEW} was declared with no reason after it"`.

```
current : (1, 'NO-REVIEW: was declared with no reason after it')
mutated : (1, '1 guarded path(s) changed and no review round was recorded:\n...')
```

Deleting the branch entirely leaves `14/14 passed`, because the case asserts `verdict(...)[0] == 1`
and the fall-through also returns 1. The author who wrote `NO-REVIEW:` with nothing after it is told
they recorded no review — true, but not the thing they got wrong.

(The manifest's own *"an EMPTY NO-REVIEW: is accepted"* entry is a different mutation — `if reason:`
→ `if reason is not None:` — and that one is correctly caught. This is the message half.)

**Fix:** assert the tuple, as the neighbouring `NO-REVIEW:`-reason case already does.

---

# R7 — LOW. The rename bypass is real but config-dependent.

**Item 4 answered:** `--diff-filter=A` correctly refuses to accept a *modified* review doc — I
confirmed that. The edge is rename detection, which the gate inherits from ambient config rather
than pinning:

```
 diff.renames=true (git's default):
   FAILED — 1 guarded path(s) changed and no review round was recorded: lib/bbb.ts
   added-status paths: lib/bbb.ts

 diff.renames=false:
   ok — review recorded: docs/reviews/claude/a-r1-claude-moved.md
   added-status paths: docs/reviews/claude/a-r1-claude-moved.md lib/bbb.ts
```

With rename detection off, `git mv` of any existing review document satisfies the gate. Not the
default, and GitHub runners do not set it — latent. **Should a modification satisfy the gate?** No,
and the current choice is right: a second round appends a new file (`-r2-`), so requiring an
addition matches how rounds are actually recorded.

**Fix:** pass `--find-renames` explicitly so the behaviour does not depend on the reader's gitconfig.

---

# R8 — LOW. The CI step depends on a sibling step's `/tmp` side effect.

`check-review-recorded (PR only)` reads `/tmp/pr-body.md`, which is written by the preceding
`dashboard entry ratchet` step:

```yaml
      - name: dashboard entry ratchet
        if: github.event_name == 'pull_request'
        env: { BODY: ${{ github.event.pull_request.body }} }
        run: |
          printf '%s' "$BODY" > /tmp/pr-body.md
          python3 scripts/check-dashboard-entry.py …
      - name: check-review-recorded (PR only)
        if: github.event_name == 'pull_request'
        run: |
          python3 scripts/check-review-recorded.py … --pr-body-file /tmp/pr-body.md
```

Same job, same condition, correct ordering — it works today. But the review gate's ability to read a
`NO-REVIEW:` declaration is now a side effect of an unrelated gate, undocumented at the reading end,
and if the file is absent the failure is a traceback rather than CANNOT RUN (R3). On a self-hosted
runner a stale `/tmp/pr-body.md` would carry a *previous* PR's declaration.

**Fix:** write the body in the step that reads it, as the sibling does.

---

## Item 2 — what it obliges that it should not

I looked and did not find a meaningful over-obligation, which is worth saying plainly given backlog
#56's history. The candidate was the 40 `.md` files under `.agents/`, but a `SKILL.md` **is**
behaviour in this project — `docs/plugins.md` treats a vendored `SKILL.md` as layer 3 of an
enforcement mechanism and has a gate defending its contents. Guarding it is right.

The remaining pressure is a comment-only change to a script obliging a round, and `NO-REVIEW:` with
a reason is exactly the pressure valve backlog #56 says such a gate needs. The scope decision is
sound.

---

## Summary

| Severity | Count | Findings |
|---|---|---|
| Blocking | 0 | — |
| High | 2 | R1, R2 |
| Medium | 3 | R3, R4, R5 |
| Low | 3 | R6, R7, R8 |

**The gate is the right gate.** It asks the diff rather than a naming convention, it scopes by blast
radius, it shares the declaration parser instead of copying it, it echoes the reason into the log,
and its author deleted a constant rather than ship a case that could not see it — which is the
discipline three rounds on `brief-compose.py` were spent arguing for. The design decisions are all
the ones I would defend.

Every finding is in one place: **the gate knows its own logic and does not know its population.**

- **R1** — the guarded set is a hand-kept enumeration, and the two members it is missing are the
  request-path middleware and the file that registers every hook in the enforcement table this gate
  exists to complete. Inverting it to an exempt list is the structural fix.
- **R5** — that same set has no coverage: three of its entries delete cleanly at 14/14, because the
  case testing the list is written *over* the list.
- **R2** — "added in the range" is not "reviewed on this branch", and the range is not always the
  branch.
- **R3** and **R4** are one-line fixes with real consequences: CANNOT RUN is indistinguishable from
  a violation, and a `NO-REVIEW:` line carrying an HTML comment is unprotected.

R1 and R3 are the two I would fix before merge. Nothing here argues against shipping it — a gate
that catches three of three true positives with no false positives is worth having imperfect, and
the alternative measured on 2026-09-09 was five unreviewed merges in one night.

VERDICT: NOT CONVERGED
