from .base_lab_seeder import LabSeederCommand


class Command(LabSeederCommand):
    help = "Creates Cross-Site Scripting (XSS) lab tasks with theory and simulation content"
    lab_name = "Cross-Site Scripting (XSS)"

    tasks_data = [
        {
            "name": "Introduction to Cross-Site Scripting",
            "description": "Learn the basics of XSS vulnerabilities and how they occur in web applications.",
            "task_type": "theory",
            "order": 1,
            "theory_content": """
                <h2>What is Cross-Site Scripting (XSS)?</h2>
                <p>Cross-Site Scripting (XSS) allows attackers to inject malicious scripts into pages viewed by others.</p>

                <h3>Types of XSS Attacks</h3>
                <ul>
                    <li><strong>Reflected:</strong> Input reflected in response</li>
                    <li><strong>Stored:</strong> Injected code stored on server</li>
                    <li><strong>DOM-based:</strong> Client-side JS executes attacker input</li>
                </ul>

                <h3>Impact</h3>
                <ul>
                    <li>Steal cookies / session tokens</li>
                    <li>Redirect to malicious pages</li>
                    <li>Run malware or phishing payloads</li>
                </ul>
            """,
            "mcq_question": "Which type of XSS stores malicious scripts on the server?",
            "mcq_options": [
                "A) Reflected XSS",
                "B) Stored XSS",
                "C) DOM-based XSS",
                "D) None of the above",
            ],
            "correct_answer": "B",
        },
        {
            "name": "Identifying XSS Vulnerabilities",
            "description": "Learn how to detect XSS issues in web applications.",
            "task_type": "theory",
            "order": 2,
            "theory_content": """
                <h2>Identifying XSS</h2>
                <p>Occurs when user input is reflected without encoding or sanitization.</p>

                <h3>Common injection points</h3>
                <ul>
                    <li>URL parameters</li>
                    <li>Form fields</li>
                    <li>Comments or chat messages</li>
                    <li>User profile fields</li>
                </ul>

                <h3>Example payloads</h3>
                <pre><code>
                <script>alert('xss')</script>
                <img src=x onerror=alert('xss')>
                </code></pre>
            """,
            "mcq_question": "Where are XSS vulnerabilities most commonly found?",
            "mcq_options": [
                "A) Database config files",
                "B) Network routers",
                "C) User-controlled input fields",
                "D) CSS stylesheets",
            ],
            "correct_answer": "C",
        },
        {
            "name": "Reflected XSS - Comment System",
            "description": "Exploit reflected XSS in a vulnerable comment field.",
            "task_type": "simulation",
            "order": 3,
            "simulation_config": {
                "type": "reflected_xss",
                "scenario": "vulnerable_blog",
                "target_url": "/xss-lab/blog",
                "vulnerable_parameters": ["comment"],
                "success_payload": "<script>alert('XSS')</script>",
                "success_criteria": "JavaScript alert executes",
                "hints": [
                    "Enter payload in comment field",
                    "Page reflects comment without sanitization",
                ],
                "difficulty": "beginner",
            },
        },
        {
            "name": "Stored XSS - User Profile",
            "description": "Inject stored XSS into user profile fields.",
            "task_type": "simulation",
            "order": 4,
            "simulation_config": {
                "type": "stored_xss",
                "scenario": "vulnerable_profile",
                "target_url": "/xss-lab/profile",
                "vulnerable_parameters": ["bio"],
                "success_payload": "<script>alert('Stored XSS')</script>",
                "success_criteria": "Script executes when profile is viewed",
                "difficulty": "intermediate",
            },
        },
        {
            "name": "XSS Filter Bypass - Basic",
            "description": "Bypass simple blacklist-based XSS filters.",
            "task_type": "simulation",
            "order": 5,
            "simulation_config": {
                "type": "filter_bypass",
                "scenario": "filtered_input",
                "target_url": "/xss-lab/filtered",
                "vulnerable_parameters": ["search"],
                "blocked_patterns": ["<script>", "javascript:", "onerror"],
                "success_payload": "<svg onload=alert('Bypass')>",
                "success_criteria": "JavaScript executes despite filter",
                "hints": [
                    "Try alternate tags and encodings",
                    "Some filters only block exact matches",
                ],
                "difficulty": "intermediate",
            },
        },
        {
            "name": "DOM-based XSS",
            "description": "Exploit client-side JS that writes untrusted data to the DOM.",
            "task_type": "simulation",
            "order": 6,
            "simulation_config": {
                "type": "dom_xss",
                "scenario": "client_side_vuln",
                "target_url": "/xss-lab/dom",
                "vulnerable_parameters": ["fragment"],
                "success_payload": "<img src=x onerror=alert('DOM XSS')>",
                "success_criteria": "Execute via DOM manipulation",
                "difficulty": "advanced",
            },
        },
        {
            "name": "XSS Cookie Theft",
            "description": "Show how XSS can steal user session cookies.",
            "task_type": "simulation",
            "order": 7,
            "simulation_config": {
                "type": "cookie_theft",
                "scenario": "session_hijacking",
                "target_url": "/xss-lab/cookies",
                "vulnerable_parameters": ["message"],
                "success_payload": "<script>alert(document.cookie)</script>",
                "success_criteria": "Display session cookies",
                "difficulty": "intermediate",
            },
        },
        {
            "name": "XSS Prevention Techniques",
            "description": "Learn industry best practices to stop XSS.",
            "task_type": "theory",
            "order": 8,
            "theory_content": """
                <h2>XSS Prevention</h2>
                <ul>
                    <li>Sanitize and validate all input</li>
                    <li>HTML/JS/URL encode output</li>
                    <li>Use frameworks with auto-escaping</li>
                    <li>Use Content-Security-Policy</li>
                    <li>Set HttpOnly flag on session cookies</li>
                </ul>

                <h3>Example CSP</h3>
                <pre><code>
                Content-Security-Policy: default-src 'self'; script-src 'self'
                </code></pre>
            """,
            "mcq_question": "Which header helps prevent XSS by restricting script sources?",
            "mcq_options": [
                "A) Strict-Transport-Security",
                "B) Content-Security-Policy",
                "C) X-Frame-Options",
                "D) Access-Control-Allow-Origin",
            ],
            "correct_answer": "B",
        },
    ]
