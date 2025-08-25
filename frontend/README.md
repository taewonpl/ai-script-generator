# AI Script Generator - Frontend

Production-ready React frontend built with Vite, TypeScript, and Material-UI using Feature-Sliced Design architecture.

## 🚀 Features

- **Modern Tech Stack**: Vite + React 19 + TypeScript
- **UI Framework**: Material-UI (MUI) with custom theme
- **State Management**: TanStack React Query for server state
- **Routing**: React Router DOM with lazy loading
- **Forms**: React Hook Form with Zod validation
- **Testing**: Vitest + React Testing Library + Playwright E2E
- **Mocking**: MSW (Mock Service Worker) for API mocking
- **Architecture**: Feature-Sliced Design for scalable organization
- **Code Quality**: ESLint, Prettier, Husky, lint-staged
- **Error Tracking**: Sentry integration
- **Virtualization**: TanStack Virtual for large lists

## 📁 Project Structure (Feature-Sliced Design)

```
src/
├── app/                    # Application layer
│   ├── providers/          # App providers (Router, Theme, etc.)
│   └── styles/             # Global styles
├── pages/                  # Page components
│   ├── project-list/       # Project listing page
│   ├── project-detail/     # Project detail page
│   ├── episode-list/       # Episode listing page
│   ├── episode-detail/     # Episode detail page
│   └── generation-dashboard/ # Generation dashboard
├── widgets/                # Large UI blocks
│   ├── project-card/       # Project card widget
│   ├── episode-card/       # Episode card widget
│   ├── generation-panel/   # Generation control panel
│   └── navigation/         # Navigation widget
├── features/               # Business logic features
│   ├── project-management/ # Project CRUD operations
│   ├── episode-management/ # Episode CRUD operations
│   ├── script-generation/  # AI script generation
│   └── user-auth/          # Authentication
├── entities/               # Business entities
│   ├── project/            # Project entity logic
│   ├── episode/            # Episode entity logic
│   ├── generation/         # Generation entity logic
│   └── user/               # User entity logic
└── shared/                 # Shared utilities
    ├── ui/                 # Shared UI components
    │   ├── components/     # Reusable components
    │   ├── layouts/        # Layout components
    │   └── theme/          # Theme configuration
    ├── api/                # API client and types
    ├── lib/                # Utilities and helpers
    │   ├── utils/          # Utility functions
    │   ├── hooks/          # Custom hooks
    │   ├── constants/      # Constants
    │   ├── msw/            # Mock Service Worker setup
    │   └── test/           # Test utilities
    └── assets/             # Static assets
```

## 🛠️ Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
npm install
```

### Development Server

```bash
npm run dev
```

Runs on http://localhost:3000 with:

- Hot module replacement
- API proxy to backend services (8000, 8001)
- MSW for API mocking

### Available Scripts

#### Development

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build

#### Code Quality

- `npm run lint` - Lint TypeScript files
- `npm run lint:fix` - Fix linting issues
- `npm run format` - Format code with Prettier
- `npm run format:check` - Check code formatting
- `npm run typecheck` - Run TypeScript compiler

#### Testing

- `npm run test` - Run unit tests with Vitest
- `npm run test:ui` - Run tests with UI
- `npm run test:coverage` - Run tests with coverage
- `npm run test:e2e` - Run E2E tests with Playwright
- `npm run test:e2e:ui` - Run E2E tests with UI

#### MSW (Mock Service Worker)

- `npm run msw:init` - Initialize MSW service worker

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_PROJECT_API_BASE_URL=http://localhost:8001

# Sentry (optional)
VITE_SENTRY_DSN=your-sentry-dsn

# Feature Flags
VITE_ENABLE_DEVTOOLS=true
VITE_ENABLE_MSW=true
```

### API Integration

The app integrates with two backend services:

- **Generation Service** (localhost:8000) - AI script generation
- **Project Service** (localhost:8001) - Project and episode management

API proxying is configured in `vite.config.ts`:

- `/api/*` → Generation Service (8000)
- `/project-api/*` → Project Service (8001)

### Mock Service Worker (MSW)

MSW is automatically enabled in development mode for API mocking. Mock handlers are defined in `src/shared/lib/msw/handlers.ts`.

## 📱 UI Components

### Theme System

- Material-UI theme with custom colors
- Light/dark mode support (coming soon)
- Responsive design with mobile-first approach

### Key Components

- **AppLayout**: Main application layout with drawer navigation
- **ProjectCard**: Project display and interaction card
- **Navigation**: Responsive navigation with mobile drawer

### Form Handling

- React Hook Form for performance
- Zod schemas for validation
- Material-UI integration

## 🧪 Testing Strategy

### Unit Tests (Vitest)

- Component testing with React Testing Library
- Utility function testing
- Custom hooks testing

### E2E Tests (Playwright)

- Critical user flows
- Cross-browser testing
- Mobile viewport testing

### API Mocking (MSW)

- Development mode mocking
- Test environment mocking
- Realistic API responses

## 📦 Build & Deployment

### Production Build

```bash
npm run build
```

Features:

- TypeScript compilation
- Code splitting by routes and vendors
- Source maps for debugging
- Asset optimization

### Bundle Analysis

The build process creates optimized chunks:

- `vendor`: React, React DOM
- `mui`: Material-UI components
- `router`: React Router
- `query`: TanStack React Query

### Docker Support

The frontend is designed to work with the project's Docker setup:

- Build context: `./frontend`
- Nginx serving in production
- Environment variable injection

## 🔒 Security

### Error Tracking

- Sentry integration for production error monitoring
- Source map upload for better error tracking

### API Security

- Automatic token handling in API clients
- 401 redirect to login
- Request/response interceptors

## 🔄 State Management

### Server State (TanStack Query)

- Projects: listing, details, CRUD operations
- Episodes: project episodes, details, management
- Generations: AI generation requests and status

### Local State

- Component state with useState/useReducer
- Form state with React Hook Form
- UI state (modals, drawers, etc.)

## 🎨 Styling

### Material-UI System

- Theme-based styling
- Responsive breakpoints
- Component customization

### CSS-in-JS

- Emotion for styling
- Theme access in components
- Runtime style generation

## 🚀 Performance

### Code Splitting

- Route-based lazy loading
- Dynamic imports for large features
- Vendor chunk separation

### Optimization

- React Query caching
- Virtual scrolling for large lists
- Image optimization
- Bundle size monitoring

## 📈 Monitoring

### Development Tools

- React Query Devtools
- React Developer Tools support
- Source map debugging

### Production Monitoring

- Sentry error tracking
- Performance monitoring
- User session replay (configurable)

## 🤝 Contributing

### Code Standards

- TypeScript strict mode
- ESLint + Prettier
- Husky pre-commit hooks
- Conventional commits

### Development Workflow

1. Create feature branch
2. Write tests
3. Implement feature
4. Run quality checks
5. Create pull request

### Pull Request Checklist

- [ ] Tests passing
- [ ] TypeScript compilation successful
- [ ] Linting and formatting passed
- [ ] E2E tests updated (if needed)
- [ ] Documentation updated

---

**Production-ready React frontend for AI Script Generator v3.0! 🎬✨**
