# Bug Reporter (BLT)

A professional bug tracking application built with React, TypeScript, Cloudflare Workers, and D1.

## Features

- **Authentication**: JWT-based auth with role-based access control (RBAC)
- **Bug Management**: Report, view, and update bug status across the lifecycle
- **Project & Repository Management**: Organize bugs by projects and repositories
- **User Management**: Admin can update roles and delete users
- **File Uploads**: Screenshot and attachment support via Cloudflare R2
- **Responsive UI**: Clean, modern interface with accessibility considerations
- **Security**: bcrypt password hashing, security headers, CORS protection

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
Copy the example environment file and configure your settings:

```bash
cp env.example .env
```

Edit `.env` with your values:
```env
JWT_SECRET=your-super-secret-jwt-key-here
ADMIN_EMAIL=admin@example.com
VITE_API_URL=http://localhost:8787
R2_BUCKET_NAME=bug-reporter-uploads
CORS_ORIGINS=http://localhost:5173
```

### 3) Setup Cloudflare resources

#### Create D1 Database
```bash
wrangler d1 create bug-reporter-db
```

Update the `database_id` in `wrangler.toml` with the ID from the output.

#### Create R2 Bucket (for file uploads)
```bash
wrangler r2 bucket create bug-reporter-uploads
```

#### Configure R2 Credentials
```bash
# Set R2 credentials for file uploads
wrangler secret put R2_ACCESS_KEY_ID
wrangler secret put R2_SECRET_ACCESS_KEY
```

### 4) Initialize database
```bash
wrangler d1 execute bug-reporter-db --file=worker/schema.sql
```

### 5) Run locally

#### Start the API (Cloudflare Worker):
```bash
npm run worker:dev
```

#### Start the frontend (in another terminal):
```bash
npm run dev
```

- Frontend: `http://localhost:5173`
- API: `http://localhost:8787`

## 🔑 Authentication
- Default admin: Use `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables
- Login and registration use JWT with PBKDF2 password hashing
- Role-based access control (admin/user)

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
├── env.example             # Environment variables template
├── wrangler.toml           # Cloudflare configuration
└── wrangler.toml.example   # Configuration template
```

## 🛠️ Scripts

- `npm run dev` - Start frontend dev server
- `npm run build` - Build frontend for production
- `npm run deploy` - Deploy frontend (e.g., Cloudflare Pages)
- `npm run worker:dev` - Start worker locally
- `npm run worker:deploy` - Deploy worker
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint issues

## 🚀 Production Deployment

### 1) Set up secrets in Cloudflare
```bash
# Generate a strong JWT secret
openssl rand -base64 32

# Set secrets in Cloudflare
wrangler secret put JWT_SECRET
wrangler secret put ADMIN_EMAIL
wrangler secret put CORS_ORIGINS
```

### 2) Update configuration
- Update `wrangler.toml` with your production database ID
- Set `VITE_API_URL` to your production API URL
- Update `CORS_ORIGINS` with your production domain

### 3) Deploy
```bash
# Build frontend
npm run build

# Deploy worker
npm run worker:deploy

# Deploy frontend (to Cloudflare Pages or your CDN)
npm run deploy
```

## 🔒 Security Features

- **Password Security**: PBKDF2 hashing with 100,000 iterations and random salt
- **JWT Authentication**: Secure token-based auth
- **CORS Protection**: Environment-based origin restrictions
- **Security Headers**: XSS protection, content type sniffing prevention
- **File Upload Security**: Type and size validation
- **Input Validation**: Server-side validation for all endpoints

## 📁 File Uploads

File uploads are stored in Cloudflare R2 with:
- Image type validation (JPEG, PNG, GIF, WebP)
- 5MB size limit
- Unique filename generation
- Public URL generation

## 🧪 Testing

See `TESTING.md` for comprehensive testing instructions including:
- Local setup verification
- API endpoint testing
- Authentication flow testing
- Admin functionality testing
