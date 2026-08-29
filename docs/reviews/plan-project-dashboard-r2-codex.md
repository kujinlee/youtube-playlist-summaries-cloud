<!-- codex-review: model=gpt-5.5 -->

> **Editor's note, added after the run — read before the findings.**
>
> **Subject reviewed:** plan `4077817` (v2). While this was running, `7ce2ac6` (v2.1) landed, which
> had **already fixed** two of the findings below — the HTML-comment exemption (High) and the
> mismatched-fence toggle (Medium). Those were found independently, from two directions, which is
> confirmation the defects were real rather than duplicated effort. The other five were new and are
> all now addressed in the plan; dispositions are in its *Round 2* section.
>
> **The Blocking about `gen-dashboard.py --self-test` is a finding about MY verification, not just
> the plan.** I had reported 55/55 for that suite. Transcribing the plan into a scratch file I wrote
> `"could not"` where the plan says `"could not tell"`, and the weakened assertion passed. Codex
> transcribed faithfully and got 54/55. The green I reported was measured against a softened test.
>
> **⚠ The Claude half of round 2 has NOT run**, so this round is one reviewer, not two. Round 1's
> halves overlapped on only 2 of ~26 findings. Do not read a single NOT CONVERGED — or a later
> single CONVERGED — as the gate.
>
> REVIEW GAP: claude — the half needs a fresh subagent with an independent read of the plan, and
> this session is configured not to spawn subagents unless the user asks. A pass written by the
> context that authored v2 is not the missing half: this very round proves why, since its headline
> Blocking is that my own transcription silently weakened an assertion and reported green. **Run
> `superpowers:requesting-code-review` against the plan before the PR opens.** Until then, round 2's
> Blocking/High list is one reviewer's, and the overlap that made round 1 trustworthy is absent.

READY TO EXECUTE: NO

Shortest must-change list: fix the failing dashboard self-test, move `check-dashboard-entry.py` creation before `no_entry_prs()` verification or defer that verification, remove `set -e` from the scratch controls or guard expected failures, fix CI’s base ref fetch, and harden `NO-ENTRY:` parsing against invisible/commented or mismatched-fence declarations.

**What I Ran**
Transcribed the plan Python into `/tmp/dashboard-plan-r2b`.

Actual outputs:

```text
$ python3 /tmp/dashboard-plan-r2b/01.python --self-test
NotImplementedError
rc=1

$ python3 /tmp/dashboard-plan-r2b/20.python --self-test
NotImplementedError
rc=1

$ python3 /tmp/dashboard-plan-r2b/check_dashboard_entry.py --self-test
20/20 passed
gate_rc=0

$ python3 /tmp/dashboard-plan-r2b/gen_dashboard.py --self-test
  [FAIL] gh failure says could not tell
    got:  False
    want: True

54/55 passed
gen_rc=1
```

Task 4 controls A-E were run verbatim and stopped at A because of `set -e`. Re-run without `set -e`, A-E produced the expected pass/refuse sequence.

NOT RUN: browser/manual Task 5 fold behavior and Ask-tray visual checks, because the implementation is still a plan, not installed into the repo.

Blocking — “Run: `python3 scripts/gen-dashboard.py --self-test` Expected: exit 0, no `[FAIL]` lines.”
What I checked: assembled `gen-dashboard.py` from the plan’s Python blocks, then ran `python3 /tmp/dashboard-plan-r2b/gen_dashboard.py --self-test`.
Actually true: the self-test fails:
```text
[FAIL] gh failure says could not tell
  got:  False
  want: True
54/55 passed
gen_rc=1
```
The renderer says “I could not also check open pull requests”, but the test asserts the exact substring `could not tell`.
VERIFIED

Blocking — “Step 6: Verify both against the real repo … `no-entry: 0` is expected today”
What I checked: `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md:544-585`; ran `no_entry_prs()` with `scripts/check-dashboard-entry.py` absent, which is the Task 2 state because the gate is not created until Task 4.
Actually true:
```text
absent: (None, "could not load the gate's exemption reader: [Errno 2] No such file or directory: '/tmp/dashboard-plan-r2b/check-dashboard-entry.py'")
```
Task 2 depends on a file created two tasks later. The expected `no-entry: 0 err: None` cannot happen in task order.
VERIFIED

Blocking — “Required output — all five, or the gate is not proven”
What I checked: Task 4 Step 6, lines `1358-1396`, run verbatim in a throwaway git repo.
Actually true: the script exits at Control A because `set -e` treats the expected refusal as fatal:
```text
REFUSED — 1 tracked file(s) changed and no entry was added to docs/dashboard-entries.md...
```
Exit code was `1`; it never printed `A rc=1` and never reached B-E. Without `set -e`, A-E do produce:
```text
A rc=1
B rc=0
C rc=1
+## not-a-date
D rc=1
E rc=0
```
VERIFIED

High — “`git fetch --no-tags --depth=200 origin "$GITHUB_BASE_REF"` … `--base "origin/$GITHUB_BASE_REF"`”
What I checked: Task 6 Step 5, lines `1726-1735`; simulated a branch-only shallow checkout and then ran the proposed fetch plus ratchet.
Actually true:
```text
fetch_rc=0
CANNOT RUN — git diff exited 128: fatal: ambiguous argument 'origin/master...HEAD': unknown revision or path not in the working tree.
ratchet_rc=2
```
The fetch can succeed while still not creating `origin/$GITHUB_BASE_REF`. This is loud, but it makes the CI ratchet not reliably runnable as written.
VERIFIED

High — “Exemptions must be explicit and visible”
What I checked: `exemption_reason()` with `NO-ENTRY:` inside an HTML comment.
Actually true:
```text
leading html comment line => 'hidden?'
```
A PR body containing:
```html
<!--
NO-ENTRY: hidden?
-->
```
passes the gate with a declaration hidden from the rendered PR body. That violates the visibility requirement.
VERIFIED

Medium — “Fenced code is skipped”
What I checked: `exemption_reason()` with a fence opened by backticks and “closed” by tildes.
Actually true:
```text
mismatched tick tilde => 'after?'
```
The parser toggles on either ``` or `~~~`, so it treats a mismatched closer as ending the fence. CommonMark requires the closing fence to match the opener character.
VERIFIED

Medium — “A header typed without the space (`##2026-08-28`) must become a MALFORMED entry”
What I checked: plan lines `139-144`, spec lines `111-115`, and `parse_entries("##2026-08-28\nNo space.\n")`.
Actually true:
```text
no-space
[('2026-08-28', '2026-08-28/1', 'No space.', False, None)]
```
The code accepts it as a normal entry, while the plan comment says malformed and the spec grammar says block start is `## ` followed by the date.
VERIFIED

NOT CONVERGED
