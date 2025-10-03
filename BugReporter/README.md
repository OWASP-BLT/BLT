# 🐛 Bug Reporter (OWASP)

A professional bug tracking application built with React, TypeScript, Cloudflare Workers, and D1.

## ✨ Features

- **🔐 Authentication**: JWT-based auth with role-based access control (RBAC)
- **🐛 Bug Management**: Report, view, and update bug status across the lifecycle
- **🏢 Project & Repository Management**: Organize bugs by projects and repositories
- **👥 User Management**: Admin can update roles and delete users
- **📱 Responsive UI**: Clean, modern interface with accessibility considerations

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

> Do not commit real secrets. Use separate values for development and production.

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
- For development only, tokens are stored in `localStorage` for simplicity. See Security Hardening for production guidance.

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

## 🔒 Security Hardening (Production)

Use the following checklist before going live:

- **Secrets Management**
  - Use strong, unique `JWT_SECRET`. Rotate periodically.
  - Use environment variables with Cloudflare and do not commit secrets.

- **Token Storage**
  - Prefer storing JWT in an HttpOnly, `Secure`, `SameSite=Lax` cookie set by the worker.
  - Avoid `localStorage` for production to reduce XSS token theft risk. If you keep localStorage, enforce strong CSP and input sanitization.

- **CORS**
  - In `worker/index.ts`, restrict `Access-Control-Allow-Origin` to your production frontend domain.
  - Disallow `*` in production.

- **Input Validation**
  - Validate and sanitize all inputs server-side (projects, repositories, bugs, users).
  - Enforce string length limits, allowed character sets, and required fields.

- **Database Safety**
  - Use parameterized queries only (no string interpolation).
  - Apply least privilege; ensure only intended tables are exposed.

- **Rate Limiting & Abuse**
  - Add per-IP rate limiting on auth and write endpoints (e.g., KV or Durable Objects throttling in Workers).

- **Content Security Policy (CSP)**
  - Serve the frontend with a strict CSP header to reduce XSS risk.
  - Example baseline: `default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self' https://api.yourdomain.com;`

- **HTTPS**
  - Enforce HTTPS end-to-end. Redirect HTTP to HTTPS at the edge.

- **Logging & Monitoring**
  - Add logging for auth failures and admin actions. Consider alerting on anomaly patterns.

- **Dependencies**
  - Run `npm audit` and keep dependencies updated.

- **Admin Controls**
  - Limit admin role assignment surface area. Ensure only admins can access admin routes.

- **Uploads**
  - If using file uploads, validate file type/size on the server, store in a safe bucket, and do not serve untrusted files from the same origin without sanitization.

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

4) Configure CORS in `worker/index.ts` to allow only your production origin.

## 🧪 Testing

- Unit test critical utilities and components
- Verify RBAC: non-admins cannot access admin pages/routes
- Validate bug create/update flows, project/repo create and delete
- Verify repository/project details modals and delete confirmations
- Validate login/logout edge cases and token expiry handling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

Built with ❤️ for the OWASP community