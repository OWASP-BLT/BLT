#!/bin/bash

# Create a temporary directory for the zip contents
mkdir -p /tmp/owasp-compliance-checker

# Create directory structure
mkdir -p /tmp/owasp-compliance-checker/client/src/{components,hooks,layouts,lib,pages,types}
mkdir -p /tmp/owasp-compliance-checker/client/src/components/ui
mkdir -p /tmp/owasp-compliance-checker/server/compliance
mkdir -p /tmp/owasp-compliance-checker/shared

# Copy client files
cp -r client/src/components /tmp/owasp-compliance-checker/client/src/
cp -r client/src/hooks /tmp/owasp-compliance-checker/client/src/
cp -r client/src/layouts /tmp/owasp-compliance-checker/client/src/
cp -r client/src/lib /tmp/owasp-compliance-checker/client/src/
cp -r client/src/pages /tmp/owasp-compliance-checker/client/src/
cp -r client/src/types /tmp/owasp-compliance-checker/client/src/
cp client/src/App.tsx /tmp/owasp-compliance-checker/client/src/
cp client/src/index.css /tmp/owasp-compliance-checker/client/src/
cp client/src/main.tsx /tmp/owasp-compliance-checker/client/src/
cp client/index.html /tmp/owasp-compliance-checker/client/

# Copy server files
cp -r server/compliance /tmp/owasp-compliance-checker/server/
cp server/index.ts /tmp/owasp-compliance-checker/server/
cp server/routes.ts /tmp/owasp-compliance-checker/server/
cp server/storage.ts /tmp/owasp-compliance-checker/server/
cp server/vite.ts /tmp/owasp-compliance-checker/server/

# Copy shared files
cp shared/schema.ts /tmp/owasp-compliance-checker/shared/

# Copy configuration files
cp package.json /tmp/owasp-compliance-checker/
cp tsconfig.json /tmp/owasp-compliance-checker/
cp vite.config.ts /tmp/owasp-compliance-checker/
cp postcss.config.js /tmp/owasp-compliance-checker/
cp tailwind.config.ts /tmp/owasp-compliance-checker/
cp theme.json /tmp/owasp-compliance-checker/
cp drizzle.config.ts /tmp/owasp-compliance-checker/

# Create README file
cat > /tmp/owasp-compliance-checker/README.md << 'EOL'
# OWASP Compliance Checker

A web application that checks open-source projects against OWASP compliance standards and generates a detailed 100-point assessment report.

## Features

- Check GitHub repositories against 100 OWASP compliance criteria
- Generate detailed compliance reports with scores for 10 categories
- Visualize results with interactive dashboards
- Receive actionable recommendations for improving compliance
- Download PDF reports for documentation and sharing

## Project Structure

```
├── client/                # Frontend React application
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── layouts/       # Page layouts
│   │   ├── lib/           # Utility functions
│   │   ├── pages/         # Page components
│   │   ├── types/         # TypeScript type definitions
│   │   ├── App.tsx        # Main application component
│   │   ├── index.css      # Global styles
│   │   └── main.tsx       # Entry point
│   └── index.html         # HTML template
│
├── server/                # Backend Node.js application
│   ├── compliance/        # Compliance checking logic
│   │   ├── checker.ts     # Repository analysis
│   │   ├── criteria.ts    # 100-point criteria definitions
│   │   ├── github.ts      # GitHub API integration
│   │   └── report.ts      # PDF report generation
│   ├── index.ts           # Server entry point
│   ├── routes.ts          # API route definitions
│   ├── storage.ts         # Data storage implementation
│   └── vite.ts            # Vite server configuration
│
└── shared/                # Shared code between frontend and backend
    └── schema.ts          # Data schema definitions
```

## Getting Started

1. Install dependencies:
   ```
   npm install
   ```

2. Run the development server:
   ```
   npm run dev
   ```

3. Open http://localhost:5000 in your browser

## Technologies Used

- React with TypeScript
- Node.js with Express
- TanStack Query for data fetching
- Tailwind CSS for styling
- Shadcn UI components
- Zod for validation
- PDF report generation
EOL

# Create a zip file
cd /tmp
zip -r owasp-compliance-checker.zip owasp-compliance-checker

# Move the zip to the project root
mv /tmp/owasp-compliance-checker.zip /home/runner/${REPL_SLUG}/owasp-compliance-checker.zip

# Clean up
rm -rf /tmp/owasp-compliance-checker

echo "ZIP file created: owasp-compliance-checker.zip"