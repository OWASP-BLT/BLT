from django.core.management.base import BaseCommand
from website.models import Labs, TaskContent, Tasks
from django.core.management.base import CommandError


class Command(BaseCommand):
    help = "Creates Insecure Direct Object Reference (IDOR) lab tasks with theory and simulation content"

    def handle(self, *args, **kwargs):
        try:
            idor_lab = Labs.objects.get(name="Insecure Direct Object Reference (IDOR)")
        except Labs.DoesNotExist:
            raise CommandError(
                "Insecure Direct Object Reference (IDOR) lab not found. Please run create_initial_labs first."
            )

        tasks_data = [
            {
                "name": "Introduction to IDOR",
                "description": "Learn what Insecure Direct Object References (IDOR) are and how they occur.",
                "task_type": "theory",
                "order": 1,
                "theory_content": """
                <h2>What is Insecure Direct Object Reference (IDOR)?</h2>
                <p>IDOR occurs when an application exposes references to internal objects, such as user IDs, filenames, or database keys, without verifying user access permissions.</p>

                <h3>Example</h3>
                <pre><code>
                GET /profile?user_id=101
                </code></pre>
                <p>If changing <code>user_id=101</code> to <code>user_id=102</code> shows another user's profile, the application is vulnerable to IDOR.</p>

                <h3>Impact</h3>
                <ul>
                    <li>Unauthorized access to other users' data</li>
                    <li>Data modification or deletion</li>
                    <li>Exposure of sensitive information</li>
                </ul>
                """,
                "mcq_question": "What is the core issue in an IDOR vulnerability?",
                "mcq_options": [
                    "A) Lack of authentication",
                    "B) Lack of authorization checks on object access",
                    "C) Use of weak encryption",
                    "D) Unpatched server software",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Common IDOR Attack Scenarios",
                "description": "Explore how IDOR appears in real-world web applications and APIs.",
                "task_type": "theory",
                "order": 2,
                "theory_content": """
                <h2>Common IDOR Scenarios</h2>
                <ul>
                    <li><strong>Profile Access:</strong> <code>/profile?user_id=5</code></li>
                    <li><strong>Invoice Download:</strong> <code>/invoice?id=873</code></li>
                    <li><strong>File Access:</strong> <code>/files/report_2023.pdf</code></li>
                </ul>
                <p>If changing these identifiers reveals unauthorized information, it's an IDOR vulnerability.</p>

                <h3>API-based Example</h3>
                <pre><code>
                GET /api/user/45
                </code></pre>
                <p>If user A can access user B's data by changing the ID, the endpoint lacks proper access control.</p>
                """,
                "mcq_question": "Which of the following URLs likely contains an IDOR vulnerability?",
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
                "description": "Try to access another user's profile by modifying the user_id parameter.",
                "task_type": "simulation",
                "order": 3,
                "simulation_config": {
                    "type": "idor_profile",
                    "scenario": "profile_data_access",
                    "target_url": "/vulnerable-profile?user_id=2",
                    "vulnerable_parameters": ["user_id"],
                    "success_payload": "Change user_id=2 to user_id=3",
                    "success_criteria": "Access another user's profile data by changing the user_id value.",
                    "hints": [
                        "Look for numeric identifiers in the URL or request body.",
                        "Increment or decrement the user_id to test for data exposure.",
                        "Observe the response content for another user's details.",
                    ],
                    "difficulty": "beginner",
                },
            },
            {
                "name": "Advanced IDOR - API Endpoint",
                "description": "Exploit an API that exposes user data without proper access control.",
                "task_type": "simulation",
                "order": 4,
                "simulation_config": {
                    "type": "idor_api",
                    "scenario": "api_data_leak",
                    "target_url": "/api/user?id=101",
                    "vulnerable_parameters": ["id"],
                    "success_payload": "Change id=101 to id=102",
                    "success_criteria": "Obtain data of another user by modifying the API request parameter.",
                    "hints": [
                        "Try sequential IDs to enumerate users.",
                        "Use Burp or browser tools to intercept and modify requests.",
                        "Compare the JSON response for different IDs.",
                    ],
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "Preventing IDOR Vulnerabilities",
                "description": "Understand how to secure applications against IDOR attacks.",
                "task_type": "theory",
                "order": 5,
                "theory_content": """
                <h2>Preventing IDOR Vulnerabilities</h2>
                <ul>
                    <li>Implement proper authorization checks on all sensitive object access.</li>
                    <li>Use indirect references (e.g., random UUIDs) instead of sequential numeric IDs.</li>
                    <li>Never rely solely on client-side validation.</li>
                    <li>Review access control logic regularly and test for bypasses.</li>
                </ul>

                <h3>Secure Example</h3>
                <pre><code>
                # Insecure
                GET /profile?user_id=123

                # Secure
                GET /profile
                (server uses session user ID internally)
                </code></pre>
                """,
                "mcq_question": "Which is the best defense against IDOR?",
                "mcq_options": [
                    "A) Use POST requests for all endpoints",
                    "B) Hide IDs in HTML comments",
                    "C) Verify object ownership server-side",
                    "D) Minify JavaScript files",
                ],
                "correct_answer": "C",
            },
        ]

        for task_data in tasks_data:
            task, created = Tasks.objects.update_or_create(
                lab=idor_lab,
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
                content_data.update({"simulation_config": task_data["simulation_config"]})

            task_content, content_created = TaskContent.objects.update_or_create(task=task, defaults=content_data)

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created task: "{task.name}"'))
            else:
                self.stdout.write(self.style.WARNING(f'Task "{task.name}" already exists'))

            if content_created:
                self.stdout.write(self.style.SUCCESS(f'Created content for task: "{task.name}"'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated content for task: "{task.name}"'))

        idor_lab.update_total_tasks()
        self.stdout.write(self.style.SUCCESS(f"IDOR lab setup complete with {idor_lab.total_tasks} tasks"))
