from .base_lab_seeder import LabSeederCommand

class Command(LabSeederCommand):
    help = "Creates Broken Authentication / Authentication Bypass lab tasks"
    lab_name = "Broken Authentication"

    tasks_data = [
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
                "success_payload": {"username": "admin", "password": "admin"},
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
                "success_payload": {"sessionid": "fixed-session-0001"},
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
                "success_payload": "Bearer token with {\"role\":\"admin\"}",
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
                "success_payload": {"username": "victim", "password": "P@ssw0rd!"},
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
    ]
