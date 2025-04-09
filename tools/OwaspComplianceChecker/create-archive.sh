#!/bin/bash

# Create a temporary directory for the archive contents
mkdir -p /tmp/owasp-compliance-checker

# Create directory structure
mkdir -p /tmp/owasp-compliance-checker/client/src/{components,hooks,layouts,lib,pages,types}
mkdir -p /tmp/owasp-compliance-checker/client/src/components/ui
mkdir -p /tmp/owasp-compliance-checker/server/compliance
mkdir -p /tmp/owasp-compliance-checker/shared
mkdir -p /tmp/owasp-compliance-checker/scripts

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

# Create comprehensive README file
cat > /tmp/owasp-compliance-checker/README.md << 'EOL'
# OWASP Compliance Checker

A comprehensive web application that checks open-source projects against OWASP compliance standards and generates a detailed 100-point assessment report.

![OWASP Compliance Checker](https://img.shields.io/badge/OWASP-Compliance%20Checker-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

## 📋 Overview

This application helps developers and security teams evaluate GitHub repositories against a comprehensive 100-point checklist based on OWASP security standards. It provides a detailed assessment across ten critical categories:

1. General Compliance & Governance
2. Documentation & Usability
3. Code Quality & Best Practices
4. Security & OWASP Compliance
5. CI/CD & DevSecOps
6. Testing & Validation
7. Performance & Scalability
8. Logging & Monitoring
9. Community & Support
10. Legal & Compliance

## ✨ Features

- **Repository Analysis**: Enter a GitHub repository URL to automatically check it against 100 compliance criteria
- **Comprehensive Dashboard**: Visual presentation of compliance scores with an intuitive interface
- **Category Breakdown**: Detailed scores for each of the 10 assessment categories
- **Interactive Visualization**: Progress bars and charts showing compliance levels
- **Actionable Recommendations**: Get specific recommendations for improving compliance
- **Downloadable Reports**: Generate and download PDF reports for documentation

## 🖥️ Screenshots

![Dashboard Screenshot](screenshots/dashboard.png)
![Results Screenshot](screenshots/results.png)

## 🛠️ Technologies Used

- **Frontend**: React, TypeScript, TailwindCSS, shadcn/ui
- **Backend**: Node.js, Express
- **State Management**: TanStack Query (React Query)
- **Data Validation**: Zod
- **Styling**: TailwindCSS with custom theming
- **PDF Generation**: Custom PDF generation service

## 🚀 Getting Started

### Prerequisites

- Node.js 16+ and npm

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/owasp-compliance-checker.git
   cd owasp-compliance-checker
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and navigate to http://localhost:5000

### Usage

1. Enter a GitHub repository URL in the format `https://github.com/organization/repository`
2. Click "Check Compliance"
3. Review the comprehensive report with scores across all 10 categories
4. Expand categories to see detailed checkpoint results
5. Review recommendations for improving compliance
6. Download the PDF report for sharing or documentation

## 📁 Project Structure

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

## 📊 Compliance Categories

1. **General Compliance & Governance (10 points)**
   - Project goals and scope
   - Open-source licensing
   - Documentation standards
   - Contribution guidelines
   - Project governance

2. **Documentation & Usability (10 points)**
   - README quality
   - Installation & usage guides
   - API documentation
   - Code comments
   - Versioning strategy

3. **Code Quality & Best Practices (10 points)**
   - Coding standards
   - Code modularity
   - Secure coding principles
   - Input validation
   - Output encoding

4. **Security & OWASP Compliance (15 points)**
   - Dependency vulnerabilities
   - Authentication mechanisms
   - Access control implementation
   - OWASP Top 10 compliance
   - Secure communications

5. **CI/CD & DevSecOps (10 points)**
   - Automated testing
   - Continuous integration
   - Security scanning
   - Dependency checking
   - Container security

6. **Testing & Validation (10 points)**
   - Test coverage
   - Edge case testing
   - Security testing
   - Performance testing
   - Regression testing

7. **Performance & Scalability (10 points)**
   - Code optimization
   - Database efficiency
   - Caching strategies
   - Load handling
   - Resource management

8. **Logging & Monitoring (10 points)**
   - Comprehensive logging
   - Error handling
   - Monitoring integration
   - Alerting mechanisms
   - Audit trails

9. **Community & Support (10 points)**
   - Active maintainers
   - Issue responsiveness
   - Community engagement
   - Documentation quality
   - Support channels

10. **Legal & Compliance (5 points)**
    - License compliance
    - Copyright notices
    - Third-party licenses
    - Export compliance
    - Privacy considerations

## 🧪 Running Tests

Run the test suite with:

```bash
npm test
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👏 Acknowledgements

- [OWASP Foundation](https://owasp.org/) for their security standards and best practices
- [Shadcn UI](https://ui.shadcn.com/) for the beautiful UI components
- [React](https://reactjs.org/) and [Node.js](https://nodejs.org/) communities for the excellent frameworks
EOL

# Create LICENSE file
cat > /tmp/owasp-compliance-checker/LICENSE << 'EOL'
MIT License

Copyright (c) 2023 OWASP Compliance Checker

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOL

# Create CONTRIBUTING.md file
cat > /tmp/owasp-compliance-checker/CONTRIBUTING.md << 'EOL'
# Contributing to OWASP Compliance Checker

We love your input! We want to make contributing to the OWASP Compliance Checker as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

### Pull Requests

1. Fork the repository and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

### Issues

We use GitHub issues to track public bugs. Report a bug by opening a new issue; it's that easy!

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Code of Conduct

### Our Pledge

In the interest of fostering an open and welcoming environment, we as contributors and maintainers pledge to making participation in our project and our community a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment include:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

Examples of unacceptable behavior by participants include:

- The use of sexualized language or imagery and unwelcome sexual attention or advances
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information, such as a physical or electronic address, without explicit permission
- Other conduct which could reasonably be considered inappropriate in a professional setting

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.
EOL

# Create .gitignore file
cat > /tmp/owasp-compliance-checker/.gitignore << 'EOL'
# Dependency directories
node_modules/
dist/
build/
.cache/

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Editor directories and files
.idea/
.vscode/
*.swp
*.swo
*~

# Debug logs
npm-debug.log*
yarn-debug.log*
yarn-error.log*
debug.log

# Production build files
/dist
/build
/out

# Coverage directory used by tools like istanbul
coverage/

# TypeScript cache
*.tsbuildinfo

# Optional npm cache directory
.npm

# Optional eslint cache
.eslintcache

# Yarn Integrity file
.yarn-integrity

# dotenv environment variable files
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# parcel-bundler cache
.parcel-cache

# Next.js build output
.next
out

# Serverless directories
.serverless/

# Mac files
.DS_Store

# Windows files
Thumbs.db
ehthumbs.db
Desktop.ini

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
venv/
ENV/
EOL

# Create DEPENDENCIES.md file
cat > /tmp/owasp-compliance-checker/DEPENDENCIES.md << 'EOL'
# Project Dependencies

## Node.js Dependencies

### Core Dependencies
- `react`: ^18.2.0
- `react-dom`: ^18.2.0
- `express`: ^4.18.2
- `drizzle-orm`: ^0.27.0
- `zod`: ^3.22.2
- `@tanstack/react-query`: ^5.8.4

### UI and Components
- `@radix-ui/*`: Various UI primitives
- `class-variance-authority`: ^0.7.0
- `clsx`: ^2.0.0
- `cmdk`: ^0.2.0
- `tailwindcss`: ^3.3.3
- `tailwindcss-animate`: ^1.0.7
- `lucide-react`: ^0.292.0
- `react-icons`: ^4.12.0

### Form Handling
- `react-hook-form`: ^7.48.2
- `@hookform/resolvers`: ^3.3.2

### Data Validation
- `zod`: ^3.22.2
- `drizzle-zod`: ^0.4.2
- `zod-validation-error`: ^1.5.0

### Routing and Navigation
- `wouter`: ^2.12.0

### State Management
- `@tanstack/react-query`: ^5.8.4

### Database
- `@neondatabase/serverless`: ^0.6.0
- `drizzle-kit`: ^0.19.13
- `drizzle-orm`: ^0.27.0

### Development Tools
- `typescript`: ^5.2.2
- `vite`: ^4.5.0
- `@vitejs/plugin-react`: ^4.1.1
- `tailwindcss`: ^3.3.3
- `postcss`: ^8.4.31
- `autoprefixer`: ^10.4.16
- `esbuild`: ^0.19.8
- `tsx`: ^4.6.2
EOL

# Create requirements.txt file for Python dependencies
cat > /tmp/owasp-compliance-checker/requirements.txt << 'EOL'
# Python dependencies (if using Python components)
flask==2.0.1
reportlab==3.6.1
PyPDF2==1.26.0
PyGithub==1.55
requests==2.26.0
python-dotenv==0.19.0
pandas==1.3.3
numpy==1.21.2
pytest==6.2.5
EOL

# Create a setup script
cat > /tmp/owasp-compliance-checker/scripts/setup.sh << 'EOL'
#!/bin/bash
# Setup script for OWASP Compliance Checker

# Ensure we're in the project root
cd "$(dirname "$0")/.." || exit

# Install dependencies
echo "Installing dependencies..."
npm install

# Create necessary directories
mkdir -p screenshots

echo "Setup complete! You can now run 'npm run dev' to start the application."
EOL
chmod +x /tmp/owasp-compliance-checker/scripts/setup.sh

# Create a tar.gz file
cd /tmp
tar -czvf owasp-compliance-checker.tar.gz owasp-compliance-checker

# Move the archive to the project root
mv /tmp/owasp-compliance-checker.tar.gz /home/runner/${REPL_SLUG}/owasp-compliance-checker.tar.gz

# Clean up
rm -rf /tmp/owasp-compliance-checker

echo "Archive created: owasp-compliance-checker.tar.gz"