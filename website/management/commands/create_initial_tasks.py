from django.core.management.base import BaseCommand

from website.models import Labs


class Command(BaseCommand):
    help = "Creates initial security lab data"

    def handle(self, *args, **kwargs):
        # Define the initial labs
        labs_data = [
            {
                "name": "SQL Injection",
                "description": "Learn about SQL injection vulnerabilities and how to exploit them. This lab covers basic to advanced SQL injection techniques, including union-based, error-based, and blind SQL injection.",
                "estimated_time": 60,  # 60 minutes
                "order": 1,
            },
            {
                "name": "Cross-Site Scripting (XSS)",
                "description": "Master the art of identifying and exploiting XSS vulnerabilities. Learn about different types of XSS attacks including reflected, stored, and DOM-based XSS.",
                "estimated_time": 45,  # 45 minutes
                "order": 2,
            },
            {
                "name": "Cross-Site Request Forgery",
                "description": "Understand CSRF attacks and prevention techniques. Learn how to identify CSRF vulnerabilities and implement proper protection mechanisms.",
                "estimated_time": 30,  # 30 minutes
                "order": 3,
            },
            {
                "name": "Command Injection",
                "description": "Learn about command injection vulnerabilities and exploitation. This lab covers how to identify and exploit command injection flaws in web applications.",
                "estimated_time": 40,  # 40 minutes
                "order": 4,
            },
            {
                "name": "Broken Authentication",
                "description": "Explore broken authentication issues: weak passwords, session fixation, credential stuffing, and poor session handling. Learn how to identify and exploit authentication flaws and implement robust defenses.",
                "estimated_time": 50,  # 50 minutes
                "order": 5,
            },
            {
                "name": "Insecure Direct Object Reference (IDOR)",
                "description": "Hands-on lab for IDOR vulnerabilities where access controls are missing or incorrect. Learn how to enumerate object IDs and access unauthorized resources.",
                "estimated_time": 45,  # 45 minutes
                "order": 6,
            },
            {
                "name": "File Upload Vulnerabilities",
                "description": "Study File Upload Vulnerabilities handling. Practice bypassing upload restrictions, uploading web shells, and implementing secure upload validation and storage.",
                "estimated_time": 50,  # 50 minutes
                "order": 7,
            },
            {
                "name": "Sensitive Data Exposure",
                "description": "Learn about common causes of sensitive data exposure: improper storage, weak encryption, verbose error messages, and insecure transport. Practice discovering leaked data and applying mitigation strategies.",
                "estimated_time": 40,  # 40 minutes
                "order": 8,
            },
            {
                "name": "Open Redirect",
                "description": "Practice finding and exploiting open redirect issues and understand how they enable phishing and other attacks. Learn secure coding patterns to prevent them.",
                "estimated_time": 25,  # 25 minutes
                "order": 9,
            },
            {
                "name": "Server-Side Request Forgery (SSRF)",
                "description": "Hands-on SSRF lab: learn how to trick a server into making unintended requests (internal network, metadata services), and techniques to prevent SSRF.",
                "estimated_time": 55,  # 55 minutes
                "order": 10,
            },
        ]

        # Create the labs
        for lab_data in labs_data:
            lab, created = Labs.objects.get_or_create(
                name=lab_data["name"],
                defaults={
                    "description": lab_data["description"],
                    "estimated_time": lab_data["estimated_time"],
                    "order": lab_data["order"],
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created lab "{lab.name}"'))
            else:
                self.stdout.write(self.style.WARNING(f'Lab "{lab.name}" already exists'))
