import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { jwt, sign, verify } from 'hono/jwt';
import { HTTPException } from 'hono/http-exception';

type Bindings = {
  DB: D1Database;
  UPLOADS: R2Bucket;
  JWT_SECRET: string;
  ADMIN_EMAIL: string;
  CORS_ORIGINS: string;
};

type Variables = {
  user: {
    id: number;
    email: string;
    role: string;
  };
};

const app = new Hono<{ Bindings: Bindings; Variables: Variables }>();

// Security headers middleware
app.use('*', async (c, next) => {
  await next();
  c.header('X-Content-Type-Options', 'nosniff');
  c.header('X-Frame-Options', 'DENY');
  c.header('X-XSS-Protection', '1; mode=block');
  c.header('Referrer-Policy', 'strict-origin-when-cross-origin');
  c.header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;");
});

// CORS middleware with environment-based origins
app.use('*', cors({
  origin: (origin, c) => {
    const allowedOrigins = c.env.CORS_ORIGINS?.split(',') || ['http://localhost:5173', 'http://localhost:3000'];
    return allowedOrigins.includes(origin || '');
  },
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization'],
}));

// Auth middleware with better error handling
const authMiddleware = async (c: any, next: any) => {
  try {
    const authHeader = c.req.header('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new HTTPException(401, { message: 'Missing or invalid authorization header' });
    }

    const token = authHeader.substring(7);
    const payload = await verify(token, c.env.JWT_SECRET);
    
    // Check if token is expired
    if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) {
      throw new HTTPException(401, { message: 'Token expired' });
    }

    c.set('jwtPayload', payload);
    await next();
  } catch (error) {
    console.error('Auth middleware error:', error);
    throw new HTTPException(401, { message: 'Invalid token' });
  }
};

// Helper function to hash passwords using PBKDF2 (Cloudflare Workers compatible)
async function hashPassword(password: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  
  const key = await crypto.subtle.importKey(
    'raw',
    data,
    'PBKDF2',
    false,
    ['deriveBits']
  );
  
  const derivedBits = await crypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      salt: salt,
      iterations: 100000,
      hash: 'SHA-256'
    },
    key,
    256
  );
  
  // Combine salt and hash
  const combined = new Uint8Array(salt.length + derivedBits.byteLength);
  combined.set(salt);
  combined.set(new Uint8Array(derivedBits), salt.length);
  
  return Array.from(combined)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

// Helper function to verify passwords with backward compatibility
async function verifyPassword(password: string, hash: string): Promise<boolean> {
  // Note: Legacy admin password check removed for security
  
  // Check if it's a PBKDF2 hash (hex string of length 96 = 16 bytes salt + 32 bytes hash)
  if (hash.length === 96) {
    try {
      const hexPairs = hash.match(/.{2}/g);
      if (!hexPairs) return false;
      const combined = new Uint8Array(hexPairs.map(byte => parseInt(byte, 16)));
      const salt = combined.slice(0, 16);
      const storedHash = combined.slice(16);
      
      const encoder = new TextEncoder();
      const data = encoder.encode(password);
      
      const key = await crypto.subtle.importKey(
        'raw',
        data,
        'PBKDF2',
        false,
        ['deriveBits']
      );
      
      const derivedBits = await crypto.subtle.deriveBits(
        {
          name: 'PBKDF2',
          salt: salt,
          iterations: 100000,
          hash: 'SHA-256'
        },
        key,
        256
      );
      
      const derivedHash = new Uint8Array(derivedBits);
      return storedHash.every((byte, index) => byte === derivedHash[index]);
    } catch (error) {
      console.error('PBKDF2 verification error:', error);
      return false;
    }
  }
  
  // Legacy SHA-256 fallback for old passwords
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const shaHash = await crypto.subtle.digest('SHA-256', data);
  const shaHashString = Array.from(new Uint8Array(shaHash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
  return shaHashString === hash;
}

// Auth routes
app.post('/api/auth/login', async (c) => {
  try {
    const { email, password } = await c.req.json();
    
    const user = await c.env.DB.prepare(
      'SELECT * FROM users WHERE email = ?'
    ).bind(email).first();

    if (!user) {
      throw new HTTPException(401, { message: 'Invalid credentials' });
    }

    const isValidPassword = await verifyPassword(password, user.password_hash);
    if (!isValidPassword) {
      throw new HTTPException(401, { message: 'Invalid credentials' });
    }

    const token = await sign(
      { 
        id: user.id, 
        email: user.email, 
        role: user.role,
        exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60) // 24 hours
      },
      c.env.JWT_SECRET
    );

    return c.json({
      token,
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        role: user.role,
        avatar_url: user.avatar_url
      }
    });
  } catch (error) {
    console.error('Login error:', error);
    throw new HTTPException(500, { message: 'Login failed' });
  }
});

app.post('/api/auth/register', async (c) => {
  try {
    const { email, name, password } = await c.req.json();
    
    // Check if user already exists
    const existingUser = await c.env.DB.prepare(
      'SELECT id FROM users WHERE email = ?'
    ).bind(email).first();

    if (existingUser) {
      throw new HTTPException(400, { message: 'User already exists' });
    }

    const hashedPassword = await hashPassword(password);
    const role = email === c.env.ADMIN_EMAIL ? 'admin' : 'user';

    const result = await c.env.DB.prepare(
      'INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?) RETURNING *'
    ).bind(email, name, hashedPassword, role).first();

    const token = await sign(
      { 
        id: result.id, 
        email: result.email, 
        role: result.role,
        exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60)
      },
      c.env.JWT_SECRET
    );

    return c.json({
      token,
      user: {
        id: result.id,
        email: result.email,
        name: result.name,
        role: result.role,
        avatar_url: result.avatar_url
      }
    });
  } catch (error) {
    console.error('Registration error:', error);
    throw new HTTPException(500, { message: 'Registration failed' });
  }
});

// Protected routes
app.use('/api/protected/*', authMiddleware);

// File upload endpoint (protected)
app.post('/api/protected/uploads', async (c) => {
  try {
    const formData = await c.req.formData();
    const file = formData.get('file') as File;
    
    if (!file) {
      throw new HTTPException(400, { message: 'No file provided' });
    }
    
    // Validate file type (images only)
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      throw new HTTPException(400, { message: 'Only image files are allowed' });
    }
    
    // Validate file size (max 5MB)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      throw new HTTPException(400, { message: 'File size must be less than 5MB' });
    }
    
    // Generate unique filename
    const timestamp = Date.now();
    const randomId = crypto.randomUUID();
    const extension = file.name.split('.').pop() || 'jpg';
    const filename = `uploads/${timestamp}-${randomId}.${extension}`;
    
    // Upload to R2
    await c.env.UPLOADS.put(filename, file.stream(), {
      httpMetadata: {
        contentType: file.type,
      },
    });
    
    // Return public URL
    const publicUrl = `https://pub-${c.env.UPLOADS.bucket_name}.r2.dev/${filename}`;
    
    return c.json({ url: publicUrl });
  } catch (error) {
    console.error('File upload error:', error);
    if (error instanceof HTTPException) {
      throw error;
    }
    throw new HTTPException(500, { message: 'File upload failed' });
  }
});

// User info
app.get('/api/protected/me', async (c) => {
  const payload = c.get('jwtPayload');
  const user = await c.env.DB.prepare(
    'SELECT id, email, name, role, avatar_url FROM users WHERE id = ?'
  ).bind(payload.id).first();
  
  return c.json({ user });
});

// Bugs routes - visible to all users
app.get('/api/protected/bugs', async (c) => {
  const url = new URL(c.req.url);
  const search = url.searchParams.get('search');
  const status = url.searchParams.get('status');
  const severity = url.searchParams.get('severity');
  const project = url.searchParams.get('project');
  
  let query = `
    SELECT b.*, u.name as reporter_name, u.email as reporter_email,
           p.name as project_name, r.name as repository_name
    FROM bugs b
    LEFT JOIN users u ON b.reporter_id = u.id
    LEFT JOIN projects p ON b.project_id = p.id
    LEFT JOIN repositories r ON b.repository_id = r.id
  `;
  
  const conditions: string[] = [];
  const params: any[] = [];
  
  if (search) {
    conditions.push('(b.title LIKE ? OR b.description LIKE ? OR u.name LIKE ? OR p.name LIKE ?)');
    const searchTerm = `%${search}%`;
    params.push(searchTerm, searchTerm, searchTerm, searchTerm);
  }
  
  if (status) {
    conditions.push('b.status = ?');
    params.push(status);
  }
  
  if (severity) {
    conditions.push('b.severity = ?');
    params.push(severity);
  }
  
  if (project) {
    conditions.push('p.name LIKE ?');
    params.push(`%${project}%`);
  }
  
  if (conditions.length > 0) {
    query += ' WHERE ' + conditions.join(' AND ');
  }
  
  query += ' ORDER BY b.created_at DESC';
  
  const bugs = await c.env.DB.prepare(query).bind(...params).all();
  
  return c.json({ bugs: bugs.results });
});

// Get single bug details
app.get('/api/protected/bugs/:id', async (c) => {
  const bugId = c.req.param('id');
  const bug = await c.env.DB.prepare(`
    SELECT b.*, u.name as reporter_name, u.email as reporter_email,
           p.name as project_name, r.name as repository_name
    FROM bugs b
    LEFT JOIN users u ON b.reporter_id = u.id
    LEFT JOIN projects p ON b.project_id = p.id
    LEFT JOIN repositories r ON b.repository_id = r.id
    WHERE b.id = ?
  `).bind(bugId).first();
  
  if (!bug) {
    throw new HTTPException(404, { message: 'Bug not found' });
  }
  
  return c.json({ bug });
});

app.post('/api/protected/bugs', async (c) => {
  try {
    const payload = c.get('jwtPayload');
    const { title, description, severity, project_id, repository_id, screenshot_url, steps_to_reproduce, expected_behavior, actual_behavior } = await c.req.json();
    
    const result = await c.env.DB.prepare(`
      INSERT INTO bugs (title, description, severity, reporter_id, project_id, repository_id, screenshot_url, steps_to_reproduce, expected_behavior, actual_behavior)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      RETURNING *
    `).bind(title, description, severity, payload.id, project_id, repository_id, screenshot_url, steps_to_reproduce, expected_behavior, actual_behavior).first();

    return c.json({ bug: result });
  } catch (error) {
    console.error('Create bug error:', error);
    throw new HTTPException(500, { message: 'Failed to create bug' });
  }
});

app.put('/api/protected/bugs/:id', async (c) => {
  try {
    const payload = c.get('jwtPayload');
    const bugId = c.req.param('id');
    const updates = await c.req.json();
    
    // Check if user owns the bug or is admin
    const bug = await c.env.DB.prepare('SELECT * FROM bugs WHERE id = ?').bind(bugId).first();
    if (!bug || (payload.role !== 'admin' && bug.reporter_id !== payload.id)) {
      throw new HTTPException(403, { message: 'Not authorized to update this bug' });
    }
    
    // Build update query dynamically
    const allowedFields = ['title', 'description', 'severity', 'status', 'project_id', 'repository_id', 'screenshot_url', 'steps_to_reproduce', 'expected_behavior', 'actual_behavior'];
    const updateFields = Object.keys(updates).filter(key => allowedFields.includes(key));
    
    if (updateFields.length === 0) {
      throw new HTTPException(400, { message: 'No valid fields to update' });
    }
    
    const setClause = updateFields.map(field => `${field} = ?`).join(', ');
    const values = updateFields.map(field => updates[field]);
    
    await c.env.DB.prepare(`UPDATE bugs SET ${setClause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?`)
      .bind(...values, bugId).run();
    
    // Return updated bug
    const updatedBug = await c.env.DB.prepare(`
      SELECT b.*, u.name as reporter_name, u.email as reporter_email,
             p.name as project_name, r.name as repository_name
      FROM bugs b
      LEFT JOIN users u ON b.reporter_id = u.id
      LEFT JOIN projects p ON b.project_id = p.id
      LEFT JOIN repositories r ON b.repository_id = r.id
      WHERE b.id = ?
    `).bind(bugId).first();
    
    return c.json({ bug: updatedBug });
  } catch (error) {
    console.error('Update bug error:', error);
    throw new HTTPException(500, { message: 'Failed to update bug' });
  }
});

// Projects routes
app.get('/api/protected/projects', async (c) => {
  const url = new URL(c.req.url);
  const search = url.searchParams.get('search');
  const status = url.searchParams.get('status');
  
  let query = `
    SELECT p.*, u.name as created_by_name,
           COUNT(b.id) as bugs_count
    FROM projects p
    LEFT JOIN users u ON p.created_by = u.id
    LEFT JOIN bugs b ON p.id = b.project_id
  `;
  
  const conditions: string[] = [];
  const params: any[] = [];
  
  if (search) {
    conditions.push('(p.name LIKE ? OR p.description LIKE ? OR u.name LIKE ?)');
    const searchTerm = `%${search}%`;
    params.push(searchTerm, searchTerm, searchTerm);
  }
  
  if (status) {
    conditions.push('p.status = ?');
    params.push(status);
  }
  
  if (conditions.length > 0) {
    query += ' WHERE ' + conditions.join(' AND ');
  }
  
  query += ' GROUP BY p.id ORDER BY p.created_at DESC';
  
  const projects = await c.env.DB.prepare(query).bind(...params).all();
  
  return c.json({ projects: projects.results });
});

// Get single project details
app.get('/api/protected/projects/:id', async (c) => {
  const projectId = c.req.param('id');
  const project = await c.env.DB.prepare(`
    SELECT p.*, u.name as created_by_name,
           COUNT(b.id) as bugs_count
    FROM projects p
    LEFT JOIN users u ON p.created_by = u.id
    LEFT JOIN bugs b ON p.id = b.project_id
    WHERE p.id = ?
    GROUP BY p.id
  `).bind(projectId).first();
  
  if (!project) {
    throw new HTTPException(404, { message: 'Project not found' });
  }
  
  return c.json({ project });
});

app.post('/api/protected/projects', async (c) => {
  try {
    const payload = c.get('jwtPayload');
    const { name, description } = await c.req.json();
    
    // Check if project already exists
    const existingProject = await c.env.DB.prepare(
      'SELECT id FROM projects WHERE LOWER(name) = LOWER(?)'
    ).bind(name).first();

    if (existingProject) {
      throw new HTTPException(400, { message: 'Project with this name already exists' });
    }
    
    const result = await c.env.DB.prepare(
      'INSERT INTO projects (name, description, created_by) VALUES (?, ?, ?) RETURNING *'
    ).bind(name, description, payload.id).first();

    return c.json({ project: result });
  } catch (error) {
    console.error('Create project error:', error);
    throw new HTTPException(500, { message: 'Failed to create project' });
  }
});

// Find or create project by name
app.post('/api/protected/projects/find-or-create', async (c) => {
  try {
    const payload = c.get('jwtPayload');
    const { name, description } = await c.req.json();
    
    // First try to find existing project
    let project = await c.env.DB.prepare(
      'SELECT * FROM projects WHERE LOWER(name) = LOWER(?)'
    ).bind(name).first();

    if (!project) {
      // Create new project if it doesn't exist
      project = await c.env.DB.prepare(
        'INSERT INTO projects (name, description, created_by) VALUES (?, ?, ?) RETURNING *'
      ).bind(name, description || '', payload.id).first();
    }

    return c.json({ project });
  } catch (error) {
    console.error('Find or create project error:', error);
    throw new HTTPException(500, { message: 'Failed to find or create project' });
  }
});

// Find or create repository by name
app.post('/api/protected/repositories/find-or-create', async (c) => {
  try {
    const { name, url, language, project_id } = await c.req.json();
    
    // First try to find existing repository
    let repository = await c.env.DB.prepare(
      'SELECT * FROM repositories WHERE LOWER(name) = LOWER(?) AND project_id = ?'
    ).bind(name, project_id).first();

    if (!repository) {
      // Create new repository if it doesn't exist
      repository = await c.env.DB.prepare(
        'INSERT INTO repositories (name, url, language, project_id) VALUES (?, ?, ?, ?) RETURNING *'
      ).bind(name, url || '', language || '', project_id).first();
    }

    return c.json({ repository });
  } catch (error) {
    console.error('Find or create repository error:', error);
    throw new HTTPException(500, { message: 'Failed to find or create repository' });
  }
});

// Get single repository details
app.get('/api/protected/repositories/:id', async (c) => {
  const repoId = c.req.param('id');
  const repository = await c.env.DB.prepare(`
    SELECT r.*, p.name as project_name,
           COUNT(b.id) as bugs_count
    FROM repositories r
    LEFT JOIN projects p ON r.project_id = p.id
    LEFT JOIN bugs b ON r.id = b.repository_id
    WHERE r.id = ?
    GROUP BY r.id
  `).bind(repoId).first();
  
  if (!repository) {
    throw new HTTPException(404, { message: 'Repository not found' });
  }
  
  return c.json({ repository });
});

// Repositories routes
app.get('/api/protected/repositories', async (c) => {
  const url = new URL(c.req.url);
  const search = url.searchParams.get('search');
  const status = url.searchParams.get('status');
  const project = url.searchParams.get('project');
  const language = url.searchParams.get('language');
  
  let query = `
    SELECT r.*, p.name as project_name
    FROM repositories r
    LEFT JOIN projects p ON r.project_id = p.id
  `;
  
  const conditions: string[] = [];
  const params: any[] = [];
  
  if (search) {
    conditions.push('(r.name LIKE ? OR r.url LIKE ? OR p.name LIKE ?)');
    const searchTerm = `%${search}%`;
    params.push(searchTerm, searchTerm, searchTerm);
  }
  
  if (status) {
    conditions.push('r.status = ?');
    params.push(status);
  }
  
  if (project) {
    conditions.push('p.name LIKE ?');
    params.push(`%${project}%`);
  }
  
  if (language) {
    conditions.push('r.language LIKE ?');
    params.push(`%${language}%`);
  }
  
  if (conditions.length > 0) {
    query += ' WHERE ' + conditions.join(' AND ');
  }
  
  query += ' ORDER BY r.created_at DESC';
  
  const repositories = await c.env.DB.prepare(query).bind(...params).all();
  
  return c.json({ repositories: repositories.results });
});

app.post('/api/protected/repositories', async (c) => {
  try {
    const { name, url, language, project_id } = await c.req.json();
    
    const result = await c.env.DB.prepare(
      'INSERT INTO repositories (name, url, language, project_id) VALUES (?, ?, ?, ?) RETURNING *'
    ).bind(name, url, language, project_id).first();

    return c.json({ repository: result });
  } catch (error) {
    console.error('Create repository error:', error);
    throw new HTTPException(500, { message: 'Failed to create repository' });
  }
});

// Admin-only routes
app.use('/api/protected/admin/*', async (c, next) => {
  const payload = c.get('jwtPayload');
  if (payload.role !== 'admin') {
    throw new HTTPException(403, { message: 'Admin access required' });
  }
  await next();
});

app.get('/api/protected/admin/users', async (c) => {
  const url = new URL(c.req.url);
  const search = url.searchParams.get('search');
  const role = url.searchParams.get('role');
  
  let query = `
    SELECT u.id, u.email, u.name, u.role, u.created_at,
           COUNT(b.id) as bugs_reported
    FROM users u
    LEFT JOIN bugs b ON u.id = b.reporter_id
  `;
  
  const conditions: string[] = [];
  const params: any[] = [];
  
  if (search) {
    conditions.push('(u.name LIKE ? OR u.email LIKE ?)');
    const searchTerm = `%${search}%`;
    params.push(searchTerm, searchTerm);
  }
  
  if (role) {
    conditions.push('u.role = ?');
    params.push(role);
  }
  
  if (conditions.length > 0) {
    query += ' WHERE ' + conditions.join(' AND ');
  }
  
  query += ' GROUP BY u.id ORDER BY u.created_at DESC';
  
  const users = await c.env.DB.prepare(query).bind(...params).all();
  
  return c.json({ users: users.results });
});

app.get('/api/protected/admin/stats', async (c) => {
  const [totalBugs, criticalBugs, resolvedBugs, totalUsers, totalProjects, totalRepositories] = await Promise.all([
    c.env.DB.prepare('SELECT COUNT(*) as count FROM bugs').first(),
    c.env.DB.prepare('SELECT COUNT(*) as count FROM bugs WHERE severity = "critical"').first(),
    c.env.DB.prepare('SELECT COUNT(*) as count FROM bugs WHERE status = "resolved"').first(),
    c.env.DB.prepare('SELECT COUNT(*) as count FROM users').first(),
    c.env.DB.prepare('SELECT COUNT(*) as count FROM projects').first(),
    c.env.DB.prepare('SELECT COUNT(*) as count FROM repositories').first(),
  ]);

  return c.json({
    stats: {
      totalBugs: totalBugs.count,
      criticalBugs: criticalBugs.count,
      resolvedBugs: resolvedBugs.count,
      totalUsers: totalUsers.count,
      totalProjects: totalProjects.count,
      totalRepositories: totalRepositories.count
    }
  });
});

// Delete project endpoint
app.delete('/api/protected/projects/:id', async (c) => {
  try {
    const payload = c.get('jwtPayload');
    const projectId = c.req.param('id');
    
    // Check if user is admin or created the project
    const project = await c.env.DB.prepare('SELECT * FROM projects WHERE id = ?').bind(projectId).first();
    if (!project) {
      throw new HTTPException(404, { message: 'Project not found' });
    }
    
    if (payload.role !== 'admin' && project.created_by !== payload.id) {
      throw new HTTPException(403, { message: 'Not authorized to delete this project' });
    }
    
    await c.env.DB.prepare('DELETE FROM projects WHERE id = ?').bind(projectId).run();
    
    return c.json({ message: 'Project deleted successfully' });
  } catch (error) {
    console.error('Delete project error:', error);
    throw new HTTPException(500, { message: 'Failed to delete project' });
  }
});

// Delete repository endpoint
app.delete('/api/protected/repositories/:id', async (c) => {
  try {
    const payload = c.get('jwtPayload');
    const repoId = c.req.param('id');
    
    const repository = await c.env.DB.prepare('SELECT * FROM repositories WHERE id = ?').bind(repoId).first();
    if (!repository) {
      throw new HTTPException(404, { message: 'Repository not found' });
    }
    
    // Check if user is admin or has access to the project
    const project = await c.env.DB.prepare('SELECT * FROM projects WHERE id = ?').bind(repository.project_id).first();
    if (payload.role !== 'admin' && project.created_by !== payload.id) {
      throw new HTTPException(403, { message: 'Not authorized to delete this repository' });
    }
    
    await c.env.DB.prepare('DELETE FROM repositories WHERE id = ?').bind(repoId).run();
    
    return c.json({ message: 'Repository deleted successfully' });
  } catch (error) {
    console.error('Delete repository error:', error);
    if (error instanceof HTTPException) {
      throw error;
    }
    throw new HTTPException(500, { message: 'Failed to delete repository' });
  }
});

// Delete user endpoint
app.delete('/api/protected/admin/users/:id', async (c) => {
  try {
    const payload = c.get('jwtPayload');
    const userId = c.req.param('id');
    
    // Prevent admin from deleting themselves
    if (payload.id === parseInt(userId)) {
      throw new HTTPException(400, { message: 'Cannot delete your own account' });
    }
    
    const user = await c.env.DB.prepare('SELECT * FROM users WHERE id = ?').bind(userId).first();
    if (!user) {
      throw new HTTPException(404, { message: 'User not found' });
    }
    
    await c.env.DB.prepare('DELETE FROM users WHERE id = ?').bind(userId).run();
    
    return c.json({ message: 'User deleted successfully' });
  } catch (error) {
    console.error('Delete user error:', error);
    throw new HTTPException(500, { message: 'Failed to delete user' });
  }
});

// Update user endpoint
app.put('/api/protected/admin/users/:id', async (c) => {
  try {
    const userId = c.req.param('id');
    const { name, email, role, password } = await c.req.json();
    
    const user = await c.env.DB.prepare('SELECT * FROM users WHERE id = ?').bind(userId).first();
    if (!user) {
      throw new HTTPException(404, { message: 'User not found' });
    }
    
    // Check if email is already taken by another user
    if (email !== user.email) {
      const existingUser = await c.env.DB.prepare('SELECT id FROM users WHERE email = ? AND id != ?').bind(email, userId).first();
      if (existingUser) {
        throw new HTTPException(400, { message: 'Email already taken' });
      }
    }
    
    // If password is provided, hash it and update
    if (password) {
      const hashedPassword = await hashPassword(password);
      await c.env.DB.prepare('UPDATE users SET name = ?, email = ?, role = ?, password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?')
        .bind(name, email, role, hashedPassword, userId).run();
    } else {
      await c.env.DB.prepare('UPDATE users SET name = ?, email = ?, role = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?')
        .bind(name, email, role, userId).run();
    }
    
    const updatedUser = await c.env.DB.prepare('SELECT id, email, name, role, avatar_url, created_at FROM users WHERE id = ?').bind(userId).first();
    
    return c.json({ user: updatedUser });
  } catch (error) {
    console.error('Update user error:', error);
    throw new HTTPException(500, { message: 'Failed to update user' });
  }
});

// Change own password endpoint
app.put('/api/protected/change-password', async (c) => {
  try {
    const payload = c.get('jwtPayload');
    const { currentPassword, newPassword } = await c.req.json();
    
    if (!currentPassword || !newPassword) {
      throw new HTTPException(400, { message: 'Current password and new password are required' });
    }
    
    // Verify current password
    const user = await c.env.DB.prepare('SELECT * FROM users WHERE id = ?').bind(payload.id).first();
    if (!user) {
      throw new HTTPException(404, { message: 'User not found' });
    }
    
    const isValidPassword = await verifyPassword(currentPassword, user.password_hash);
    if (!isValidPassword) {
      throw new HTTPException(401, { message: 'Current password is incorrect' });
    }
    
    // Hash and update new password
    const hashedPassword = await hashPassword(newPassword);
    await c.env.DB.prepare('UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?')
      .bind(hashedPassword, payload.id).run();
    
    return c.json({ message: 'Password changed successfully' });
  } catch (error) {
    console.error('Change password error:', error);
    throw new HTTPException(500, { message: 'Failed to change password' });
  }
});

export default app;
