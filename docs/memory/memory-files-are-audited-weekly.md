---
name: memory-files-are-audited-weekly
description: "FIRES-WHEN: writing or correcting a memory file, the index nears its 24,985-char limit, or the weekly reset arrives. Owner 11-13 16:30: audit all memory files once, then weekly."
metadata:
  type: feedback
---

**The rule:** each memory file opens with its CURRENT rule; history goes below it, moves out, or is cut. The index holds one line per memory, describing the situation it fires in, and stays under ~90% of 24,985 characters.

Owner 2026-11-13 16:30: audit ALL memory files once (195 files; 45 carry correction layers; 30 over 8 KB). Then option B: a CI shape check on every PR (index size, file size, a correction layer that isn't on top), plus a WEEKLY content audit at the weekly reset of the files changed since the last one (stale facts, contradictions). Measure the first weekly run: over ~1 weekly point → switch to monthly and tell the owner.

**Why:** the index loads on every turn and is cut off WITHOUT WARNING past its limit. A rule buried under its own corrections gets read in its old form.

**How to apply:** when correcting a memory, REWRITE its top; never append another ⟳ section. In-flight id `memory-audit`. Related: [[a-usage-limit-stop-needs-a-wake-at-reset]], [[slice-history]].
