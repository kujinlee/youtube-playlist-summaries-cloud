---
name: the-control-refuted-the-premise
description: "FIRES-WHEN: about to call a premise MEASURED without having run the control — ⭐ TWICE: a premise I called MEASURED died to the control I never ran. (1) a skill's 3/3 baseline was an artifact of no-repo-access; (2) a flaky-suite cause I recorded as PROVEN was only red→fix→green, and the suite is green with the 'cause' still present"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 92595a72-4e72-4cb8-9e2c-8cddc19a2bb3
  modified: 2026-08-28T02:10:56.597Z
---

**Two instances. §1–3 = 2026-08-24 (`explain-findings`, PR #141). §4 = 2026-08-27 (flaky integration
suite) — the same hole in a completely different activity, which is why this is a class, not an
anecdote.**

## 1 — The baseline I "measured" was an artifact of the test setup

Four fresh-context runs, same three findings, one of them **false** (true premise, conclusion that
does not follow):

| Condition | Result |
|---|---|
| no repo access (3 runs) | all 3 accepted the false finding; interrogated only its **severity**; bundled it with a real one as "same root cause" |
| repo access, skill absent (1 run) | **caught it unaided** — named the field that actually carries the claim, quoted the consumer, refused to bundle, and found something I had missed |

**The failure was absent EVIDENCE, not absent discipline.** Agents that could not read the code
reasoned around the gap; one that could did not need telling. I had been about to ship a skill whose
stated justification was the artifact.

`superpowers:writing-skills` says this explicitly and it is worth obeying literally: *"Always include
a no-guidance control. If the control doesn't exhibit the failure, there is nothing to fix — stop."*
**Run the control under the SAME conditions as the treatment.** Different tool access between arms
means you measured access, not guidance.

**How to apply:** before writing guidance to prevent a failure, ask *what would have to be true for a
capable agent to fail here?* If the answer is "it couldn't see the thing", the fix is access or an
explicit "unverifiable from here", never prose. Related: [[a-mocked-boundary-tests-the-contract-you-imagined]]
(the inverse error — the fixture hid the real contract).

## 2 — A control run inside the repo AUTO-DISCOVERS the skill you just wrote

The first control announced *"Using `.agents/skills/explain-findings` (project-local skill,
untracked)"*. `claude -p --add-dir <repo>` picks up `.agents/skills/`, so the "before" arm silently
became an "after" arm. It was caught only because the output named a skill that was supposed to be
absent.

**Move the skill out of the tree for the control run** (`mv` it to a temp dir, run, move it back) and
**assert its absence in the output** (`grep -c '<skill-name>'` → 0) rather than assuming.

## 3 — What survived, and why the work was still worth it

The **extraction** was independently justified by measured duplication (the delivery loop written out
in full in two skills), and `scripts/check-explainer-delivery.py` (8-case self-test) caught a
restatement I had missed **in my own extraction**. The skill shipped with the honest, narrower claim
that 4/4 runs failed at **form and delivery** — every one produced a markdown file instead of a
served page, one wrote it into the repo — with a table in its own body telling the reader not to cite
its baseline as proof the epistemic rule is load-bearing.

## 4 — ⭐ "red → fix → green" IS NOT A CAUSE. The control is *defect present, fix absent*

**MEASURED 2026-08-27.** The integration suite failed 2 of 538 twice. I deleted 15 leftover `vid-%`
`jobs` rows, it went **535 green**, and I wrote the cause up as **PROVEN** — in a handoff, as the
recommended next task, with a fix already chosen.

**The next session ran the missing control: leave the rows in place and just run it.**

| Run | Leftover rows present | Result |
|---|---|---|
| control 1 | 15 `jobs` + 100 `videos` | **535 passed, exit 0** |
| control 2 | 15 `jobs` + 105 `videos` (dirtier) | **535 passed, exit 0** |

The leftovers are **not sufficient** to make the suite red, so "proven" was never earned. What I had
was one arm of a two-arm experiment. **A fix that precedes a green run explains nothing until you
have also run the defect WITHOUT the fix.**

**Two tells I walked past, both visible at the time:**

1. **The failures picked a DIFFERENT pair each run.** The claim rests on `claim_next_job`'s
   `order by created_at, id` — which is *deterministic*, so a data cause selects the **same** victims
   every time. Varying victims means timing or resources, not rows. *When the proposed cause is
   deterministic and the symptom is not, the cause is wrong.*
2. **An uncontrolled confound sat between red and green:** Docker was restarted (VM footprint
   8,090 → 1,750 MB) and Supabase pulled newer images. I changed the data *and* the machine, then
   attributed the result to the data.

**How to apply:** before recording a cause as proven — especially before writing it into a handoff,
where it becomes the next session's starting premise and is never re-derived — state the control
(*"the defect still reproduces with the fix reverted"*) and **run it**. If it cannot be run, the
finding is a **hypothesis**, and must be labelled one. Related:
[[check-the-assumption-not-just-the-code]], [[a-hang-is-not-a-diagnosis]] (one observation is not a
diagnosis), [[quote-the-code-dont-characterise-it]].
