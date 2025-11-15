from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import Labs, TaskContent, Tasks


class Command(BaseCommand):
    help = "Seeds security labs (IDOR, File Upload, Sensitive Data Exposure, Broken Authentication, Open Redirect, SSRF) with all their tasks"

    def handle(self, *args, **kwargs):
        labs_data = [
            {
                "name": "Insecure Direct Object Reference (IDOR)",
                "description": "Master IDOR vulnerabilities where applications expose internal object references without proper authorization checks. Learn to exploit direct object references in URLs, APIs, and file access.",
                "estimated_time": 45,
                "order": 1,
                "tasks": [
                    {
                        "name": "Introduction to IDOR",
                        "description": "Learn what Insecure Direct Object References (IDOR) are and how they occur.",
                        "task_type": "theory",
                        "order": 1,
                        "theory_content": """
                            <h2>What is Insecure Direct Object Reference (IDOR)?</h2>
                            <p>IDOR occurs when an application exposes internal object references like user IDs, filenames, or database keys, without verifying authorization.</p>

                            <h3>Example</h3>
                            <pre><code>
                            GET /profile?user_id=101
                            </code></pre>
                            <p>If changing user_id=101 to user_id=102 reveals another user's profile, this is an IDOR vulnerability.</p>

                            <h3>Impact</h3>
                            <ul>
                                <li>Unauthorized data access</li>
                                <li>Data modification or deletion</li>
                                <li>Sensitive info exposure</li>
                            </ul>
                        """,
                        "mcq_question": "What is the core issue in an IDOR vulnerability?",
                        "mcq_options": [
                            "A) Lack of authentication",
                            "B) Lack of authorization checks on object access",
                            "C) Weak encryption",
                            "D) Unpatched server",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Common IDOR Attack Scenarios",
                        "description": "Explore real-world cases and common patterns.",
                        "task_type": "theory",
                        "order": 2,
                        "theory_content": """
                            <h2>Common IDOR Scenarios</h2>
                            <ul>
                                <li>Profile access: /profile?user_id=5</li>
                                <li>Invoice download: /invoice?id=873</li>
                                <li>File access: /files/report_2023.pdf</li>
                            </ul>

                            <h3>API Example</h3>
                            <pre><code>
                            GET /api/user/45
                            </code></pre>
                            <p>If user A can access user B's info by changing the ID, it's IDOR.</p>
                        """,
                        "mcq_question": "Which URL is most likely vulnerable to IDOR?",
                        "mcq_options": [
                            "A) /login",
                            "B) /dashboard",
                            "C) /profile?user_id=5",
                            "D) /home",
                        ],
                        "correct_answer": "C",
                    },
                    {
                        "name": "IDOR Exploit Simulation - Profile Access",
                        "description": "Access another user's profile by modifying user_id.",
                        "task_type": "simulation",
                        "order": 3,
                        "simulation_config": {
                            "type": "idor_profile",
                            "scenario": "profile_data_access",
                            "target_url": "/vulnerable-profile?user_id=2",
                            "vulnerable_parameters": ["user_id"],
                            "success_payload": "Change user_id=2 to user_id=3",
                            "success_criteria": "See another user's profile by changing user_id.",
                            "hints": [
                                "Look for numeric IDs",
                                "Try incrementing/decrementing ID",
                            ],
                            "difficulty": "beginner",
                        },
                    },
                    {
                        "name": "Advanced IDOR - API Endpoint",
                        "description": "Exploit insecure API ID parameter to pull another user's data.",
                        "task_type": "simulation",
                        "order": 4,
                        "simulation_config": {
                            "type": "idor_api",
                            "scenario": "api_data_leak",
                            "target_url": "/api/user?id=101",
                            "vulnerable_parameters": ["id"],
                            "success_payload": "Change id=101 to id=102",
                            "success_criteria": "Obtain data of another user via API.",
                            "hints": [
                                "Try sequential IDs",
                                "Compare JSON responses",
                            ],
                            "difficulty": "intermediate",
                        },
                    },
                    {
                        "name": "Preventing IDOR Vulnerabilities",
                        "description": "Learn secure techniques to avoid IDOR.",
                        "task_type": "theory",
                        "order": 5,
                        "theory_content": """
                            <h2>Preventing IDOR</h2>
                            <ul>
                                <li>Check authorization for all object access</li>
                                <li>Use indirect references (random UUIDs)</li>
                                <li>Do backend validation; never trust client input</li>
                            </ul>

                            <pre><code>
                            # Insecure
                            GET /profile?user_id=123

                            # Secure
                            GET /profile
                            (server gets logged-in user from session)
                            </code></pre>
                        """,
                        "mcq_question": "What is the best defense against IDOR?",
                        "mcq_options": [
                            "A) Use POST for everything",
                            "B) Hide IDs in HTML",
                            "C) Verify object ownership server-side",
                            "D) Minify JavaScript",
                        ],
                        "correct_answer": "C",
                    },
                ],
            },
            {
                "name": "File Upload Vulnerabilities",
                "description": "Explore critical file upload security flaws that allow attackers to upload malicious files and execute code on servers. Learn to bypass extension filters, MIME type validation, and path traversal restrictions.",
                "estimated_time": 50,
                "order": 2,
                "tasks": [
                    {
                        "name": "Introduction to File Upload Vulnerabilities",
                        "description": "Learn why unrestricted file uploads are dangerous and common attack patterns.",
                        "task_type": "theory",
                        "order": 1,
                        "theory_content": """
                            <h2>What are File Upload Vulnerabilities?</h2>
                            <p>File Upload Vulnerabilities occur when an application accepts files from users without proper validation, allowing attackers to upload malicious files (web shells), bypass access controls, or overwrite sensitive files.</p>

                            <h3>Common risks</h3>
                            <ul>
                                <li>Remote code execution (uploading web shells)</li>
                                <li>Content-based attacks (malicious scripts disguised as images)</li>
                                <li>Path traversal (writing files outside allowed directories)</li>
                                <li>Denial of Service (large or numerous uploads)</li>
                            </ul>

                            <h3>Typical vulnerable code</h3>
                            <pre><code>
                            // Poor example: saving uploaded file with original filename without validation
                            filename = request.FILES['file'].name
                            open("/var/www/uploads/" + filename, "wb").write(request.FILES['file'].read())
                            </code></pre>
                        """,
                        "mcq_question": "Which of the following is the best practice to reduce file upload risk?",
                        "mcq_options": [
                            "A) Allow any file extension but scan contents on demand",
                            "B) Validate file type, restrict extensions, and store outside the web root",
                            "C) Save files using user-controlled filenames",
                            "D) Serve uploaded files directly from the application server",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "File Type & Content Validation",
                        "description": "Understand checks for MIME type, extension and magic bytes, and why each matters.",
                        "task_type": "theory",
                        "order": 2,
                        "theory_content": """
                            <h2>File Validation Techniques</h2>
                            <ul>
                                <li><strong>Extension checks:</strong> Useful but can be bypassed by renaming files.</li>
                                <li><strong>MIME type checks:</strong> Based on headers; can be spoofed.</li>
                                <li><strong>Magic byte inspection:</strong> Checking file signatures is stronger.</li>
                                <li><strong>Content scanning:</strong> Anti-virus / malware scanning as an additional layer.</li>
                            </ul>

                            <h3>Best practices</h3>
                            <ul>
                                <li>Whitelist allowed file types and verify magic bytes</li>
                                <li>Store uploads outside the web root and serve via authenticated proxy</li>
                                <li>Rename files to server-generated tokens (avoid original filenames)</li>
                                <li>Limit file size and enforce quotas</li>
                            </ul>
                        """,
                        "mcq_question": "Why is checking only file extension insufficient?",
                        "mcq_options": [
                            "A) Extensions are always correct",
                            "B) Attackers can rename files to bypass extension checks",
                            "C) Extensions validate magic bytes",
                            "D) Extensions prevent XSS",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Simulation: Upload a Web Shell (Safe Lab)",
                        "description": "Simulate uploading a malicious web shell file and demonstrating execution (lab safely simulates execution output).",
                        "task_type": "simulation",
                        "order": 3,
                        "simulation_config": {
                            "type": "upload_shell",
                            "scenario": "web_shell_upload",
                            "target_url": "/upload",
                            "vulnerable_parameters": ["file"],
                            "success_payload": "upload a file named shell.php containing '<?php echo shell_exec($_GET[\"cmd\"]); ?>'",
                            "success_criteria": "Lab marks it as executable and returns simulated command output",
                            "hints": [
                                "Try a .php file with a simple payload",
                                "Try double extensions like image.php.jpg",
                                "The lab simulates execution (no real system commands run)",
                            ],
                            "difficulty": "intermediate",
                        },
                    },
                    {
                        "name": "Simulation: Content-Type Bypass",
                        "description": "Bypass naive MIME-type checks by uploading a malicious payload disguised as an image.",
                        "task_type": "simulation",
                        "order": 4,
                        "simulation_config": {
                            "type": "upload_mimetype_bypass",
                            "scenario": "mimetype_bypass",
                            "target_url": "/upload",
                            "vulnerable_parameters": ["file"],
                            "success_payload": "Upload file with .jpg extension but with embedded script content",
                            "success_criteria": "Lab detects disguised malicious content",
                            "hints": [
                                "Add PHP inside a .jpg",
                                "Try payload in EXIF or metadata (simulated)",
                            ],
                            "difficulty": "intermediate",
                        },
                    },
                    {
                        "name": "Simulation: Path Traversal via Filename",
                        "description": "Exploit improper file path handling to write outside upload directory.",
                        "task_type": "simulation",
                        "order": 5,
                        "simulation_config": {
                            "type": "upload_path_traversal",
                            "scenario": "path_traversal",
                            "target_url": "/upload?path=",
                            "vulnerable_parameters": ["file", "path"],
                            "success_payload": "Use '../../secrets.txt' to simulate writing outside upload directory",
                            "success_criteria": "Lab reveals simulated secret contents",
                            "hints": [
                                "Try ../ sequences",
                                "Use URL-encoded traversal",
                            ],
                            "difficulty": "advanced",
                        },
                    },
                    {
                        "name": "Secure File Upload Practices",
                        "description": "Learn secure practices for file upload systems.",
                        "task_type": "theory",
                        "order": 6,
                        "theory_content": """
                            <h2>Secure File Upload Best Practices</h2>
                            <ul>
                                <li>Whitelist extensions + verify magic bytes</li>
                                <li>Store uploads outside web root</li>
                                <li>Generate server-side filenames</li>
                                <li>Use auth-protected file serving</li>
                                <li>Limit upload size</li>
                            </ul>
                        """,
                        "mcq_question": "Which is NOT a recommended secure upload practice?",
                        "mcq_options": [
                            "A) Store uploads outside webroot",
                            "B) Validate magic bytes",
                            "C) Use user-controlled filenames directly",
                            "D) Use server-generated filenames",
                        ],
                        "correct_answer": "C",
                    },
                    {
                        "name": "File Upload Challenge - Restricted Extensions",
                        "description": "Server blocks .php and .jsp — find a bypass.",
                        "task_type": "simulation",
                        "order": 7,
                        "simulation_config": {
                            "type": "upload_restricted_ext_bypass",
                            "scenario": "double_extension",
                            "target_url": "/upload",
                            "vulnerable_parameters": ["file"],
                            "success_payload": "shell.php.jpg",
                            "success_criteria": "Lab simulates execution output from double-extension file",
                            "hints": [
                                "Try double extensions",
                                "Try tricky filenames / mixed casing",
                            ],
                            "difficulty": "advanced",
                        },
                    },
                ],
            },
            {
                "name": "Sensitive Data Exposure",
                "description": "Discover how applications inadvertently expose sensitive information through misconfigurations and poor security practices. Learn to identify leaked credentials, API keys, and personal data in error messages, backups, and client-side code.",
                "estimated_time": 40,
                "order": 3,
                "tasks": [
                    {
                        "name": "Introduction to Sensitive Data Exposure",
                        "description": "Understand what sensitive data exposure is, why it matters, and common sources of leaks.",
                        "task_type": "theory",
                        "order": 1,
                        "theory_content": """
                            <h2>What is Sensitive Data Exposure?</h2>
                            <p>Sensitive Data Exposure occurs when applications, APIs, or servers fail to adequately protect confidential information such as credentials, API keys, personal data, or cryptographic keys.</p>

                            <h3>Common sensitive data types</h3>
                            <ul>
                              <li>Passwords and password hashes</li>
                              <li>API keys, tokens, and secrets</li>
                              <li>Personally Identifiable Information (PII)</li>
                              <li>Encryption keys and certificates</li>
                              <li>Internal configuration and debug data</li>
                            </ul>

                            <h3>Typical sources of exposure</h3>
                            <ul>
                              <li>Misconfigured storage (public S3 buckets, exposed directories)</li>
                              <li>Verbose error messages or stack traces</li>
                              <li>Unencrypted transmissions (HTTP instead of HTTPS)</li>
                              <li>Leftover files (.git, backups) on web root</li>
                              <li>Logging secrets to accessible logs</li>
                            </ul>
                        """,
                        "mcq_question": "Which of the following is a primary risk from sensitive data exposure?",
                        "mcq_options": [
                            "A) Faster page loads",
                            "B) Credential theft and service compromise",
                            "C) Improved SEO",
                            "D) Reduced disk usage",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Data-in-Transit: TLS and Transport Security",
                        "description": "Learn about protecting data during transport and common TLS misconfigurations.",
                        "task_type": "theory",
                        "order": 2,
                        "theory_content": """
                            <h2>Protecting Data in Transit</h2>
                            <p>Use TLS to encrypt data between clients and servers.</p>
                            <ul>
                                <li>Enforce TLS 1.2+ and disable insecure ciphers</li>
                                <li>Use HSTS</li>
                                <li>Redirect HTTP to HTTPS and validate certificates</li>
                            </ul>
                        """,
                        "mcq_question": "Which practice helps protect data in transit?",
                        "mcq_options": [
                            "A) Serving sensitive API over HTTP",
                            "B) Enforcing HTTPS with HSTS",
                            "C) Embedding credentials in query strings",
                            "D) Using self-signed certificates in production",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Leakage via Debug/Error Messages (Simulation)",
                        "description": "Simulate leaking secrets in verbose error pages.",
                        "task_type": "simulation",
                        "order": 3,
                        "simulation_config": {
                            "type": "error_leak",
                            "scenario": "stack_trace_disclosure",
                            "target_url": "/user/profile?show=error",
                            "vulnerable_parameters": ["show"],
                            "success_payload": "Trigger a stack trace showing 'DB_PASSWORD=secret_db_pass'",
                            "success_criteria": "Simulated trace reveals safe example of a secret.",
                            "hints": [
                                "Try show=error",
                                "Look for debug endpoints",
                            ],
                            "difficulty": "beginner",
                        },
                    },
                    {
                        "name": "Exposed Backup/.git or Public Files (Simulation)",
                        "description": "Simulate exposed config or repository files revealing secrets.",
                        "task_type": "simulation",
                        "order": 4,
                        "simulation_config": {
                            "type": "file_exposure",
                            "scenario": "exposed_git",
                            "target_url": "/.git/HEAD",
                            "vulnerable_parameters": [],
                            "success_payload": "Access /.git/config or backup/config.bak and find simulated AWS key",
                            "success_criteria": "Retrieve simulated config with safe example key",
                            "hints": [
                                "Try /.git/HEAD",
                                "/backup/config.bak",
                                "/config/.env",
                            ],
                            "difficulty": "intermediate",
                        },
                    },
                    {
                        "name": "API Key / Secret in JavaScript or HTML (Simulation)",
                        "description": "Simulate discovering secrets embedded in static files.",
                        "task_type": "simulation",
                        "order": 5,
                        "simulation_config": {
                            "type": "asset_leak",
                            "scenario": "frontend_key_disclosure",
                            "target_url": "/static/js/app.js",
                            "vulnerable_parameters": [],
                            "success_payload": "Find 'API_KEY = \"AKIA...EXAMPLE\"'",
                            "success_criteria": "Locate simulated hardcoded API key",
                            "hints": [
                                "Inspect JS/CSS",
                                "Search for TOKEN or KEY strings",
                            ],
                            "difficulty": "beginner",
                        },
                    },
                    {
                        "name": "Insecure Storage: Plaintext Secrets (Simulation)",
                        "description": "Simulate plaintext stored credentials.",
                        "task_type": "simulation",
                        "order": 6,
                        "simulation_config": {
                            "type": "storage_plaintext",
                            "scenario": "plaintext_passwords",
                            "target_url": "/admin/export-users",
                            "vulnerable_parameters": [],
                            "success_payload": "Download simulated CSV with plaintext password example",
                            "success_criteria": "Reveal plaintext or weak-hash example",
                            "hints": [
                                "Try admin/export endpoints",
                            ],
                            "difficulty": "intermediate",
                        },
                    },
                    {
                        "name": "Token Replay & Poorly Scoped Tokens",
                        "description": "Theory: long-lived tokens & overly broad scopes.",
                        "task_type": "theory",
                        "order": 7,
                        "theory_content": """
                            <h2>Token Risks</h2>
                            <p>Tokens should expire fast, be scoped, and revocable.</p>
                            <ul>
                                <li>Short expiry</li>
                                <li>Minimal permissions</li>
                                <li>Revocation & monitoring</li>
                            </ul>
                        """,
                        "mcq_question": "Which reduces the blast radius if a key is leaked?",
                        "mcq_options": [
                            "A) Long-lived, broad tokens",
                            "B) Short-lived minimal scope tokens",
                            "C) Hardcode secrets",
                            "D) Reuse same key everywhere",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Prevention & Remediation Best Practices",
                        "description": "Learn controls to prevent leaks.",
                        "task_type": "theory",
                        "order": 8,
                        "theory_content": """
                            <h2>Remediation & Prevention</h2>
                            <ul>
                              <li>Encrypt at rest + in transit</li>
                              <li>Use secrets managers</li>
                              <li>Do not store secrets in repos</li>
                              <li>Limit PII and retention</li>
                            </ul>
                        """,
                        "mcq_question": "Which is a secure way to manage secrets?",
                        "mcq_options": [
                            "A) Put secrets in git",
                            "B) Use a secrets manager",
                            "C) Store plaintext secrets in web root",
                            "D) Hardcode in source",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Sensitive Data Exposure Challenge - Safe Remediation",
                        "description": "Simulation: find exposed secret & provide remediation text.",
                        "task_type": "simulation",
                        "order": 9,
                        "simulation_config": {
                            "type": "remediation_plan",
                            "scenario": "identify_and_remediate",
                            "target_url": "/.env",
                            "vulnerable_parameters": [],
                            "success_payload": "Find simulated SECRET_KEY and provide remediation steps",
                            "success_criteria": "User mentions rotate, revoke, secrets manager",
                            "hints": [
                                "Search for exposed /.env",
                                "Provide fix steps",
                            ],
                            "difficulty": "advanced",
                        },
                    },
                ],
            },
            {
                "name": "Broken Authentication",
                "description": "Comprehensive coverage of authentication vulnerabilities including weak credentials, session management flaws, and JWT misconfigurations. Practice credential stuffing, session fixation, and token forgery attacks.",
                "estimated_time": 50,
                "order": 4,
                "tasks": [
                    {
                        "name": "Introduction to Broken Authentication",
                        "description": "Overview of authentication failures, their causes, and impacts.",
                        "task_type": "theory",
                        "order": 1,
                        "theory_content": """
                            <h2>What is Broken Authentication?</h2>
                            <p>Broken Authentication refers to weaknesses in authentication and session management that allow attackers to compromise passwords or impersonate users.</p>

                            <h3>Common Issues</h3>
                            <ul>
                                <li>Weak/default passwords</li>
                                <li>Brute-force or credential stuffing</li>
                                <li>Predictable session IDs</li>
                                <li>Insecure password reset flows</li>
                                <li>JWT misconfigurations (alg=none)</li>
                            </ul>
                        """,
                        "mcq_question": "Which control mitigates credential stuffing?",
                        "mcq_options": [
                            "A) Unlimited login attempts",
                            "B) Progressive rate-limiting and lockouts",
                            "C) Client-side only validation",
                            "D) Remove password complexity rules",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Default & Weak Credentials",
                        "description": "Why default credentials are dangerous.",
                        "task_type": "theory",
                        "order": 2,
                        "theory_content": """
                            <h2>Default Credentials</h2>
                            <p>Attackers try common default passwords like admin/admin.</p>
                            <h3>Prevention</h3>
                            <ul>
                                <li>Force password change at first login</li>
                                <li>Strong password requirements</li>
                                <li>Use MFA</li>
                            </ul>
                        """,
                        "mcq_question": "What reduces risk of default credentials?",
                        "mcq_options": [
                            "A) Force credential change on first use",
                            "B) Publish default passwords publicly",
                            "C) Use same default creds everywhere",
                            "D) Disable logs",
                        ],
                        "correct_answer": "A",
                    },
                    {
                        "name": "Simulation: Login with Default Credentials",
                        "description": "Log in with a simulated default credential pair.",
                        "task_type": "simulation",
                        "order": 3,
                        "simulation_config": {
                            "type": "auth_default_creds",
                            "scenario": "default_login",
                            "target_url": "/login",
                            "vulnerable_parameters": ["username", "password"],
                            "success_payload": "username=admin&password=admin",
                            "success_criteria": "Admin login without changing default credentials.",
                            "hints": [
                                "Try admin/admin",
                                "Try admin/password",
                            ],
                            "difficulty": "beginner",
                        },
                    },
                    {
                        "name": "Session Fixation & Session Management",
                        "description": "Understand why session IDs must rotate after login.",
                        "task_type": "theory",
                        "order": 4,
                        "theory_content": """
                            <h2>Session Fixation</h2>
                            <p>Attacker gives user a session ID, and it remains valid after login.</p>
                            <h3>Mitigation</h3>
                            <ul>
                                <li>Rotate session ID after login</li>
                                <li>Secure cookie flags</li>
                                <li>Invalidate sessions on logout</li>
                            </ul>
                        """,
                        "mcq_question": "How to prevent session fixation?",
                        "mcq_options": [
                            "A) Keep the same session ID",
                            "B) Rotate session ID after login",
                            "C) Store ID in URL",
                            "D) Disable cookie flags",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Simulation: Session Fixation Reuse",
                        "description": "Provide a fixed session ID and use it after login.",
                        "task_type": "simulation",
                        "order": 5,
                        "simulation_config": {
                            "type": "session_fixation",
                            "scenario": "fixation_reuse",
                            "target_url": "/session-test",
                            "vulnerable_parameters": ["sessionid"],
                            "success_payload": "sessionid=fixed-session-0001",
                            "success_criteria": "Reuse same sessionid after login to access protected page.",
                            "hints": [
                                "Set sessionid first",
                                "Log in and reuse sessionid",
                            ],
                            "difficulty": "intermediate",
                        },
                    },
                    {
                        "name": "JWT Misconfiguration (alg=none)",
                        "description": "Learn about forging JWTs when signature isn't checked.",
                        "task_type": "theory",
                        "order": 6,
                        "theory_content": """
                            <h2>JWT Pitfalls</h2>
                            <p>Accepting alg=none or weak secrets allows forging tokens.</p>
                            <h3>Fixes</h3>
                            <ul>
                                <li>Reject alg=none</li>
                                <li>Validate signature always</li>
                                <li>Use strong secrets + rotate periodically</li>
                            </ul>
                        """,
                        "mcq_question": "Which vulnerability allows unsigned JWTs?",
                        "mcq_options": [
                            "A) Short expiration",
                            "B) Accepting alg=none",
                            "C) Using strong RSA keys",
                            "D) Validating payload",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Simulation: Forge JWT for Admin Access",
                        "description": "Craft admin JWT (alg=none or weak-secret).",
                        "task_type": "simulation",
                        "order": 7,
                        "simulation_config": {
                            "type": "jwt_forge",
                            "scenario": "jwt_admin",
                            "target_url": "/admin",
                            "vulnerable_parameters": ["Authorization"],
                            "success_payload": 'Bearer token with {"role":"admin"}',
                            "success_criteria": "Access /admin using forged token.",
                            "hints": [
                                "Set alg:none",
                                "Remove signature or use weak-secret",
                            ],
                            "difficulty": "intermediate",
                        },
                    },
                    {
                        "name": "Password Reset Flaws",
                        "description": "Weak reset tokens, long lifetime, predictable values.",
                        "task_type": "theory",
                        "order": 8,
                        "theory_content": """
                            <h2>Password Reset Risks</h2>
                            <ul>
                                <li>Predictable or short tokens</li>
                                <li>Long-lived reset links</li>
                                <li>Tokens exposed in URLs/logs</li>
                            </ul>
                            <h3>Best Practices</h3>
                            <ul>
                                <li>Short-lived, single-use tokens</li>
                                <li>Server-side validation</li>
                                <li>Rate-limit attempts</li>
                            </ul>
                        """,
                        "mcq_question": "Which is secure practice?",
                        "mcq_options": [
                            "A) Long-lived tokens",
                            "B) Single-use short-lived tokens",
                            "C) Embed reset token in GET URL",
                            "D) Reuse tokens",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Simulation: Guess Weak Reset Token",
                        "description": "Guess short predictable token to reset password.",
                        "task_type": "simulation",
                        "order": 9,
                        "simulation_config": {
                            "type": "password_reset_guess",
                            "scenario": "guess_reset_token",
                            "target_url": "/reset-password?token=",
                            "vulnerable_parameters": ["token"],
                            "success_payload": "token=AB12",
                            "success_criteria": "Submit valid simulated token and reset password.",
                            "hints": [
                                "Try small alphanumeric combinations",
                                "Lab only simulates tiny safe token space",
                            ],
                            "difficulty": "intermediate",
                        },
                    },
                    {
                        "name": "Brute-Force & Rate-Limiting Controls",
                        "description": "Why progressive delays and lockouts stop brute-force.",
                        "task_type": "theory",
                        "order": 10,
                        "theory_content": """
                            <h2>Brute-force Defenses</h2>
                            <ul>
                                <li>Rate-limiting per IP/account</li>
                                <li>Progressive delay after failures</li>
                                <li>MFA</li>
                            </ul>
                        """,
                        "mcq_question": "Which helps block credential stuffing?",
                        "mcq_options": [
                            "A) Unlimited retries",
                            "B) Per-account/IP rate-limiting + delays",
                            "C) Client-side only validation",
                            "D) Logout users constantly",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Simulation: Brute-Force with Rate-Limit",
                        "description": "Simulated brute-force with lockout logic.",
                        "task_type": "simulation",
                        "order": 11,
                        "simulation_config": {
                            "type": "bruteforce_sim",
                            "scenario": "rate_limit_test",
                            "target_url": "/login",
                            "vulnerable_parameters": ["username", "password"],
                            "success_payload": "username=victim&password=P@ssw0rd!",
                            "success_criteria": "Find valid credential while respecting simulated rate limits.",
                            "hints": [
                                "Small controlled attempts",
                                "Lab simulates lockout",
                            ],
                            "difficulty": "advanced",
                        },
                    },
                    {
                        "name": "Authentication Remediation & Best Practices",
                        "description": "Final summary of secure approaches.",
                        "task_type": "theory",
                        "order": 12,
                        "theory_content": """
                            <h2>Remediation Checklist</h2>
                            <ul>
                                <li>Strong passwords + MFA</li>
                                <li>Session rotation on login</li>
                                <li>Strict JWT validation</li>
                                <li>Brute-force protections</li>
                                <li>Secure password reset tokens</li>
                            </ul>
                        """,
                        "mcq_question": "Which improves authentication security?",
                        "mcq_options": [
                            "A) Weak passwords + long-lived tokens",
                            "B) MFA + rate-limiting + session rotation",
                            "C) No logging",
                            "D) Reuse tokens everywhere",
                        ],
                        "correct_answer": "B",
                    },
                ],
            },
            {
                "name": "Open Redirect",
                "description": "Understand how open redirect vulnerabilities enable phishing attacks and security bypasses. Learn to exploit redirect parameters without validation to redirect users to malicious sites.",
                "estimated_time": 25,
                "order": 5,
                "tasks": [
                    {
                        "name": "Introduction to Open Redirect",
                        "description": "Learn what open redirect vulnerabilities are, why they matter, and common attack scenarios.",
                        "task_type": "theory",
                        "order": 1,
                        "theory_content": """
                            <h2>What is an Open Redirect?</h2>
                            <p>An open redirect occurs when an application sends users to a destination URL controlled by user input, without validation.</p>

                            <h3>Example</h3>
                            <pre><code>
                            GET /redirect?next=https://trusted.com/dashboard
                            </code></pre>

                            <h3>Impact</h3>
                            <ul>
                                <li>Phishing attacks using trusted domains</li>
                                <li>Bypass domain allow-lists</li>
                                <li>Chaining to server-side request (SSRF)</li>
                            </ul>
                        """,
                        "mcq_question": "What is a primary risk posed by open redirects?",
                        "mcq_options": [
                            "A) Enabling phishing to attacker-controlled sites",
                            "B) Executing SQL queries",
                            "C) Breaking CDN caching",
                            "D) Triggering HTTP/2",
                        ],
                        "correct_answer": "A",
                    },
                    {
                        "name": "Typical Open Redirect Patterns",
                        "description": "Where open redirects occur and how to detect them.",
                        "task_type": "theory",
                        "order": 2,
                        "theory_content": """
                            <h2>Where to find open redirects</h2>
                            <ul>
                              <li>Login flows: ?next=/path</li>
                              <li>Return-To parameters</li>
                              <li>Tracking/callback URLs</li>
                            </ul>

                            <h3>Code Smell</h3>
                            <pre><code>
                            return redirect(request.GET.get('next'))
                            </code></pre>

                            <h3>Defenses</h3>
                            <ul>
                              <li>Whitelist domains or internal paths</li>
                              <li>Normalize and validate destination</li>
                              <li>Prefer internal route names instead of raw URLs</li>
                            </ul>
                        """,
                        "mcq_question": "Which prevents open redirects?",
                        "mcq_options": [
                            "A) Accept any 'next' URL",
                            "B) Whitelist redirect hosts or limit to internal paths",
                            "C) Use attacker controlled scripts",
                            "D) Base64 encode next value only",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Basic Open Redirect - Redirect to Attacker",
                        "description": "Exploit a naive redirect parameter to send a user to attacker domain.",
                        "task_type": "simulation",
                        "order": 3,
                        "simulation_config": {
                            "type": "open_redirect_basic",
                            "scenario": "redirect_to_attacker",
                            "target_url": "/redirect?next=https://example.com",
                            "vulnerable_parameters": ["next"],
                            "success_payload": "https://evil.attacker.example/phish",
                            "success_criteria": "Redirect to attacker-controlled website",
                            "hints": [
                                "Replace ?next= with full attacker URL",
                                "Try http & https",
                            ],
                            "difficulty": "beginner",
                        },
                    },
                    {
                        "name": "Phishing Simulation via Open Redirect",
                        "description": "Show how attackers make a trusted-looking link forward to evil site.",
                        "task_type": "simulation",
                        "order": 4,
                        "simulation_config": {
                            "type": "open_redirect_phish",
                            "scenario": "phishing_link",
                            "target_url": "/redirect?next=",
                            "vulnerable_parameters": ["next"],
                            "success_payload": "https://trusted.example/login?next=https://evil.attacker.example",
                            "success_criteria": "Trusted domain forwards into malicious page",
                            "hints": [
                                "Create trusted-looking URL that chains attacker destination",
                            ],
                            "difficulty": "intermediate",
                        },
                    },
                    {
                        "name": "Open Redirect Chaining to SSRF or Internal Targets",
                        "description": "Use nested redirect to reach simulated internal host.",
                        "task_type": "simulation",
                        "order": 5,
                        "simulation_config": {
                            "type": "open_redirect_chain",
                            "scenario": "chain_to_internal",
                            "target_url": "/redirect?next=",
                            "vulnerable_parameters": ["next"],
                            "success_payload": "http://evil.attacker.example/redirect?to=http://127.0.0.1:8080/secret",
                            "success_criteria": "Chain redirect to internal resource",
                            "hints": [
                                "Use nested redirects",
                                "Internal host access simulated safely",
                            ],
                            "difficulty": "advanced",
                        },
                    },
                    {
                        "name": "Bypass Attempts & URL Encodings",
                        "description": "Encoding tricks that bypass naive validation (educational only).",
                        "task_type": "theory",
                        "order": 6,
                        "theory_content": """
                            <h2>Bypass Tricks</h2>
                            <ul>
                              <li>Percent-encoding</li>
                              <li>Protocol-relative URLs (//evil.com)</li>
                              <li>username@host patterns</li>
                              <li>Nested redirects</li>
                            </ul>
                        """,
                        "mcq_question": "Which encoding can bypass naive checks?",
                        "mcq_options": [
                            "A) Percent-encoding",
                            "B) Remove slashes",
                            "C) Use only relative paths",
                            "D) Strip query params",
                        ],
                        "correct_answer": "A",
                    },
                    {
                        "name": "Open Redirect Prevention & Best Practices",
                        "description": "How to safely handle redirects.",
                        "task_type": "theory",
                        "order": 7,
                        "theory_content": """
                            <h2>Prevention</h2>
                            <ul>
                                <li>Whitelist allowed redirect domains</li>
                                <li>Only allow internal routes</li>
                                <li>Normalize URLs before validation</li>
                                <li>Optionally show confirmation for external redirects</li>
                            </ul>
                        """,
                        "mcq_question": "Which is a secure redirect pattern?",
                        "mcq_options": [
                            "A) Allow any raw URL",
                            "B) Whitelist internal paths",
                            "C) Base64 encode and trust input",
                            "D) Use attacker-controlled site redirects",
                        ],
                        "correct_answer": "B",
                    },
                ],
            },
            {
                "name": "Server-Side Request Forgery (SSRF)",
                "description": "Advanced SSRF techniques to make servers request internal resources and cloud metadata services. Learn to bypass filters using encoding tricks and redirect chains.",
                "estimated_time": 55,
                "order": 6,
                "tasks": [
                    {
                        "name": "Introduction to SSRF",
                        "description": "Learn what SSRF attacks are, how they work, and their potential impact.",
                        "task_type": "theory",
                        "order": 1,
                        "theory_content": """
                            <h2>What is Server-Side Request Forgery (SSRF)?</h2>
                            <p>SSRF is a vulnerability that allows attackers to trick a server into making unintended HTTP requests. The attacker controls the target URL or request destination and uses the server's privileges to access internal systems or sensitive data.</p>

                            <h3>How SSRF Works</h3>
                            <ol>
                                <li>Web application accepts a URL or resource path as input.</li>
                                <li>Server fetches that resource on behalf of the user.</li>
                                <li>Attacker provides a crafted URL pointing to an internal or restricted resource.</li>
                                <li>Server makes a request to the attacker-controlled or internal endpoint.</li>
                            </ol>

                            <h3>Example</h3>
                            <pre><code>
                            GET /fetch?url=http://internal-service/admin
                            </code></pre>
                            The attacker changes the URL to something like:
                            <pre><code>
                            GET /fetch?url=http://169.254.169.254/latest/meta-data/
                            </code></pre>
                            (This accesses AWS instance metadata.)

                            <h3>Impact</h3>
                            <ul>
                                <li>Access internal networks</li>
                                <li>Read cloud instance metadata</li>
                                <li>Bypass firewalls</li>
                                <li>Trigger internal POST requests to sensitive services</li>
                            </ul>
                        """,
                        "mcq_question": "What is the main purpose of an SSRF attack?",
                        "mcq_options": [
                            "A) Trick the server into making unauthorized requests",
                            "B) Steal client-side cookies",
                            "C) Modify HTML content of the user's browser",
                            "D) Exploit SQL databases directly",
                        ],
                        "correct_answer": "A",
                    },
                    {
                        "name": "Common SSRF Attack Scenarios",
                        "description": "Understand the types and sources of SSRF vulnerabilities in web applications.",
                        "task_type": "theory",
                        "order": 2,
                        "theory_content": """
                            <h2>Common SSRF Scenarios</h2>
                            <ul>
                                <li><strong>Image URL Fetching:</strong> Application fetches remote image URLs for preview.</li>
                                <li><strong>PDF Generation:</strong> Server fetches external content to embed.</li>
                                <li><strong>Webhook / Callback URLs:</strong> API calls user-specified endpoints.</li>
                                <li><strong>URL Shorteners:</strong> Follow attacker-controlled redirects.</li>
                            </ul>

                            <h3>Advanced Exploits</h3>
                            <ul>
                                <li>Access cloud metadata service: <code>http://169.254.169.254/</code></li>
                                <li>Port scanning internal network via response timing.</li>
                                <li>POST requests to internal admin panels.</li>
                            </ul>
                        """,
                        "mcq_question": "Which of the following could be an SSRF entry point?",
                        "mcq_options": [
                            "A) File upload feature",
                            "B) URL preview generator",
                            "C) Client-side JavaScript",
                            "D) HTML forms only",
                        ],
                        "correct_answer": "B",
                    },
                    {
                        "name": "Basic SSRF Attack - Internal Access",
                        "description": "Exploit a vulnerable endpoint that fetches URLs without validation.",
                        "task_type": "simulation",
                        "order": 3,
                        "simulation_config": {
                            "type": "basic_ssrf",
                            "scenario": "internal_metadata_access",
                            "target_url": "/fetch?url=",
                            "vulnerable_parameters": ["url"],
                            "success_payload": "http://169.254.169.254/latest/meta-data/",
                            "success_criteria": "Fetch internal AWS metadata endpoint using /fetch?url parameter.",
                            "hints": [
                                "Try targeting internal IPs such as 127.0.0.1 or 169.254.169.254",
                                "Experiment with the url parameter value",
                                "Observe server response for signs of internal access",
                            ],
                            "difficulty": "beginner",
                        },
                    },
                    {
                        "name": "SSRF with Redirection",
                        "description": "Use open redirects or intermediate URLs to reach internal systems.",
                        "task_type": "simulation",
                        "order": 4,
                        "simulation_config": {
                            "type": "redirect_ssrf",
                            "scenario": "redirect_to_internal",
                            "target_url": "/fetch?url=",
                            "vulnerable_parameters": ["url"],
                            "success_payload": "http://evil.com/redirect?to=http://localhost:8080/admin",
                            "success_criteria": "Use a redirection chain to access an internal service through SSRF.",
                            "hints": [
                                "Construct an attacker-hosted redirect",
                                "Chain redirect → internal host",
                                "Observe if the server follows redirects automatically",
                            ],
                            "difficulty": "intermediate",
                        },
                    },
                    {
                        "name": "SSRF Bypass Filters - Using Encodings",
                        "description": "Bypass blacklist filters to reach internal hosts.",
                        "task_type": "simulation",
                        "order": 5,
                        "simulation_config": {
                            "type": "ssrf_bypass",
                            "scenario": "encoding_trick",
                            "target_url": "/fetch?url=",
                            "vulnerable_parameters": ["url"],
                            "success_payload": "http://127.0.0.1@evil.com/",
                            "success_criteria": "Bypass SSRF filters using encoding, obfuscation, or DNS tricks.",
                            "hints": [
                                "Try IPv6, decimal, hex: 0x7f000001",
                                "Use @, # tricks to mask the internal host",
                                "Try DNS rebinding or redirect-based payloads",
                            ],
                            "difficulty": "advanced",
                        },
                    },
                    {
                        "name": "SSRF to RCE via Webhook",
                        "description": "Trigger server-side requests that execute commands on internal systems.",
                        "task_type": "simulation",
                        "order": 6,
                        "simulation_config": {
                            "type": "ssrf_rce",
                            "scenario": "webhook_rce",
                            "target_url": "/webhook/test",
                            "vulnerable_parameters": ["target"],
                            "success_payload": "http://localhost:8080/admin/run?cmd=whoami",
                            "success_criteria": "Trigger command execution by calling an internal admin endpoint.",
                            "hints": [
                                "Use internal admin interfaces",
                                "Use query parameters to run commands",
                                "Observe the system's execution response",
                            ],
                            "difficulty": "advanced",
                        },
                    },
                    {
                        "name": "SSRF Prevention Techniques",
                        "description": "Learn defenses against SSRF attacks.",
                        "task_type": "theory",
                        "order": 7,
                        "theory_content": """
                            <h2>Preventing SSRF</h2>
                            <ul>
                                <li>Validate and whitelist URLs strictly (domain and protocol)</li>
                                <li>Disallow internal IP ranges (127.0.0.1, 10.x.x.x, 169.254.x.x)</li>
                                <li>Disable redirects or restrict them to trusted hosts</li>
                                <li>Avoid fetching arbitrary URLs from user input</li>
                                <li>Use SSRF-aware proxy services</li>
                            </ul>

                            <h3>Secure Example</h3>
                            <pre><code>
                            allowed_hosts = ["example.com", "api.trusted.com"]
                            parsed = urlparse(user_url)
                            if parsed.hostname not in allowed_hosts:
                                raise ValueError("Untrusted URL")
                            </code></pre>
                        """,
                        "mcq_question": "Which of these is an effective defense against SSRF?",
                        "mcq_options": [
                            "A) Allowing all internal IPs",
                            "B) Whitelisting allowed domains",
                            "C) Disabling SSL verification",
                            "D) Following all redirects",
                        ],
                        "correct_answer": "B",
                    },
                ],
            },
        ]

        total_labs = 0
        total_tasks = 0

        with transaction.atomic():
            for lab_data in labs_data:
                # Create or update lab
                lab, created = Labs.objects.update_or_create(
                    name=lab_data["name"],
                    defaults={
                        "description": lab_data["description"],
                        "estimated_time": lab_data["estimated_time"],
                        "order": lab_data["order"],
                        "is_active": True,
                    },
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created lab: "{lab.name}"'))
                else:
                    self.stdout.write(self.style.WARNING(f'Lab "{lab.name}" already exists, updating...'))

                # Create tasks for this lab
                task_count = 0
                for task_data in lab_data["tasks"]:
                    task, task_created = Tasks.objects.update_or_create(
                        lab=lab,
                        name=task_data["name"],
                        defaults={
                            "order": task_data["order"],
                            "description": task_data["description"],
                            "task_type": task_data["task_type"],
                            "is_active": True,
                        },
                    )

                    # Create task content
                    content_data = {}
                    if task_data["task_type"] == "theory":
                        content_data = {
                            "theory_content": task_data.get("theory_content", ""),
                            "mcq_question": task_data.get("mcq_question", ""),
                            "mcq_options": task_data.get("mcq_options", []),
                            "correct_answer": task_data.get("correct_answer", ""),
                            "simulation_config": {},
                        }
                    else:  # simulation
                        content_data = {
                            "simulation_config": task_data.get("simulation_config", {}),
                            "theory_content": "",
                            "mcq_question": "",
                            "mcq_options": [],
                            "correct_answer": "",
                        }

                    TaskContent.objects.update_or_create(task=task, defaults=content_data)

                    task_count += 1
                    total_tasks += 1
                    if task_created:
                        self.stdout.write(self.style.SUCCESS(f'  Created task: "{task.name}"'))
                    else:
                        self.stdout.write(self.style.WARNING(f'  Task "{task.name}" already exists, updated'))

                lab.update_total_tasks()
                total_labs += 1
                self.stdout.write(self.style.SUCCESS(f'  Lab "{lab.name}" has {task_count} tasks'))

            self.stdout.write(
                self.style.SUCCESS(f"Successfully seeded {total_labs} labs with {total_tasks} total tasks!")
            )
