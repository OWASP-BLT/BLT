from .base_lab_seeder import LabSeederCommand

class Command(LabSeederCommand):
    help = "Creates Insecure Direct Object Reference (IDOR) lab tasks"
    lab_name = "Insecure Direct Object Reference (IDOR)"

    tasks_data = [
        {
            "name": "Introduction to IDOR",
            "description": "Learn what Insecure Direct Object References (IDOR) are and how they occur.",
            "task_type": "theory",
            "order": 1,
            "theory_content": """
                <h2>What is Insecure Direct Object Reference (IDOR)?</h2>
                <p>IDOR occurs when an application exposes internal object references like user IDs, filenames, or database keys, without verifying authorization.</p>

                <h3>Example</h3>
                <pre><code>
                GET /profile?user_id=101
                </code></pre>
                <p>If changing user_id=101 to user_id=102 reveals another user's profile, this is an IDOR vulnerability.</p>

                <h3>Impact</h3>
                <ul>
                    <li>Unauthorized data access</li>
                    <li>Data modification or deletion</li>
                    <li>Sensitive info exposure</li>
                </ul>
            """,
            "mcq_question": "What is the core issue in an IDOR vulnerability?",
            "mcq_options": [
                "A) Lack of authentication",
                "B) Lack of authorization checks on object access",
                "C) Weak encryption",
                "D) Unpatched server",
            ],
            "correct_answer": "B",
        },
        {
            "name": "Common IDOR Attack Scenarios",
            "description": "Explore real-world cases and common patterns.",
            "task_type": "theory",
            "order": 2,
            "theory_content": """
                <h2>Common IDOR Scenarios</h2>
                <ul>
                    <li>Profile access: /profile?user_id=5</li>
                    <li>Invoice download: /invoice?id=873</li>
                    <li>File access: /files/report_2023.pdf</li>
                </ul>

                <h3>API Example</h3>
                <pre><code>
                GET /api/user/45
                </code></pre>
                <p>If user A can access user B's info by changing the ID, it's IDOR.</p>
            """,
            "mcq_question": "Which URL is most likely vulnerable to IDOR?",
            "mcq_options": [
                "A) /login",
                "B) /dashboard",
                "C) /profile?user_id=5",
                "D) /home",
            ],
            "correct_answer": "C",
        },
        {
            "name": "IDOR Exploit Simulation - Profile Access",
            "description": "Access another user's profile by modifying user_id.",
            "task_type": "simulation",
            "order": 3,
            "simulation_config": {
                "type": "idor_profile",
                "scenario": "profile_data_access",
                "target_url": "/vulnerable-profile?user_id=2",
                "vulnerable_parameters": ["user_id"],
                "success_payload": "Change user_id=2 to user_id=3",
                "success_criteria": "See another user's profile by changing user_id.",
                "hints": [
                    "Look for numeric IDs",
                    "Try incrementing/decrementing ID",
                ],
                "difficulty": "beginner",
            },
        },
        {
            "name": "Advanced IDOR - API Endpoint",
            "description": "Exploit insecure API ID parameter to pull another user's data.",
            "task_type": "simulation",
            "order": 4,
            "simulation_config": {
                "type": "idor_api",
                "scenario": "api_data_leak",
                "target_url": "/api/user?id=101",
                "vulnerable_parameters": ["id"],
                "success_payload": "Change id=101 to id=102",
                "success_criteria": "Obtain data of another user via API.",
                "hints": [
                    "Try sequential IDs",
                    "Compare JSON responses",
                ],
                "difficulty": "intermediate",
            },
        },
        {
            "name": "Preventing IDOR Vulnerabilities",
            "description": "Learn secure techniques to avoid IDOR.",
            "task_type": "theory",
            "order": 5,
            "theory_content": """
                <h2>Preventing IDOR</h2>
                <ul>
                    <li>Check authorization for all object access</li>
                    <li>Use indirect references (random UUIDs)</li>
                    <li>Do backend validation; never trust client input</li>
                </ul>

                <pre><code>
                # Insecure
                GET /profile?user_id=123

                # Secure
                GET /profile
                (server gets logged-in user from session)
                </code></pre>
            """,
            "mcq_question": "What is the best defense against IDOR?",
            "mcq_options": [
                "A) Use POST for everything",
                "B) Hide IDs in HTML",
                "C) Verify object ownership server-side",
                "D) Minify JavaScript",
            ],
            "correct_answer": "C",
        },
    ]
