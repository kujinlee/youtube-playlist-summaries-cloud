---
name: explain-findings
description: Use when findings, defects, review results or open questions need a file / don't-file / severity decision from a human — including "should this be a backlog item", "triage these", "explain this issue", or a list of things an investigation turned up. Not for explaining a code change (use explain-diff) or reporting where work stands (use brief).
---

# Explain Findings

Build a page that lets a human decide, **per finding**, whether it becomes a tracked item and at what
severity.

**Announce at start:** "Using explain-findings to build a verdict page."

## The one rule

**Re-derive every finding's conclusion before you present it, and mark the verification status of
each claim inline, next to the claim.**

Not in a trailing "limits" section. Each finding is an independent claim, so a status that does not
travel attached to it protects nothing.

**If you cannot reach the evidence, that is the finding.** Say "unverifiable from here, and here is
what would verify it" and stop. Do not substitute reasoning for the read — that substitution is the
single failure the baseline below actually caught.

## What the baseline actually showed (measured 2026-08-24) — read this before trusting the rule below

Four fresh-context runs were handed the same three findings from a real investigation. One finding
was **false**: a true fact about write ordering with a conclusion that did not follow.

**Without repo access (3 runs): all three accepted the false finding.** Each interrogated its
*severity* and none its *truth* —

> "Impact turns on what reads the annotation downstream — cosmetic if display-only, materially
> worse if anything treats it as applied state. **Establish that before sizing.**"

— and all three bundled it with a real finding as "same root cause, one fix closes both".

**With repo access (1 run, this skill absent): it caught the false finding unaided.** It named the
field that actually carries the claim, quoted the consumer, refused to bundle the two findings, and
surfaced something the investigator had missed (a retry default that under-reports usage on the
*success* path too).

**So the epistemic rule below is NOT what this skill buys you.** A capable agent that can read the
code already applies it. What the baseline shows is narrower and worth stating honestly:

| Measured | Implication |
|---|---|
| 3/3 without access accepted a false finding | The failure is **absent evidence**, not absent discipline. Get access, or say the claim is unverifiable — never reason around it |
| 4/4 produced a markdown file, not a served page | The **form and delivery** are what nobody converges on unaided |
| 1/4 wrote its document **into the repo** (`docs/reviews/`) | Left uncorrected, these accumulate as untracked clutter |

**Do not cite this section as proof that the rule is load-bearing.** It is proof that the rule is
*correct* — an independent run reached it unprompted — and that the **form** is what needs writing
down. If you find yourself about to claim this skill prevents a defect, re-read this table first.

| Rationalization | Reality |
|---|---|
| "The investigator already checked this" | You are the second reader. That is the entire value you add. |
| "The evidence is code reading, so it's cheap to confirm later" | Then confirm it **now** — later never arrives, and you are about to ask someone to spend on it. |
| "The open question is how bad it is" | That question presumes the answer to a prior one. Ask whether it is true first. |
| "It's the same root cause as the real one" | Shared code path is not shared defect. Bundling a false finding is how a fix gets designed around a fiction. |
| "I'll flag it as unverified and let the maintainer decide" | Handing over an unverified claim with a label is not triage, it is forwarding. |

## Red flags — STOP and go read the consumer

- You are about to write "impact depends on what reads X" — **go read what reads X.**
- You are about to write "confirmable with one query" — **run the query.**
- You are grouping findings by "same root cause" before each is independently confirmed.
- You are describing a field's meaning from its **name** rather than from a call site.
- Your only open question about a finding is its severity.

## Before writing anything

1. **Take each finding one at a time.** Do not read them as a set; a set invites bundling.
2. **For every claim of the form "X means Y" or "so Z is broken": find the code that consumes X.**
   `grep` the symbol across the whole tree, open each hit, and read what it does with the value. A
   negative claim ("nothing checks this") requires a search, never a read.
3. **Re-derive the conclusion.** The premise being true does not make the conclusion true. Write down
   which of the two you actually confirmed.
4. **Run what can be run.** A production read, a test, a query — anything that converts *argued* to
   *measured* before the page is written, not after.
5. Record what you could not check, and say why, per finding.

**Count how many findings changed status because you did this, and report that count.** Zero is a
valid answer and a suspicious one.

## Verification vocabulary — use exactly these

| Label | Means |
|---|---|
| **MEASURED** | a command was run and its output observed, in this invocation |
| **OBSERVED** | seen directly (a UI, a log, a response body), not inferred |
| **READ** | confirmed by opening the code, quoting `file:line` |
| **ARGUED** | reasoning over measured facts; nothing executed |
| **UNVERIFIED** | could not be checked — say what would check it |

`ARGUED` is not a failure state. Presenting `ARGUED` in the register of `MEASURED` is.

## Sections, in this order

1. **Masthead** — the decision being asked for, in one sentence, and where the findings came from.
2. **Stat strip** — how many findings, how many recommended for filing, **how many changed status
   during this pass**, and the money or scope at stake if there is any.
3. **Verdicts at a glance** — one row per finding: verdict (FILE / WITHDRAW / NEEDS-WORK), proposed
   severity, and the basis chip. A reader who stops here has what they need.
4. **One section per finding**, each containing:
   - the claim, stated plainly;
   - the evidence, with `file:line` quoted and any measurement shown as its actual output;
   - **the verification status of each load-bearing sub-claim**, inline;
   - the consequence — what it costs if real, using observable units;
   - the proposed severity **and why not the neighbouring one**;
   - options where a genuine fork exists, with a recommendation.
5. **Withdrawn findings get a full section, not a footnote.** What was claimed, what re-reading
   showed, and why the behaviour is correct. This is the highest-value section on the page: it is the
   one that saves the reader work, and the one a reader is most likely to disbelieve without detail.
6. **What is measured, what is only argued** — one row per claim across all findings, using the
   vocabulary above. Include your own inferences here, especially the alarming ones.
7. **Recommendation** — what to file, at what severity, with the strongest argument against it and
   your answer to that argument.
8. **Ground-truth footer** — commit, branch, deployed release, and the timestamp.

## Severity: state the observation that would move it

Never assign a severity by feel. For each, name what would make it one level worse and one level
better. If no observation distinguishes them, the severity is a guess — say so.

A finding that spends money, evades a bound, or corrupts durable data is at least as severe as the
worst thing a caller can reach on purpose — not the worst thing observed by accident.

## Delivery

**Follow `../shared/explainer-delivery.md`** — file location, the self-contained-HTML rules, the Ask
tray, `explainer-serve.py`, arming the Monitor push loop, and answering in the page. It is the one
description of that loop; do not restate it here.

Visual craft comes from `artifact-design`. One colour must mean one thing everywhere: pick a hue for
defects, one for verified/measured, one for structural fact, one for decisions, one for withdrawn —
and reuse it in chips, callouts and table cells.

## When NOT to use this

- **A code change** → `explain-diff`. It has a diff; this has claims.
- **Where the work stands** → `brief`. It reports state; this asks for a verdict.
- **Unfamiliar code** → `zoom-out`.
- **A single finding you have already verified and the user has already agreed to file** → just file
  it. A page is for a decision that has not been made.

## Common mistakes

| Mistake | Fix |
|---|---|
| Findings presented in the investigator's words | Re-derive first; your wording should differ because your evidence does |
| A "limits" section at the end | Status per claim, inline. The end is where readers stop |
| Withdrawn finding deleted from the page | Keep it, with the reasoning. Absence teaches nothing |
| Every finding recommended for filing | If nothing was refuted, say what you checked to earn that |
| Severity stated without a falsifier | Name the observation that would move it |
