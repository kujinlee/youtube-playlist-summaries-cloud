<!-- codex-review: model=gpt-6.1-sol -->

Both baseline suites pass (35/35 and 76/76). All eight new mutations fail their named cases. Two Major defects remain, reproduced entirely in temporary copies.

1. **Major — cycle cutting detaches valid tails and invents additional work lines.**  
   `scripts/gen-work-lines.py:123–133`

   **Input:** `y → z → y`, with `a.parent = y` and `b.parent = z`.

   The cut selects the alphabetically first **unplaced** node:
   ```python
   cut = min(s for s in by_slug if s not in seen)
   ```
   Unplaced nodes include descendants outside the cycle. Here it cuts `y → a` and `z → b` before cutting the actual cycle.

   **Executed output:**
   ```text
   TAILS roots/children [('a', [], True), ('b', [], True), ('y', ['z'], True)]
   ```
   Rendering reports:
   ```html
   3 line(s) · <strong>3 still owe something</strong>
   ```
   It also falsely says that `a`’s and `b`’s recorded parents “lead back to itself.” Neither tail participates in a cycle. One connected work line becomes three, losing valid lineage.

   **Suggested fix:** follow parent pointers until a repeated node identifies the actual cycle; detach one edge belonging to that cycle. Add a fixture whose tails sort before its cycle members, asserting one root, one cycle cut, and retained tail attachments. The existing tail fixture uses `t` after `a`/`b`, avoiding this failure.

2. **Major — sentinel validation still attaches an unrelated same-stem Markdown plan.**  
   `scripts/begin-plan.py:366–372`

   **Input:** two distinct files exist:
   ```text
   .claude/plans/real.md
   .claude/plans/real.txt
   ```
   Arm `real.txt` through supported `--plan` mode, then begin `nonmd-child`.

   **Executed output:**
   ```text
   NONMD --plan rc 0 begin rc 0 parent real
   ```

   Validation checks the resolved directory and existence, then returns `target.stem`. It does not check whether the target is a file the generator reads. `read_plans()` at `scripts/gen-work-lines.py:271` reads only `*.md`, so the child attaches to unrelated `real.md`. Without that Markdown file, the page instead claims the existing parent no longer exists.

   **Suggested fix:** require the resolved target to belong to the generator’s indexed Markdown files before converting it to a slug. Otherwise warn and record unknown lineage. Add a `--plan` round-trip test with same-stem `.txt` and `.md` files.

Additional executed checks: 18,247 unique-slug parent configurations produced acyclic forests with each node exactly once; this supports termination but does not establish correct cuts. Absolute paths, `..`, trailing sentinel whitespace, paused sentinels, and an internal symlink resolved successfully. Legacy markerless re-arms remained markerless, honestly preserving unknown history; explicit new `--serving` replaced the objective.

VERDICT: NOT CONVERGED
