# Round 1 — `seed-explainer-serve-manifest` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: seed-explainer-serve-manifest
halves:
  claude: ran
  codex: gap
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: src-reach-verdict, disposition: fixed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: false, component: regenerate, disposition: fixed}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: true, component: manifest-attribution, disposition: fixed}
  - {id: M4, severity: Medium, aim: instrument, fix_induced: true, component: claimed-bound, disposition: fixed}
  - {id: M5, severity: Medium, aim: deliverable, fix_induced: false, component: escaping, disposition: fixed}
  - {id: M6, severity: Medium, aim: deliverable, fix_induced: false, component: start-stop-status, disposition: fixed}
  - {id: L7, severity: Low, aim: deliverable, fix_induced: false, component: resolve-page, disposition: fixed}
  - {id: L8, severity: Low, aim: instrument, fix_induced: true, component: src-caller, disposition: fixed}
  - {id: L9, severity: Low, aim: instrument, fix_induced: true, component: src-root, disposition: fixed}
  - {id: L10, severity: Low, aim: deliverable, fix_induced: true, component: docstring, disposition: fixed}
  - {id: L11, severity: Low, aim: deliverable, fix_induced: false, component: pid-alive, disposition: fixed}
  - {id: S1, severity: Low, aim: instrument, fix_induced: true, component: resolve-page, disposition: fixed}
  - {id: S2, severity: Low, aim: instrument, fix_induced: true, component: sandbox-hygiene, disposition: fixed}
  - {id: S3, severity: Low, aim: instrument, fix_induced: true, component: manifest-attribution, disposition: fixed}
```

## REVIEW GAP: codex — the run TIMED OUT and the wrapper refused to write a partial review

`scripts/codex-review.py` reported `gpt-5.5: try_next — timed out — any partial message is an
incomplete review`, then `gate_ran=false`. **The wrapper behaved correctly**: it wrote no review file
rather than an empty one, and recorded the refusal in
`docs/reviews/verdicts/seed-explainer-serve-manifest-r1-codex.verdict.json`.

Per `docs/plugins.md` the rule is **do not wait, do not retry** — fall back to a Claude adversarial
review and note the gap. That is what round 2 is: a **fresh** Claude reviewer with an explicit
adversarial mandate, standing in for Codex on the fixed tree. The Codex-specific pass can be
re-attempted before merge if access returns.

⚠ **AND THE FAILURE PATH TOOK SEVEN FILES THAT WERE NOT ITS OWN — backlog #92, live.** The wrapper's
`quarantine()` moved seven scratchpad files created during its run to
`/var/.../codex-review-quarantine-1lnfyzpd`. They belonged to the **concurrently running Claude
half** — its mutation harness (`mut.py`), its four spec files, and a 41 KB baseline capture. It
finished its 452-line review anyway; the files were restored by the coordinator. Nothing in the repo
was touched. Recorded because #92 describes this for `docs/reviews/` and this instance was in the
scratchpad, which is the same mechanism one directory over.

## The Claude half: 11 findings, every one measured, none Blocking

Its own lead sentence is worth keeping: *the branch is correct and is a real improvement* — all 17
original entries attributed to exactly one red case, and the debt ratchet fires both ways. What it
found is that **the 17 entries sat almost entirely in the pure-helper layer**, and that two claims in
the commit's prose are contradicted by measurement.

## H1 — HIGH — the /src/ security verdict has FOUR clauses; I cased the one I tripped over

`scripts/explainer-serve.py:238-241`. The branch's headline was *"clause 2, `SERVABLE` excludes
`.env*`, had no case at all"* — true, and fixed. The sentence has four clauses. Measured:

| clause | mutation | before |
|---|---|---|
| 3 · listener is 127.0.0.1 | `HOST` → `"0.0.0.0"` | **149/149 SURVIVED** |
| 4 · no CORS header | `_send` gains `Access-Control-Allow-Origin: *` | **149/149 SURVIVED** |

⭐ **This is this repo's *after fixing, SEARCH for the class* — failing inside the commit that was
celebrating finding a class.** Clause 4 is stated a second time at `:1065` as a load-bearing
decision and refined over six more lines at `:243`; the one line all of that rests on could be
deleted or inverted silently. Clause 3 is the difference between a loopback dev server and one
reachable from the LAN, over a subsystem the same comment says serves the whole checkout.

**Fixed** with three cases. ⚠ Asserted on **what `_send` actually emits**, via a header-capturing
stub — not on the absence of a string in source, which would pass on a header added through a helper.

## H2 — HIGH — `_regenerate` had zero cases, and a timeout reported as success survived

`scripts/explainer-serve.py:1166-1209`. Neither `_regenerate` nor `source_shell` was named anywhere in
the 149-case suite. Four documented decisions all survived; the load-bearing one:

> A timeout is NOT a failure to report as "rebuilt". The reader is told the page may now be
> half-written, because silence here reads as success.

Turning that 504 arm into `200 {"ok": true}` passed **149/149**. That comment is `CLAUDE.md`'s
***"cannot run" is a FAILURE, never a pass*** written into a handler, and the mutation that turns it
back into a pass was invisible.

Also surviving: deleting the warning channel (`warn = []`) — **a Codex Medium that was fixed and
never cased**, restoring the degraded-gate-reports-success shape its comment exists to close — and
`isinstance(want, str)` → `want is not None`, which is a live `TypeError: unhashable type` inside the
handler, i.e. backlog #87/#123's dropped-connection symptom at a third site.

**Fixed** with five cases driving the real handler through a stubbed `subprocess.run` — no process
spawned, the `_drive_src` pattern already in the suite.

## M3 — MEDIUM — one entry's kill was real and its ATTRIBUTION misleading, and the proposed fix did not work

The entry named *"safe_path tests containment BEFORE resolving"* but pointed `expect` at *"a raw NUL
byte does not escape safe_path"*. The reviewer measured that the two cases whose names contain
**traversal** are **unchanged** by that mutation — they pass because `passwd` has no suffix, so
`SERVABLE` rejects them before containment is ever consulted. So the entry certified containment
using a case about a crash.

⭐ **Its proposed repair — point `expect` at the `/src/` escape case — was applied and REFUSED by the
harness:** under the mutation that case dies by `ValueError` carrying a machine-specific temp path, so
its parsed name attributes to nothing. **The bound measured in M4 defeated the fix proposed in the
same review.** *A filed finding's proposed fix is a hypothesis.*

**Fixed** by writing the case that did not exist: containment asserted **at `safe_path` itself**, over
a `.md` file that really sits one level outside the root. A `.md` gets past the suffix allowlist, so
containment is the only thing that can refuse it — which is what makes the case about containment.

⚠ **And one entry was DELETED rather than forced.** Removing only `.resolve()` reddens a dozen
"serving stopped working" cases, but that is an artefact of macOS symlinking `/var` → `/private/var`,
and no red case's name describes the defect the entry claimed. An entry that has to borrow another
case to look covered is the coverage theatre M3 is about. 26 → **25** entries.

## M4 — MEDIUM — a claim I made in four places is false as stated

I wrote that a case dying by RAISING **"can never be named by a manifest entry"**. The reviewer fed
the **real** `parse_fail_names` and the **real** matcher an `expect` carrying the full
`{name} — AssertionError: {msg}` string: **it attributes**, because `_Forbidden`'s message is built
from two call-site literals and is deterministic.

The honest bound, which survives being checked: *naming a raise kill means embedding the exception
type and message — unattributable the moment that message carries runtime data (the same sweep
produced a `ValueError` naming a temp path), and coupled to one failure mode of the case even when it
does not.* **The design decision it justified is unchanged; only its reason survives.** Corrected in
all four places, including the backlog closure, which carried it behind a ⛔.

## M5, M6, L7, L11 — documented decisions with no case, all fixed

- **M5** `safe_href`'s docstring credits `md_render` with closing the attribute break-out; **both
  quote escapes could be deleted at 149/149**. And `source_shell` — which renders every `/src/` file —
  had no cases: its non-markdown arm could stop escaping `<` at 149/149, injecting raw markup into the
  viewer page for every `.html`/`.js`/`.svg`/`.css` in the checkout. That is *content*, which the reach
  verdict's path-oracle reasoning does not cover. Three cases.
- **M6** `status()` returning `0` with nothing listening survived — *"cannot run" reported as a pass*
  in the one command a human runs to ask whether the server is up. Two cases, `port_busy` stubbed.
- **L7** the `.html` fallback's *"not a second chance"* rule survived; `/secret.env` would get a
  second attempt with `.html` glued on. Two cases, **with decoy files**, because the rule is about the
  fallback and a first version tested a direct hit instead (S1).
- **L11** `pid_alive`'s falsy guard: `if not pid:` → `if pid is None:` survived. With a pidfile of
  `0`, `os.kill(0, 0)` succeeds, so `stop()` would SIGTERM **pid 0 — the whole process group**.

## L8, L9, L10 — my own prose and instruments, corrected

- **L8** the new RATCHETABLE case asserted only half of what its comment claimed — `_raises(...) is
  False` is also true when the drive raises something else or serves nothing. Both halves now asserted.
- **L9** it introduced a **second** literal for "a path that does not exist" while `_norepo` was in
  scope four lines above — and a world-writable path a case requires to be *absent* is a
  false-failure channel. Reuses `_norepo`.
- **L10** my `home_escapes` repair changed the docstring example to `~me/…`, a shape
  `observed.fallback` (always `SCRIPTS.parent`) cannot hold — and the same file documents that
  `shlex.quote` leaves a tilde unexpanded, so the example's own *fixed* command was still broken. Now
  `/srv/me/…`: absolute, producible, and outside the flagged prefixes.

## S1, S2, S3 — defects in this round's own fixes, recorded not smoothed

- **S1** the L7 case first asserted `resolve_page("/notes.md") is None`, which is red on **correct**
  code — a direct hit on a real servable file is what the resolver is *for*. It tested the wrong half.
- **S2** the L7 decoys were written into the **shared** sandbox and reddened a later case
  (`orders newest first`). `with_env`'s own docstring warns that a case leaking *state* corrupts the
  cases after it; a case leaking *files* does the same. Now in a dedicated subdirectory.
- **S3** the M3 repair (above) — the reviewer's proposed `expect` was refused by the harness.

## Evidence

`python3 scripts/check-plan-code.py --mutate .` — **668 mutations, 668 killed, 668 attributed to the
case each names, 0 survivors**, every file's control proved green first. Suite **149 → 167**, manifest
**17 → 25**, declared total **660 → 668**. Fourteen gates green, including under the non-existent
`$HOME` the harness spawns with.

## Q4 / Q5

**Convergence: not reached.** Two High plus non-trivial fixes → `fixes_nontrivial: true` → **round 2
owed**, and it also discharges the Codex gap above.

**Thrashing: not armed.** S1–S3 are fix-induced but were all caught and closed **within** this round;
the rule needs two consecutive rounds carrying defects caused by the previous round's fix in one
component. ⚠ **Pre-committed before round 2 runs:** if round 2 finds a fix-induced defect in
`manifest-attribution` — the component S3 sits in — that is one round of thrash there, and a third
attempt at an entry's attribution should be answered by **deleting the entry** rather than
re-pointing it again. An entry that cannot find an honest case to name is telling you the case does
not exist yet.
