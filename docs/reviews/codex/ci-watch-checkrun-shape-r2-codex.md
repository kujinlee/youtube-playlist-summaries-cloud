<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `2780b05a..93e3133a`. Commands executed; checkout unchanged. **No Blocking or High found. The deliverable carries Medium findings.**

**Blocking:** None found.

**High:** None found.

**Medium 1 — Concurrent clearing can crash the observer.**

Claim: shared per-sha state safely supports independent worktrees.

Location: `scripts/check-ci-watched.py:512`.

Command: an in-memory Python probe called `run_decide()` with a pending check, intercepting `Path.iterdir()` to delete the yielded record after enumeration and before the sorting key calls `stat()`. This reproduces another process’s `--clear`.

Output:

```text
concurrent --clear between enumeration and sorting:
FileNotFoundError [Errno 2] No such file or directory: '…/ci-watching.d/aaaaaaaa…'
```

The new read path has an unhandled filesystem race. A normal concurrent clear can replace the intended warning/verdict with a traceback. Snapshotting mtimes needs to tolerate disappearing records.

**Medium 2 — The corrected refusal still makes a false diagnosis.**

Claim: the near-miss branch applies when models are offered but none is listed.

Location: `scripts/codex-frontier-model.py:146`.

Command: imported `usable_models` and `refusal_message`, then supplied:

```json
{"client_version":"0.160.1","models":[
  {"slug":"hidden","priority":1,"visibility":"hide","supported_in_api":true},
  {"slug":"listed","priority":2,"visibility":"list","supported_in_api":false}
]}
```

Output:

```text
mixed cache usable: []
MOST LIKELY CAUSE: this Codex CLI is behind — models were offered but none is listed.
Run `codex update`, then re-run this.
```

A model **is listed**. The predicate establishes a visibility near-miss, not absence of listed models or CLI staleness. The correction retains the misleading diagnosis for mixed populations.

**Medium 3 — The vendor-meaning correction remains incomplete.**

Claim: the fold removed unsupported interpretations of `visibility`.

Locations: `docs/plugins.md:144`, `docs/dashboard-entries.md:14301`.

Commands: `git diff 2780b05a..HEAD -- docs/plugins.md docs/dashboard-entries.md`; opened the official `openai_models.rs`.

Output from the changed documentation:

```text
visibility governs the picker; supported_in_api says whether a model works
```

The official source says:

```text
Visibility of a model in the picker or APIs.
```

The fold itself correctly rejects the narrower interpretation at `docs/process-rationale.md:1023`, but retains it in the operator documentation and newly added dashboard prose. The source also describes API *support*, not guaranteed operation. [Official source](https://raw.githubusercontent.com/openai/codex/main/codex-rs/protocol/src/openai_models.rs)

**Low 1 — The measured anchor count belongs to the pre-fold tree.**

Claim: 1,414 anchors across 59 manifests.

Locations: `docs/backlog.md:267`, `docs/dashboard-entries.md:14388`.

Command: Python enumerated every manifest and counted every `edits` find-string, both from git objects and the checkout.

Output:

```text
2780b05a anchors 1414
HEAD anchors 1416
ANCHORS 1416 MANIFESTS 59 BAD []
```

The two added mutations increase the count. The delivered “now” measurement is stale, although every anchor currently binds exactly once.

**Low 2 — `--clear` reports success when HEAD is unreadable.**

Location: `scripts/check-ci-watched.py:1143`.

Command: in a temporary sentinel directory, created a record, patched `_run` to return `None`, and called `main(['--clear'])`.

Output:

```text
nothing to clear for ?
unreadable HEAD clear rc= 0 record remains= True
```

The operation cannot identify its target but reports QUIET success. Preserving other records is correct; reporting inability to clear would make the result truthful.

Additional verification:

- Fast checks: **82/82, 22/22, 178/178**, documentation integrity passed.
- Pruned copy: rsynced all six `HARNESS_TREE` paths, retained both subject manifests, reduced `EXPECTED_MUTATIONS` only in the copy. Output: **44 mutations, 44 killed, 44 attributed, 0 survivors**.
- Every subject `expect` matched exactly one case; checked through the real `parse_fail_names` consumer.
- `decide` executable AST is unchanged; all **six** `watching_sha` mutation entries are unchanged.
- Concurrent arms preserved both files. Mtime ties preserved each HEAD’s own arm; other-arm selection follows directory order.
- A file at `SENTINEL` degraded to WARN without crashing. Synthetic `bad/name` HEAD crashed the write path; real git-produced SHAs cannot contain `/`.
- Deleted-worktree records have no cleanup mechanism and remain eligible as other-arm explanations.
- PRs **364/366/367** each returned **12 rows, zero `state` keys**. The saved cache confirmed **0.142.5, two hidden models, no `gpt-6*`**.
- #250/#251/#252 all state falsifiers. #252 covers branch row #245’s proposal and adds attribution checking. `origin/master` ends at **237**; #364’s branch contains **238–248**. #251’s 🔴 is supported by #248’s removable failing verdict, but “gate-removing defect twice” overstates #241’s separate output-coverage defect.
- **48/48 document guards remains unverified.** The broader sweep had two 45-second timeouts; isolated retries were stopped without results. Other completed checks passed.

**NOT CONVERGED**
