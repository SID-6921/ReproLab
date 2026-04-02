# ReproLab SaaS Frontend

React + Vite + Supabase authentication layer for the ReproLab reproducibility scoring backend.

## Quick Start

### Prerequisites
- Node.js 18+
- Supabase account (free tier available at supabase.com)

### Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure Supabase:**
   - Copy `.env.example` to `.env.local`
   - Add your Supabase project URL and anon key
   - Create auth users in Supabase dashboard

3. **Start development server:**
   ```bash
   npm run dev
   ```
   - Frontend runs on http://localhost:5173
   - API proxy forwards `/api/*` to http://localhost:8000

### Build for Production

```bash
npm run build
npm run preview
```

## Architecture

```
frontend/
├── src/
│   ├── components/       # React components
│   │   └── ProtocolEditor.jsx    # Main editing interface
│   ├── pages/           # Page components  
│   │   ├── LoginPage.jsx
│   │   ├── DashboardPage.jsx
│   │   └── ProtocolEditorPage.jsx
│   ├── lib/             # Utilities
│   │   └── supabase.js  # Supabase client
│   ├── services/        # API clients
│   │   └── apiClient.js # Axios HTTP client
│   ├── store/           # State management
│   │   └── authStore.js # Zustand auth state
│   ├── App.jsx          # Main app component
│   └── main.jsx         # Entry point
├── package.json
├── vite.config.js
└── index.html
```

## Key Features

- **Authentication:** Supabase email/password auth with session management
- **Protocol Editor:** Live form editing with real-time reproducibility scoring
- **Dashboard:** Browse and manage protocols with score visualization
- **Live Scoring:** Debounced scoring updates as user edits (0-100 scale)
- **Responsive Design:** Mobile-friendly UI with gradient theme

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `VITE_SUPABASE_URL` | Supabase project URL | `https://xyz.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key | `eyJhbGc...` |
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

## Development

### Add a New Page

1. Create component in `src/pages/`
2. Add route in `App.jsx`
3. Use `useAuthStore()` for auth state
4. Use `protocolAPI` for backend calls

### Add a New Component

1. Create component in `src/components/`
2. Import and use in pages
3. Add corresponding CSS file

### API Integration

All API calls go through `apiClient.js` with `/api` prefix:
- Development: proxied to `http://localhost:8000`
- Production: set `VITE_API_URL` to production backend

## Testing

```bash
npm run lint
```

## Deployment

Frontend can be deployed to Vercel, Netlify, or any static host:

```bash
npm run build
# Output in dist/ directory
```

Configure `VITE_API_URL` environment variable to point to production backend.
