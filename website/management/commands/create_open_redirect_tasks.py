from django.core.management.base import BaseCommand
from website.models import Labs, TaskContent, Tasks


class Command(BaseCommand):
    help = "Creates Open Redirect lab tasks with theory and simulation content"

    def handle(self, *args, **kwargs):
        try:
            or_lab = Labs.objects.get(name="Open Redirect")
        except Labs.DoesNotExist:
            self.stdout.write(self.style.ERROR("Open Redirect lab not found. Please run create_initial_labs first."))
            return

        tasks_data = [
            {
                "name": "Introduction to Open Redirect",
                "description": "Learn what open redirect vulnerabilities are, why they matter, and common attack scenarios.",
                "task_type": "theory",
                "order": 1,
                "theory_content": """
                <h2>What is an Open Redirect?</h2>
                <p>An open redirect occurs when a web application redirects users to a URL that is controlled or influenced by user input, without validating that the destination is safe. Attackers can use open redirects in phishing attacks, to bypass domain-based security checks, or to chain to other vulnerabilities.</p>

                <h3>Example</h3>
                <pre><code>
                GET /redirect?next=https://trusted.com/dashboard
                </code></pre>
                <p>If the application redirects to any user-supplied URL (including attacker-controlled domains), it is vulnerable.</p>

                <h3>Impact</h3>
                <ul>
                    <li>Phishing: attackers craft links that appear to originate from a trusted domain</li>
                    <li>Bypass of filter/allow-lists that rely on a trusted domain</li>
                    <li>Chaining to SSRF or other server-side interactions via malicious redirect targets</li>
                </ul>
                """,
                "mcq_question": "What is a primary risk posed by open redirects?",
                "mcq_options": [
                    "A) Allowing client-side XSS",
                    "B) Enabling phishing by redirecting users to attacker-controlled sites",
                    "C) Executing SQL queries on the server",
                    "D) Breaking CDN caching",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Typical Open Redirect Patterns",
                "description": "Where open redirects commonly appear and patterns to look for in code and URLs.",
                "task_type": "theory",
                "order": 2,
                "theory_content": """
                <h2>Where to find open redirects</h2>
                <ul>
                  <li>Login flows with `next` or `return_to` parameters</li>
                  <li>Third-party integrations and callback URLs</li>
                  <li>Tracking or short-link services that accept a destination URL</li>
                </ul>

                <h3>Code smell</h3>
                <pre><code>
                # Dangerous pattern (no validation)
                return redirect(request.GET.get('next'))
                </code></pre>

                <h3>Defenses</h3>
                <ul>
                  <li>Whitelist allowed domains or relative paths</li>
                  <li>Normalize and validate destination URLs before redirecting</li>
                  <li>Prefer using internal route identifiers instead of raw URLs</li>
                </ul>
                """,
                "mcq_question": "Which is an effective prevention for open redirect?",
                "mcq_options": [
                    "A) Accept any 'next' URL and redirect",
                    "B) Whitelist allowed redirect hosts or require internal paths",
                    "C) Use user-supplied scripts for destination",
                    "D) Obfuscate redirect parameters with base64 only",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Basic Open Redirect - Redirect to Attacker",
                "description": "Exploit a naive redirect parameter to send a victim to an attacker-controlled domain.",
                "task_type": "simulation",
                "order": 3,
                "simulation_config": {
                    "type": "open_redirect_basic",
                    "scenario": "redirect_to_attacker",
                    "target_url": "/redirect?next=https://example.com",
                    "vulnerable_parameters": ["next"],
                    "success_payload": "https://evil.attacker.example/phish",
                    "success_criteria": "Construct a URL using the redirect parameter that sends the user to an attacker-controlled domain (the lab recognizes that the redirect target is not whitelisted)",
                    "hints": [
                        "Replace the 'next' parameter with a fully-qualified attacker URL",
                        "Try both http and https schemes",
                        "Observe whether the server follows or sanitizes the provided URL",
                    ],
                    "difficulty": "beginner",
                },
            },
            {
                "name": "Phishing Simulation via Open Redirect",
                "description": "Demonstrate how open redirects can be used to craft phishing links that appear to originate from a trusted site.",
                "task_type": "simulation",
                "order": 4,
                "simulation_config": {
                    "type": "open_redirect_phish",
                    "scenario": "phishing_link",
                    "target_url": "/redirect?next=",
                    "vulnerable_parameters": ["next"],
                    "success_payload": "https://trusted.example/login?next=https://evil.attacker.example",
                    "success_criteria": "Create a redirect URL that appears to be from the trusted site but forwards to a malicious page (lab verifies that final destination is attacker-controlled)",
                    "hints": [
                        "Combine the trusted domain and attacker domain using redirect parameters",
                        "Shortened forms or nested redirects may be useful",
                        "Check whether the application displays the destination or hides it behind the trusted domain",
                    ],
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "Open Redirect Chaining to SSRF or Internal Targets",
                "description": "Use an open redirect to chain to another vulnerability (simulated), such as SSRF or internal resource access.",
                "task_type": "simulation",
                "order": 5,
                "simulation_config": {
                    "type": "open_redirect_chain",
                    "scenario": "chain_to_internal",
                    "target_url": "/redirect?next=",
                    "vulnerable_parameters": ["next"],
                    "success_payload": "http://evil.attacker.example/redirect?to=http://127.0.0.1:8080/secret",
                    "success_criteria": "Use nested redirect to reach an internal/simulated target; lab simulates the chained request and marks the chain successful",
                    "hints": [
                        "Try nesting redirects where the attacker-controlled redirect then forwards to an internal host (simulated)",
                        "The lab only simulates allowed chain patterns for safety",
                        "Observe how the server follows redirects and whether it normalizes the destination",
                    ],
                    "difficulty": "advanced",
                },
            },
            {
                "name": "Bypass Attempts & URL Encodings",
                "description": "Learn encoding tricks and parameter abuses attackers may try to bypass naive whitelist checks (educational only).",
                "task_type": "theory",
                "order": 6,
                "theory_content": """
                <h2>Bypass tricks</h2>
                <ul>
                  <li>URL-encode the destination (percent-encoding)</li>
                  <li>Use protocol-relative URLs (//evil.example)</li>
                  <li>Embed username@host (e.g., http://evil.com@trusted.example/)</li>
                  <li>Use nested redirects or shorteners</li>
                </ul>
                <p><strong>Warning:</strong> These techniques are shown for education; do not use them against systems you don't own or have permission to test.</p>
                """,
                "mcq_question": "Which encoding or representation can sometimes bypass naive redirect checks?",
                "mcq_options": [
                    "A) Percent-encoding of the URL",
                    "B) Using only relative internal paths",
                    "C) Removing the scheme entirely",
                    "D) Using a vetted CDN host",
                ],
                "correct_answer": "A",
            },
            {
                "name": "Open Redirect Prevention & Best Practices",
                "description": "How to prevent open redirect vulnerabilities during development and code review.",
                "task_type": "theory",
                "order": 7,
                "theory_content": """
                <h2>Prevention</h2>
                <ul>
                    <li>Whitelist allowed redirect destinations (domains or internal routes)</li>
                    <li>Prefer internal route names or IDs instead of raw URLs</li>
                    <li>Normalize and parse URLs before validating hostnames</li>
                    <li>Where possible, show a confirmation page when redirecting to external sites</li>
                </ul>

                <h3>Secure Example</h3>
                <pre><code>
                # Secure pattern: only allow internal paths
                next_url = request.GET.get('next')
                if not next_url or not next_url.startswith('/'):
                    next_url = '/home'
                return redirect(next_url)
                </code></pre>

                <p>Always validate untrusted input before using it in redirects. Even small oversights can enable phishing or more severe chained attacks.</p>
                """,
                "mcq_question": "Which of the following is a secure pattern for handling redirects?",
                "mcq_options": [
                    "A) Allow any URL as a redirect target",
                    "B) Whitelist internal paths only",
                    "C) Use raw user input in the redirect function",
                    "D) Base64 encode URLs and redirect blindly",
                ],
                "correct_answer": "B",
            },
        ]

        for task_data in tasks_data:
            task, created = Tasks.objects.update_or_create(
                lab=or_lab,
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

        or_lab.update_total_tasks()
        self.stdout.write(self.style.SUCCESS(f"Open Redirect lab setup complete with {or_lab.total_tasks} tasks"))