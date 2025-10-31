from django.core.management.base import BaseCommand
from website.models import Labs, TaskContent, Tasks
from django.core.management.base import CommandError


class Command(BaseCommand):
    help = "Creates Sensitive Data Exposure lab tasks with theory and simulation content"

    def handle(self, *args, **kwargs):
        try:
            sde_lab = Labs.objects.get(name="Sensitive Data Exposure")
        except Labs.DoesNotExist:
            raise CommandError(
                "Sensitive Data Exposure lab not found. Please run create_initial_labs first."
            )

        tasks_data = [
            {
                "name": "Introduction to Sensitive Data Exposure",
                "description": "Understand what sensitive data exposure is, why it matters, and common sources of leaks.",
                "task_type": "theory",
                "order": 1,
                "theory_content": """
                <h2>What is Sensitive Data Exposure?</h2>
                <p>Sensitive Data Exposure occurs when applications, APIs, or servers fail to adequately protect confidential information such as credentials, API keys, personal data, or cryptographic keys. Attackers who obtain this data can impersonate users, access services, or escalate attacks.</p>

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
                <p>Use TLS (HTTPS) to encrypt data between clients and servers. Common mistakes include allowing insecure protocols, using expired/invalid certificates, or downgrading TLS via insecure redirects.</p>

                <h3>Best practices</h3>
                <ul>
                  <li>Enforce TLS 1.2+ and disable insecure ciphers</li>
                  <li>Use HSTS (HTTP Strict Transport Security)</li>
                  <li>Redirect HTTP to HTTPS and validate certificate chains</li>
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
                "description": "Simulate a verbose error page or stack trace that reveals credentials or secrets.",
                "task_type": "simulation",
                "order": 3,
                "simulation_config": {
                    "type": "error_leak",
                    "scenario": "stack_trace_disclosure",
                    "target_url": "/user/profile?show=error",
                    "vulnerable_parameters": ["show"],
                    "success_payload": "Trigger an error that displays a stack trace containing 'DB_PASSWORD=secret_db_pass'",
                    "success_criteria": "Cause the simulated app to reveal a stack trace or error page that includes a secret string (e.g., DB password or API key).",
                    "hints": [
                        "Toggle parameters that influence server behavior (e.g., show=error)",
                        "Look for endpoints that print debug info when given unusual input",
                        "The lab simulates an error page containing a safe example secret for learning",
                    ],
                    "difficulty": "beginner",
                },
            },
            {
                "name": "Exposed Backup/.git or Public Files (Simulation)",
                "description": "Find leftover files or directories that reveal configuration or secrets (simulated discovery).",
                "task_type": "simulation",
                "order": 4,
                "simulation_config": {
                    "type": "file_exposure",
                    "scenario": "exposed_git",
                    "target_url": "/.git/HEAD",
                    "vulnerable_parameters": [],
                    "success_payload": "Access /.git/config or /backup/config.bak and find a simulated 'aws_access_key_id' or 'secret_key'",
                    "success_criteria": "Retrieve a simulated config file that contains an API key or credential example.",
                    "hints": [
                        "Try common backup filenames or paths like /.git/HEAD, /backup/config.bak, /config/.env",
                        "Use GET requests to known file paths that might be accidentally exposed",
                        "The lab uses safe simulated files and values for demonstration",
                    ],
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "API Key / Secret in JavaScript or HTML (Simulation)",
                "description": "Detect API keys or secrets embedded in frontend assets or JavaScript files (simulated).",
                "task_type": "simulation",
                "order": 5,
                "simulation_config": {
                    "type": "asset_leak",
                    "scenario": "frontend_key_disclosure",
                    "target_url": "/static/js/app.js",
                    "vulnerable_parameters": [],
                    "success_payload": "Find a simulated string like 'API_KEY = \"AKIA...EXAMPLE\"' inside /static/js/app.js",
                    "success_criteria": "Locate an embedded API key or token within a served frontend asset (lab provides simulated example key).",
                    "hints": [
                        "Inspect served JavaScript/CSS and HTML for hardcoded keys",
                        "Search for plausible variable names like 'API_KEY', 'TOKEN', or 'SECRET'",
                        "The lab's static files include safe example keys for learning",
                    ],
                    "difficulty": "beginner",
                },
            },
            {
                "name": "Insecure Storage: Plaintext Secrets (Simulation)",
                "description": "Simulate retrieval of stored plaintext credentials from a misconfigured datastore or file.",
                "task_type": "simulation",
                "order": 6,
                "simulation_config": {
                    "type": "storage_plaintext",
                    "scenario": "plaintext_passwords",
                    "target_url": "/admin/export-users",
                    "vulnerable_parameters": [],
                    "success_payload": "Request /admin/export-users to retrieve a simulated CSV containing 'email, password' with plaintext example 'password123'",
                    "success_criteria": "Obtain the simulated exported data showing plaintext passwords or weak hashing examples.",
                    "hints": [
                        "Look for admin or export endpoints that might expose user data",
                        "The lab simulates a safe export that demonstrates why storing plaintext is dangerous",
                        "Check both JSON and CSV endpoints for exported data",
                    ],
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "Token Replay & Poorly Scoped Tokens",
                "description": "Theory: understand risks of long-lived tokens, overly broad scopes, and token replay.",
                "task_type": "theory",
                "order": 7,
                "theory_content": """
                <h2>Token Management Risks</h2>
                <p>Tokens and API keys should be short-lived, scoped to minimal privileges, and revocable. Long-lived or overly-permissive tokens increase impact when leaked.</p>

                <h3>Best practices</h3>
                <ul>
                  <li>Use short expiry, rotate secrets regularly</li>
                  <li>Scope tokens to minimum required permissions</li>
                  <li>Monitor token usage and provide revocation mechanisms</li>
                </ul>
                """,
                "mcq_question": "Which reduces the blast radius if an API key is leaked?",
                "mcq_options": [
                    "A) Long-lived, global-scope tokens",
                    "B) Short-lived tokens with minimal scope",
                    "C) Embedding keys in client-side code",
                    "D) Reusing the same token across services",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Prevention & Remediation Best Practices",
                "description": "Learn controls and practices to prevent sensitive data exposure in applications and infrastructure.",
                "task_type": "theory",
                "order": 8,
                "theory_content": """
                <h2>Prevention & Remediation</h2>
                <ul>
                  <li>Encrypt sensitive data at rest and in transit</li>
                  <li>Use managed secrets stores (e.g., Vault, AWS Secrets Manager)</li>
                  <li>Avoid storing secrets in source control; scan repos for secrets</li>
                  <li>Limit data retention and anonymize PII where possible</li>
                  <li>Harden servers and remove development/debug features in production</li>
                </ul>

                <h3>Example: Using a secrets manager</h3>
                <pre><code>
                # Pseudocode
                db_password = secrets_manager.get_secret("prod/db_password")
                connect(database_url, password=db_password)
                </code></pre>
                """,
                "mcq_question": "Which is a recommended approach to manage secrets securely?",
                "mcq_options": [
                    "A) Commit secrets to git for easy deployment",
                    "B) Use a dedicated secrets manager and avoid storing secrets in repos",
                    "C) Store secrets in plaintext files on web root",
                    "D) Hardcode secrets in application source",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Sensitive Data Exposure Challenge - Safe Remediation",
                "description": "Simulation: identify a leaked secret and demonstrate a safe remediation plan (lab validates detection and suggested remediation text).",
                "task_type": "simulation",
                "order": 9,
                "simulation_config": {
                    "type": "remediation_plan",
                    "scenario": "identify_and_remediate",
                    "target_url": "/.env",
                    "vulnerable_parameters": [],
                    "success_payload": "Find a simulated SECRET_KEY in /.env and submit a remediation text explaining rotation and use of secrets manager",
                    "success_criteria": "Lab detects the found simulated secret and verifies the remediation text includes key steps (rotate key, revoke, use secrets manager).",
                    "hints": [
                        "Search common exposed filenames like /.env, config.php, or backup files",
                        "When you find a simulated secret, provide a short remediation plan (rotate, revoke, replace with managed secret)",
                        "The lab validates remediation text heuristically (contains key phrases)",
                    ],
                    "difficulty": "advanced",
                },
            },
        ]

        for task_data in tasks_data:
            task, created = Tasks.objects.update_or_create(
                lab=sde_lab,
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
                        "theory_content": task_data["theory_content"],
                        "mcq_question": task_data["mcq_question"],
                        "mcq_options": task_data["mcq_options"],
                        "correct_answer": task_data["correct_answer"],
                    }
                )
            else:
                content_data.update(
                    {
                        "simulation_config": task_data["simulation_config"],
                    }
                )

            task_content, content_created = TaskContent.objects.update_or_create(task=task, defaults=content_data)

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created task: "{task.name}"'))
            else:
                self.stdout.write(self.style.WARNING(f'Task "{task.name}" already exists'))

            if content_created:
                self.stdout.write(self.style.SUCCESS(f'Created content for task: "{task.name}"'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated content for task: "{task.name}"'))

        sde_lab.update_total_tasks()
        self.stdout.write(
            self.style.SUCCESS(f"Sensitive Data Exposure lab setup complete with {sde_lab.total_tasks} tasks")
        )
