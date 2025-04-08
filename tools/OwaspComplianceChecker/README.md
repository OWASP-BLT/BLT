# OWASP Compliance Checker

A comprehensive web application that checks open-source projects against OWASP compliance standards and generates a detailed 100-point assessment report.

![OWASP Compliance Checker]
![License]

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
   git clone https://github.com/satishkumar620/owasp-compliance-checker.git
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

## 🚢 Deployment


### Deployment Options

#### Deploying to Heroku

1. Create a `Procfile` in the root directory:
   ```
   web: npm start
   ```

2. Add a start script to `package.json`:
   ```json
   "scripts": {
     "start": "node dist/server/index.js",
     "build": "tsc -p ."
   }
   ```

3. Deploy to Heroku:
   ```bash
   heroku create
   git push heroku main
   ```

#### Deploying with Docker

1. Create a `Dockerfile` in the root directory:
   ```Dockerfile
   FROM node:16-alpine
   WORKDIR /app
   COPY package*.json ./
   RUN npm install
   COPY . .
   RUN npm run build
   EXPOSE 5000
   CMD ["npm", "start"]
   ```

2. Build and run the Docker image:
   ```bash
   docker build -t owasp-compliance-checker .
   docker run -p 5000:5000 owasp-compliance-checker
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
