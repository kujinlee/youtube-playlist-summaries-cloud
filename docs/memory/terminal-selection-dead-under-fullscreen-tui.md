---
name: terminal-selection-dead-under-fullscreen-tui
description: "Mouse selection stops working in the Cursor terminal because Claude Code's fullscreen TUI turns on mouse reporting; the macOS fix is one Cursor setting"
metadata: 
  node_type: memory
  type: project
  originSessionId: 38bb4af3-a4bd-4dda-b9ef-dff52df13e20
  modified: 2026-10-22T17:19:27.444Z
---

**Symptom:** cannot drag-select any of the Claude Code transcript in the Cursor terminal. Holding
Option shows a **crosshair** but still selects nothing. Persisted silently for weeks.

**Cause chain, each link measured 2026-10-22, not inferred:**

1. `~/.claude/settings.json` has `"tui": "fullscreen"`. That renderer emits `?1049h` (alternate
   screen) + `?1000h` + `?1006h` (mouse reporting) — counted in the `claude` binary. `?1002`/`?1003`
   are absent, so it asks only for button events, but xterm.js kills native selection on *any*
   mouse mode.
2. With mouse reporting on, the terminal forwards mousedown to Claude Code instead of selecting.
3. The escape hatch is xterm.js `shouldForceSelection`, whose **macOS** branch is
   `e.altKey && macOptionClickForcesSelection` — and that option ships `false`. So on a Mac,
   Option-drag is *constant false*: it could never work. The `e.shiftKey` branch is the
   **non-Mac** path, which is why adding Shift changes nothing.
4. The crosshair came from a *different* function, `shouldColumnSelect`, which carries the same
   flag with the opposite sign (`&& !(isMac && macOptionClickForcesSelection)`) and so evaluated
   to plain `e.altKey` → `.xterm.column-select.focus{cursor:crosshair}`. Affordance on,
   behaviour off — [[a-check-result-is-not-the-claim]].

**Fix (applied, works):** `terminal.integrated.macOptionClickForcesSelection: true` in
`~/Library/Application Support/Cursor/User/settings.json`. Then **Option-drag selects**.

⭐ **Its own falsifier:** the one flag flips both functions at once, so **the crosshair
disappearing IS the confirmation**. Crosshair still there → the setting has not been picked up;
reload the window, then `claude --continue`.

**Why:** the subject lives in three places that never mention each other — a Claude Code setting, a
terminal escape sequence, and a vendor default inside Cursor's `node_modules`. Nothing surfaces the
link, so the next occurrence re-derives from zero.

**How to apply:** if selection or scrollback dies in a terminal, check whether the TUI is in
fullscreen before suspecting the terminal. The blunt alternative is `/tui default`
(or `CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1`), which drops mouse reporting entirely and restores
native scrollback too — at the cost of focus view and some flicker.
