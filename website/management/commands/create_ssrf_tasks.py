from typing import Any, ClassVar

from .base_lab_seeder import LabSeederCommand


class Command(LabSeederCommand):
    help = "Creates Server-Side Request Forgery (SSRF) lab tasks with theory and simulation content"
    lab_name = "Server-Side Request Forgery (SSRF)"

    tasks_data: ClassVar[list[dict[str, Any]]] = [
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
    ]
