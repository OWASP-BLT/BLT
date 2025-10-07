#  Bug Reporter (BLT)

A professional bug tracking application built with React, TypeScript, Cloudflare Workers, and D1.

## Features

- **Authentication**: JWT-based auth with role-based access control (RBAC)
- **Bug Management**: Report, view, and update bug status across the lifecycle
- **Project & Repository Management**: Organize bugs by projects and repositories
- **User Management**: Admin can update roles and delete users
- **Responsive UI**: Clean, modern interface with accessibility considerations

## 🚀 Quick Start (Local Dev)

### Prerequisites
- Node.js 18+
- Cloudflare account
- Wrangler CLI: `npm install -g wrangler`

### 1) Install dependencies
```bash
npm install
```

### 2) Configure environment
Create or update `wrangler.toml` with strong secrets:

```toml
[vars]
JWT_SECRET = "<generate-a-strong-random-secret>"
ADMIN_EMAIL = "<your-admin-email@example.com>"

[[d1_databases]]
binding = "DB"                # used in the worker
database_name = "bug-reporter-db"
database_id = "<your-d1-database-id>"
```

### 3) Initialize database
```bash
npm run db:migrate
```

### 4) Run locally
- API (Cloudflare Worker):
```bash
npm run worker:dev
```
- Frontend:
```bash
npm run dev
```

- Frontend: `http://localhost:5173`
- API: `http://localhost:8787`

## 🔑 Authentication
- Login and registration use JWT.

## 🗂️ Project Structure

```
BugReporter/
├── src/                    # React frontend
│   ├── components/         # Reusable UI components
│   ├── pages/              # Page components
│   ├── contexts/           # React contexts (Auth, Notifications)
│   ├── services/           # API service layer
│   └── types.ts            # TypeScript definitions
├── worker/                 # Cloudflare Worker backend
│   ├── index.ts            # API routes and logic
│   └── schema.sql          # Database schema
└── wrangler.toml           # Cloudflare configuration
```

## 🛠️ Scripts

- `npm run dev` - Start frontend dev server
- `npm run build` - Build frontend for production
- `npm run deploy` - Deploy frontend (e.g., Cloudflare Pages)
- `npm run worker:dev` - Start worker locally
- `npm run worker:deploy` - Deploy worker
- `npm run db:migrate` - Apply database schema/migrations

## 🚀 Deployment

1) Build frontend
```bash
npm run build
```

2) Deploy frontend (Pages/your CDN)
```bash
npm run deploy
```

3) Deploy worker
```bash
npm run worker:deploy
```
