/**
 * Section identity across a re-summarize — evidence for the "introduce a stable sectionId"
 * question, and for the magazine model's title-proxy drift guard.
 *
 * THE SETUP (all verified in code, not assumed):
 *   - A summary section's `startSec` is minted by `ensureSectionTimestamps` INSIDE
 *     `generateSummary` (`lib/gemini.ts:387`) and carried ONLY in the MD's `▶` line. It is
 *     `allocateSectionStarts`-unique *within one generation*, and nothing anchors it across
 *     generations — a re-summarize mints a fresh set from the new model output.
 *   - Dug content is keyed on that `startSec` (`digSectionKey(base, sectionId)`,
 *     `enqueue-dig-core.ts:34`, `dig-handler.ts:64`).
 *   - `mergeDigDoc` (spec §3a) therefore matches dug → section in two steps:
 *       step 1: DugSection.sectionId === section.startSec   (numeric)
 *       step 2: exact TITLE match                            (string fallback)
 *   - The magazine model's gists are trusted only when `sameTitles(parsedTitles,
 *     envelope.sourceSections)` — positional + exact string.
 *
 * So section identity is answered THREE different ways across the codebase, and two of them
 * are the section TITLE — a string the LLM rewrites freely. These tests pin what that costs.
 *
 * This file is a CHARACTERIZATION of current behaviour: every test here passes today. It
 * exists so the cost is measured rather than argued, and so a future stable-sectionId change
 * has a regression baseline.
 */
import { mergeDigDoc } from '@/lib/html-doc/dig-merge';
import type { ParsedSummary } from '@/lib/html-doc/types';
import type { ModelEnvelope } from '@/lib/html-doc/model-store';
import type { DugSection } from '@/lib/dig/companion-doc';

function summary(sections: { title: string; startSec: number }[]): ParsedSummary {
  return {
    sections: sections.map((s) => ({
      numeral: null,
      title: s.title,
      prose: `prose for ${s.title}`,
      timeRange: { startSec: s.startSec, endSec: s.startSec + 60, label: '', url: '' },
    })),
  } as unknown as ParsedSummary;
}

function dug(sectionId: number, title: string): DugSection {
  return {
    sectionId, startSec: sectionId, title,
    bodyMarkdown: `DUG BODY for ${title}`,
    generatedAt: '2026-07-30T00:00:00.000Z', genVersion: 9,
  };
}

function envelope(titles: string[]): ModelEnvelope {
  return {
    sourceMd: 'x.md', generatedAt: '2026-07-30T00:00:00.000Z',
    sourceSections: titles, generatorVersion: 'magazine-skim v2',
    model: { sections: titles.map((t) => ({ lead: `lead ${t}`, bullets: [`b ${t}`] })) },
  } as unknown as ModelEnvelope;
}

const ORIGINAL = [{ title: 'Alpha', startSec: 0 }, { title: 'Beta', startSec: 120 }];

describe('section identity survives a re-summarize only by accident', () => {
  it('baseline: same titles AND same startSec — dug content lands', () => {
    const res = mergeDigDoc(summary(ORIGINAL), envelope(['Alpha', 'Beta']), [dug(120, 'Beta')]);
    expect(res.sections[1].dug?.bodyMarkdown).toContain('DUG BODY for Beta');
    expect(res.orphans).toEqual([]);
  });

  // A re-summarize mints fresh timestamps: `allocateSectionStarts` keeps the model's value only
  // when it fits the strictly-increasing window, else synthesizes one. New model output ⇒ new
  // numbers. The numeric key is therefore NOT stable across generations — only the title saves it.
  it('startSec changed, titles unchanged → step 1 FAILS, rescued only by the TITLE fallback', () => {
    const resummarized = [{ title: 'Alpha', startSec: 0 }, { title: 'Beta', startSec: 137 }];
    const res = mergeDigDoc(summary(resummarized), envelope(['Alpha', 'Beta']), [dug(120, 'Beta')]);

    expect(res.sections[1].dug?.bodyMarkdown).toContain('DUG BODY for Beta'); // step 2 saved it
    expect(res.orphans).toEqual([]);
  });

  // The case the title fallback cannot cover. A re-summarize is free to reword a heading —
  // nothing constrains it — and the moment it does, PAID dug content detaches from its section.
  it('startSec AND title changed → dug content ORPHANS off its section', () => {
    const resummarized = [{ title: 'Alpha', startSec: 0 }, { title: 'Beta, revisited', startSec: 137 }];
    const res = mergeDigDoc(summary(resummarized), envelope(['Alpha', 'Beta, revisited']), [dug(120, 'Beta')]);

    expect(res.sections[1].dug).toBeNull();                       // section shows no dig
    expect(res.orphans).toHaveLength(1);                          // content survives, detached
    expect(res.orphans[0].bodyMarkdown).toContain('DUG BODY for Beta');
  });

  // A one-character heading edit invalidates EVERY section's gist, not just the edited one —
  // sameTitles is all-or-nothing across the whole array.
  it('a single retitled section drops the magazine gists for ALL sections', () => {
    const retitled = [{ title: 'Alpha', startSec: 0 }, { title: 'Beta!', startSec: 120 }];
    const res = mergeDigDoc(summary(retitled), envelope(['Alpha', 'Beta']), []);

    expect(res.sections[0].gist).toBeNull();   // untouched section loses its gist too
    expect(res.sections[1].gist).toBeNull();
  });

  // The inverse, and the one that matters for the drift guard: titles held CONSTANT while the
  // prose changes. `fixSummary`'s prompt pins headings on purpose ("do NOT ... restructure any
  // sections ... Preserve all markdown formatting exactly: headings"), so this is the DESIGNED
  // shape of a corrections regenerate — and the title proxy cannot see it at all.
  it('prose changed but titles identical → stale gists are served as fresh', () => {
    const stale = envelope(['Alpha', 'Beta']);          // built from the OLD prose
    const res = mergeDigDoc(summary(ORIGINAL), stale, []);

    expect(res.sections[0].gist).toEqual({ lead: 'lead Alpha', bullets: ['b Alpha'] });
    // Nothing in the merge inputs can distinguish this from a genuinely-fresh model: the
    // envelope's `sourceMdHash` — the exact signal — is never consulted here or in isFresh().
  });
});
