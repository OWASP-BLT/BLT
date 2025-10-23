# Testing Guide for Bug Reporter

This guide provides comprehensive testing instructions for the Bug Reporter application.

## 🚀 Local Setup Verification

### 1. Environment Setup
```bash
# Copy environment template
cp env.example .env

# Edit .env with your values
# JWT_SECRET=your-super-secret-jwt-key-here
# ADMIN_EMAIL=admin@example.com
# VITE_API_URL=http://localhost:8787
# R2_BUCKET_NAME=bug-reporter-uploads
# CORS_ORIGINS=http://localhost:5173
```

### 2. Database Setup
```bash
# Create D1 database
wrangler d1 create bug-reporter-db

# Update database_id in wrangler.toml

# Initialize database
wrangler d1 execute bug-reporter-db --file=worker/schema.sql
```

### 3. R2 Bucket Setup
```bash
# Create R2 bucket for file uploads
wrangler r2 bucket create bug-reporter-uploads
```

### 4. Start Services
```bash
# Terminal 1: Start API
npm run worker:dev

# Terminal 2: Start Frontend
npm run dev
```

## 🔧 API Testing

### Authentication Endpoints

#### 1. Register New User
```bash
curl -X POST http://localhost:8787/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "name": "Test User",
    "password": "testpass123"
  }'
```

#### 2. Login
```bash
curl -X POST http://localhost:8787/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "$ADMIN_EMAIL",
    "password": "$ADMIN_PASSWORD"
  }'
```

**Expected Response:**
```json
{
  "token": "eyJ...",
  "user": {
    "id": 1,
    "email": "admin@example.com",
    "name": "Admin User",
    "role": "admin",
    "avatar_url": null
  }
}
```

#### 3. Get Current User
```bash
curl -X GET http://localhost:8787/api/protected/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Bug Management Endpoints

#### 1. Get All Bugs
```bash
curl -X GET http://localhost:8787/api/protected/bugs \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 2. Create Bug
```bash
curl -X POST http://localhost:8787/api/protected/bugs \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Bug",
    "description": "This is a test bug description",
    "severity": "high",
    "project_id": 1,
    "repository_id": 1,
    "steps_to_reproduce": "1. Open app\n2. Click button\n3. See error",
    "expected_behavior": "Button should work",
    "actual_behavior": "Button crashes app"
  }'
```

#### 3. Update Bug Status
```bash
curl -X PUT http://localhost:8787/api/protected/bugs/1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress"
  }'
```

### File Upload Testing

#### 1. Upload Screenshot
```bash
curl -X POST http://localhost:8787/api/protected/uploads \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/screenshot.png"
```

**Expected Response:**
```json
{
  "url": "https://pub-bug-reporter-uploads.r2.dev/uploads/1234567890-uuid.png"
}
```

### Project Management Endpoints

#### 1. Get All Projects
```bash
curl -X GET http://localhost:8787/api/protected/projects \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 2. Create Project
```bash
curl -X POST http://localhost:8787/api/protected/projects \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Project",
    "description": "A test project for bug tracking"
  }'
```

### Admin Endpoints

#### 1. Get All Users (Admin Only)
```bash
curl -X GET http://localhost:8787/api/protected/admin/users \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

#### 2. Update User Role
```bash
curl -X PUT http://localhost:8787/api/protected/admin/users/2 \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "email": "updated@example.com",
    "role": "admin"
  }'
```

#### 3. Get Dashboard Stats
```bash
curl -X GET http://localhost:8787/api/protected/admin/stats \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

## 🌐 Frontend Testing

### 1. Authentication Flow
1. Navigate to `http://localhost:5173`
2. Click "Login" or "Register"
3. Test login with `$ADMIN_EMAIL` / `$ADMIN_PASSWORD`
4. Verify redirect to `/app/bugs`
5. Test logout functionality

### 2. Bug Management
1. **Create Bug:**
   - Click "Report Bug" button
   - Fill in all required fields
   - Upload a screenshot
   - Submit and verify success message

2. **View Bugs:**
   - Navigate to Bugs page
   - Verify bug cards display correctly
   - Test search and filter functionality
   - Click on bug to view details

3. **Update Bug:**
   - Click on a bug to open details
   - Change status using dropdown
   - Verify status updates immediately

### 3. Project Management
1. Navigate to Projects page
2. Click "Create Project"
3. Fill in project details
4. Submit and verify project appears in list
5. Test project search functionality

### 4. Repository Management
1. Navigate to Repositories page
2. Click "Add Repository"
3. Fill in repository details
4. Link to existing project
5. Submit and verify repository appears

### 5. Admin Functions (Admin Only)
1. Login as admin user
2. Navigate to User Management
3. Test user role updates
4. Test user deletion (be careful!)
5. Verify dashboard stats display

## 🔒 Security Testing

### 1. Authentication Security
- Test with invalid credentials
- Test with expired tokens
- Test with malformed tokens
- Verify 401 responses for unauthorized access

### 2. Authorization Testing
- Test admin-only endpoints with regular user
- Test user can only update their own bugs
- Test CORS with different origins

### 3. File Upload Security
- Test with non-image files (should fail)
- Test with oversized files (should fail)
- Test with malicious filenames
- Verify file type validation

### 4. Input Validation
- Test with empty required fields
- Test with SQL injection attempts
- Test with XSS payloads
- Test with extremely long inputs

## 🐛 Common Issues & Solutions

### 1. Database Connection Issues
```bash
# Check if database exists
wrangler d1 list

# Recreate database if needed
wrangler d1 delete bug-reporter-db
wrangler d1 create bug-reporter-db
```

### 2. CORS Issues
- Verify `CORS_ORIGINS` in environment
- Check browser console for CORS errors
- Ensure frontend URL matches CORS configuration

### 3. File Upload Issues
- Verify R2 bucket exists
- Check bucket permissions
- Test with small files first

### 4. Authentication Issues
- Verify JWT_SECRET is set
- Check token expiration
- Clear browser localStorage if needed

## 📊 Performance Testing

### 1. Load Testing
```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test API endpoints
ab -n 100 -c 10 http://localhost:8787/api/protected/bugs
```

### 2. Database Performance
- Test with large datasets
- Verify index usage
- Monitor query performance

## 🧪 Automated Testing

### 1. API Tests (using curl scripts)
Create test scripts for each endpoint and run them in sequence.

### 2. Frontend Tests
- Test all user flows
- Test error scenarios
- Test responsive design
- Test accessibility

### 3. Integration Tests
- Test complete bug reporting flow
- Test file upload integration
- Test admin workflows

## 📝 Test Checklist

- [ ] Environment setup complete
- [ ] Database initialized
- [ ] R2 bucket configured
- [ ] API endpoints responding
- [ ] Authentication working
- [ ] File uploads working
- [ ] Admin functions working
- [ ] Security measures active
- [ ] Frontend fully functional
- [ ] Error handling working
- [ ] Performance acceptable

## 🚨 Production Testing

Before deploying to production:

1. **Security Audit:**
   - Verify all secrets are set via `wrangler secret put`
   - Test with production CORS origins
   - Verify security headers

2. **Performance Testing:**
   - Load test with realistic data
   - Monitor database performance
   - Test file upload limits

3. **Backup Testing:**
   - Test database backup/restore
   - Test R2 bucket backup
   - Verify disaster recovery procedures

## 📞 Support

If you encounter issues:

1. Check the browser console for errors
2. Check the API logs in the terminal
3. Verify environment variables are set correctly
4. Test with curl commands to isolate issues
5. Check Cloudflare dashboard for D1 and R2 status
