from django.core.management.base import BaseCommand
from website.models import Labs, TaskContent, Tasks


class Command(BaseCommand):
    help = "Creates File Upload Vulnerabilities lab tasks with theory and simulation content"

    def handle(self, *args, **kwargs):
        try:
            upload_lab = Labs.objects.get(name="File Upload Vulnerabilities")
        except Labs.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("File Upload Vulnerabilities lab not found. Please run create_initial_labs first.")
            )
            return

        tasks_data = [
            {
                "name": "Introduction to File Upload Vulnerabilities",
                "description": "Learn why unrestricted file uploads are dangerous and common attack patterns.",
                "task_type": "theory",
                "order": 1,
                "theory_content": """
                <h2>What is File Upload Vulnerabilities?</h2>
                <p>File Upload Vulnerabilities occurs when an application accepts files from users without proper validation, allowing attackers to upload malicious files (web shells), bypass access controls, or overwrite sensitive files.</p>

                <h3>Common risks</h3>
                <ul>
                    <li>Remote code execution (uploading web shells)</li>
                    <li>Content-based attacks (malicious scripts disguised as images)</li>
                    <li>Path traversal (writing files outside allowed directories)</li>
                    <li>Denial of Service (large or numerous uploads)</li>
                </ul>

                <h3>Typical vulnerable code</h3>
                <pre><code>
                // Poor example: saving uploaded file with original filename without validation
                filename = request.FILES['file'].name
                open("/var/www/uploads/" + filename, "wb").write(request.FILES['file'].read())
                </code></pre>
                """,
                "mcq_question": "Which of the following is the best practice to reduce file upload risk?",
                "mcq_options": [
                    "A) Allow any file extension but scan contents on demand",
                    "B) Validate file type, restrict extensions, and store outside the web root",
                    "C) Save files using user-controlled filenames",
                    "D) Serve uploaded files directly from the application server",
                ],
                "correct_answer": "B",
            },
            {
                "name": "File Type & Content Validation",
                "description": "Understand checks for MIME type, extension and magic bytes, and why each matters.",
                "task_type": "theory",
                "order": 2,
                "theory_content": """
                <h2>File Validation Techniques</h2>
                <ul>
                    <li><strong>Extension checks:</strong> Useful but can be bypassed by renaming files.</li>
                    <li><strong>MIME type checks:</strong> Based on headers; can be spoofed.</li>
                    <li><strong>Magic byte inspection:</strong> Checking file signatures is stronger.</li>
                    <li><strong>Content scanning:</strong> Anti-virus / malware scanning as an additional layer.</li>
                </ul>

                <h3>Best practices</h3>
                <ul>
                    <li>Whitelist allowed file types and verify magic bytes</li>
                    <li>Store uploads outside the web root and serve via authenticated proxy</li>
                    <li>Rename files to server-generated tokens (avoid original filenames)</li>
                    <li>Limit file size and enforce quotas</li>
                </ul>
                """,
                "mcq_question": "Why is checking only file extension insufficient?",
                "mcq_options": [
                    "A) Extensions are always correct",
                    "B) Attackers can rename files to bypass extension checks",
                    "C) Extensions validate magic bytes",
                    "D) Extensions prevent XSS",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Simulation: Upload a Web Shell (Safe Lab)",
                "description": "Simulate uploading a malicious web shell file and demonstrating execution (lab safely simulates execution output).",
                "task_type": "simulation",
                "order": 3,
                "simulation_config": {
                    "type": "upload_shell",
                    "scenario": "web_shell_upload",
                    "target_url": "/upload",
                    "vulnerable_parameters": ["file"],
                    "success_payload": "upload a file named shell.php containing '<?php echo shell_exec($_GET[\"cmd\"]); ?>' (lab simulates and returns command output when accessed)",
                    "success_criteria": "Upload file that the lab marks as an executable web shell and returns simulated command output on access",
                    "hints": [
                        "Try uploading a .php file with a simple command-executing payload (lab simulates execution in a controlled environment)",
                        "If .php is blocked, try using double extensions (e.g., image.php.jpg) — the lab simulates common server misconfigurations",
                        "The lab will never execute arbitrary commands on real servers; it returns a simulated output for demonstration",
                    ],
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "Simulation: Content-Type Bypass",
                "description": "Bypass naive MIME-type checks by uploading a malicious payload disguised as an image.",
                "task_type": "simulation",
                "order": 4,
                "simulation_config": {
                    "type": "upload_mimetype_bypass",
                    "scenario": "mimetype_bypass",
                    "target_url": "/upload",
                    "vulnerable_parameters": ["file"],
                    "success_payload": "Upload a file with .jpg extension but with embedded PHP or script content (lab simulates detection of disguised payload)",
                    "success_criteria": "Lab detects disguised malicious content despite extension or header checks and marks the challenge complete",
                    "hints": [
                        "Try adding PHP tags inside a file with a .jpg extension (lab simulates common server parsing issues)",
                        "Consider embedding the payload in EXIF or alternate data streams (simulated)",
                        "The lab only simulates unsafe server behavior to show why magic byte checks matter",
                    ],
                    "difficulty": "intermediate",
                },
            },
            {
                "name": "Simulation: Path Traversal via Filename",
                "description": "Exploit improper filename handling to write files outside the intended upload directory (simulated).",
                "task_type": "simulation",
                "order": 5,
                "simulation_config": {
                    "type": "upload_path_traversal",
                    "scenario": "path_traversal",
                    "target_url": "/upload?path=",
                    "vulnerable_parameters": ["file", "path"],
                    "success_payload": "Upload a file with filename '../../secrets.txt' or set path to '../../secrets.txt' so server writes outside uploads folder (lab simulates file placement and reveals contents)",
                    "success_criteria": "Lab detects file written outside allowed directory and reveals simulated secret contents to the user",
                    "hints": [
                        "Try using ../ sequences in the filename or path parameter",
                        "Some servers normalize paths — try multiple ../ levels or URL-encoded traversal",
                        "The lab simulates file placement and reveals a safe example secret when successful",
                    ],
                    "difficulty": "advanced",
                },
            },
            {
                "name": "Secure File Upload Practices",
                "description": "Learn the defenses to properly secure file-upload functionality.",
                "task_type": "theory",
                "order": 6,
                "theory_content": """
                <h2>Secure File Upload Best Practices</h2>
                <ul>
                    <li>Whitelist file extensions and validate magic bytes</li>
                    <li>Generate server-side filenames and store outside document root</li>
                    <li>Use content-disposition headers and serve files via a proxy endpoint with authorization</li>
                    <li>Scan files with anti-malware solutions when possible</li>
                    <li>Limit upload size and rate-limit endpoints</li>
                </ul>

                <h3>Example secure storage flow</h3>
                <pre><code>
                filename = generate_random_token()
                save_path = os.path.join(PROTECTED_UPLOAD_DIR, filename)
                save_file(save_path, uploaded_file)
                provide_temporary_signed_url_for_download(filename)
                </code></pre>
                """,
                "mcq_question": "Which is NOT a recommended secure-upload practice?",
                "mcq_options": [
                    "A) Storing uploads outside the webroot and serving via a proxy",
                    "B) Validating magic bytes and not trusting Content-Type headers",
                    "C) Using original user-controlled filenames directly",
                    "D) Using randomized server-generated filenames",
                ],
                "correct_answer": "C",
            },
            {
                "name": "File Upload Challenge - Restricted Extensions",
                "description": "Advanced simulation: the server blocks .php and .jsp extensions. Find a simulated bypass allowed by the lab (e.g., double-extension or alternate parsing).",
                "task_type": "simulation",
                "order": 7,
                "simulation_config": {
                    "type": "upload_restricted_ext_bypass",
                    "scenario": "double_extension",
                    "target_url": "/upload",
                    "vulnerable_parameters": ["file"],
                    "success_payload": "Upload file named shell.php.jpg containing a simulated web shell (lab simulates vulnerable parsing where server treats as PHP)",
                    "success_criteria": "Lab accepts the file and returns simulated execution output when the attacker accesses the uploaded file",
                    "hints": [
                        "Try double extensions or tricky filenames the server might mis-handle",
                        "Experiment with content and headers — the lab simulates only a few bypass variants",
                        "This is an educational simulation; it won't execute real server commands",
                    ],
                    "difficulty": "advanced",
                },
            },
        ]

        for task_data in tasks_data:
            task, created = Tasks.objects.update_or_create(
                lab=upload_lab,
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

        upload_lab.update_total_tasks()
        self.stdout.write(
            self.style.SUCCESS(f"File Upload Vulnerabilities lab setup complete with {upload_lab.total_tasks} tasks")
        )
