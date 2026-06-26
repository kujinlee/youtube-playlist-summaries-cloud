import { readIndex, writeIndex } from './index-store';
import { planMigration } from './serial-migrate';

export function runPhaseA(outputFolder: string): { assigned: number } {
  const index = readIndex(outputFolder);
  const { assignments } = planMigration(index.videos);
  if (assignments.length === 0) return { assigned: 0 };
  const serialById = new Map(assignments.map((a) => [a.id, a.serial]));
  const videos = index.videos.map((v) =>
    serialById.has(v.id) ? { ...v, serialNumber: serialById.get(v.id)! } : v,
  );
  writeIndex(outputFolder, { ...index, videos });   // single atomic write (temp→rename)
  return { assigned: assignments.length };
}
