Reviewed head: f8bd907eb0c911d8c70c559a057defeb257f065d
# Round 4 — 627-serve-master (backlog #627) — Claude half (adversarial)

Codex half skipped this round by alternation (`REVIEW GAP: codex — alternation`).

Subject: commit f8bd907e only (`git diff d0d7eeee f8bd907e`): 14 `expect` strings in
`scripts/mutations/explainer-serve.json` and `scripts/mutations/regen-pages.json`, and two self-test
cases in `scripts/explainer-serve.py` (`_local_link`, `_through_handler`). The mandate was to refute.

## How I tested

1. **Every expect checked against the literal case names, not only the 14 changed ones.** I parsed both
   suites with `ast` (which joins implicit string concatenation) and collected the first argument of every
   `case(...)` call that is a string constant. Then I checked every `expect` in both manifests for
   exactly one match: 112 entries for explainer-serve, 72 for regen-pages.
   - All 14 changed expects match **exactly one** static case name.
   - 3 expects did not match a static name. All 3 belong to **unchanged** entries whose cases are
     f-strings, built in a loop: `explainer-serve.py:3155` (`a real {_secret!r} in the root is NOT servable…`),
     and `regen-pages.py:1691` (`…in git or not ({i})`) and `regen-pages.py:1813`
     (`the tree swapped for a symlink to {name} before removal…`). Their expects equal one expansion of
     the f-string. Commit f8bd907e did not change them, and the coordinator's full sweeps cover them.
   - None of the 14 old (prefix) expects is still in either file, so no entry with the same prefix
     defect was left unfixed.
2. **Both self-tests on the worktree** (it was at aebe685c, and that merge leaves `scripts/` unchanged):
   `explainer-serve.py --self-test` gave 282/282 and `regen-pages.py --self-test` gave 121/121, both rc 0.
3. **Mutants applied to copies outside the repo** (`git archive <sha> scripts`, extracted into the
   scratchpad's `r4review/` directory). I ran the edits the manifest entry gives, and read the `[FAIL]` lines:
   - `#627 r1 (Codex 4): the local verdict wins before master is consulted…` on f8bd907e: it fails as
     `[FAIL] ⭐ #627 r1 (Codex 4): a local LINK over a page master has serves master's; one master lacks stays refused`.
     The line has no ` — Exc:` suffix, so it equals the expect.
   - `#627 r1 (Claude half's survivor): do_GET never starts a fetch…` on f8bd907e: it fails as
     `[FAIL] ⭐ #627 r1 (Codex 5, Claude F1): THROUGH do_GET … all reach the response`, with no suffix.
     The **same mutant on d0d7eeee** gives `… reach the response — AttributeError: 'NoneType' object has no attribute 'join'`.
     That reproduces the CI defect and shows that this commit fixes it.
   - (Both copies also print 2 environmental `[FAIL]`s about declared sources and the archive file. They
     come from the copy having no `docs/`. They are unrelated to the subject.)
4. **Weakening analysis of the two changed cases:**
   - `_local_link`: when `da.served` is non-None the returned tuple is the same as before. When it is
     None, the tuple holds `None`s, which can never equal `("serve", "master", "<p>A v1</p>")`. So no
     input that used to fail can pass now. `dn.served` was never dereferenced, so it is unchanged.
   - `_through_handler`: the guard only skips `join` when `thread is None`, and in that state no fetch
     ran, so there is nothing to wait for. The 9th assertion in `_handler_want` needs `"still running"` in
     `out["pending"]`, and `CopyFetcher.note()` says that only when `running()` is true. `running()` is
     `self.thread is not None and self.thread.is_alive()`. So a `None` thread forces assertion 9 to False,
     and the case still fails. A mutant that killed it by raising now kills it by value.
5. **Scope:** both code hunks are inside `_serve_copy_cases` (the self-test). The commit does not
   change the server, the fetcher, `decide`, or `regen-pages.py` code.

## Findings

None.

VERDICT: CONVERGED
