from typing import Any, ClassVar

from .base_lab_seeder import LabSeederCommand


class Command(LabSeederCommand):
    help = "Creates Open Redirect lab tasks"
    lab_name = "Open Redirect"

    tasks_data: ClassVar[list[dict[str, Any]]] = [
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
    ]
