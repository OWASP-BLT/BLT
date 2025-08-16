from django.core.management.base import BaseCommand

from website.models import Labs, TaskContent, Tasks


class Command(BaseCommand):
    help = "Creates Cross-Site Request Forgery (CSRF) lab tasks with theory and simulation content"

    def handle(self, *args, **kwargs):
        try:
            csrf_lab = Labs.objects.get(name="Cross-Site Request Forgery")
        except Labs.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("Cross-Site Request Forgery lab not found. Please run create_initial_labs first.")
            )
            return

        tasks_data = [
            {
                "name": "Introduction to CSRF",
                "description": "Learn the fundamentals of Cross-Site Request Forgery attacks and their impact.",
                "task_type": "theory",
                "order": 1,
                "theory_content": """
                <h2>What is Cross-Site Request Forgery (CSRF)?</h2>
                <p>Cross-Site Request Forgery (CSRF) is an attack that forces authenticated users to submit unintended requests to a web application. The attacker tricks the victim into executing unwanted actions on a web application where they're currently authenticated.</p>
                
                <h3>How CSRF Works</h3>
                <ol>
                    <li>User logs into a legitimate website (e.g., online banking)</li>
                    <li>User visits a malicious website while still logged in</li>
                    <li>Malicious site sends a request to the legitimate site using the user's session</li>
                    <li>The legitimate site processes the request as if the user intended it</li>
                </ol>
                
                <h3>Common CSRF Attack Vectors</h3>
                <ul>
                    <li><strong>HTML Forms:</strong> Auto-submitting forms with hidden fields</li>
                    <li><strong>Image Tags:</strong> Using img src to trigger GET requests</li>
                    <li><strong>JavaScript:</strong> AJAX requests from malicious sites</li>
                    <li><strong>Links:</strong> Tricking users to click malicious links</li>
                </ul>
                
                <h3>Example CSRF Attack</h3>
                <pre><code>
                &lt;!-- Malicious HTML page --&gt;
                &lt;form action="https://bank.com/transfer" method="POST" id="csrf-form"&gt;
                    &lt;input type="hidden" name="amount" value="1000"&gt;
                    &lt;input type="hidden" name="to_account" value="attacker_account"&gt;
                &lt;/form&gt;
                &lt;script&gt;document.getElementById('csrf-form').submit();&lt;/script&gt;
                </code></pre>
                
                <h3>Impact of CSRF</h3>
                <ul>
                    <li>Unauthorized fund transfers</li>
                    <li>Account settings changes</li>
                    <li>Password modifications</li>
                    <li>Data deletion or modification</li>
                </ul>
                """,
                "mcq_question": "What is required for a CSRF attack to be successful?",
                "mcq_options": [
                    "A) The victim must visit a malicious website",
                    "B) The victim must be authenticated to the target site",
                    "C) The target site must lack CSRF protection",
                    "D) All of the above",
                ],
                "correct_answer": "D",
            },
            {
                "name": "CSRF Protection Mechanisms",
                "description": "Learn about different methods to prevent CSRF attacks.",
                "task_type": "theory",
                "order": 2,
                "theory_content": """
                <h2>CSRF Protection Mechanisms</h2>
                <p>There are several effective methods to prevent CSRF attacks. The key is to ensure that requests genuinely originate from the authenticated user.</p>
                
                <h3>1. CSRF Tokens</h3>
                <p>The most common and effective protection method:</p>
                <ul>
                    <li>Generate a unique, unpredictable token for each session</li>
                    <li>Include the token in all state-changing requests</li>
                    <li>Verify the token on the server before processing requests</li>
                </ul>
                <pre><code>
                &lt;form method="POST"&gt;
                    &lt;input type="hidden" name="csrf_token" value="abc123xyz789"&gt;
                    &lt;input type="text" name="email"&gt;
                    &lt;button type="submit"&gt;Update Email&lt;/button&gt;
                &lt;/form&gt;
                </code></pre>
                
                <h3>2. SameSite Cookie Attribute</h3>
                <p>Prevents cookies from being sent with cross-site requests:</p>
                <pre><code>
                Set-Cookie: sessionid=abc123; SameSite=Strict
                Set-Cookie: sessionid=abc123; SameSite=Lax
                </code></pre>
                
                <h3>3. Origin and Referer Headers</h3>
                <p>Verify that requests come from the expected origin:</p>
                <ul>
                    <li>Check the Origin header matches your domain</li>
                    <li>Validate the Referer header (less reliable)</li>
                </ul>
                
                <h3>4. Double Submit Cookie</h3>
                <p>Store CSRF token in both a cookie and request parameter:</p>
                <ul>
                    <li>Set CSRF token as a cookie</li>
                    <li>Include same token in form/header</li>
                    <li>Verify both values match</li>
                </ul>
                """,
                "mcq_question": "Which CSRF protection method is considered the most secure?",
                "mcq_options": [
                    "A) Checking Referer header only",
                    "B) Using SameSite=Lax cookies",
                    "C) CSRF tokens with proper validation",
                    "D) Origin header validation only",
                ],
                "correct_answer": "C",
            },
            {
                "name": "Basic CSRF Attack - Email Change",
                "description": "Practice exploiting a CSRF vulnerability to change user email address.",
                "task_type": "simulation",
                "order": 3,
                "simulation_config": {
                    "type": "basic_csrf",
                    "scenario": "email_change",
                    "target_url": "/profile/update",
                    "vulnerable_parameters": ["email"],
                    "success_payload": "<form action='/profile/update' method='POST'><input name='email' value='attacker@evil.com'></form>",
                    "hints": [
                        "Create an HTML form that submits to the target URL",
                        "The form should change the email to a value you control",
                        "Use POST method for the form submission",
                        "The target site doesn't validate CSRF tokens",
                    ],
                    "success_criteria": "HTML form that performs unauthorized email change",
                    "difficulty": "beginner",
                },
            },
            {
                "name": "CSRF with Auto-Submit",
                "description": "Create a CSRF attack that automatically submits when the page loads.",
                "task_type": "simulation",
                "order": 4,
                "simulation_config": {
                    "type": "auto_submit_csrf",
                    "scenario": "fund_transfer",
                    "target_url": "/transfer/money",
                    "vulnerable_parameters": ["amount", "to_account"],
                    "success_payload": "<form id='csrf' action='/transfer/money' method='POST'><input name='amount' value='1000'><input name='to_account' value='attacker'></form><script>document.getElementById('csrf').submit()</script>",
                    "hints": [
                        "Create a form that submits automatically using JavaScript",
                        "Include hidden input fields for amount and destination account",
                        "Use document.getElementById().submit() to auto-submit",
                        "The form should transfer money to your account",
                    ],
                    "success_criteria": "Auto-submitting form that transfers funds without user interaction",
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "Image-based CSRF Attack",
                "description": "Exploit CSRF using image tags for GET-based vulnerable endpoints.",
                "task_type": "simulation",
                "order": 5,
                "simulation_config": {
                    "type": "image_csrf",
                    "scenario": "account_deletion",
                    "target_url": "/account/delete",
                    "vulnerable_parameters": ["confirm"],
                    "success_payload": "<img src='/account/delete?confirm=yes' style='display:none'>",
                    "hints": [
                        "Use an img tag with the vulnerable URL as the src",
                        "Include the required parameters in the URL query string",
                        "Hide the image so the user doesn't see it",
                        "The request happens when the image 'loads'",
                    ],
                    "success_criteria": "Hidden image that triggers account deletion via GET request",
                    "difficulty": "beginner",
                },
            },
            {
                "name": "CSRF with AJAX",
                "description": "Perform CSRF attacks using JavaScript and AJAX requests.",
                "task_type": "simulation",
                "order": 6,
                "simulation_config": {
                    "type": "ajax_csrf",
                    "scenario": "password_change",
                    "target_url": "/account/password",
                    "vulnerable_parameters": ["new_password"],
                    "success_payload": "<script>fetch('/account/password', {method: 'POST', body: 'new_password=hacked123', headers: {'Content-Type': 'application/x-www-form-urlencoded'}})</script>",
                    "hints": [
                        "Use JavaScript fetch() or XMLHttpRequest",
                        "Send a POST request to the vulnerable endpoint",
                        "Include the new password in the request body",
                        "Set proper Content-Type header for form data",
                    ],
                    "success_criteria": "JavaScript code that changes user password via AJAX",
                    "difficulty": "advanced",
                },
            },
            {
                "name": "CSRF Token Bypass Techniques",
                "description": "Learn methods to bypass weak CSRF token implementations.",
                "task_type": "theory",
                "order": 7,
                "theory_content": """
                <h2>CSRF Token Bypass Techniques</h2>
                <p>Even when CSRF tokens are implemented, they may have weaknesses that can be exploited by attackers.</p>
                
                <h3>Common Bypass Techniques</h3>
                
                <h4>1. Missing Token Validation</h4>
                <ul>
                    <li>Application accepts requests without CSRF tokens</li>
                    <li>Simply omit the token from the request</li>
                    <li>Server doesn't enforce token presence</li>
                </ul>
                
                <h4>2. Predictable Tokens</h4>
                <ul>
                    <li>Tokens generated using weak algorithms</li>
                    <li>Sequential or timestamp-based tokens</li>
                    <li>Reused tokens across sessions</li>
                </ul>
                
                <h4>3. Token Leakage</h4>
                <ul>
                    <li>Tokens exposed in URLs (GET parameters)</li>
                    <li>Tokens in Referer headers</li>
                    <li>Tokens accessible via XSS</li>
                </ul>
                
                <h4>4. Subdomain Attacks</h4>
                <ul>
                    <li>Weak domain validation</li>
                    <li>Accepting requests from any subdomain</li>
                    <li>Cookie scope issues</li>
                </ul>
                
                <h3>Testing for CSRF Vulnerabilities</h3>
                <ol>
                    <li>Remove CSRF token and replay request</li>
                    <li>Change token value to invalid/empty</li>
                    <li>Use token from different session</li>
                    <li>Check if token is validated on server</li>
                    <li>Test with different HTTP methods</li>
                </ol>
                
                <h3>Example Bypass</h3>
                <pre><code>
                // Original request with token
                POST /transfer HTTP/1.1
                csrf_token=abc123&amount=100&to=victim
                
                // Bypass attempt - remove token
                POST /transfer HTTP/1.1
                amount=100&to=attacker
                </code></pre>
                """,
                "mcq_question": "Which scenario makes CSRF tokens ineffective?",
                "mcq_options": [
                    "A) Tokens are generated using strong randomness",
                    "B) Server accepts requests without validating tokens",
                    "C) Tokens are properly tied to user sessions",
                    "D) Tokens are validated on every request",
                ],
                "correct_answer": "B",
            },
        ]

        for task_data in tasks_data:
            task, created = Tasks.objects.update_or_create(
                lab=csrf_lab,
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

        csrf_lab.update_total_tasks()
        self.stdout.write(self.style.SUCCESS(f"CSRF lab setup complete with {csrf_lab.total_tasks} tasks"))
