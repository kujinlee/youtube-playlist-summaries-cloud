import { EventEmitter } from 'events';

const registry = new Map<string, EventEmitter>();

export function createJob(jobId: string): EventEmitter {
  const emitter = new EventEmitter();
  registry.set(jobId, emitter);
  return emitter;
}

export function getJob(jobId: string): EventEmitter | undefined {
  return registry.get(jobId);
}

export function deleteJob(jobId: string): void {
  registry.delete(jobId);
}

export function _resetJobRegistry(): void {
  registry.clear();
}
