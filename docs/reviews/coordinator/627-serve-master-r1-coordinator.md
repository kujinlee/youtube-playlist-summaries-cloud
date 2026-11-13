# Round 1 — `627-serve-master` (backlog #627) — coordinator — ⟳ NOT CONVERGED; all folded

```yaml
round: 1
fixes_nontrivial: true
subject: 627-serve-master
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: serve-chooser, disposition: fixed}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: serve-chooser, disposition: fixed}
  - {id: X3, severity: Major, aim: deliverable, fix_induced: false, component: serve-handler, disposition: fixed}
  - {id: X4, severity: Major, aim: deliverable, fix_induced: false, component: serve-chooser, disposition: fixed}
  - {id: X5, severity: Major, aim: deliverable, fix_induced: false, component: suite-isolation, disposition: fixed}
  - {id: X6, severity: Minor, aim: deliverable, fix_induced: false, component: serve-fetcher, disposition: fixed}
  - {id: F1, severity: Major, aim: deliverable, fix_induced: false, component: serve-handler, disposition: fixed}
  - {id: F2, severity: Minor, aim: deliverable, fix_induced: false, component: serve-chooser, disposition: fixed}
  - {id: F3, severity: Minor, aim: deliverable, fix_induced: false, component: serve-chooser, disposition: fixed}
  - {id: F4, severity: Minor, aim: deliverable, fix_induced: false, component: serve-chooser, disposition: fixed}
  - {id: F5, severity: Minor, aim: deliverable, fix_induced: false, component: serve-label, disposition: fixed}
  - {id: F6, severity: Minor, aim: deliverable, fix_induced: false, component: serve-label, disposition: fixed}
  - {id: F7, severity: Minor, aim: deliverable, fix_induced: false, component: serve-fetcher, disposition: fixed}
  - {id: F8, severity: Minor, aim: prose, fix_induced: false, component: docstring, disposition: fixed}
  - {id: F9, severity: Minor, aim: deliverable, fix_induced: false, component: serve-port, disposition: fixed}
```

Reviewed `354a7ace` (both halves). X = the Codex half (`docs/reviews/codex/627-serve-master-r1-codex.md`,
findings 1–6), F = the Claude half (`docs/reviews/claude/627-serve-master-r1-claude.md`).

**The fold's shape.** Every page decision now goes through ONE chooser, `decide(url_path, setup, *, note, want_local)
-> Decision(verdict, served, info)`. `do_GET`, `/_rev`, `/` and `/latest` all call it, or call `page_list` /
`latest_of`, which use the same tree. A master page's bytes are read ONCE, from git (`git cat-file blob <oid>` in
the serve copy, the oid from a cached `ls-tree`), and travel in `Served.body`. They are never read from the copy's
working tree.

| Id | Finding | Disposition and evidence |
|---|---|---|
| X1 | A damaged copy (missing file, unreadable objects) silently enabled stale local edits | **Fixed.** A missing working-tree file no longer matters: the bytes come from the object. An unreadable tree or blob gives kind `no-copy`, labelled "cannot be READ", never "not on master". Case *(Codex 1)*. It is checked both with the tree still cached and after the cache is cleared, because the first version of the case let mutant `codex1-unreadable-says-absent` SURVIVE. With the strengthened case it is killed. |
| X2 / F2 | A background `checkout --force` raced the decision and the send: the bytes and the footer could disagree, or a vanished file dropped the connection | **Fixed** by the same change. The bytes and the rev (`m-<oid>`) come from the same tree entry, and the label's sha names that commit, so a concurrent checkout cannot split them. A local page's bytes and rev (`l-<mtime_ns>:<size>`) are read together by `_read_local`. Cases *(Codex 2)*: bytes read once, two local reads. |
| X3 | `/` and `/latest` hid master-only pages | **Fixed.** `page_list` / `latest_of` merge master's tree with the local pages. `index_html(root, pages, source)` adds the footer. Case *(Codex 3)*, plus the handler case. Mutant `codex3-index-local-only` is killed. |
| X4 | Local retirement or link metadata suppressed master's valid page | **Fixed.** The local verdict is consulted only after master's tree. A retired page still redirects. A local LINK over a page master has serves master's page; one that master lacks stays refused. Case *(Codex 4)*. Mutant `codex4-local-verdict-first` is killed. |
| X5 / F1 | The second isolation guard failed for scripts staged outside git, and do_GET's wiring was untested (5 surviving mutants) | **Fixed.** Both guards are now a WHITELIST: true only strictly inside a `fixture-tmp-*` `tempfile.tempdir`. They are `_suite_owns` (explainer-serve) and an independent `_inside_suite_tmp` (regen-pages), and they protect ROOT whether or not it is in git. The regen-pages cases went red first: a sibling of the tempdir, and `ROOT.parent`. A new handler case, *THROUGH do_GET on a temp clone*, drives the real handler. It checks the merged page, the index, /latest, /_rev moving, the bar, ?source=local, a failed fetch, the `:fetch-failed` rev and a running fetch. All five of Claude's mutants (`handler-note-dropped`, `handler-no-poke`, `handler-want-local-off`, `rev-old-resolver`, `rev-kind-dropped`) are KILLED. |
| X6 / F7 | A slow fetch served the old copy with no freshness warning, and every load waited on ANY running fetch | **Fixed.** `poke` joins only a fetch it started. `note()` adds "still running" to the footer. `/_rev` carries `:fetch-failed`. Bound, by design: /_rev does not carry "running", because that alone would reload every open tab twice a minute. Case *(Claude F7, Codex 6)*. Mutants `f7-waits-on-any`, `c6-running-unsaid` and `rev-failed-flag-dropped` are killed. |
| F3 | A committed but unmerged local edit was hidden behind master's page with no bar | **Fixed.** `choose_source` compares against the merge-base ancestor when it is known, so a committed edit gets the bar. Case *(Claude F3, F5)*. Mutant `f3-ancestor-ignored` is killed. |
| F4 | A case-variant URL on case-insensitive APFS got a false bar | **Fixed.** `_true_name`: an exact match wins, then the ONE case-folded match. An ambiguous one is left as is. Two cases. Mutant `f4-no-casefold` is killed. |
| F5 | Three footer labels stated something false | **Fixed.** `source_label` takes a `why`: same / behind / overlay / deleted / committed. "Committed" and "deleted on master" are now said. Mutant `f5-why-dropped` is killed. |
| F6 | The bar's link was built from the raw request path (`//page.html` → protocol-relative) | **Fixed.** The link is built from `served.rel`, quoted. Case *(Claude F6)*. Mutant `f6-raw-request` is killed. |
| F8 | `move_serve_copy`'s docstring promised the copy is untouched on any failure | **Fixed (prose).** The docstring now says a failure after the checkout can leave the copy at the new sha. The server stays consistent because the label's sha and the bytes come from one commit. |
| F9 | A non-integer `EXPLAINER_SERVE_PORT` crashed every mode at import | **Fixed.** `port_from(raw) -> (port, error)` never raises. `main` returns rc 2 with the error, except under `--self-test`. Case *(Claude F9)*. Mutant `f9-port-unchecked` is killed. |

**TDD, said plainly.** The explainer-serve fixes were written before their cases, so the evidence that the cases
bite is a mutant run on a copy of `scripts/` OUTSIDE the repository (no `.git`, verified). 19 mutants were run.
18 were killed at once. One, `codex1-unreadable-says-absent`, SURVIVED, and its case was strengthened until it was
killed. The regen-pages guard was done red-first.

**The manifest.** Nine existing anchors were orphaned by the folds (entries 45, 46, 74, 81, 82, 83, 85, 86, and
47/58, which matched twice until `decide` stopped duplicating `retirement`'s retired check). Each was re-bound. 18
entries were added to `explainer-serve.json` and 1 to `regen-pages.json`. Every anchor matches exactly once, and
every `expect` is a case name in the source. All 26 new or re-bound entries were applied on the out-of-repo copy, and
each went red through the case it names. The pins are 87 → 105 and 64 → 65. `check-fixture-variation` then found
`decide`, `page_list` and `index_html` called with one value per input. One case now varies each input at its own
call site. Self-tests: explainer-serve 277/277, regen-pages 117/117. The regen-pages outsider case (1), `ROOT.parent`,
accepts either guard's refusal: in the harness's staged copy ROOT is in no repository, so the second guard answers
instead of the first. The local `--mutate --only` for either script is refused as over the 10-minute budget
(42.9 and 42.5 min), so the full sweep runs on the PR's CI shards.

Round 2 alternates: ONE half (owner 2026-10-28).
