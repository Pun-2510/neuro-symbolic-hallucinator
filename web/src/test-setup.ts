// Vitest setup — runs before each test file.
// Auto-cleanup @testing-library/react side effects.
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => cleanup());
