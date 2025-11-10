from typing import Any, ClassVar

from .base_lab_seeder import LabSeederCommand


class Command(LabSeederCommand):
    help = "Creates Cross-Site Request Forgery (CSRF) lab tasks"
    lab_name = "Cross-Site Request Forgery"

    tasks_data: ClassVar[list[dict[str, Any]]] = [
        {
            "name": "Introduction to CSRF",
            "description": "Learn the fundamentals of Cross-Site Request Forgery attacks and their impact.",
            "task_type": "theory",
            "order": 1,
            "theory_content": """
                <h2>What is Cross-Site Request Forgery (CSRF)?</h2>
                <p>Cross-Site Request Forgery (CSRF) is an attack that forces authenticated users to submit unintended requests to a web application.</p>

                <h3>How CSRF Works</h3>
                <ol>
                    <li>User logs into a legitimate website</li>
                    <li>User visits a malicious website</li>
                    <li>Malicious site sends unauthorized request using victim's session</li>
                </ol>

                <h3>Common Attack Vectors</h3>
                <ul>
                    <li>Auto-submitting forms</li>
                    <li>Image tags triggering GET requests</li>
                    <li>AJAX requests from malicious pages</li>
                    <li>Malicious links</li>
                </ul>

                <h3>Impact Examples</h3>
                <ul>
                    <li>Fund transfers</li>
                    <li>Password change</li>
                    <li>Account deletion</li>
                </ul>
            """,
            "mcq_question": "What is required for a CSRF attack to be successful?",
            "mcq_options": [
                "A) Victim visits a malicious site",
                "B) Victim is authenticated",
                "C) Target lacks CSRF protection",
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
                <h3>1. CSRF Tokens</h3>
                <ul>
                    <li>Unique token per session</li>
                    <li>Included on POST requests</li>
                    <li>Server validates token</li>
                </ul>

                <h3>2. SameSite Cookie Attribute</h3>
                <pre><code>Set-Cookie: sessionid=abc123; SameSite=Strict</code></pre>

                <h3>3. Origin / Referer Validation</h3>

                <h3>4. Double Submit Cookie</h3>
            """,
            "mcq_question": "Which CSRF protection method is considered the most secure?",
            "mcq_options": [
                "A) Checking Referer only",
                "B) SameSite=Lax cookies",
                "C) CSRF Tokens with validation",
                "D) Origin header only",
            ],
            "correct_answer": "C",
        },
        {
            "name": "Basic CSRF Attack - Email Change",
            "description": "Practice exploiting a CSRF vulnerability to change user email.",
            "task_type": "simulation",
            "order": 3,
            "simulation_config": {
                "type": "basic_csrf",
                "scenario": "email_change",
                "target_url": "/profile/update",
                "vulnerable_parameters": ["email"],
                "success_payload": "<form action='/profile/update' method='POST'><input name='email' value='attacker@evil.com'></form>",
                "success_criteria": "HTML form that changes email without user interaction",
                "hints": [
                    "Use POST form",
                    "Submit to target URL",
                ],
                "difficulty": "beginner",
            },
        },
        {
            "name": "CSRF with Auto-Submit",
            "description": "Form auto-submits when page loads.",
            "task_type": "simulation",
            "order": 4,
            "simulation_config": {
                "type": "auto_submit_csrf",
                "scenario": "fund_transfer",
                "target_url": "/transfer/money",
                "vulnerable_parameters": ["amount", "to_account"],
                "success_payload": "<form id='csrf' action='/transfer/money' method='POST'><input name='amount' value='1000'><input name='to_account' value='attacker'></form><script>document.getElementById('csrf').submit()</script>",
                "success_criteria": "Auto-submitting form that transfers funds",
                "hints": [
                    "Use JS submit()",
                    "Use hidden fields",
                ],
                "difficulty": "intermediate",
            },
        },
        {
            "name": "Image-based CSRF",
            "description": "Trigger GET CSRF using image tag.",
            "task_type": "simulation",
            "order": 5,
            "simulation_config": {
                "type": "image_csrf",
                "scenario": "account_deletion",
                "target_url": "/account/delete",
                "vulnerable_parameters": ["confirm"],
                "success_payload": "<img src='/account/delete?confirm=yes' style='display:none'>",
                "success_criteria": "Hidden image triggers GET action",
                "hints": [
                    "Use <img>",
                    "Add query params in URL",
                ],
                "difficulty": "beginner",
            },
        },
        {
            "name": "CSRF with AJAX",
            "description": "Use JavaScript to send malicious POST request.",
            "task_type": "simulation",
            "order": 6,
            "simulation_config": {
                "type": "ajax_csrf",
                "scenario": "password_change",
                "target_url": "/account/password",
                "vulnerable_parameters": ["new_password"],
                "success_payload": "<script>fetch('/account/password',{method:'POST',body:'new_password=hacked123',headers:{'Content-Type':'application/x-www-form-urlencoded'}})</script>",
                "success_criteria": "JavaScript request performs password change",
                "hints": [
                    "Use fetch() or XMLHttpRequest",
                    "POST with form data",
                ],
                "difficulty": "advanced",
            },
        },
        {
            "name": "CSRF Token Bypass Techniques",
            "description": "Learn bypass methods for weak CSRF implementations.",
            "task_type": "theory",
            "order": 7,
            "theory_content": """
                <h2>CSRF Token Bypass</h2>
                <ul>
                    <li>Server doesn't validate token</li>
                    <li>Predictable token values</li>
                    <li>Token leakage in URL</li>
                    <li>Weak domain restrictions</li>
                </ul>
            """,
            "mcq_question": "Which scenario makes CSRF tokens ineffective?",
            "mcq_options": [
                "A) Strong randomness",
                "B) Tokens not validated",
                "C) Tied to session",
                "D) Checked every request",
            ],
            "correct_answer": "B",
        },
    ]
