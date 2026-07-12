import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import { assertLogicalKey } from '@/lib/storage/blob-store';

/** job_version for a cloud dig job — encodes DIG_GENERATOR_VERSION so a bump lands in a
 *  distinct jobs_idem_active slot (which includes job_version), permitting a legit re-enqueue. */
export function digJobVersion(): string {
  return `dig-${DIG_GENERATOR_VERSION}`;
}

/** Per-section dig blob key. One blob per section ⇒ concurrent digs of different sections
 *  never write the same object (no lost update). The `.r{V}` segment makes a version bump
 *  produce a fresh key, so a stale-version blob is simply absent at the current key. */
export function digSectionKey(base: string, sectionId: number): string {
  if (!Number.isInteger(sectionId) || sectionId < 0) {
    throw Object.assign(new Error(`invalid dig sectionId: ${sectionId}`), { statusCode: 400 });
  }
  // `base` MUST be a single path component. assertLogicalKey does NOT reject an interior '/', so
  // `dig/a/b/1.r9.md` would slip past it — guard the base explicitly here.
  if (base.length === 0 || /[/\\\0]/.test(base) || base === '.' || base === '..') {
    throw Object.assign(new Error(`invalid dig base: ${base}`), { statusCode: 400 });
  }
  const key = `dig/${base}/${sectionId}.r${DIG_GENERATOR_VERSION}.md`;
  assertLogicalKey(key); // belt-and-suspenders: leading '/', '..' segment, '\0'
  return key;
}
