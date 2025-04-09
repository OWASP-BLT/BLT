# Organization Dashboard

An advanced organizational security and activity monitoring dashboard designed to provide comprehensive insights into project health, contributor performance, and system vulnerabilities.

## 📋 Overview

The Enhanced Organization Dashboard is a sophisticated platform that helps organizations seamlessly manage their security issues, bug reports, and contributor activity in a unified, visual interface. The system follows OWASP BLT (Bug Logging Tool) guidelines to ensure secure implementation.

### Key Features

- **Real-time issue tracking**: Monitor security issues and bug reports in real-time via WebSockets
- **Advanced filtering and reporting**: Filter bugs and security issues by severity, status, assignee, etc.
- **Comprehensive visualization**: Review security trends, risk distribution, and activity metrics through interactive charts
- **Secure implementation**: Built following OWASP security guidelines with multiple security middleware layers
- **Real-time notifications**: Receive instant updates when new issues are reported or existing ones are updated
- **Containerized deployment**: Easy deployment with Docker and Docker Compose

## 🏗️ Architecture

The system follows a hybrid architecture:

- **Frontend**: React application with modern UI components (shadcn, TailwindCSS)
- **Backend**: 
  - Django REST API for secure data handling and persistence
  - Node.js/Express server for frontend and WebSocket services
- **Database**: PostgreSQL for reliable data storage
- **Real-time communication**: WebSockets for instant updates and notifications

## 💻 Technology Stack

### Frontend
- React
- TailwindCSS
- shadcn UI components
- WebSockets for real-time updates
- TanStack Query for data fetching
- Recharts for data visualization

### Backend
- Django 5.0 with Django REST Framework (minimal imports)
- Node.js/Express
- Drizzle ORM
- WebSocket Server (ws)
- PostgreSQL database

### Security Features
- Security Headers Middleware
- SQL Injection Protection
- Rate Limiting
- CSRF Protection
- Secure Logging
- Custom Exception Handling

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- PostgreSQL 14+
- Docker and Docker Compose (for containerized deployment)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd enhanced-organization-dashboard
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your database credentials and other settings
   ```

3. **Install dependencies**

   Frontend and Node.js backend:
   ```bash
   npm install
   ```

   Django backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   npm run db:push
   cd backend
   python manage.py migrate
   ```

5. **Start development servers**

   Using the combined script:
   ```bash
   ./run-servers.sh
   ```

   Or individually:
   ```bash
   # Start Node.js server with WebSockets
   npm run dev
   
   # In another terminal, start Django server
   ./start-django.sh
   ```

6. Access the application at http://localhost:3000

## 🐳 Docker Deployment

The application can be deployed using Docker Compose for both development and production environments.

1. **Build and start containers**
   ```bash
   docker-compose up -d
   ```

2. **Apply migrations (if needed)**
   ```bash
   docker-compose exec app npm run db:push
   docker-compose exec app bash -c "cd backend && python manage.py migrate"
   ```

3. Access the application at http://localhost:3000

## 📊 Production Deployment

For production deployment, consider the following:

1. **Set production environment variables**
   - Set `NODE_ENV=production`
   - Set `DEBUG=False` for Django
   - Generate a secure `SECRET_KEY` for Django
   - Configure `ALLOWED_HOSTS` for Django

2. **Use a production-ready database setup**
   - Proper user permissions
   - Regular backups
   - Connection pooling

3. **Configure a reverse proxy (Nginx/Apache)**
   - Handle SSL termination
   - Load balancing (if scaling)
   - Static file serving

4. **Deploy using Docker**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

## 🔒 Security Features

The application implements multiple security layers following OWASP guidelines:

1. **Security Headers Middleware**: Adds security headers to prevent XSS, clickjacking, etc.
2. **SQL Injection Protection**: Filters request parameters for potential SQL injection patterns
3. **Rate Limiting**: Prevents brute force attacks by limiting API request frequency
4. **Content Security Policy**: Restricts resources that the application can load
5. **CSRF Protection**: Prevents cross-site request forgery attacks
6. **Secure Password Validation**: Enforces password complexity and prevents common passwords
7. **Secure Logging**: Prevents sensitive data exposure in logs
8. **Containerization**: Isolates the application for improved security

## ⚠️ Minimal Django Implementation

The Django backend follows a minimal approach, with:

- Only necessary Django imports
- Streamlined middleware configuration
- Focused use of Django REST Framework
- Minimal database queries
- Clean separation of concerns

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.