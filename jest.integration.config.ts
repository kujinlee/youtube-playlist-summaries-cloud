import nextJest from 'next/jest.js';
const createJestConfig = nextJest({ dir: './' });
export default createJestConfig({
  testEnvironment: 'node',
  moduleNameMapper: { '^@/(.*)$': '<rootDir>/$1' },
  setupFiles: ['<rootDir>/tests/integration/setup.ts'],
  testMatch: ['<rootDir>/tests/integration/**/*.test.ts'],
  // NOTE: these tests share ONE local Supabase stack and must run serially — that is
  // enforced by `--runInBand` on the `test:integration` npm script (maxWorkers is a
  // runner option, not valid inside next/jest's project config).
});
