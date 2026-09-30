---
name: extract-and-run-a-plans-code
description: "FIRES-WHEN: reviewing a plan or spec that contains fenced code — A plan containing fenced code is EXECUTABLE — extracting and running it found 2 defects that three careful readers all read past"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 66a4d4cf-146a-4aa0-8d45-f3efd21579f7
  modified: 2026-09-12T14:42:00.144Z
---

**A plan full of ```python blocks is not prose. Extract the blocks into a module and RUN them
against the plan's own test cases.** Measured 2026-09-11/12 on the goal-work-threads plan: 39 cases
extracted, 2 failed — and both had been read past by Codex, by a Claude reviewer, and by me.

**Why:** ⭐ Post-Plan Gate round 3 found one Blocking by three independent routes. Codex found it by
reading. The Claude half found it by transcribing the plan into a module and running the suite. I
found it by extracting the code blocks and executing every case. But the *second* defect in the same
two lines was **invisible to reading** and only the two executing routes caught it:

- `d["rel"]` → `KeyError` on a record without one.
- `d.get("rel")` → returns `None`, so **every rel-less document keys to the same `None`**, the extra
  document matched the spec, and it was silently dropped. *The case written to prove extras render
  proved the opposite, and looked correct on the page.*
- `d is x` → exact, because `pair_documents` appends the same object it assigns to the slot.

Three attempts at one two-line fix. Same arc as `DOC_PATH`, which narrowed three times.

**How to apply:**

```python
blocks = re.findall(r"```python\n(.*?)```", plan_text, re.S)
impl = [b for b in blocks if re.search(r"^(def |[A-Z_]+ = )", b, re.M) and "eq(" not in b]
# write impl + stub esc/inline_md/ROOT to a scratch module, then run every eq() case
```

Do it **before** dispatching reviewers, not after — it turns prose findings into red tests and makes
the round cheaper. It is also the argument for stopping a review at three rounds when every Blocking
is the previous round's fix: see [[a-filed-finding-s-proposed-fix-is-a-hypothesis]] and
[[after-fixing-search-for-the-class]].
