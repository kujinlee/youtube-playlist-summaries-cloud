---
name: the-control-refuted-the-premise
description: "FIRES-WHEN: about to call a premise or cause MEASURED/PROVEN, or to justify new guidance with a baseline — run the control first. TWICE a premise I called measured died to the control I never ran (a skill baseline that measured repo access; a flaky-suite 'cause' that was only red→fix→green)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 92595a72-4e72-4cb8-9e2c-8cddc19a2bb3
  modified: 2026-08-28T02:10:56.597Z
---

⛔ **"red → fix → green" is not a cause, and a baseline is not a finding, until the CONTROL has run under the SAME
conditions.** The control for a fix is *defect present, fix absent*; the control for guidance is *no guidance, same
tool access*. If the control cannot be run, the finding is a **hypothesis** and must be labelled one — especially
before it goes into a handoff, where it becomes the next session's premise and is never re-derived.

**Why:** two instances in two unrelated activities (2026-08-24 a skill baseline; 2026-08-27 a flaky suite), each
written up as measured, each refuted by the control.

**How to apply:**
- Before writing a cause as proven: state *"the defect still reproduces with the fix reverted"* and run it.
- **Tell 1:** a deterministic proposed cause with a non-deterministic symptom (different victims each run) is wrong.
- **Tell 2:** an uncontrolled confound between red and green (e.g. Docker restarted, images pulled) means you changed
  two things.
- Before writing guidance to prevent a failure, ask *what would have to be true for a capable agent to fail here?* If
  "it couldn't see the thing", the fix is access or an explicit "unverifiable from here", never prose.
- A control run inside the repo **auto-discovers the skill you just wrote** (`claude -p --add-dir <repo>` picks up
  `.agents/skills/`): move the skill out for the control run and assert its absence in the output (`grep -c` → 0).
- `superpowers:writing-skills`: *"Always include a no-guidance control. If the control doesn't exhibit the failure,
  there is nothing to fix — stop."*

## History
- **2026-08-24, `explain-findings` (PR #141).** Same three findings, one false. No repo access (3 runs): all 3 accepted
  the false finding, interrogated only its severity, bundled it with a real one. Repo access, skill absent (1 run):
  caught it unaided and found something I had missed. The failure was absent EVIDENCE, not discipline. The first
  control also silently loaded the skill (caught only because the output named it). What survived: the extraction
  (justified by measured duplication; `scripts/check-explainer-delivery.py`, 8-case self-test, caught a restatement in
  my own extraction), shipped with the narrower claim that 4/4 runs failed at **form and delivery** (markdown file
  instead of a served page; one wrote into the repo).
- **2026-08-27, flaky integration suite.** 2 of 538 failed twice; I deleted 15 leftover `vid-%` `jobs` rows, got 535
  green, and wrote the cause up as PROVEN in a handoff. Next session's control — rows left in place: 15 jobs + 100
  videos → 535 passed; 15 jobs + 105 videos → 535 passed. The failures had picked a different pair each run although
  `claim_next_job` orders deterministically, and Docker had been restarted between runs (VM 8,090 → 1,750 MB) with
  newer Supabase images pulled.

Related: [[a-mocked-boundary-tests-the-contract-you-imagined]], [[check-the-assumption-not-just-the-code]],
[[a-hang-is-not-a-diagnosis]], [[quote-the-code-dont-characterise-it]].
