---
name: instruction-is-not-isolation
description: "FIRES-WHEN: handing an agent input files while the answer key, labels or expected output live anywhere it could reach"
metadata:
  type: feedback
---

⛔ **Telling an agent "read only these two files" is not a blind.** A directory listing hands it
everything else in the folder. **Instruction is not isolation.**

⭐ **Measured 2026-09-29, backlog #191.** A blind matching probe scored 80/80 — with
`mixed-key.json`, containing every label and every `kind`, sitting in the directory it had been
told to read from. The instruction was explicit and correct, and it proved nothing: the result was
indistinguishable from the agent having read the key.

**The fix is to rebuild the world, not to ask.** Asking the agent what it opened is weak evidence —
it may not report accurately, and a contaminated run has every reason to look clean. Instead:
a directory holding *only* the inputs, output written to a **different** directory, a fresh agent,
and a required report of every path opened. Re-run gave the same 80/80, agreeing with the suspect
run on 79/80 — so the result stood, but it could not have been defended an hour earlier.

⭐ **A graded confidence distribution is corroborating evidence, not proof.** The suspect run's
uncertainty landed exactly on the items whose labels pre-declared two acceptable answers, and its
rationales named the near-miss entries it rejected — which a key-reader would not produce. Useful,
but it was the clean room that settled it.

**How to apply:** when spawning a blind agent, `mkdir` a fresh input directory and copy in only
what it may see, before writing the prompt. Costs one command. See
[[a-case-can-pass-for-an-ambient-reason]], [[concurrent-agents-go-wrong]],
[[a-forced-choice-test-cannot-fail]].
