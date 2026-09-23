# Adversarial review — the CI observer's warn log, ROUND 1 (Claude half)

Subject: `6a8a2fbc` on `ci-observer-log`.

**Method.** Every claim below comes from running something, on a **staged copy** — `scripts/` was
copied to a scratch tree and mutated there; nothing under `scripts/` was edited and no mutating
`git` command was run (`git status --porcelain` at the end shows only the concurrent Codex half's
`docs/reviews/verdicts/ciobs-r1-codex.verdict.json`). Children ran under a fresh `$HOME` and a cwd
outside the repo. **Control first:** the delivered file scores `42/42 self-test cases passed`, rc=0,
matching the `42 cases` declared at `:42`, and writes nothing into the staged tree, the fake `$HOME`,
or the real repo (`.claude/ci-unwatched.log` still does not exist). I did not run
`check-plan-code.py --mutate .`; instead I applied all five new manifest entries by hand to fresh
copies and recorded which cases went red, which is the same attribution rule
(`check-plan-code.py:1451`) over the same subject. `--mutate .` was not needed to reach any finding
here, and three of the six findings are outside the manifest's reach by construction.

## Findings

| # | Severity | Finding |
|---|---|---|
| 1 | **Blocking (PR)** | `check-dashboard-entry.py` refuses this branch — rc=1, no entry, no `NO-ENTRY:` |
| 2 | Medium | `:572` — the wire from the hook's stdin to `run_decide` has **no case**: two survivors |
| 3 | Medium | `RecursionError` escapes the payload handler, falsifying *"costs the column, never the verdict"* |
| 4 | Medium | The 7 new parameters were not pinned in `check-fixture-variation.EXAMINED_KEYS`; coverage can now leave them silently |
| 5 | Low | Closed stdin (`0<&-`) crashes with a traceback, and rc=1 collides with this script's own `WARN` |
| 6 | Low | `--decide` now blocks until EOF on an open stdin pipe |
| 7 | Low | `log_line` does not sanitise `session`: a tab yields six columns, a newline yields two records |
| 8 | Low | `warn_reason`'s `head_sha` is never read, and the `stale` entry omits the sha that was armed |
| 9 | Low | Three fallbacks unreachable on the WARN path, un-annotated in a file whose own convention requires it |
| 10 | Low | The suite's `WARN_LOG` redirect is incomplete — `_decide_with` is a second end-to-end driver that skips it |

---

### 1 — Blocking (PR): the dashboard gate refuses this branch

```
$ python3 scripts/check-dashboard-entry.py ; echo rc=$?
REFUSED — 4 tracked file(s) changed and no entry was added to docs/dashboard-entries.md. Add a
'## YYYY-MM-DD' block describing the change in plain words, or put 'NO-ENTRY: <reason>' in the PR body.
rc=1
```

`git diff --name-only origin/master..HEAD` is `.gitignore`, `scripts/check-ci-watched.py`,
`scripts/check-plan-code.py`, `scripts/mutations/check-ci-watched.json` — four tracked files, no
entry. `docs/dev-process.md` lists this guard as mechanically enforced. **This is procedural, not a
design defect: one entry closes it.** It is listed first only because it is the single thing that
refuses *today*, and the lead asked what blocks a PR.

### 2 — Medium: `:572` is the wire the whole payload change exists for, and nothing reads it

The branch's headline argument is that a session column which is always `-` is *"a column that
cannot vary — the data-level form of a case that cannot fail"* (`:253-256`). The line that makes it
vary is the last one in the file:

```python
sys.exit(run_decide(sys.stdin.read() if not sys.stdin.isatty() else ""))
```

Measured on fresh copies, self-test only:

| Mutation of `:572` | Result |
|---|---|
| *(control)* | rc=0, **42/42** |
| `sys.exit(run_decide(""))` | rc=0, **42/42** — SURVIVOR |
| `... if sys.stdin.isatty() else ""` (guard inverted) | rc=0, **42/42** — SURVIVOR |

Both leave the delivered behaviour silently degraded to what the commit message calls the defect:
the hook pipes a payload (`block-idle-stop.sh:149`), `isatty()` is False there, the inverted guard
therefore yields `""`, and every log entry gets `-` forever. `_drive_log` calls `run_decide(payload)`
**directly**; no case ever reaches the dispatch. The manifest's fifth entry — *"the Stop payload is
ignored"* — mutates `session = str(json.loads(payload)...)` **inside** `run_decide` and is killed;
the layer one line further out is not covered.

This is the file's own recorded lesson repeated at the next layer out. `:413-422`, added by a
previous round, reads: *"THE RULE ABOVE WAS COVERED AND THE CALL SITE WAS NOT, which is this repo's
recorded unit coverage does not compose — mutate the CALL SITE."* That comment is in this file, and
this commit adds a new call site beneath it without one.

**Why Medium and not High:** it cannot change a verdict, cannot lose a warning, and the failure is
self-announcing in the artifact (a column of all `-`) — the same tell the commit describes.

**Smallest fix:** factor `:572` into a testable `_payload_from(stream)` (or `main(argv, stream)`) and
give it two cases — a non-tty stream carrying `{"session_id": …}` and a tty stub — plus a manifest
entry anchored on the new function.

### 3 — Medium: `RecursionError` escapes the handler the comment promises

`:261` catches `(ValueError, TypeError, AttributeError)`, beside the comment *"an unreadable payload
costs the column, never the verdict"* (`:262`). Measured, piping `"[" * 200000 + "]" * 200000` into
`--decide` on the staged copy:

```
rc = 1
RecursionError: Stack overflow (used 16352 kB) while decoding a JSON array from a unicode string
```

It cost the verdict, not the column. The single defending case uses `payload="not json at all"`,
which lands in the `ValueError` member of the union — exactly the shape this file already paid for
and documented at `:408-411`: *"TWO DISTINCT EXCEPTIONS, because the handler catches a UNION and one
member is enough to satisfy a single-input case while the other is silently dropped."*

**Exploitability is nil** — the payload is Claude Code's own Stop JSON, not attacker-controlled — so
this is an undefended claim rather than a live hazard. But the claim is written in the code as a
guarantee, and a guarantee no case reads is what this repo calls an undefended claim.

**Smallest fix:** catch `Exception` (or add `RecursionError`) on that line, and add a second case at a
distinct union member.

### 4 — Medium: the 7 new parameters are unpinned, so coverage can leave them silently

`check-fixture-variation.py` is the guard that mechanically enforces the ⭐ rule in the brief. It
passes (`625 parameter(s) examined across 57 file(s)`, rc=0) and it *does* analyse the new functions
live — `check-ci-watched.py` alone now reports `14 parameter(s) examined`, up from the **7** pinned in
`EXAMINED_KEYS` (`decide.head_sha`, `decide.rows`, `decide.watching_sha`, `parse_sentinel.text`,
`render_sentinel.sha`, `render_sentinel.when`, `unresolved_checks.rows`). The branch adds exactly
seven more (`warn_reason.watching_sha`, `warn_reason.head_sha`, `log_line.{reason,detail,when,session}`,
`run_decide.payload`) and does not pin them.

The pin is only compared in **one** direction — `pinned - keys` at `:931-937`. An arrival is enforced
at file level (`population_drift`) but not at key level, so nothing fired. Control/treatment, single-file
mode, on staged copies:

| Variant | Guard says |
|---|---|
| control | `OK — 14 parameter(s) examined` |
| `decide` → `_decide` (**pinned**) | `FAILED — 3 parameter(s)`: ``decide.head_sha`` … *"was examined and is NOT any more"* |
| `warn_reason` → `_warn_reason` (**new**) | `OK — 12 parameter(s) examined` |

So coverage leaving the new code — a rename, a privatisation, a lost call site — is detected for the
seven old keys and **silent** for the seven this commit adds. The guard's own header at `:286-290`
states the convention this misses: *"pinned in the commit that adds it — this guard refused it until
it was."*

**Smallest fix:** add the seven keys to `EXAMINED_KEYS['check-ci-watched.py']`, derived by running
`python3 scripts/check-fixture-variation.py scripts/check-ci-watched.py`, not transcribed.

### 5 — Low: closed stdin crashes, and rc=1 is this script's `WARN`

```
$ python3 .../check-ci-watched.py --decide 0<&-
AttributeError: 'NoneType' object has no attribute 'isatty'   (line 572)
rc=1
```

Before this commit `--decide` never touched stdin, so `0<&-` was harmless. rc=1 is `WARN` in this
file's own vocabulary (`:43`), so a crash is indistinguishable from a legitimate warning by exit code
— and the hook maps any non-zero to the same non-blocking error. The production caller always pipes,
so this is latent. Both siblings share the hole (`check-banner-armed.py:2543`,
`check-closing-table.py:1653` both call `sys.stdin.read()` unguarded), so fixing it here alone
introduces the divergence the commit's `log_line` argument is at pains to avoid — worth doing across
all three, or not at all.

### 6 — Low: `--decide` now blocks until EOF

Measured: spawned with `stdin=PIPE` left open, the process was still alive after 3s; closing the pipe
produced rc=0 immediately. `block-idle-stop.sh:149` uses `printf … | python3`, which closes, so this
does not fire today. It matters because `:39` documents `python3 scripts/check-ci-watched.py --decide`
as a bare command; under an interactive terminal `isatty()` saves it, but under any non-tty,
non-closing stdin (a wrapper, a CI step, a tool harness — this review's own Bash tool reports
`isatty: False` on a live stdin object) it hangs.

### 7 — Low: `log_line` does not sanitise the externally-sourced `session`

```python
>>> log_line("unwatched", "1 unresolved on aaaa", "T", "s\tinjected\tcols")
'T\ts\tinjected\tcols\tunwatched\t1 unresolved on aaaa\n'   # 6 columns, not 4
>>> log_line("unwatched", "d", "T", "s\nsecond-line")
'T\ts\nsecond-line\tunwatched\td\n'                          # 2 records, not 1
```

`session` is the only field that comes from outside the process. `session_id` is a UUID in practice,
so this is a contract hole rather than a live corruption. `check-banner-armed.py:636` is byte-identical
and has the same hole; same caveat as #5 — fix the family or neither.

### 8 — Low: `warn_reason`'s second parameter is never read, and the `stale` entry loses the armed sha

AST-verified: `warn_reason` declares `['watching_sha', 'head_sha']`; the only names its body
references are `{'str', 'watching_sha'}`. `head_sha` is unread. Separately, `detail` is
`f"{len(...)} unresolved on {(head or '?')[:8]}"` — it records HEAD and never `watching_sha`, so a
`stale` row cannot say **which** commit was armed, and one-push-stale is indistinguishable from
ten-pushes-stale. The parameter that would carry that is present and ignored. Either drop `head_sha`
or put the armed sha in `detail`.

Note this does **not** invalidate the two-distinct-inputs cases at `:448-457`: the operand that
decides the class, `watching_sha`, is varied across the pair (`"deadbeef"`→`"1111111"`, `None`→`""`).
Only the ignored parameter's variation is theatre.

### 9 — Low: three unreachable fallbacks, un-annotated

On the WARN path, `decide` has already guaranteed `head_sha is not None`, `rows is not None` and
`pending` non-empty (`:101-110`). So `rows or []` (`:295`), `head or '?'` (`:295`) and `head or ""`
(`:299`) are all unreachable — no input can distinguish them from `rows`, `head`, `head`. That is
fine as defence, but this file's convention is to **say so**: `:85-88` carries an explicit *"DEFENSIVE,
not decisive, and deliberately not mutation-tested … NO input can tell the two apart"* note for the
one pre-existing instance, and `check-plan-code.py:681` cites that note. Three new instances arrived
without one.

### 10 — Low: the suite's `WARN_LOG` redirect is incomplete

`_drive_log` redirects `WARN_LOG` correctly, and the brief's fear does not materialise on the
delivered code — I verified nothing is written anywhere. But `_decide_with` (`:423-442`) is a **second**
end-to-end driver of `run_decide` that patches `_pr_checks_raw` and `_skip_reason` and **not**
`WARN_LOG`. Today its two call sites return QUIET and CANNOT_RUN, so the write is never reached. Under
the manifest's own third mutation (`if code == WARN:` → `if True:`) it fires, and I measured the
resulting file:

```
.claude/ci-unwatched.log   ->   2026-09-22T18:14:12-07:00	-	unwatched	0 unresolved on ?
```

`head=None`/`0 unresolved` identifies it as `_decide_with(None, False)`. **Contained in practice**:
`check-plan-code.py:159-161` records that `shutil.copytree` makes `ROOT` resolve inside the staged
tree, and `WARN_LOG` derives from `ROOT`, not `$HOME` — so the `$HOME` redirect is irrelevant here and
the copy boundary is what protects the reader. The residual risk is a future third `_decide_with` case
with a pending row, which would append to the real `.claude/ci-unwatched.log` with nothing to notice.
One line — adding `WARN_LOG` to `_decide_with`'s patched globals — removes it.

---

## Attacked, and found sound

- **The control, and the declared count.** `42/42`, rc=0, on a staged copy under a fresh `$HOME` with
  cwd outside the repo. `check-selftest-counts.py` reports `45 script(s) declare a count, every one
  verified by running it`, rc=0, and `check-ci-watched.py` is a pinned member (`:105`).
- **The attribution rule, all five new mutations.** Each applied by hand to a fresh copy; each goes
  red; each `expect` string matches **exactly one** RED case name by exact equality — 39/42, 36/42,
  41/42, 41/42, 41/42 respectively. No anchor was ambiguous (each `old` string occurs exactly once).
  `len(manifest) == 19 == EXPECTED_MUTATIONS["scripts/check-ci-watched.py"]` (`check-plan-code.py:684`),
  and `check-plan-code.py --self-test` is `128/128` with the declared sum `944`.
- **The QUIET/WARN contrast is real and can fail.** The brief's suspicion that it passes for an ambient
  reason does not hold: `if code == WARN:` → `if True:` takes the suite to 41/42 red on exactly the
  QUIET case and nothing else. It is the contrast, not the ambient absence of a file, that fails.
- **`stale` is reachable end to end, not merely as a unit call.** `_drive_log(_PENDING, "sha: 0000…")`
  drives the real `run_decide` through `parse_sentinel` → `decide`'s `watching_sha == head_sha` branch
  → the log write, and the recorded class is `stale`. Collapsing `warn_reason` to one class reddens
  both the unit case and that end-to-end one. The sibling's recorded failure — a class the log cannot
  express — is not reproduced here.
- **The redirect, for the delivered code.** Nothing appeared in the staged tree, the fake `$HOME`, or
  the real repo; `.claude/ci-unwatched.log` does not exist after every run in this review. Finding 10
  is a conditional residual, not a live leak.
- **`WARN_LOG` as an indirection is defended.** Replacing it at the write site with a literal
  `ROOT / ".claude/ci-unwatched.log"` reddens 2 cases — the redirect cannot be quietly bypassed.
- **The payload cannot change the VERDICT** (setting aside finding 3's crash). `json.loads` returning
  an int, a string, `null` or a list all land in the `AttributeError` arm; the measured
  `"not json at all"` case stays WARN and still logs. An absent or `/dev/null` stdin gives rc=0.
- **Both sibling claims in the commit message are literally true.** `check-banner-armed.py:636` is
  byte-identical to `check-ci-watched.py:169` (`{when}\t{session or '-'}\t{reason}\t{detail}\n`), and
  the unwritable-log choice matches `check-banner-armed.py:1167-1171` in substance and wording.
  `check-closing-table.py:866` is the genuinely different fourth grammar the commit says it is.
- **The `.gitignore` claim.** `.claude/banner-warnings*.log` is at `:102`, above `:118` as stated, and
  `git check-ignore -v` confirms `:118` is the rule that fires on the new path.
- **The "third `log_line`" judgement — I agree, and would not accept a consolidation in this slice.**
  `check-vocabulary-collisions.py --self-test` is 10/10 green; matching the sibling exactly is what
  keeps the three logs comparable, and #164/#165 own the design question. Inventing a fourth grammar
  to look tidy is the change that would make this worse.
- **The "false-alarm rate" argument survives the obvious objection.** Logging warnings only does not
  destroy the denominator: for a false-alarm *rate* the denominator is the warnings themselves,
  classified by hand — which is what the session column is for. Repeat entries across several stops of
  one pending CI are dedupable on `(session, sha8)` because `detail` carries the head sha.
- **Repo gate battery, all green:** `check-ratchet-contract.py` (40 guards) rc=0; `check-guard-coverage.py
  --self-test` 37/37; `check-docs.py` rc=0; `check-gate-falsifiability.py` rc=0;
  `check-producer-enumeration.py --self-test` 11/11; `check-review-rounds.py` rc=0;
  `check-fixture-variation.py` rc=0.

**VERDICT: NOT CONVERGED**
