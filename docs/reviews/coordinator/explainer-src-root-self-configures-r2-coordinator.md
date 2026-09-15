# Round 2 — `explainer-src-root-self-configures` (PR #295) — coordinator

```yaml
round: 2
fixes_nontrivial: true
subject: explainer-src-root-self-configures
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: instrument, fix_induced: true, component: src-root-help, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: src-root-help, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: src-root-help, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: page-chrome-suite, disposition: fixed}
  - {id: L2, severity: Low, aim: instrument, fix_induced: false, component: fixture-variation, disposition: fixed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: true, component: pidfile-recovery, disposition: filed}
  - {id: L4, severity: Low, aim: instrument, fix_induced: true, component: src-root-help, disposition: fixed}
```

## The round in one line

**Round 2 reviewed round 1's fixes, and four of its seven findings were defects those fixes
introduced** — which is exactly why this project runs a round on its own repairs.

## Topology — ALTERNATED, not concurrent

Per `docs/plugins.md`: round 1 concurrently, rounds 2+ alternate, *"because a concurrent pair
never reviews the FIXES."* Codex ran first, its M1 was fixed, and the Claude half then reviewed a
tree containing that fix — and found that **the fix's guard was inverted**. A concurrent pair
would have missed it.

## Findings

### M1 — Medium — r1's fix for M1 was wrong in production → **FIXED** (fix-induced)

r1 replaced `{repo}/scripts/explainer-serve.py` with `Path(__file__).resolve()` and commented
*"which necessarily exists"*. Both claims false: production calls `src_root_help(…, REPO)` (`:1071`)
with `REPO = Path(__file__).resolve().parent.parent` (`:115`), so the interpreter's own file is
**inside** the directory the message declares missing. Same `[Errno 2]`, one indirection away.

⭐ **The r1 case passed throughout** because it asked a fixture instead of the caller — synthetic
`/tmp/gone` while `__file__` was live. *Fixing a premise is not covering the branch.*

Now recovers through the pidfile (`ROOT = Path.home()/"explainers"`, outside every checkout).

### H1 — High — the guard for that fix was INVERTED → **FIXED** (fix-induced)

`str(PIDFILE) in _arm` — the substring instrument this branch condemned in `page_chrome` one
commit earlier. Measured under `HOME=/tmp/it's home`: `shlex.quote` emits `'/tmp/it'"'"'s home/…`,
so the raw path stops being a substring — **the correct code failed 113/114 and the unquoted
mutant passed 114/114.** A guard that rewards the absence of its own fix is worse than none.

Fixed with this branch's own r1 H1 remedy — an injectable `pidfile` parameter and ARGV comparison
over five hostile fixtures. ⚠ `shlex.split` cannot parse the whole line (it does not re-open a
quoting context inside `$( )` the way `sh` does); the substitution is split out first. That was
learned by **running** it, not by reasoning about it.

### M2 — Medium — the sibling arm was never re-read → **FIXED**

`src_root` returns None for a set-but-bad env var without consulting `REPO` (`:479-480`) and the
caller is unconditional, so a stale `EXPLAINER_DOCS_ROOT` **plus** a moved checkout reached the arm
that names paths under the missing repo. Both paths now route to one `_gone_checkout_help`.

⭐ **Restructuring exposed a third defect neither half named:** the old shape fell through to the
gone-checkout text when the repo **exists** and the env var is empty — telling a reader their
checkout was deleted when it was not.

### L1 — Low — a raise hid ~58 cases → **FIXED** (fix-induced)

Applying `page_chrome`'s own manifest entry made `shlex.split` raise on the `/tmp/it's here`
fixture, **aborting the suite**. The mutation was attributed only because `/tmp/some repo` comes
first in the tuple. One fixture-order swap and `check-plan-code` would have reported *"the suite
went RED but printed no `[FAIL]` line … NOTHING COULD SEE THE KILL"*. The raise is now a value;
measured after, the same mutation prints 4 `[FAIL]` lines and no traceback.

### L2 — Low — `EXAMINED_KEYS` → **FIXED**

Pinned the subset this branch made load-bearing. ⭐ **And the guard immediately caught the new seam
not being used:** every hostile-pidfile case reached the arm through `_gone_checkout_help`, so
`src_root_help(pidfile=…)` was *"the SAME value at every call site (10x `<omitted, default>`)"* — an
injectable parameter that nothing injected. Two cases now drive it through the public function.

### L4 — Low — a comment's own line references → **FIXED** in passing

The r2 comments were rewritten during M2's restructure and now cite the live lines.

### L3 — Low — the pidfile is the sole recovery anchor → **FILED**

It can legitimately be absent while the server is up. Needs a mechanism (liveness distinct from
pidfile presence), so Q3 files it.

## Q4 — is another round owed?

**(a) Convergence: CONTINUE.** A High, two Mediums, findings in the deliverable,
`fixes_nontrivial: true`. Four findings were fix-induced.

**(b) Tree identity: a round is owed regardless** — every fix above is code no round has seen, and
the two Codex verdicts on this branch recorded the **wrong head** (backlog #121), so no verdict yet
names a commit on this branch at all.

## Q5 — thrashing?

⚠ **Answered honestly, and it is close.** `src-root-help` carried fix-induced findings in **round
2** (M1, H1, L4). That is **one** round, not two — the arming condition is *two consecutive rounds*
whose findings came from the previous round's fix, in one component. Round 1's findings in that
component were **not** fix-induced (they were original defects). **So it does not fire.**

⛔ **But it is one round away, and the next round must answer this question first.** If round 3
finds another fix-induced defect in `src-root-help`, the architecture review is armed and the
answer is not another patch.
