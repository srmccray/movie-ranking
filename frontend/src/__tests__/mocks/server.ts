/**
 * MSW server configuration for Node.js test environment.
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Create the MSW server with the handlers
export const server = setupServer(...handlers);
