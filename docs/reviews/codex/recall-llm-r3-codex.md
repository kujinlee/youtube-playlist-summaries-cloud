<!-- codex-review: model=gpt-5.5 -->

## HIGH

### H1 · `rc=2` still means “armed but cannot answer” on `--arm`

[file](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/recall-llm.py:934)

Actual line:

```python
raise Refusal(msg)
```

`#202` fixed the hook-visible `--fire` path by mapping `cached_entry_verdict(...)->CANNOT_RUN` to `Unanswerable` at `do_fire`, but the same semantic split was not applied to `--arm`. Once `prepared_prompt()` has successfully read an armed plan, `read_corpus()` still raises bare `Refusal` rc=2 for missing memory, empty memory, or zero triggers. `call_model()` also raises rc=2 after a valid armed plan for missing CLI, timeout, non-zero CLI, or empty model output, and `do_arm()` returns rc=2 when the paid answer cannot be written to cache.

Reproduction, no filesystem writes:

```bash
python3 - <<'PY'
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("rl", "scripts/recall-llm.py")
rl = importlib.util.module_from_spec(spec); spec.loader.exec_module(rl)

plan_text = "- [ ] **Step 1 of 1** — Do\n  - **Doing:** doing it\n"
rl.read_armed_plan = lambda: ("plan: p.md\n", Path("p.md"), plan_text)
rl.memory_dir = lambda: None

try:
    rl.prepared_prompt()
except rl.Refusal as exc:
    print(exc.rc, str(exc))
PY
```

Observed: rc `2` with a readable armed plan, because only the corpus is missing.

Enumeration I get:

`--fire` rc=2 paths:
- no sentinel: genuinely routine absence.
- bad CLI usage if not actually naming `--fire`: outside the hook path.

`--fire` non-routine armed failures now split correctly:
- unreadable sentinel/plan/no plan named/vanished plan/mixed plan: rc=5.
- missing/stale/bad cache, vanished entry, lost trigger: rc=3.
- valid cache names an entry and corpus is unreachable: rc=6.
- cached `NONE` with missing corpus: rc=0, intentionally silent.

`--arm` rc=2 paths:
- no sentinel: routine absence.
- no memory directory after a plan is armed: not routine.
- memory directory has zero entry files: not routine.
- memory files exist but zero triggers: not routine.
- `claude` missing, timeout, non-zero, or empty stdout after preflight: not routine.
- cache write failure after a paid answer: not routine.

Observation that would prove this wrong: `prepared_prompt()` or `do_arm()` emits rc=6 or another non-routine code for an armed readable plan with an unreachable/unusable corpus, while preserving rc=2 only for no armed plan.

## MEDIUM

### M1 · `check-rc-contract.py` can miss a real handled arm by indentation, including rc=4

[file](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:101)

Actual line:

```python
_ARM_RE = re.compile(r"^\s{2}(\d+)\)", re.M)
```

The guard does not parse the bash `case`; it recognizes only arms indented by exactly two spaces. That makes the `DELIBERATELY_UNHANDLED[4]` reason fragile: rc=4 can become handled by the hook and still be invisible to the checker if the arm is indented differently.

Reproduction:

```bash
python3 - <<'PY'
import importlib.util
spec = importlib.util.spec_from_file_location("crc", "scripts/check-rc-contract.py")
crc = importlib.util.module_from_spec(spec); spec.loader.exec_module(crc)

D = {"OK": 0, "CANNOT_RUN": 2, "STALE_CACHE": 3,
     "BAD_RESPONSE": 4, "UNREADABLE_PLAN": 5, "UNANSWERABLE": 6}

hook = '''case "$RC" in
    4) PAYLOAD="rejected. Detail: $OUT" ;;
  0) : ;;
  3) : ;;
  5) : ;;
  6) : ;;
  *) : ;;
esac
'''

print("handled:", crc.handled_codes(hook))
print("unguarded:", crc.unguarded_detail_arms(hook))
print("verdict:", crc.verdict(D, crc.handled_codes(hook), crc.unguarded_detail_arms(hook)))
PY
```

Observed: `handled` is `{0, 3, 5, 6}`, `unguarded` is `[]`, and `verdict` is `[]`, even though bash would handle rc=4 and build an unguarded `Detail:` payload. That is exactly the class this guard claims to own.

Observation that would prove this wrong: the checker either rejects any real `case` arm not matching the canonical indentation, or parses the actual case structure and reports the four-space `4)` arm.

## LOW

### L1 · The architecture review’s corrected verdict is now stale about the seam guard

[file](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/reviews/architecture-review-2026-09-30-recall-matcher.md:54)

Actual line:

```markdown
> **The rc contract spans TWO LANGUAGES, nothing reconciles the codes the matcher emits against the
```

That was true for the reviewed tree, but the current branch now includes `scripts/check-rc-contract.py`, and CI runs it. The stronger current claim is “a reconciliation guard exists, but it is shape-fragile” rather than “nothing reconciles.”

Reproduction:

```bash
python3 scripts/check-rc-contract.py
rg -n "check-rc-contract.py" .github/workflows/ci.yml
```

Observed: the guard runs and reports agreement, and CI has dedicated steps for both the guard and its self-test.

Observation that would prove this wrong: the document is explicitly scoped as a historical pre-guard snapshot, not as the current architecture review carried forward in this branch.

## What I Could Not Establish

I did not run the real hook as sole caller against the live `.claude` state, because that would consume or mutate the live dedupe markers. I verified the hook/message logic by reading the current arm shapes and by running the Python-side gates. Current claimed gates I ran: `recall-llm.py --self-test`, `check-rc-contract.py`, and `check-rc-contract.py --self-test`; all passed.

Not converged: H1 keeps the rc=2 conjunction alive on `--arm`.
