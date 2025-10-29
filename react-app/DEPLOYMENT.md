# Deploying BLT React App to Cloudflare Pages

This guide explains how to deploy the BLT React application to Cloudflare Pages.

## Prerequisites

- A Cloudflare account
- Git repository with the BLT code
- Django backend API deployed and accessible

## Deployment Options

### Option 1: Deploy via Cloudflare Dashboard (Recommended)

This is the easiest method and provides automatic deployments on git push.

#### Steps:

1. **Push Code to Git Repository**
   - Ensure your code is pushed to GitHub, GitLab, or Bitbucket
   - Make sure the `react-app` directory is in your repository

2. **Connect to Cloudflare Pages**
   - Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
   - Navigate to "Pages" in the left sidebar
   - Click "Create a project"
   - Click "Connect to Git"
   - Authorize Cloudflare to access your repository
   - Select the repository containing BLT code

3. **Configure Build Settings**
   ```
   Project name: blt-react (or your preferred name)
   Production branch: main
   Build command: cd react-app && npm install && npm run build
   Build output directory: react-app/dist
   Root directory: /
   ```

4. **Set Environment Variables**
   - Click "Environment variables"
   - Add the following variable:
     - Variable name: `VITE_API_URL`
     - Value: Your production Django API URL (e.g., `https://api.owaspblt.org`)
   - Note: This variable is used at build time, not runtime

5. **Deploy**
   - Click "Save and Deploy"
   - Cloudflare will build and deploy your application
   - Wait for the deployment to complete (usually 2-5 minutes)
   - You'll receive a URL like `https://blt-react.pages.dev`

6. **Set Up Custom Domain (Optional)**
   - Go to your project's "Custom domains" tab
   - Click "Set up a custom domain"
   - Enter your domain (e.g., `app.owaspblt.org`)
   - Follow the DNS configuration instructions
   - Wait for DNS to propagate (can take up to 24 hours)

### Option 2: Deploy via Wrangler CLI

This method is useful for CI/CD pipelines or manual deployments.

#### Steps:

1. **Install Wrangler**
   ```bash
   npm install -g wrangler
   ```

2. **Authenticate with Cloudflare**
   ```bash
   wrangler login
   ```
   This will open a browser window for authentication.

3. **Build the Application**
   ```bash
   cd react-app
   npm install
   VITE_API_URL=https://api.owaspblt.org npm run build
   ```

4. **Deploy to Cloudflare Pages**
   ```bash
   wrangler pages deploy dist --project-name=blt-react
   ```

5. **Access Your Deployment**
   - Wrangler will provide a URL after deployment
   - Visit the URL to see your deployed application

## Post-Deployment Configuration

### CORS Configuration

Ensure your Django backend allows requests from your Cloudflare Pages domain:

1. Update `blt/settings.py`:
   ```python
   CORS_ALLOWED_ORIGINS = [
       'https://blt-react.pages.dev',
       'https://app.owaspblt.org',  # if using custom domain
   ]
   ```

2. Install django-cors-headers if not already installed:
   ```bash
   poetry add django-cors-headers
   ```

3. Add to INSTALLED_APPS:
   ```python
   INSTALLED_APPS = [
       # ...
       'corsheaders',
       # ...
   ]
   ```

4. Add to MIDDLEWARE (near the top):
   ```python
   MIDDLEWARE = [
       'corsheaders.middleware.CorsMiddleware',
       # ...
   ]
   ```

### Environment Variables

The React app uses the following environment variable:

- `VITE_API_URL`: Django backend API URL
  - Development: `http://localhost:8000`
  - Production: Your production API URL

## Continuous Deployment

Once connected to Git, Cloudflare Pages automatically:
- Builds and deploys on every push to production branch
- Creates preview deployments for pull requests
- Provides unique URLs for each deployment

## Monitoring and Logs

1. **View Build Logs**
   - Go to your project in Cloudflare Dashboard
   - Click on a deployment
   - View the build logs to debug any issues

2. **Analytics**
   - Enable Web Analytics in Cloudflare Dashboard
   - Monitor traffic, performance, and errors

3. **Real-Time Logs**
   ```bash
   wrangler pages deployment tail
   ```

## Troubleshooting

### Build Fails

**Problem:** Build fails with npm errors
**Solution:** 
- Ensure `package-lock.json` is committed
- Check Node.js version (should be 20.x)
- Verify all dependencies are listed in `package.json`

### API Connection Issues

**Problem:** Frontend can't connect to backend
**Solution:**
- Verify `VITE_API_URL` is set correctly
- Check CORS configuration on Django backend
- Ensure backend is accessible from Cloudflare's network
- Check browser console for detailed error messages

### Routing Issues

**Problem:** Page refresh returns 404 error
**Solution:**
- Verify `_redirects` file exists in `public/` directory
- Content should be: `/* /index.html 200`
- This file is automatically copied to dist during build

### Environment Variables Not Working

**Problem:** API URL is not being picked up
**Solution:**
- Environment variables must be set at build time, not runtime
- Rebuild the application after changing environment variables
- In Cloudflare Dashboard, go to Settings → Environment variables
- Click "Redeploy" to trigger a new build with updated variables

## Performance Optimization

Cloudflare Pages provides:
- Global CDN distribution
- Automatic HTTPS
- HTTP/2 and HTTP/3 support
- Brotli compression
- DDoS protection

No additional configuration needed!

## Cost

Cloudflare Pages is free for:
- Unlimited requests
- Unlimited bandwidth
- 500 builds per month
- 100GB storage

Perfect for the BLT React app!

## Support

For Cloudflare Pages specific issues:
- [Cloudflare Pages Documentation](https://developers.cloudflare.com/pages)
- [Cloudflare Community](https://community.cloudflare.com)

For BLT app issues:
- Check the main BLT repository issues
- Consult the BLT documentation
