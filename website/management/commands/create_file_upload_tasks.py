from .base_lab_seeder import LabSeederCommand


class Command(LabSeederCommand):
    help = "Creates File Upload Vulnerabilities lab tasks"
    lab_name = "File Upload Vulnerabilities"

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
                "success_payload": "upload a file named shell.php containing '<?php echo shell_exec($_GET[\"cmd\"]); ?>'",
                "success_criteria": "Lab marks it as executable and returns simulated command output",
                "hints": [
                    "Try a .php file with a simple payload",
                    "Try double extensions like image.php.jpg",
                    "The lab simulates execution (no real system commands run)",
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
                "success_payload": "Upload file with .jpg extension but with embedded script content",
                "success_criteria": "Lab detects disguised malicious content",
                "hints": [
                    "Add PHP inside a .jpg",
                    "Try payload in EXIF or metadata (simulated)",
                ],
                "difficulty": "intermediate",
            },
        },
        {
            "name": "Simulation: Path Traversal via Filename",
            "description": "Exploit improper file path handling to write outside upload directory.",
            "task_type": "simulation",
            "order": 5,
            "simulation_config": {
                "type": "upload_path_traversal",
                "scenario": "path_traversal",
                "target_url": "/upload?path=",
                "vulnerable_parameters": ["file", "path"],
                "success_payload": "Use '../../secrets.txt' to simulate writing outside upload directory",
                "success_criteria": "Lab reveals simulated secret contents",
                "hints": [
                    "Try ../ sequences",
                    "Use URL-encoded traversal",
                ],
                "difficulty": "advanced",
            },
        },
        {
            "name": "Secure File Upload Practices",
            "description": "Learn secure practices for file upload systems.",
            "task_type": "theory",
            "order": 6,
            "theory_content": """
                <h2>Secure File Upload Best Practices</h2>
                <ul>
                    <li>Whitelist extensions + verify magic bytes</li>
                    <li>Store uploads outside web root</li>
                    <li>Generate server-side filenames</li>
                    <li>Use auth-protected file serving</li>
                    <li>Limit upload size</li>
                </ul>
            """,
            "mcq_question": "Which is NOT a recommended secure upload practice?",
            "mcq_options": [
                "A) Store uploads outside webroot",
                "B) Validate magic bytes",
                "C) Use user-controlled filenames directly",
                "D) Use server-generated filenames",
            ],
            "correct_answer": "C",
        },
        {
            "name": "File Upload Challenge - Restricted Extensions",
            "description": "Server blocks .php and .jsp — find a bypass.",
            "task_type": "simulation",
            "order": 7,
            "simulation_config": {
                "type": "upload_restricted_ext_bypass",
                "scenario": "double_extension",
                "target_url": "/upload",
                "vulnerable_parameters": ["file"],
                "success_payload": "shell.php.jpg",
                "success_criteria": "Lab simulates execution output from double-extension file",
                "hints": [
                    "Try double extensions",
                    "Try tricky filenames / mixed casing",
                ],
                "difficulty": "advanced",
            },
        },
    ]
