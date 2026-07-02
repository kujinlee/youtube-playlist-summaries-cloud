import nextJest from 'next/jest.js';
const createJestConfig = nextJest({ dir: './' });
export default createJestConfig({
  testEnvironment: 'node',
  moduleNameMapper: { '^@/(.*)$': '<rootDir>/$1' },
  setupFiles: ['<rootDir>/tests/integration/setup.ts'],
  testMatch: ['<rootDir>/tests/integration/**/*.test.ts'],
});
