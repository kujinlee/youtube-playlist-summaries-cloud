<!-- codex-review: model=gpt-5.5 -->

Blocking — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:187-193`

The one-record journal breaks on a blocked Stop that re-fires inside the same turn. At the first Stop of turn T, the guard judges T-1 and then overwrites the journal with T. If `check-plan-progress.py` blocks, the same turn continues; its hook feedback is `isMeta` and not a boundary under `records_since_last_user`. At the next Stop in the same turn, the judged turn is still T-1, but the journal now contains T, so the key mismatches and the guard reports CANNOT RUN against a subject it just had.

Concrete sequence: Stop T-1 writes `{boundary_uuid: u1}`. Turn T opens with user uuid `u2`. First Stop T judges `u1`, writes `u2`, then `check-plan-progress.py` blocks. Continuation Stop T still has prior judged turn `u1`; journal says `u2`; CANNOT RUN.

Fix: the journal cannot be a single “last Stop” record. Store at least two keyed records, or keep separate `sampled_live_turn` and `last_judged_turn`, and define `stop_hook_active` behavior explicitly so a continuation does not overwrite the still-needed prior sample.

High — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:170-193`

The fixed path `.claude/banner-turn-state.json` is unsafe for concurrent sessions in the same repo. Boundary UUID uniqueness does not solve shared storage: session A and session B can overwrite each other’s one record even with distinct UUIDs. That produces false CANNOT RUNs in ordinary concurrent use, which this project already treats as a known dangerous shape.

Concrete sequence: session A Stop writes `{uA}`. Session B Stop writes `{uB}`. Session A next Stop judges its prior turn `uA`, finds `uB`, and reports CANNOT RUN. With `--resume`, the same failure appears whenever another session touched the repo journal while the resumed transcript was idle.

Fix: scope state by `session_id` and transcript identity, not just boundary UUID. Use either one journal per session/transcript or a multi-record map keyed by `(transcript_path, session_id, boundary_uuid)`, with atomic write/replace and locking.

High — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:118-124`

“Last NON-EMPTY window” is defined as “contains at least one assistant text block,” but that skips real work. The existing `decide()` can warn on `texts=[]` when `armed=True`, `steps` has unticked work, and `edited=True`; that is exactly the plan-without-banner branch. A tool-only assistant turn has no text block but can edit files.

Concrete input: user opens a turn; assistant emits only an `Edit` tool_use block; tool_result succeeds; no assistant text block is flushed. The prior turn has `edited=True`, no banner, and no assistant text. The selector skips it as “empty,” so the unbannered warning is never evaluated.

Fix: “judgable turn” should not mean “has assistant text.” It should mean the window contains assistant activity relevant to the guard, at minimum an assistant record or a repo edit/tool_use. Keep slash-command shell windows excluded because they have no assistant activity, not because they lack assistant text.

High — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:152-161`

The refutation of the `UserPromptSubmit` alternative is wrong. `check-plan-progress.py:180-182` does unlink the sentinel when all steps are ticked, but that does not imply a false `unarmed` warning. For a completed plan whose final visible prior-turn banner is `STEP n of n`, `check-banner-armed.py:325-327` returns QUIET before the `armed` check matters. For a completed plan with no banner, `armed=False` and no unticked steps also does not trigger the unbannered branch. For an incomplete plan, the sentinel is not unlinked.

Concrete input: prior turn text contains `## ▶ STEP 3 of 3`; next `UserPromptSubmit` sees no sentinel, so `decide([banner], armed=False)` returns QUIET, not WARN.

Fix: either reconsider `UserPromptSubmit` as a simpler design, or reject it for a real reason with a concrete failing case. The current reason does not hold.

Medium — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:98-100` and `:174`

The `windows(records)[-1] == records_since_last_user(lines)` assertion conflicts with the journal key requirement. `records_since_last_user` excludes the opening user boundary by setting `start = i + 1`. But the journal needs the `uuid` of that opening record. If a window includes its opener, equality is false; if it excludes the opener, the window cannot supply `boundary_uuid`.

Concrete input: `[user(uuid="u1"), assistant("x")]`. Existing `records_since_last_user` returns only `[assistant("x")]`. A window that “opens at” `u1` and carries the key must know about the user record, so it is not equal as a `list[dict]`.

Fix: define a real structure, e.g. `TurnWindow(opener: dict | None, body: list[dict])`, and assert `windows(records)[-1].body == records_since_last_user(lines)`. Add fixtures for normal user, tool-result non-boundary, `isMeta` injection, and `isMeta` carrying a real message.

Medium — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:203-208` and `:221-247`

The CANNOT RUN taxonomy has an unresolved precedence conflict. The behavior table says “no prior turn” is QUIET. Section 5.1 says a failed journal write returns CANNOT RUN. On the first substantive turn, both can be true: there is no prior judged subject, but the guard still must write the live turn’s journal for next time.

Concrete sequence: first substantive Stop in a fresh session; no prior non-empty window exists; `.claude/banner-turn-state.json` cannot be written. If the implementation returns early for “no subject,” journal failure becomes a quiet pass. If write failure wins, F5 as written is incomplete.

Fix: specify precedence. “No subject” is QUIET only if live sampling and journal write succeed or are not attempted by design. If the journal is required for the next turn, failed write must return CANNOT RUN even on the first Stop, and F5 needs to say that explicitly.

Low — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:52-60`

The numbers are mostly internally consistent, but the denominator claim is imprecise. The table says 9 bannered turns hid closing banners and 8 changed the verdict. The text says “this is one bannered turn in six.” That is true for 8/48, not 9/48. If the paragraph is about hidden closing banners, it is about 1 in 5.3; if it is about verdict flips, say so.

Fix: state both rates separately: 9/48 had hidden closing banners; 8/48 changed the verdict.

VERDICT: NOT CONVERGED
