-- Users table
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
  avatar_url TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived')),
  created_by INTEGER REFERENCES users(id),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Repositories table
CREATE TABLE IF NOT EXISTS repositories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  language TEXT,
  project_id INTEGER REFERENCES projects(id),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'scanning', 'completed')),
  last_scan DATETIME,
  vulnerabilities_count INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Bugs table
CREATE TABLE IF NOT EXISTS bugs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  status TEXT DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
  reporter_id INTEGER REFERENCES users(id),
  assignee_id INTEGER REFERENCES users(id),
  project_id INTEGER REFERENCES projects(id),
  repository_id INTEGER REFERENCES repositories(id),
  screenshot_url TEXT,
  steps_to_reproduce TEXT,
  expected_behavior TEXT,
  actual_behavior TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Bug comments table
CREATE TABLE IF NOT EXISTS bug_comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bug_id INTEGER REFERENCES bugs(id),
  user_id INTEGER REFERENCES users(id),
  comment TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin user (password: admin123)
INSERT OR IGNORE INTO users (email, name, password_hash, role) 
VALUES ('admin@example.com', 'Admin User', '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin');

-- Insert sample projects
INSERT OR IGNORE INTO projects (name, description, created_by) 
VALUES 
  ('OWASP BLT Core', 'Main bug tracking platform for OWASP BLT', 1),
  ('Mobile Security Testing', 'Security testing for mobile applications', 1),
  ('Web API Security', 'API security vulnerability assessment', 1);

-- Insert sample repositories
INSERT OR IGNORE INTO repositories (name, url, language, project_id, status, last_scan, vulnerabilities_count) 
VALUES 
  ('owasp-blt/frontend', 'https://github.com/owasp-blt/frontend', 'TypeScript', 1, 'active', '2024-09-28', 3),
  ('owasp-blt/backend', 'https://github.com/owasp-blt/backend', 'Python', 1, 'scanning', '2024-09-27', 7),
  ('mobile-security/android-app', 'https://github.com/mobile-security/android-app', 'Java', 2, 'completed', '2024-09-26', 12);