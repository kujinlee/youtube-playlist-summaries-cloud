---
name: after-fixing-search-for-the-class
description: "FIRES-WHEN: having just fixed a defect (or a reviewer's listed instances), before claiming it fixed or writing a comment that says a class is closed. Fixing the instance, not the class, is my dominant failure — SEARCH for the class"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9a5869f4-2023-4101-bcc9-ee6ffd9db5f3
  modified: 2026-08-27T21:29:46.327Z
---

**The rule: before claiming a fix done, ask "what else is this true of?" and answer it with a SEARCH, not a recollection. Then LOOK AGAIN — a fix believed to close the class usually does not.**

**How to apply — three questions, in order, after any fix:**
1. **Another LEVEL?** (encoding, nesting, indirection — `%2e` fixed, `%25` not; a statement one indent deeper.)
2. **Another SITE doing the same job?** (a second producer, the identical bug 26 lines up, a sibling refusal.)
3. **Another COPY of this sentence/number?** (grep the number or the message shape across every file.)

Concretely: a wrong number → grep it everywhere; a mishandled delimiter → enumerate EVERY delimiter the format uses and test each; a guard for one KIND → probe every kind the code claims; a dying call site → grep the SHAPE (e.g. `grep -n "args\[\|\.args)"`, under a minute).

- ⭐ **A reviewer's finding LISTS INSTANCES; it does not define the class.** Name the general shape and check the fix covers shapes nobody has written yet.
- ⛔ **A comment may state what was FIXED. It may not state that a CLASS is closed** ("one owner for X") unless a search was run and can be quoted — an overclaiming comment tells the next reader not to look.
- **When two components must agree about an input, assert the AGREEMENT,** not either side's behaviour.
- A case with no mutation manifest has never been shown able to fail; a decorative guard and a real one read identically.

**Why:** after finding a defect I look at the thing I fixed, not at what else is true of it. The cost of asking is one grep; not asking cost extra review rounds on every branch below.

## History (condensed)

- **2026-08-27, backlog #65 (PR #160, `201d2d8`):** **4 of 9** findings were instance-not-class, **reviewers found all four, I found none** — `27` corrected in one sentence and live four sentences later; a dangling `⛔ AND` fixed with its twin 26 lines up; a refusal with no remedy beside the one I fixed; `#` in identifiers fixed and `@` shipped in the same commit.
- **2026-09-08, backlog #91 r3:** I wrote in code *"ONE OWNER FOR THE WORD 'assembled', and it is `files`"* — false when written; a second route existed since `master`; all 223 cases blind to it in both directions. Round 4 found it.
- **2026-09-15, PR #295 r8:** killed the two bypasses a reviewer constructed; the next reviewer killed the case again one indent in (`httpd.timeout = …` inside the `try`) — case GREEN, 2 of 3 mutations survived; the file had no manifest for its 140 cases. Filed backlog #122, #125; PR parked.
- **2026-09-16, PR #312:** three instances in one round — `%25` after `%2e` (a REGRESSION: decoding before a resolver that decodes again; master refused `%252e`, my fix served it), a second HTML producer, a second paragraph repeating corrected advice.
- **2026-10-04, `d2-main-drivable` — the search paid:** round 5 wrapped one site; round 6 found two siblings; grepping the shape found a **thirteenth** dying site no review had named.

Related: [[a-convention-catches-what-you-read]], [[a-shim-can-fail-in-both-directions]] (measuring found six where I saw one), [[dual-review-what-it-catches]], [[assert-the-property-not-the-mechanism]], [[cannot-die-may-mean-a-second-clause]].
