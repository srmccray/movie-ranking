# Movie Ranking Frontend

A lightweight, responsive React frontend for the Movie Ranking API.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing

## Features

- User registration and login
- Add movies with title and year
- Rate movies from 1-5 stars
- View and manage your movie rankings
- Responsive design (mobile and desktop)

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running on http://localhost:8000

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment file (optional, defaults work for local dev)
cp .env.example .env

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

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── api/            # API client
│   │   └── client.ts   # HTTP client with auth
│   ├── components/     # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── StarRating.tsx
│   │   ├── Modal.tsx
│   │   ├── Header.tsx
│   │   ├── MovieCard.tsx
│   │   ├── EmptyState.tsx
│   │   ├── AddMovieForm.tsx
│   │   └── ProtectedRoute.tsx
│   ├── context/        # React context providers
│   │   └── AuthContext.tsx
│   ├── hooks/          # Custom React hooks
│   │   └── useRankings.ts
│   ├── pages/          # Page components
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   └── RankingsPage.tsx
│   ├── types/          # TypeScript type definitions
│   │   └── index.ts
│   ├── App.tsx         # Root component with routing
│   ├── main.tsx        # Application entry point
│   └── index.css       # Global styles
├── index.html          # HTML template
├── package.json        # Dependencies and scripts
├── tsconfig.json       # TypeScript configuration
├── vite.config.ts      # Vite configuration
└── eslint.config.js    # ESLint configuration
```

## Development

### API Proxy

In development, API requests to `/api/*` are proxied to `http://localhost:8000`. This is configured in `vite.config.ts`.

### Authentication

The app uses JWT tokens stored in localStorage. The `AuthContext` manages authentication state and provides login/logout/register functions to all components.

### Styling

Styles are written in plain CSS with CSS custom properties (variables) for theming. The design system is documented in `/docs/design-system.md`.

## Building for Production

```bash
# Build optimized bundle
npm run build

# Preview the build
npm run preview
```

The build output will be in the `dist/` directory.

### Environment Variables for Production

Set `VITE_API_BASE_URL` to your production API URL:

```bash
VITE_API_BASE_URL=https://api.yourdomain.com/api/v1
```

## Bundle Size

The application is optimized for a lightweight footprint:

- Target: < 100KB gzipped
- Code splitting for React and React Router
- Tree shaking via Vite/Rollup
- No heavy UI framework dependencies

## Browser Support

- Chrome (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- Edge (last 2 versions)

## License

MIT
