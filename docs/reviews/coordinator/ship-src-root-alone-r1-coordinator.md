# Round 1 — `ship-src-root-alone` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: ship-src-root-alone
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: src-root-reach, disposition: fixed}
  - {id: H2, severity: High, aim: instrument, fix_induced: false, component: src-caller, disposition: fixed}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: false, component: dup-key-guard, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: false, component: report-format, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: false, component: src-root, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: f3-anchor, disposition: fixed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: dup-key-guard, disposition: fixed}
  - {id: L4, severity: Low, aim: deliverable, fix_induced: false, component: backlog-counts, disposition: refuted}
  - {id: S1, severity: Low, aim: instrument, fix_induced: true, component: src-caller, disposition: fixed}
  - {id: S2, severity: Low, aim: instrument, fix_induced: true, component: src-caller, disposition: fixed}
```

## The halves disagreed, and the disagreeing half was right

**Codex: CONVERGED, zero findings.** It ran the eight checks in the brief, verified the extraction
hygiene (no live restart symbol, `start()` back to master's, the one `inspect.getsource` slice still
bracketing the intended branch, `page_chrome`/manifest/`check-plan-code` byte-identical to master),
and stated a falsifier.

**Claude: NOT CONVERGED — 2 High, 2 Medium, 4 Low**, every one measured by mutating the delivered
scripts over a control proved green.

Nothing Codex asserted was wrong. Its falsifier was *"a live restart route/symbol, a stale pin or
manifest anchor, a red check, or an `inspect.getsource` slice whose markers no longer bracket the
branch"* — a good list for **extraction damage**, and the extraction was in fact clean. Both Highs
are outside that frame: H1 is a comment that was already false on the branch it came from, and H2 is
coverage that never existed in either branch. ⭐ **This is the dual-review entry in this repo's
memory paying out again** — a Codex-only round would have merged both.

## H1 — HIGH, CONFIRMED and FIXED. The only statement of `/src/`'s reach was wrong by 8.5x, in the direction that mattered

`scripts/explainer-serve.py:213-225` (as shipped in `e06ddb2e`).

The comment claimed *"~1,345 files … `node_modules/` is absent here and WOULD be reachable in a real
checkout"*, itemised to `CONTEXT.md`, and instructed the reader **not to re-run it**.

**Re-measured independently by the coordinator** in the main checkout, walking for `SERVABLE`
suffixes:

```
TOTAL 11506    node_modules 9528 · docs 1294 · .next 379 · .superpowers 105
               .remember 76 · scratchpad 44 · .agents 40 · .claude 19 · (top) 6
```

`node_modules/` is **present and is the largest contributor** — the one thing the comment named as
its stated bound. The reviewer served `/src/node_modules/next/dist/docs/index.md` → 200 live.

⚠ **The cause is the corpus, and it is the same failure H1 is an instance of.** The count was taken
in PR #295's linked worktree, which has never had `npm install` run in it, and shipped into the repo
where it is false. The old comment said of itself *"this count is taken INSIDE the corpus it measures
and is therefore stale at commit time"* — and still asserted a digit.

**Fixed by deleting the number, not correcting it.** The paragraph now states the reach
qualitatively — *every `SERVABLE`-suffixed file under the checkout, including `node_modules/`,
`.next/`, `.remember/`, `.superpowers/`, `.claude/`* — which is true in every worktree and cannot
drift. The security judgement is re-taken against that reach and the reasoning kept: `safe_path`
resolves before the containment test, `SERVABLE` excludes `.env*` by suffix, the listener is
127.0.0.1, and **no CORS header is emitted**, so a cross-origin page can cause a request but cannot
read the reply. What changed is the **cost** of an escape, not its likelihood, and the comment now
says so.

## H2 — HIGH, CONFIRMED and FIXED. The branch's own call site had zero coverage; three mutations of it passed 123/123

`scripts/explainer-serve.py:1113-1121` — the `if path.startswith("/src/"):` branch of `do_GET`.

All 35 new cases called `src_root()` or `src_root_help()` **directly**. Nothing called the branch
that wires them together — and the four-day outage was a *wiring* defect. Reproduced by the
coordinator, each at **123/123 green**:

| mutation | before |
|---|---|
| the caller re-emits master's broken text, unfilled `<dir>` and all | 123/123 |
| the caller stops calling `src_root_help` and sends `b"no source root"` | 123/123 |
| the caller RE-READS `os.environ` — what `SrcRoot`'s docstring forbids | 123/123 |

**Fixed** with a `_drive_src` harness that calls the real `do_GET` on an `object.__new__(Handler)`
with `_send` stubbed — no port bound, no socket — plus an `os.environ` proxy that **counts** reads
of `SRC_ROOT_ENV`. The count, not the absence, is the assertion: the caller is allowed exactly the
one read `src_root` makes, and a second is the defect.

⭐ **Two of my own fix's cases were defective and are recorded as findings, not smoothed over**
(S1/S2 below). That is this branch's history repeating in miniature — the fix for a defect
introducing the next one — and the reason the round is `fixes_nontrivial: true`.

## S1 — the readiness case I wrote asserted a repo file exists

The first `_drive_src` case was `GET /src/CONTEXT.md -> 200`. The harness stages `HARNESS_TREE`, not
the whole repo, so a case naming a checked-in file reports on the stager. Replaced: with the env
unset, `GET /src/<nonexistent>.md` must answer `no such source file` — reachable only **after**
`observed.root` resolved, and the fallback mutation renders the help instead. Depends on no file
existing. The 200 path moved to a nested root the suite populates itself.

## S2 — my `~` case was green locally and RED under the harness, and the guard caught it

`case("src_root: a ~ path is expanded", … == pathlib.Path.home())`. `check-selftest-counts` spawns
every suite through `check-plan-code.child_env`, which sets `HOME` to a path it **deliberately does
not create**; `~` then expands to a non-directory, `src_root` correctly returns `None`, and the case
failed over an ambient fact. ⭐ **The finding was a guard disagreeing with a green local run** — the
exact shape this repo files under *"cannot run is a failure"*. Fixed by pointing `$HOME` at the
sandbox, restored in a `finally`. Verified green under both the real home and a non-existent one.

## M1 — MEDIUM, CONFIRMED and FIXED. The duplicate-key guard claimed three literals; one was exercised

`scripts/check-fixture-variation.py`. Narrowing `wanted` to `{"EXAMINED_KEYS"}` passed **64/64**, so
the cover of `KNOWN_UNVARIED` (127 entries) and `EXEMPT` (7) was asserted by prose. Restoring the r6
Low (`tree.body` → `ast.walk`) also passed 64/64. Three cases added, 64 → 67; both mutations now red
via the case that names them. The finding was about one literal and the fix was widened to three —
*a framing widened to fit is no longer a claim*, measured at last.

## M2 — MEDIUM, CONFIRMED and FIXED. The `[FAIL] ` repair the commit calls a deliverable was guarded by nothing

Reverting `[FAIL] ` → `FAIL: ` passed **123/123**, and nothing else in the tree reads it: this file
has no manifest (backlog #122), so `check-plan-code.parse_fail_names` never sees it. One case added.

⚠ **The first version of that case went RED on correct code** — it spelled the forbidden literal in
its own assertion, putting the token into the file it searches. The bad token is now assembled at
runtime and the search is scoped to the runner block, since the prose above legitimately discusses
both spellings. A case about a token, defeated by being written: worth the two lines of comment it
now carries.

## L1, L2, L3 — CONFIRMED and FIXED

- **L1** `expanduser()` deletable at 123/123, in the commit that took `src_root` from 0 cases to 12.
  Distinct from backlog #123 (`~unknownuser` *raising*): the supported spelling was never exercised.
- **L2** `gen-dashboard.py`'s F3 comment cites evidence **not reproducible in this tree** — the
  chrome that broke it is the parked restart control, so reverting the fix passes 325/325 here. The
  fix still ships (the defect is in the read, not the chrome); the comment now says where the
  measurement was taken and that it cannot be reproduced here. It was also the last surviving
  textual reference to the parked feature in `scripts/`.
- **L3** the `isinstance(n, str)` filter is belt-and-braces, not the crash fix its comment claimed —
  both uses intersect with `wanted`. Line kept, comment corrected so nobody defends it as
  load-bearing.

## L4 — REFUTED, and the refutation is a measurement

The finding: backlog #122/#125/#127 say *"none of that file's **140** cases"*, while master runs 88
and this branch 123, so *"the rows describe no tree in the repo."*

**Measured in PR #295's own worktree:** `self-test: 140/140 passed`, and its docstring declares 140.
Those rows explicitly name the parked branch (*"travels with the parked restart feature"*, *"PR #295
is PARKED behind this"*) — 140 is correct about their subject. The reviewer measured master and this
branch and not the tree the rows name.

⭐ **It is the same corpus error as H1, committed by the review that found H1.** Recorded rather
than quietly dropped, because a refuted finding that is never written down gets re-filed.

## Falsifier for this round's fixes

Every mutation below was re-run after the fixes, over a control proved green (`133/133`), and each
goes red **via the case that names it**:

| mutation | red cases |
|---|---|
| the fallback removed (the original four-day bug) | 5 |
| the caller re-emits master's `<dir>` text | 1 |
| the caller re-reads `os.environ` | 4 |
| `safe_path` bypassed at the caller | 4 |
| `expanduser()` deleted | 1 |
| `[FAIL] ` → `FAIL: ` | 1 |
| `wanted` narrowed to one literal | 2 |
| `tree.body` → `ast.walk` | 1 |

⚠ **And one of those is a case I had to strengthen after it passed for the wrong reason.** The
confinement case asked for `/src/../../etc/passwd` from a root in a temp dir; under a `safe_path`
bypass the traversal lands on a path that does not exist, so it 404'd anyway and stayed green. It
now serves from a NESTED root with a real `escaped.md` one level above it, so a bypass would serve
a file that exists and the case goes red for the reason it names. *Fixing a premise is not covering
the branch* — found by asking, of my own new case, what would make it fail.

## Q4 / Q5

**Convergence: not reached in round 1.** Eight findings, six fixed in code, two comment repairs, one
refuted, plus two self-inflicted instrument defects found and fixed while fixing H2.
`fixes_nontrivial: true` → **round 2 is owed**, and per `review-method.md` rounds 2+ **alternate**
rather than run concurrently, because a concurrent pair never reviews the fixes.

**Thrashing: not armed.** S1 and S2 are fix-induced, but they are in *this round's* instrument and
were caught within the round, not across two. The arming condition is two consecutive rounds whose
findings came from the previous round's fix, in one component. Round 2 will answer whether the
`src-caller` component is thrashing.
