---
name: after-fixing-search-for-the-class
description: "FIRES-WHEN: having just fixed a defect, before moving on — ⭐ MEASURED 2026-08-27 — FOUR instance-not-class defects in ONE slice, two in ONE commit; reviewers found all four, I found none. After fixing X, SEARCH for the class of X before claiming it fixed"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9a5869f4-2023-4101-bcc9-ee6ffd9db5f3
  modified: 2026-08-27T21:29:46.327Z
---

**Fixing the instance in front of me and not the class is my dominant failure shape.** Measured on
backlog #65 (PR #160, merged `201d2d8`): **four of nine review findings were exactly this**, and
**reviewers found all four — I found none of them.**

| I fixed | What was still there |
|---|---|
| `27 foreign objects` → 15 in one sentence | `27` still live **four sentences later, in the same backlog row** |
| the dangling `⛔ AND` in the drift branch | the identical bug **26 lines up, same function**, untouched |
| the unreachable remedy on the drift failure | the refusal **beside it** printed *no* remedy at all |
| `#` inside an identifier in `load_accepted` | `@` does the same thing — **in the same commit, minutes later** |

The last pair is the sharpest: I wrote the `#` fix *and its rationale*, then shipped the identical
hole one delimiter over. Codex found `@` by reading the same file I had just edited.

**Why:** after finding a defect I look at the thing I just fixed, not at what else is true of it.
The evidence is a *reason to search*, and I treat it as a task that is now complete.

## The habit

**Before claiming a fix is done, ask: "what else is this true of?" — and answer it with a SEARCH, not
a recollection.** Concretely:

- a wrong NUMBER → grep the number across every file, not just the sentence you corrected;
- a wrong MESSAGE → grep the message's shape (`⛔ AND`, `regenerate the`) across the function/file;
- a DELIMITER mishandled (`.`, `#`, `@`, quote, backslash) → enumerate **every** delimiter that
  string format uses and test each one;
- a guard added for one KIND → enumerate every kind the code claims to cover and probe each.

The cost of asking is one grep. The cost of not asking, here, was two extra review rounds.

**Related:** [[a-convention-catches-what-you-read]] (a script catches what a hand pass does not),
[[a-shim-can-fail-in-both-directions]] (measuring found six where I had seen one),
[[dual-review-what-it-catches]] — the halves caught different instances of this, which is
the strongest practical argument for running both.


---

## ⭐ ⟳ 2026-09-08 — the aggravated form: a COMMENT asserting the class is closed

Backlog #91 r3 fixed one route to a self-contradicting evidence block and I wrote, in the code:

> *"⟳ code review r3, H3. **ONE OWNER FOR THE WORD 'assembled', and it is `files`.**"*

It was **false when written**. A second route — a file tagged with a non-python fence is reported *and assembled anyway* — had existed since `master`, measured identical on every revision. Round 4 found it from the shipped CLI.

**An overclaiming comment is worse than no comment, because it tells the next reader not to look.** A normal instance-not-class defect waits to be found; this one actively deflects the search. ⚠ And all 223 cases were blind to it **in both directions** — the reviewer applied the fix and the suite stayed green either way, so nothing would ever have contradicted the sentence.

**Rule: a comment may state what was FIXED. It may not state that a CLASS is closed unless a search was run and can be quoted.** "One owner for X" is a claim about every site that writes X — so `grep` for the writes before writing the sentence.

## ⟳ 2026-09-15 — THE SHARPEST INSTANCE YET: closing exactly what the reviewer NAMED

PR #295, round 8. A reviewer measured **two** ways to bypass a property case:

    os.close(w_fd); detach_streams()             -> predicate True
    with httpd, open("/missing") as _x:          -> predicate True

I rewrote the case over the AST and killed **both**. The next reviewer then killed the case again —
with the same defect **one indent in**, inside the `try` the write lives in:

    httpd.timeout = float(os.environ["EXPLAINER_TIMEOUT"])   # after the K write, INSIDE the try
    -> rc=0, "serving … (pid 50580)", pidfile names a DEAD pid, nothing listening
    -> the case: GREEN.  2 of 3 mutations against it survived.

⭐ **A REVIEWER'S FINDING LISTS INSTANCES; IT DOES NOT DEFINE THE CLASS.** Closing every example
someone hands me feels like completeness and is not — the examples are what *they* happened to
construct. The question after any fix is *"what is the general shape, and does my fix cover shapes
nobody has written yet?"* Here the general shape was **"a statement after the readiness byte that
can fail"**, and my fix covered only *statements at the same nesting level as the ones quoted*.

⚠ **AND IT WAS A GUARD FOR A GUARD.** The case existed to catch a specific High; it was green while
that exact High was happening. See [[assert-the-property-not-the-mechanism]] — an AST check is not
automatically a property check; mine still recognised a *shape*.

⛔ **THE ROOT ENABLER, WORTH MORE THAN THE INSTANCE:** the file had **no mutation manifest**, so none
of its 140 cases had ever been shown able to fail. Without that, a decorative guard and a real one
read identically. Filed as backlog #122 and #125; PR #295 was PARKED behind them rather than merged.



## ⟳ 2026-09-16 — FOUR CONSECUTIVE BRANCHES, and one round had THREE instances

PR #312 alone: the `%25` level of an encoding bug I had just fixed at `%2e`; a second HTML producer
twelve lines of diff from the one I escaped; and a second paragraph in the SAME document repeating
the advice I had just corrected. Each time I fixed exactly what the finding showed me.

⭐ **The `%25` one is the sharpest, because the fix was a REGRESSION rather than an omission.**
Decoding in the classifier and handing the decoded string to a resolver that decodes AGAIN moved the
disagreement up one encoding level — master refused `%252e`, my fix served it. **When two components
must agree about an input, assert the AGREEMENT, not either side's behaviour.**

**How to apply, sharpened:** after any fix, ask the three questions in order — *is there another
LEVEL of this (encoding, nesting, indirection)? another SITE that does the same job? another COPY of
this sentence?* All three were productive here, and all three were cheap to ask.

⟳ **2026-10-04, `d2-main-drivable`, and this one PAID — the rare case where I ran the search and it
returned.** Round 5 wrapped ONE site whose case died rather than reported, and treated the class as
done. Round 6's review found **two siblings**. Instead of fixing those two, I grepped the *shape*
— every indexed access to a call's arguments — and found a **thirteenth dying site no review has
ever named**, plus a fourth uncovered member of the same class.

**The sequence is the lesson: fix the class, then LOOK AGAIN.** Round 5 fixed an instance and
believed the class closed; round 6 proved it had not; the grep then beat round 6 too. Two reviews
and a search were needed for one shape.

⚠ And the cheap version is enough — this was `grep -n "args\[\|\.args)"` with the AST-attribute
spellings filtered out, under a minute. See [[cannot-die-may-mean-a-second-clause]].
