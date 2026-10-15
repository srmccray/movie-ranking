# Movie Ranking Frontend

A lightweight, responsive React frontend for the Movie Ranking API.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite 6** - Build tool and dev server
- **React Router 6** - Client-side routing
- **Vitest + React Testing Library + MSW** - Testing

## Features

- User registration and login (email/password or Google sign-in)
- Link a Google account to an existing account (Settings)
- Search TMDB to add movies (or enter one manually) and rate them 1-5 stars
- View, sort, re-rate, and delete your movie rankings
- Analytics dashboard: stats, activity heatmap, genre radar chart, rating distribution
- Import watch history from an Amazon Prime CSV (Settings)
- Automatic logout when the API returns 401
- Responsive design (mobile and desktop)

## Getting Started

### Prerequisites

- Node.js 18+
- npm
- Backend API running on http://localhost:8000

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at http://localhost:3000

### Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |
| `npm test` | Run Vitest in watch mode |
| `npm run test:run` | Run tests once |
| `npm run test:coverage` | Run tests once with coverage |
| `npm run test:e2e` | Run Playwright e2e specs in `e2e/` (starts its own backend and Vite; first run needs `npx playwright install chromium`) |
| `npm run test:e2e:ui` | Playwright UI mode |

`npm run build` runs `tsc -b` first, so type errors fail the build.

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── api/            # API client (client.ts) with typed methods
│   ├── components/     # Reusable UI components (buttons, forms, modal,
│   │                   #   movie search/cards, analytics charts, import wizard,
│   │                   #   Google sign-in button, ProtectedRoute)
│   ├── context/        # AuthContext (auth state, token, 401 auto-logout)
│   ├── hooks/          # useRankings
│   ├── pages/          # Login, Register, GoogleCallback, Rankings,
│   │                   #   Analytics, Settings
│   ├── styles/         # Modular CSS (index.css imports variables, base,
│   │                   #   components/, pages/, utilities)
│   ├── types/          # TypeScript type definitions (index.ts)
│   ├── __tests__/      # Test setup and MSW mocks (tests are also colocated)
│   ├── App.tsx         # Root component with routing
│   └── main.tsx        # Application entry point (imports styles/index.css)
├── index.html          # HTML template
├── package.json        # Dependencies and scripts
├── tsconfig.json       # TypeScript configuration
├── vite.config.ts      # Vite and Vitest configuration
└── eslint.config.js    # ESLint configuration
```

See [CLAUDE.md](CLAUDE.md) for the detailed component, route, and convention reference.

## Development

### API Proxy

In development, API requests to `/api/*` are proxied to `http://localhost:8000`. This is configured in `vite.config.ts`.

### Authentication

The app uses JWT tokens stored in localStorage (`movie_ranking_token`). The `AuthContext` manages authentication state and provides `login`, `register`, `logout`, and `loginWithToken` (used by the Google OAuth callback at `/auth/google/callback`) to all components. If any API call returns 401, the API client triggers `logout` automatically.

### Styling

Styles are written in plain CSS with CSS custom properties (variables) for a dark theme. Design tokens live in `src/styles/variables.css`; component and page styles are split under `src/styles/components/` and `src/styles/pages/`, all imported by `src/styles/index.css`.

## Building for Production

```bash
# Build optimized bundle
npm run build

# Preview the build
npm run preview
```

The build output will be in the `dist/` directory.

### API Base URL

The API client uses the fixed base path `/api/v1` (`API_BASE` in `src/api/client.ts`), so in production `/api/*` must be routed to the backend (e.g. by the CDN/reverse proxy).

## Bundle Size

The application is optimized for a lightweight footprint:

- Target: < 100KB gzipped (not measured here)
- Manual chunks for React and React Router (see `vite.config.ts`)
- Tree shaking via Vite/Rollup
- No heavy UI framework dependencies

## Browser Support

- Chrome (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- Edge (last 2 versions)

## License

MIT
