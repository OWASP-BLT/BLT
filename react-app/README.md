# BLT React App

A modern React-based frontend for OWASP BLT (Bug Logging Tool), built with Vite and designed to work on Cloudflare Pages.

## Features

- 🚀 Built with React 19 and Vite for optimal performance
- 🎨 Styled with Tailwind CSS v4
- 🔐 Authentication integration with Django backend
- 📱 Fully responsive design
- ☁️ Cloudflare Pages ready

## Getting Started

### Prerequisites

- Node.js 20.x or higher
- npm 10.x or higher
- Running BLT Django backend (for API)

### Installation

1. Install dependencies:

```bash
npm install
```

2. Create environment file:

```bash
cp .env.example .env
```

3. Update `.env` with your API URL:

```env
VITE_API_URL=http://localhost:8000
```

### Development

Run the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Building for Production

Build the application:

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

## Deployment to Cloudflare Pages

### Method 1: Cloudflare Dashboard

1. Push your code to a Git repository (GitHub, GitLab, etc.)
2. Log in to Cloudflare Dashboard
3. Go to Pages and click "Create a project"
4. Connect your Git repository
5. Configure build settings:
   - **Build command:** `npm run build`
   - **Build output directory:** `dist`
   - **Root directory:** `react-app`
6. Add environment variables:
   - `VITE_API_URL`: Your production API URL
7. Click "Save and Deploy"

### Method 2: Wrangler CLI

1. Install Wrangler:

```bash
npm install -g wrangler
```

2. Login to Cloudflare:

```bash
wrangler login
```

3. Deploy:

```bash
npm run build
wrangler pages deploy dist --project-name=blt-react
```

## Project Structure

```
react-app/
├── src/
│   ├── components/     # Reusable components (Header, Footer, Layout)
│   ├── pages/          # Page components (Home, Login, Dashboard, etc.)
│   ├── services/       # API services and utilities
│   ├── config/         # Configuration files
│   ├── utils/          # Utility functions
│   ├── App.jsx         # Main app component with routing
│   ├── main.jsx        # Entry point
│   └── index.css       # Global styles with Tailwind
├── public/             # Static assets
├── .env.example        # Environment variables template
├── vite.config.js      # Vite configuration
└── package.json        # Dependencies and scripts
```

## API Integration

The React app communicates with the Django backend through REST APIs. Make sure the backend is running and accessible at the URL specified in `VITE_API_URL`.

### Available API Endpoints

- Authentication: `/auth/`
- Issues: `/api/v1/issues/`
- Profile: `/api/v1/profile/`
- Organizations: `/api/v1/organizations/`
- Leaderboard: `/api/v1/leaderboard/`

## Customization

### Colors

The app uses `#e74c3c` as the primary red color throughout. This can be customized in `src/index.css`.

### API Configuration

Update `src/config/api.js` to add or modify API endpoints.

## Contributing

Please follow the existing code style and use the provided ESLint configuration.

## License

This project is licensed under the same license as the main BLT project (AGPLv3).
