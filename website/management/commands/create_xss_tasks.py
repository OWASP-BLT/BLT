from django.core.management.base import BaseCommand

from website.models import Labs, TaskContent, Tasks


class Command(BaseCommand):
    help = "Creates Cross-Site Scripting (XSS) lab tasks with theory and simulation content"

    def handle(self, *args, **kwargs):
        try:
            xss_lab = Labs.objects.get(name="Cross-Site Scripting (XSS)")
        except Labs.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("Cross-Site Scripting (XSS) lab not found. Please run create_initial_labs first.")
            )
            return

        # Define the XSS lab tasks
        tasks_data = [
            {
                "name": "Introduction to Cross-Site Scripting",
                "description": "Learn the basics of XSS vulnerabilities and how they occur in web applications.",
                "task_type": "theory",
                "order": 1,
                "theory_content": """
                <h2>What is Cross-Site Scripting (XSS)?</h2>
                <p>Cross-Site Scripting (XSS) is a security vulnerability that allows attackers to inject malicious scripts into web pages viewed by other users. When executed, these scripts can steal sensitive information, manipulate page content, or perform actions on behalf of the victim.</p>
                
                <h3>Types of XSS Attacks</h3>
                <ul>
                    <li><strong>Reflected XSS:</strong> Malicious script is reflected off a web server (e.g., in an error message)</li>
                    <li><strong>Stored XSS:</strong> Malicious script is stored on the target server (e.g., in a database)</li>
                    <li><strong>DOM-based XSS:</strong> Vulnerability exists in client-side code rather than server-side</li>
                </ul>
                
                <h3>Common XSS Payloads</h3>
                <pre><code>
                &lt;script&gt;alert('XSS')&lt;/script&gt;
                &lt;img src=x onerror=alert('XSS')&gt;
                &lt;svg onload=alert('XSS')&gt;
                </code></pre>
                
                <h3>Impact of XSS</h3>
                <ul>
                    <li>Session hijacking and cookie theft</li>
                    <li>Defacement of web pages</li>
                    <li>Redirecting users to malicious sites</li>
                    <li>Keylogging and credential theft</li>
                </ul>
                """,
                "mcq_question": "Which type of XSS vulnerability stores malicious scripts on the server?",
                "mcq_options": [
                    "A) Reflected XSS",
                    "B) Stored XSS",
                    "C) DOM-based XSS",
                    "D) Session XSS",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Identifying XSS Vulnerabilities",
                "description": "Learn how to identify potential XSS vulnerabilities in web applications.",
                "task_type": "theory",
                "order": 2,
                "theory_content": """
                <h2>How to Identify XSS Vulnerabilities</h2>
                <p>XSS vulnerabilities typically occur when user input is not properly validated, sanitized, or encoded before being displayed on a web page.</p>
                
                <h3>Common Vulnerable Input Points</h3>
                <ul>
                    <li>Search boxes and form fields</li>
                    <li>URL parameters</li>
                    <li>Comment sections</li>
                    <li>User profile fields</li>
                    <li>HTTP headers (User-Agent, Referer)</li>
                </ul>
                
                <h3>Testing for XSS</h3>
                <ol>
                    <li>Insert test payloads in input fields</li>
                    <li>Check if the payload is reflected in the response</li>
                    <li>Verify if the script executes in the browser</li>
                    <li>Test different encoding and bypasses</li>
                </ol>
                
                <h3>Example Vulnerable Code</h3>
                <pre><code>
                // Vulnerable PHP code
                echo "Hello " . $_GET['name'];
                
                // Vulnerable JavaScript
                document.getElementById('output').innerHTML = userInput;
                </code></pre>
                """,
                "mcq_question": "Which of the following is the most common place to test for XSS vulnerabilities?",
                "mcq_options": [
                    "A) Database connections",
                    "B) User input fields",
                    "C) Server configuration files",
                    "D) Network protocols",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Reflected XSS - Comment System",
                "description": "Practice exploiting reflected XSS in a vulnerable comment system.",
                "task_type": "simulation",
                "order": 3,
                "simulation_config": {
                    "type": "reflected_xss",
                    "scenario": "vulnerable_blog",
                    "target_url": "/xss-lab/blog",
                    "vulnerable_parameter": "comment",
                    "success_payload": "<script>alert('XSS')</script>",
                    "hints": [
                        "Try injecting a simple script tag in the comment field",
                        "The application doesn't sanitize user input",
                        "Look for ways to execute JavaScript when the page loads",
                    ],
                    "expected_result": "JavaScript alert should execute showing 'XSS'",
                    "difficulty": "beginner",
                },
            },
            {
                "name": "Stored XSS - User Profile",
                "description": "Exploit stored XSS by injecting scripts into profile fields.",
                "task_type": "simulation",
                "order": 4,
                "simulation_config": {
                    "type": "stored_xss",
                    "scenario": "vulnerable_profile",
                    "target_url": "/xss-lab/profile",
                    "vulnerable_parameter": "bio",
                    "success_payload": "<script>alert('Stored XSS')</script>",
                    "hints": [
                        "Try updating your profile bio with a script",
                        "The script should execute when anyone views your profile",
                        "This is stored XSS - it persists in the database",
                    ],
                    "expected_result": "Script executes when profile is viewed",
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "XSS Filter Bypass - Basic",
                "description": "Learn to bypass basic XSS filters and input validation.",
                "task_type": "simulation",
                "order": 5,
                "simulation_config": {
                    "type": "filter_bypass",
                    "scenario": "filtered_input",
                    "target_url": "/xss-lab/filtered",
                    "vulnerable_parameter": "search",
                    "blocked_patterns": ["<script>", "javascript:", "onerror"],
                    "success_payload": "<svg onload=alert('Bypass')>",
                    "hints": [
                        "Try using different case variations",
                        "Some filters only block exact matches",
                        "Unicode encoding might help bypass filters",
                        "Look for alternative event handlers",
                    ],
                    "expected_result": "Successfully bypass the filter and execute JavaScript",
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "DOM-based XSS",
                "description": "Exploit DOM-based XSS vulnerabilities in client-side JavaScript.",
                "task_type": "simulation",
                "order": 6,
                "simulation_config": {
                    "type": "dom_xss",
                    "scenario": "client_side_vuln",
                    "target_url": "/xss-lab/dom",
                    "vulnerable_parameter": "fragment",
                    "success_payload": "<img src=x onerror=alert('DOM XSS')>",
                    "hints": [
                        "This vulnerability exists in client-side JavaScript",
                        "Try manipulating the URL fragment (after #)",
                        "The page dynamically updates content based on the fragment",
                        "No server-side filtering is involved",
                    ],
                    "expected_result": "Execute JavaScript through DOM manipulation",
                    "difficulty": "advanced",
                },
            },
            {
                "name": "XSS Cookie Theft",
                "description": "Learn to steal cookies using XSS vulnerabilities.",
                "task_type": "simulation",
                "order": 7,
                "simulation_config": {
                    "type": "cookie_theft",
                    "scenario": "session_hijacking",
                    "target_url": "/xss-lab/cookies",
                    "vulnerable_parameter": "message",
                    "success_payload": "<script>alert(document.cookie)</script>",
                    "hints": [
                        "Use document.cookie to access session cookies",
                        "Try displaying the cookie value in an alert",
                        "In real attacks, cookies would be sent to attacker's server",
                        "This demonstrates the impact of XSS on session security",
                    ],
                    "expected_result": "Display session cookie value",
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "XSS Prevention Techniques",
                "description": "Learn about effective methods to prevent XSS vulnerabilities.",
                "task_type": "theory",
                "order": 8,
                "theory_content": """
                <h2>XSS Prevention Techniques</h2>
                <p>Preventing XSS requires a multi-layered approach combining input validation, output encoding, and security headers.</p>
                
                <h3>Input Validation</h3>
                <ul>
                    <li>Whitelist allowed characters and patterns</li>
                    <li>Reject or sanitize dangerous input</li>
                    <li>Validate on both client and server side</li>
                </ul>
                
                <h3>Output Encoding</h3>
                <ul>
                    <li>HTML encode user data before display</li>
                    <li>JavaScript encode for JS contexts</li>
                    <li>URL encode for URL contexts</li>
                    <li>CSS encode for style contexts</li>
                </ul>
                
                <h3>Content Security Policy (CSP)</h3>
                <pre><code>
                Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'
                </code></pre>
                
                <h3>Secure Coding Practices</h3>
                <ul>
                    <li>Use template engines with auto-escaping</li>
                    <li>Avoid innerHTML for dynamic content</li>
                    <li>Set HttpOnly flag on session cookies</li>
                    <li>Implement proper error handling</li>
                </ul>
                """,
                "mcq_question": "Which HTTP header helps prevent XSS attacks by controlling resource loading?",
                "mcq_options": [
                    "A) X-Frame-Options",
                    "B) Content-Security-Policy",
                    "C) X-XSS-Protection",
                    "D) Strict-Transport-Security",
                ],
                "correct_answer": "B",
            },
        ]

        # Create tasks and their content
        for task_data in tasks_data:
            task, created = Tasks.objects.get_or_create(
                lab=xss_lab,
                name=task_data["name"],
                order=task_data["order"],
                defaults={
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

        # Update the total tasks count for the lab
        xss_lab.update_total_tasks()
        self.stdout.write(self.style.SUCCESS(f"XSS lab setup complete with {xss_lab.total_tasks} tasks"))
