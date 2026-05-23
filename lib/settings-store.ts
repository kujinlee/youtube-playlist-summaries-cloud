import fs from 'fs';
import path from 'path';

const SETTINGS_FILE = path.join(process.cwd(), 'settings.json');

interface Settings {
  outputFolder: string;
  baseOutputFolder?: string;
}

export function readSettings(): Settings {
  try {
    const raw = fs.readFileSync(SETTINGS_FILE, 'utf-8');
    const settings = JSON.parse(raw) as Settings;
    const folder = settings.outputFolder ?? '';
    const base = settings.baseOutputFolder ?? folder;
    return {
      outputFolder: folder ? path.resolve(folder) : folder,
      baseOutputFolder: base ? path.resolve(base) : base || undefined,
    };
  } catch {
    const folder = process.env.OUTPUT_FOLDER ?? '';
    return { outputFolder: folder ? path.resolve(folder) : folder };
  }
}

export function writeSettings(settings: Settings): void {
  fs.writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 2), 'utf-8');
}
