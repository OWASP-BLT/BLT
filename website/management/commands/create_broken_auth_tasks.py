from django.core.management.base import BaseCommand
from website.models import Labs, TaskContent, Tasks


class Command(BaseCommand):
    help = "Creates Broken Authentication / Authentication Bypass lab tasks with theory and simulation content"

    def handle(self, *args, **kwargs):
        try:
            auth_lab = Labs.objects.get(name="Broken Authentication")
        except Labs.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "Broken Authentication lab not found. Please run create_initial_labs first."
                )
            )
            return

        tasks_data = [
            {
                "name": "Introduction to Broken Authentication",
                "description": "Overview of authentication failures, their causes, and impacts.",
                "task_type": "theory",
                "order": 1,
                "theory_content": """
                <h2>What is Broken Authentication?</h2>
                <p>Broken Authentication refers to weaknesses in the authentication and session management functions that allow attackers to compromise passwords, keys, or session tokens — or to exploit implementation flaws to assume other users' identities.</p>

                <h3>Common issues</h3>
                <ul>
                    <li>Default or weak credentials</li>
                    <li>Credential stuffing and brute-force attacks</li>
                    <li>Predictable or non-rotated session identifiers</li>
                    <li>Insecure password reset implementations</li>
                    <li>JWT / token misconfiguration (e.g., accepting alg=none)</li>
                </ul>

                <h3>Impact</h3>
                <ul>
                    <li>Account takeover</li>
                    <li>Privilege escalation</li>
                    <li>Data theft and persistent unauthorized access</li>
                </ul>
                """,
                "mcq_question": "Which control most directly mitigates credential stuffing and brute-force attacks?",
                "mcq_options": [
                    "A) Allow unlimited login attempts",
                    "B) Implement progressive rate-limiting and account lockout",
                    "C) Use only client-side validation",
                    "D) Disable password complexity requirements",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Default & Weak Credentials",
                "description": "Why default or weak credentials are dangerous and how to detect them.",
                "task_type": "theory",
                "order": 2,
                "theory_content": """
                <h2>Default & Weak Credentials</h2>
                <p>Many devices and applications ship with default credentials (e.g., admin:admin). Attackers try common username/password pairs or use leaked credential lists to gain access.</p>

                <h3>Detection & Prevention</h3>
                <ul>
                    <li>Test common defaults in authorized test environments only</li>
                    <li>Force password change on first login</li>
                    <li>Enforce strong password policies and multi-factor authentication (MFA)</li>
                </ul>
                """,
                "mcq_question": "Which of the following reduces the risk posed by default credentials?",
                "mcq_options": [
                    "A) Force credential change on first use",
                    "B) Document defaults in a public README",
                    "C) Use default credentials across environments",
                    "D) Disable login logging",
                ],
                "correct_answer": "A",
            },
            {
                "name": "Simulation: Login with Default Credentials",
                "description": "Find and use default or weak credentials to log in (lab simulates acceptance of a default credential pair).",
                "task_type": "simulation",
                "order": 3,
                "simulation_config": {
                    "type": "auth_default_creds",
                    "scenario": "default_login",
                    "target_url": "/login",
                    "vulnerable_parameters": ["username", "password"],
                    "success_payload": {"username": "admin", "password": "admin"},
                    "success_criteria": "Authenticate as admin using a default credential pair (admin/admin or similar neutral example) — lab accepts the credentials and marks the task complete.",
                    "hints": [
                        "Try common default credentials such as admin/admin, admin/password, root/root.",
                        "Inspect the login form fields and attempt a POST via the task UI."
                    ],
                    "difficulty": "beginner",
                },
            },
            {
                "name": "Session Fixation & Session Management",
                "description": "Understand session fixation and how not rotating session IDs can be abused.",
                "task_type": "theory",
                "order": 4,
                "theory_content": """
                <h2>Session Fixation</h2>
                <p>Session fixation occurs when an attacker tricks a user into using a session identifier known to the attacker, and that ID remains valid after login. Proper session handling rotates session identifiers upon privilege changes.</p>

                <h3>Defenses</h3>
                <ul>
                    <li>Rotate session ID after authentication</li>
                    <li>Set cookie flags (HttpOnly, Secure, SameSite)</li>
                    <li>Invalidate sessions on logout</li>
                </ul>
                """,
                "mcq_question": "What action should an application take after a successful login to prevent session fixation?",
                "mcq_options": [
                    "A) Keep the existing session ID",
                    "B) Issue a new session ID (rotate session)",
                    "C) Store session ID in URL",
                    "D) Disable cookie flags",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Simulation: Session Fixation Reuse",
                "description": "Simulate providing a session ID before login and verify whether it remains valid after authentication (lab simulates both victim and attacker perspectives).",
                "task_type": "simulation",
                "order": 5,
                "simulation_config": {
                    "type": "session_fixation",
                    "scenario": "fixation_reuse",
                    "target_url": "/session-test",
                    "vulnerable_parameters": ["sessionid"],
                    "success_payload": {"sessionid": "fixed-session-0001"},
                    "success_criteria": "Submit a sessionid value, authenticate, and then use the same sessionid from another simulated client to access a protected page; lab detects reuse and marks the task complete.",
                    "hints": [
                        "Provide a sessionid value prior to login via the task UI, then perform login and test reuse.",
                        "If the server rotates session IDs, session fixation won't be possible."
                    ],
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "JWT Misconfiguration (alg=none & key confusion)",
                "description": "Learn common JWT pitfalls: accepting unsigned tokens, algorithm confusion, and weak secrets.",
                "task_type": "theory",
                "order": 6,
                "theory_content": """
                <h2>JWT Pitfalls</h2>
                <p>JSON Web Tokens (JWT) must be validated strictly. Vulnerable implementations may accept <code>alg=none</code> (unsigned) tokens, or they may be susceptible to algorithm confusion where the server uses an asymmetric key as an HMAC secret.</p>

                <h3>Mitigations</h3>
                <ul>
                    <li>Reject tokens with <code>alg=none</code></li>
                    <li>Enforce a single expected algorithm and validate signatures</li>
                    <li>Use strong secrets and rotate keys</li>
                </ul>
                """,
                "mcq_question": "Which vulnerability allows forging JWTs without a valid signature?",
                "mcq_options": [
                    "A) Requiring short expiry times",
                    "B) Accepting alg=none",
                    "C) Using strong RSA keys",
                    "D) Validating tokens on each request",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Simulation: Forge JWT for Admin Access",
                "description": "Create or modify a JWT so that it grants admin privileges. The lab simulates a vulnerable verifier (e.g., alg=none or weak HMAC secret) and will accept a crafted token.",
                "task_type": "simulation",
                "order": 7,
                "simulation_config": {
                    "type": "jwt_forge",
                    "scenario": "jwt_admin",
                    "target_url": "/admin",
                    "vulnerable_parameters": ["Authorization"],
                    "success_payload": "Provide a Bearer token which decodes to a payload containing {\"role\":\"admin\"} and is accepted by the simulated verifier (alg=none or weak-secret variant).",
                    "success_criteria": "Use the crafted JWT to access the /admin endpoint and perform an admin-only action; lab validates access and marks the task complete.",
                    "hints": [
                        "Decode sample tokens with base64 to inspect header and payload.",
                        "Try setting header alg to 'none' and removing the signature if the lab simulates alg=none acceptance.",
                        "If alg=none isn't accepted, the lab may simulate a weak-secret HMAC variant to demonstrate risk."
                    ],
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "Password Reset Flaws & Token Management",
                "description": "Understand insecure password reset flows, predictable tokens, and best practices for token handling.",
                "task_type": "theory",
                "order": 8,
                "theory_content": """
                <h2>Password Reset Risks</h2>
                <p>Weak reset flows may issue predictable, long-lived, or reusable tokens. Attackers can guess tokens or intercept them if they're leaked in URLs or logs.</p>

                <h3>Best practices</h3>
                <ul>
                    <li>Issue single-use, cryptographically secure tokens</li>
                    <li>Set short expiration windows</li>
                    <li>Do not expose tokens in URLs where possible</li>
                    <li>Rate-limit reset attempts and monitor for abuse</li>
                </ul>
                """,
                "mcq_question": "Which is a secure practice for password reset tokens?",
                "mcq_options": [
                    "A) Long-lived reusable tokens",
                    "B) Single-use, short-lived tokens stored server-side",
                    "C) Embedding tokens in GET URLs in emails",
                    "D) Reusing the same token for multiple users",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Simulation: Guess Weak Reset Token",
                "description": "Simulate a weak password reset flow where tokens are short and enumerable. Determine a valid token to reset a user's password (lab simulates limited, safe token space).",
                "task_type": "simulation",
                "order": 9,
                "simulation_config": {
                    "type": "password_reset_guess",
                    "scenario": "guess_reset_token",
                    "target_url": "/reset-password?token=",
                    "vulnerable_parameters": ["token"],
                    "success_payload": "token=AB12 (lab simulates a short predictable token space and accepts a small set of tokens for demonstration)",
                    "success_criteria": "Submit a valid reset token and perform a password reset; lab validates token and marks task complete.",
                    "hints": [
                        "Try short alphanumeric tokens within a small range suggested by the lab.",
                        "This simulation limits guessing to a tiny safe space to demonstrate risk without encouraging large-scale attacks."
                    ],
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "Brute-Force & Rate-limiting Controls",
                "description": "Theory: why rate-limiting, account lockout, progressive delays, and IP-based protections are necessary.",
                "task_type": "theory",
                "order": 10,
                "theory_content": """
                <h2>Brute-force Protections</h2>
                <p>To mitigate automated attacks implement layered rate-limiting (per-account and per-IP), progressive delays, CAPTCHA for suspicious behavior, and monitoring/alerts for credential-stuffing attempts.</p>

                <h3>Recommendations</h3>
                <ul>
                    <li>Progressive delay on failed attempts</li>
                    <li>Temporary account lockout or challenge after threshold</li>
                    <li>Multi-factor authentication (MFA) for high-value accounts</li>
                </ul>
                """,
                "mcq_question": "Which measure helps prevent automated credential stuffing?",
                "mcq_options": [
                    "A) Unlimited retry attempts",
                    "B) Per-account and per-IP rate-limiting with progressive delay",
                    "C) Only client-side validation",
                    "D) Logging out users frequently",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Simulation: Brute-force with Rate-Limit Bypass (Safe)",
                "description": "Simulate a brute-force attempt against a login endpoint and observe rate-limiting behavior. The lab will simulate thresholds and accept a correct credential when rate limits or lockouts are respected.",
                "task_type": "simulation",
                "order": 11,
                "simulation_config": {
                    "type": "bruteforce_sim",
                    "scenario": "rate_limit_test",
                    "target_url": "/login",
                    "vulnerable_parameters": ["username", "password"],
                    "success_payload": {"username": "victim", "password": "P@ssw0rd!"},
                    "success_criteria": "Identify a valid credential within the simulated constraints while observing rate-limiting behavior (lab simulates lockouts and progressive delays).",
                    "hints": [
                        "Respect the lab's simulated rate limits and use small, controlled attempts.",
                        "The lab will simulate lockout after a configured number of failures — this is for learning only."
                    ],
                    "difficulty": "advanced",
                },
            },
            {
                "name": "Authentication Remediation & Best Practices",
                "description": "Summarize practical steps to secure authentication and session management.",
                "task_type": "theory",
                "order": 12,
                "theory_content": """
                <h2>Remediation Checklist</h2>
                <ul>
                    <li>Enforce strong password policies and MFA</li>
                    <li>Rotate and invalidate session tokens on authentication events</li>
                    <li>Use secure token handling and strict JWT validation</li>
                    <li>Implement rate-limiting, logging, and monitoring for suspicious auth events</li>
                    <li>Secure password reset flows with single-use, short-lived tokens</li>
                </ul>
                """,
                "mcq_question": "Which combination most improves authentication security?",
                "mcq_options": [
                    "A) Weak passwords + long-lived tokens",
                    "B) MFA + strong rate-limiting + proper session rotation",
                    "C) No logging + client-side only validation",
                    "D) Reusing tokens across services",
                ],
                "correct_answer": "B",
            },
        ]

        for task_data in tasks_data:
            task, created = Tasks.objects.update_or_create(
                lab=auth_lab,
                order=task_data["order"],
                defaults={
                    "name": task_data["name"],
                    "description": task_data["description"],
                    "task_type": task_data["task_type"],
                    "is_active": True,
                },
            )

            content_data = {}
            if task_data["task_type"] == "theory":
                content_data.update(
                    {
                        "theory_content": task_data.get("theory_content", ""),
                        "mcq_question": task_data.get("mcq_question", ""),
                        "mcq_options": task_data.get("mcq_options", []),
                        "correct_answer": task_data.get("correct_answer", ""),
                    }
                )
            elif task_data["task_type"] == "simulation":
                content_data.update({"simulation_config": task_data.get("simulation_config", {})})

            task_content, content_created = TaskContent.objects.update_or_create(task=task, defaults=content_data)

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created task: "{task.name}"'))
            else:
                self.stdout.write(self.style.WARNING(f'Task "{task.name}" already exists'))

            if content_created:
                self.stdout.write(self.style.SUCCESS(f'Created content for task: "{task.name}"'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated content for task: "{task.name}"'))

        auth_lab.update_total_tasks()
        self.stdout.write(self.style.SUCCESS(f"Broken Authentication lab setup complete with {auth_lab.total_tasks} tasks"))