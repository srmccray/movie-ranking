/**
 * Verifies MSW is configured with onUnhandledRequest: 'error' (TASK-0010).
 */

import { describe, it, expect } from 'vitest';

describe('MSW unhandled requests', () => {
  it('rejects a request to an endpoint with no handler', async () => {
    await expect(fetch('http://localhost/api/v1/does-not-exist/')).rejects.toThrow();
  });
});
