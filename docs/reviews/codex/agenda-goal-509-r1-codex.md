<!-- codex-review: model=gpt-6.1-sol -->

Found four issues; none Blocking or High.

1. **Medium — Agenda goal numbers disagree with the tree.**  
   `step_goals` and `agenda_context` use `enumerate(goals, 1)`, while the tree uses `goal_numbers`, ranked by first-request time. Constructed snapshot:

   ```text
   Tree:    GOAL 2 · later
   Agenda:  GOAL 1 · later
   ```

   The wrong number appears on the step, NOW, and focus lines. Use the tree’s numbering rule in both new functions. The #509 fixtures omit request timestamps, so they cannot catch this.

2. **Medium — NOW falsely says nothing is in flight when unassigned ledger work exists.**  
   With `goals=[]`, `undeclared=[]`, and:

   ```python
   inflight_loose=[{"id": "build-777", "what": "working on backlog #777"}]
   ```

   `agenda_context` returns `now: nothing in flight`. The existing tree correctly lists this work under “IN FLIGHT, UNDER NO GOAL.” NOW ignores `inflight_loose`, and `agenda_html` also excludes it from the snapshot passed to `agenda_lines`. Include this work with an explicit no-goal label.

3. **Low — Item (4)’s agenda-age display is missing.**  
   Backlog #509 explicitly requires “say how old it is beside the page’s own generated time.” The implementation displays the agenda’s set timestamp and conditional warnings, but never calculates or displays its age. The claim that items (1)–(4) are complete is therefore premature.

4. **Low — HTML slicing tests permit lost agenda content.**  
   This temporary-copy mutation passes **334/334** tests:

   ```python
   body = body[len(ctx) + (1 if len(ctx) == 3 else 0):]
   ```

   It drops the first `when` heading whenever there are three context lines. The new HTML test checks context counts and ordering relative to `restart`, but does not verify preservation of every heading and step across context counts.

Verification performed:

- Baseline: **334/334 self-tests passed**.
- All **10 #509 manifest mutations** failed their expected named tests on temporary copies.
- Across the manifest, every find-string resolves exactly once; no two entries share one.
- Constructed probes passed for ref ordering, duplicate refs, different ref kinds, duplicate goal slugs, and a step serving two goals.
- Checked NOW states, waits, parked exclusion, duplicate threads under different goals, and undeclared count.
- Checked STALE boundaries: equal/before timestamps do not flag; later minutes do. Seconds, ISO timestamps, and missing merge times are ignored. Partial ref overlap suppresses STALE; empty and unticked all-FREE agendas are not marked finished.
- Actual HTML preserved content with 1/2/3 context lines, with and without `change_if`; escaping, PR links, and malformed/none/absent agendas passed.

Tracked files remain unchanged. No `.claude/plans/` contents were read.

VERDICT: NOT CONVERGED
