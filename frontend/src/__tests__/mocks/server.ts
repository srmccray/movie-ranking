/**
 * MSW server configuration for Node.js test environment.
 */

import { setupServer } from 'msw/node';
import { handlers, importHandlers } from './handlers';

// Create the MSW server with all handlers (main + import)
export const server = setupServer(...handlers, ...importHandlers);
