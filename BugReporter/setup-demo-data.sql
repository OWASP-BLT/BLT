-- Add some sample bugs for testing
INSERT OR IGNORE INTO bugs (id, title, description, severity, status, reporter_id, project_id, repository_id, steps_to_reproduce, expected_behavior, actual_behavior, created_at) VALUES 
(1, 'Login Form Validation Error', 'The login form does not validate email format properly', 'medium', 'open', 1, 1, 1, '1. Go to login page\n2. Enter invalid email\n3. Click submit', 'Should show email validation error', 'Form submits without validation', '2024-09-28 10:00:00'),
(2, 'Critical Security Vulnerability', 'SQL injection vulnerability in user search', 'critical', 'in_progress', 1, 1, 2, '1. Go to user search\n2. Enter SQL injection payload\n3. Execute search', 'Should sanitize input', 'Raw SQL is executed', '2024-09-28 09:30:00'),
(3, 'UI Button Alignment Issue', 'Submit button is misaligned on mobile devices', 'low', 'resolved', 1, 2, 3, '1. Open app on mobile\n2. Navigate to form\n3. Observe button position', 'Button should be centered', 'Button appears off-center', '2024-09-27 14:20:00');

-- Add a regular user for testing
INSERT OR IGNORE INTO users (id, email, name, password_hash, role, created_at) VALUES 
(2, 'user@example.com', 'Test User', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'user', '2024-09-28 10:00:00');