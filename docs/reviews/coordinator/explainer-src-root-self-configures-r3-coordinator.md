# Round 3 — `explainer-src-root-self-configures` (PR #295) — coordinator

```yaml
round: 3
fixes_nontrivial: true
subject: explainer-src-root-self-configures
halves:
  codex: ran
  claude: ran
findings:
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: src-root-help, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: src-root-help, disposition: fixed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: true, component: src-root-help, disposition: fixed}
  - {id: M4, severity: Medium, aim: instrument, fix_induced: false, component: report-format, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: src-root-help, disposition: fixed}
  - {id: L2, severity: Low, aim: instrument, fix_induced: false, component: src-root-help, disposition: fixed}
```

## ⛔ ARCHITECTURE REVIEW IS ARMED — and both halves agree while disagreeing about why

`src-root-help` carried fix-induced findings in **round 2** (from round 1's fix) and again in
**round 3** (from round 2's fix). Two consecutive rounds, one component. `review-method.md` Q5
fires.

| round | finding in `src-root-help` | fix-induced? |
|---|---|---|
| r1 | M1 — the arm named a file inside the missing directory | **no** — original defect |
| r2 | M1, H1, L4 | **yes** — caused by r1's fix |
| r3 | M1, M3, L1 | **yes** — caused by r2's fix |

### The two halves reached the same verdict from different evidence, and the difference is the finding

**Codex armed it on a race:** the caller probes the filesystem twice, so a directory that reappears
between `src_root()` and `src_root_help()` makes an unset-env failure render as *"is set to '', which
is not a directory"*.

**The Claude half tried to REFUTE that and largely succeeded on reachability** — it needs
`REPO.is_dir()` false and then true microseconds apart. It widened the trigger by measuring that
`Path.is_dir()` returns False for a real directory under a mode-000 parent (it swallows `OSError`),
so no state change is required, only a transient stat failure — but it still called the symptom a
**Low**, and said that *on Codex's finding alone it would have argued against arming*.

⭐ **What actually arms it is a thing neither half had stated, and it is a design regression rather
than a bug.** At r1 the branch was `if env_value:` and the empty-env arm was **entailed by the
caller's contract**: empty env + `src_root() is None` ⟹ `REPO.is_dir()` was false. It could not be
wrong. The r2 fix replaced that guarantee with a **second live observation**, asserted the lost
invariant in a comment (*"the second is answered above"* — the new probe **re-asks** the question, it
does not answer it), and **deleted the fallthrough arm on the strength of it.**

That is the same move as r1 M1 and r2 M1, both of which re-derived `__file__` instead of carrying a
path. **One class, four instances, two of them fix-induced in consecutive rounds.** The arming is
justified on its own terms, not on the race.

## The redesign — right axis, under-scoped as proposed

*Can a redesign remove it?* **Yes**, and the class is: **the reason for a failure is inferred rather
than carried.** `src_root()` observes why it failed and returns bare `None`; everything downstream
re-derives.

Codex proposed a structured result. The Claude half agreed with the axis and named four gaps, each
adopted:

| gap | what it means for the build |
|---|---|
| **(a)** carries the reason, not the **anchors** | r1 M1 and r2 M1 were about *which paths the message prints*. The result must carry those too |
| **(b)** the reason is still a snapshot | the false-cause sentence survives — see M3 |
| **(c)** the env var is read **twice** (`src_root` and the caller) | `bad_env(value)` must carry the value the probe actually used |
| **(d)** a 3-member sum invites a 4th | Python will not force exhaustiveness; needs an explicit refusal |

⭐ **And the thing this component has never had: a falsifier for the CLASS.** Every guard so far
names one instance, which is why the fourth arrived unguarded. Purity is testable — render the help
with `os.environ` emptied and `Path.is_dir` patched to raise. If it still renders, it carried; if it
raises, it re-derived. **That single case fails on all four historical findings.**

## Findings and disposition

- **M1** (fix-induced) — the re-probe and the fallthrough deleted on a false invariant → **FIXED by
  the redesign**.
- **M2** — `EXPLAINER_DOCS_ROOT` is read twice. The **oldest** instance of the class, unnamed across
  three rounds. Structural rather than reachable today → **FIXED by the redesign**.
- **M3** — the message asserts a CAUSE it cannot know (*"has moved or been deleted"*), measured false
  for a permission-denied parent or an unmounted volume, and the remedy is then unactionable. ⭐ This
  is the **same defect this branch fixed in `page_chrome`'s `_why` in the same commit**, not carried
  across → **FIXED**.
- **M4** — `explainer-serve.py` prints `FAIL:` where the harness parses `[FAIL] `. **Measured by the
  coordinator with `parse_fail_names`: `[]` versus `['…']` for `page_chrome`.** So the file holding
  this branch's Blocking can never join `--mutate .` — while the branch paid `page_chrome`'s ratchet
  11→13 citing exactly that invisibility. Fails loud, not open → **FIXED**, one line.
- **L1** (fix-induced) — a delegation case reintroduced `str(PIDFILE) in body`, the instrument the r2
  High condemned as inverted, **in the commit that condemned it**. Passes only because that fixture
  has no apostrophe → **FIXED**.
- **L2** — `_inner_argv` raises on a newline-bearing path; caught by the runner, prints a FAIL, not
  vacuous → **FIXED** alongside L1.

## What was checked and found CLEAN — by running it, not by trusting the other half

ARGV slicing against `)` and `$(` (9 fixtures, Codex's negative result reproduced independently);
`kill "$(cat …)"` with missing/empty/whitespace/multi-line/non-numeric pidfiles; a stale pidfile does
not block recovery because `start()` gates on `port_busy`; all three r2 fixes mutated against a green
122/122 control and each dies via the case naming it; `page_chrome`'s `_why` correct on all three
failure routes; `gen-dashboard._fragment` raises so the anchor cannot slide.

## Q4 — another round owed?

**Yes, on both halves of the question.** The redesign is substantial new code, and no round has seen
it. Round 4 reviews the redesign.
