Reviewed head: 354a7ace4a60079be01de3b71118954ba478b1f1

# Backlog #627 (serve explainer pages from origin/master) — round 1, Claude half

Branch `627-serve-master`, draft PR #576, diff `git diff origin/master...HEAD` (merge base 916fa47e).
Mandate: refute. Everything below was run against the worktree at the head above. Mutations ran on an
rsync copy under the session scratchpad, never in the repository.

## Gates run

| Check | Result |
|---|---|
| `python3 scripts/explainer-serve.py --self-test` | 260/260 passed, rc 0 |
| `python3 scripts/regen-pages.py --self-test` | 115/115 passed, rc 0 |
| 8 mutants of my own (listed in F1 and below) | 5 SURVIVED, 3 killed |
| Behaviour repro script (temp bare origin + main clone + serve copy) | R1–R7 below, all reproduced |

Killed (the case named does test the behaviour): `HEAD:{prefix}{rel}` → `HEAD:{rel}`; `_generated` → `False`;
`if want_local and local is not None` → `if False`.

## Findings

### F1 — MAJOR — the request handler's wiring of the fetcher and of `?source=local` is untested: 5 mutants survive

Every #627 case calls `served_page`, `CopyFetcher` or `page_body` directly. None goes through `do_GET` or
`/_rev` with a fetcher. It cannot: `serve_state` (`scripts/explainer-serve.py:1444-1445`) returns no fetcher
whenever `_IN_SUITE` is set, *for every root, temp roots included*. So the second suite guard also makes
the call site impossible to test. Mutants, each applied alone, each **260/260 green**:

| Mutant (in `Handler.do_GET`) | What breaks in the real server |
|---|---|
| `served_page(path, setup, note=fetcher.note() if fetcher else "",` → `note="",` | a failed fetch is SILENT on every real page: the "a failed fetch is never silent" promise is broken where it matters |
| `fetcher.poke(FETCH_WAIT)` → `pass` | the GET never fetches, so a merged page is served only after a `fresh` rebuild. That is the ⭐ FAILS-IF |
| `want_local=LOCAL_QUERY in query.split("&")` → `want_local=False` | the yellow bar's "See the local edits" link serves master's page again, so the bar's only way out is dead |
| `/_rev`: `served_page(..., setup, note=...)` → `served_page(..., SourceSetup("preview", ROOT, None, "", ROOT))` | live reload goes back to watching the working tree, so an open tab never reloads when the copy moves |
| `/_rev`: `f"{revision(served.path)}:{served.kind}"` → `f"{revision(served.path)}"` | a flip between master's file and the local one at equal mtime:size is not a revision change |

Reproduction: `scratchpad/627-mut/run.py` (rsync copy, `python3 run.py <dir>`). The log is `627-mut/mut.log`.
The two FAILS-IF cases (`_merged_within_a_minute`, `_failed_fetch_keeps_copy`) build their own
`CopyFetcher` and pass `note=f.note()` by hand. They prove the parts and never the composition the
footer depends on.
**Fix direction:** make the guard refuse the *real repository*, not "any fetcher". For example, gate on
`_regen()._is_this_repository(setup.checkout)` rather than `_IN_SUITE` alone, or inject a fetcher factory. Then
drive `do_GET` / `/_rev` end to end inside `world()`: a merged page through GET, a failed-fetch note in the
GET body, `?source=local` in the GET body, and `/_rev` changing when the copy moves. Add the five mutants above
to `scripts/mutations/explainer-serve.json`.

### F2 — MINOR — the decision and the send race the background `checkout --force`: a request can drop with no status line

`poke(FETCH_WAIT)` returns after 2 s while the fetch thread goes on running `move_serve_copy`'s
`git checkout --force` in the copy. Then `served_page` (decision, label from `copy_head`) and `page_body`
(`served.path.read_bytes()`, `:1452`) read files that git is rewriting. Repro R6: decide `/page` → kind
`master`, path inside the copy. A merge then deletes the page and the copy moves. `page_body` then raises
**FileNotFoundError**. `do_GET` has no handler for it, so the connection closes without a response.
The same window can pair new bytes with the old sha's label, or read a half-written file. It is transient and
corrected on the next load. It is still a fail-open path: the bytes and the footer can disagree.
Fix: read the bytes inside `served_page` and carry them in `Served`, and treat a vanished file as a 404 or a retry.

### F3 — MINOR — a committed but unmerged edit in the main checkout is hidden behind master's page with no bar

`choose_source` reads `local == base` as "unedited" (`:1227`). If the main checkout's HEAD holds a commit
that changes a page and is not on origin/master (local `master` ahead of origin, or any branch), then
`local == base != master`. That gives `"master"`, no bar. Repro R3: the main clone is on branch `feature` with a
committed `<p>my committed edit</p>` and master is at `v2`. The result is kind `master`, `bar=False`, body `<p>v2</p>`.
The edit is invisible and nothing says so. The rule assumes HEAD is an ancestor of origin/master, and nothing checks that.
Fix: treat `local != master` as an edit unless `base` is master's blob at some ancestor (e.g. `merge-base --is-ancestor HEAD origin/master`).

### F4 — MINOR — a case-variant URL on case-insensitive APFS gets a false yellow bar (and would bar an overlayable edit)

`safe_path` → `resolve()` keeps the request's spelling. The file is found, but `rel` carries the URL's case,
and `git cat-file blob HEAD:<prefix><rel>` (`:1414`) is case-sensitive, so `base` is None. Repro R4: an unedited page,
in a checkout behind master. `/2026-01-01-topic-a.html` gives `master`, no bar. `/2026-01-01-TOPIC-a.html` gives
**`master+bar`, bar shown** over no edits. The failure goes the safe way (master is shown). Fix: take `rel` from the git
index (`ls-files`) or compare case-folded names.

### F5 — MINOR — three footer labels state something false

- R1: `?source=local` on an UNEDITED page (local == master) is labelled `local edits on <h> — NOT master's page
  (its base is not master's copy)`. `"asked-local"` is labelled the same whatever `choose_source` would say.
- R2: a page missing from a present copy (a damaged copy) is served from the working tree as
  `local edits on <h> — not on master`, with no warning. The page IS on master.
- R7: a page DELETED on master but unedited locally is labelled `local edits on <h> — not on master`. There
  are no local edits.
The #627 FAILS-IF is "every page names its source", and here the named source is wrong.

### F6 — MINOR — the yellow bar's link is built from the raw request path, so `//page.html` gives a protocol-relative link

`page_body` uses `url_path.split("?",1)[0] + "?source=local"` (`:1457`). `safe_path` strips leading slashes, so
`GET //2026-01-01-topic-a.html` resolves the page. Repro R5 (a stale-based edit): kind `master+bar` and
`href="//2026-01-01-topic-a.html?source=local"`. A browser resolves that link to the HOST `2026-01-01-topic-a.html`.
This is only reachable from a URL the reader typed, on 127.0.0.1. Fix: build the href from the resolved relative path.

### F7 — MINOR — every page load waits on ANY running fetch, not only one it started; request-thread git calls are outside the 2 s bound

`poke` joins `self.thread` whoever started it (`:1369-1371`). The constant's comment says "a page load waits for a
fetch it STARTED" (`:1217`). A slow fetch can run up to `GIT_TIMEOUT` 120 s per git call plus the 30 s lock wait.
For all of that time every page load and Refresh pays the full 2 s, and no note says a fetch is in progress.
Separately, `served_page` runs `rev-parse HEAD` and `cat-file` on the request thread, each with a 10 s timeout
(`:1292`). So "never held past 2 s" holds only for the fetch. Fix: join only when `started`, and state the git-call bound.

### F8 — MINOR — `move_serve_copy`'s docstring promises "on any failure the copy is left where it was"; false after the checkout

The read-back (`rev-parse HEAD`) and `status --porcelain` checks in `scripts/regen-pages.py` `move_serve_copy`
run AFTER `checkout --force`. A failure there leaves the copy at the NEW sha (or dirty) while `CannotRun` reports that
it did not move. `copy_head` then labels pages `master @ <new sha> · ⚠ FAILED`. Correct the docstring, or reset on failure.

### F9 — MINOR — a non-integer `EXPLAINER_SERVE_PORT` crashes every mode at import

`PORT = int(os.environ.get("EXPLAINER_SERVE_PORT", "").strip() or 7391)` (`:107`). With `EXPLAINER_SERVE_PORT=abc`,
the result is a ValueError traceback for `--status`, `--stop` and `--self-test` too, not a message. Validate and say so.

## Questions in the brief, answered

1. **Overlay rule.** I found no input that serves a stale-based local edit as current. Every `base != master`
   edit goes to `master+bar` (mutant-tested in the manifest and by me). The inverse fails twice: a committed edit is
   hidden with no bar (F3), and a case-variant spelling bars an edit that could be overlaid (F4).
2. **Fail-open.** A failed fetch is said by `served_page`, but the handler's pass-through is unguarded (F1).
   The race in F2 can drop a request or mislabel bytes. No request hangs past 2 s on the fetch, but see F7.
3. **Suite isolation.** Both guards are real and independent. `regen-pages._IN_SUITE` + `_is_this_repository` sits in
   `refresh_serve_copy`, and `explainer-serve._IN_SUITE` sits in `serve_state`. They are separate module globals,
   armed by separate lines (`:2197`, `:2198`), and each has its own manifest mutant. `_real_fetch_refused` uses a
   recording git that refuses. This is a second guard, not a rewording. Its cost is F1.
4. **Path safety.** `?source=local` only toggles a bool, and both roots go through `resolve_page`/`safe_path`, which
   check containment after resolution. I found no traversal. F6 is a link-construction issue, not a read outside the roots.
5. **Mutation strength.** The 14 + 4 manifest mutants cover the pure parts. The call-site mutants in F1 survive.

VERDICT: NOT CONVERGED
