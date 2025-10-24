from django.core.management.base import BaseCommand

from website.models import Labs, TaskContent, Tasks


class Command(BaseCommand):
    help = "Create Command Injection lab tasks"

    def handle(self, *args, **options):
        command_injection_lab, created = Labs.objects.get_or_create(
            name="Command Injection",
            defaults={
                "description": "Learn about command injection vulnerabilities and how to exploit them",
                "difficulty": "Intermediate",
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created lab: {command_injection_lab.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"Lab already exists: {command_injection_lab.name}"))

        tasks_data = [
            {
                "order": 1,
                "name": "Understanding Command Injection",
                "description": "Learn the basics of command injection vulnerabilities",
                "task_type": "theory",
                "theory_content": """
                <h2>What is Command Injection?</h2>
                <p>Command injection allows an attacker to execute arbitrary OS commands on the server by manipulating inputs to insecure system calls.</p>
                """,
                "mcq_question": "What is Command Injection?",
                "mcq_options": [
                    "A) Injecting OS commands via user input",
                    "B) Improving system performance",
                    "C) Backing up data",
                    "D) Writing database queries",
                ],
                "correct_answer": "A",
            },
            {
                "order": 2,
                "name": "Command Injection Types",
                "description": "Understand different types of command injection",
                "task_type": "theory",
                "theory_content": """
                <h2>Types of Command Injection</h2>
                <ul>
                    <li>Blind command injection</li>
                    <li>Time-based command injection</li>
                    <li>Out-of-band command injection</li>
                </ul>
                """,
                "mcq_question": "Which of the following is NOT a type of command injection?",
                "mcq_options": [
                    "A) Blind command injection",
                    "B) Time-based command injection",
                    "C) Out-of-band command injection",
                    "D) Cross-site command injection",
                ],
                "correct_answer": "D",
            },
            {
                "order": 3,
                "name": "Basic Command Injection",
                "description": "Practice basic command injection with simple payloads",
                "task_type": "simulation",
                "simulation_config": {
                    "scenario": "ping_feature",
                    "vulnerable_parameters": ["ip_address"],
                    "success_criteria": "Execute a command that shows the current directory contents",
                    "success_payload": "127.0.0.1; ls",
                    "hints": [
                        "Use command separators like ; to chain commands",
                    ],
                    "difficulty": "beginner",
                },
            },
            {
                "order": 4,
                "name": "Command Injection with Pipes",
                "description": "Use pipe operators for command injection",
                "task_type": "simulation",
                "simulation_config": {
                    "scenario": "ping_filter_semicolon",
                    "vulnerable_parameters": ["ip_address"],
                    "success_criteria": "Execute a command that shows system information",
                    "success_payload": "127.0.0.1 | uname -a",
                    "hints": [
                        "Try the pipe operator (|) to feed output into commands",
                    ],
                    "difficulty": "beginner",
                },
            },
            {
                "order": 5,
                "name": "Blind Command Injection",
                "description": "Practice blind command injection techniques",
                "task_type": "simulation",
                "simulation_config": {
                    "scenario": "blind_injection",
                    "vulnerable_parameters": ["ip_address"],
                    "success_criteria": "Cause a measurable time delay",
                    "success_payload": "127.0.0.1; sleep 5",
                    "hints": [
                        "Use time delays like sleep to confirm injection",
                    ],
                    "difficulty": "intermediate",
                },
            },
            {
                "order": 6,
                "name": "Command Injection Prevention",
                "description": "Learn how to prevent command injection vulnerabilities",
                "task_type": "theory",
                "theory_content": """
                <h2>Prevention</h2>
                <ul>
                    <li>Validate and sanitize all inputs</li>
                    <li>Use safe, parameterized APIs instead of shell calls</li>
                    <li>Avoid invoking system commands entirely when possible</li>
                </ul>
                """,
                "mcq_question": "What is the BEST way to prevent command injection?",
                "mcq_options": [
                    "A) Input validation only",
                    "B) Parameterized commands only",
                    "C) Avoid system commands only",
                    "D) All of the above combined",
                ],
                "correct_answer": "D",
            },
            {
                "order": 7,
                "name": "Advanced Command Injection",
                "description": "Practice advanced command injection with encoding",
                "task_type": "simulation",
                "simulation_config": {
                    "scenario": "filter_bypass",
                    "vulnerable_parameters": ["ip_address"],
                    "success_criteria": "Execute a command that shows the current user",
                    "success_payload": "127.0.0.1${IFS}&&${IFS}whoami",
                    "hints": [
                        "Use ${IFS} instead of spaces to bypass filters",
                    ],
                    "difficulty": "advanced",
                },
            },
            {
                "order": 8,
                "name": "Command Injection in Web Shells",
                "description": "Understand how command injection relates to web shells",
                "task_type": "theory",
                "theory_content": """
                <h2>Web Shells</h2>
                <p>Command injection can be leveraged to upload or execute web shells, providing persistent access.</p>
                """,
                "mcq_question": "How does command injection relate to web shells?",
                "mcq_options": [
                    "A) It can be used to upload/execute shells",
                    "B) Web shells are a type of command injection",
                    "C) They are unrelated",
                    "D) Web shells prevent injection",
                ],
                "correct_answer": "A",
            },
        ]

        for task_data in tasks_data:
            task, created = Tasks.objects.update_or_create(
                lab=command_injection_lab,
                order=task_data["order"],
                defaults={
                    "name": task_data["name"],
                    "description": task_data["description"],
                    "task_type": task_data["task_type"],
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created task: {task.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Updated task: {task.name}"))

            content_defaults = {}
            if task_data["task_type"] == "theory":
                content_defaults.update(
                    {
                        "theory_content": task_data.get("theory_content", ""),
                        "mcq_question": task_data.get("mcq_question", ""),
                        "mcq_options": task_data.get("mcq_options", []),
                        "correct_answer": task_data.get("correct_answer", ""),
                    }
                )
            else:
                content_defaults.update(
                    {
                        "simulation_config": task_data.get("simulation_config", {}),
                    }
                )

            content, content_created = TaskContent.objects.update_or_create(
                task=task,
                defaults=content_defaults,
            )

            if content_created:
                self.stdout.write(self.style.SUCCESS(f"Created content for task: {task.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Updated content for task: {task.name}"))

        if hasattr(command_injection_lab, "update_total_tasks"):
            command_injection_lab.update_total_tasks()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created/updated {len(tasks_data)} tasks for Command Injection lab")
        )
