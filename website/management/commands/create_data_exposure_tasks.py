from typing import Any, ClassVar

from .base_lab_seeder import LabSeederCommand


class Command(LabSeederCommand):
    help = "Creates Sensitive Data Exposure lab tasks"
    lab_name = "Sensitive Data Exposure"

    tasks_data: ClassVar[list[dict[str, Any]]] = [
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
    ]
