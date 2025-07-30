from django.core.management.base import BaseCommand

from website.models import Labs, TaskContent, Tasks


class Command(BaseCommand):
    help = "Creates SQL injection lab tasks with theory and simulation content"

    def handle(self, *args, **kwargs):
        try:
            sql_lab = Labs.objects.get(name="SQL Injection")
        except Labs.DoesNotExist:
            self.stdout.write(self.style.ERROR("SQL Injection lab not found. Please run create_initial_labs first."))
            return

        # Define the 10 SQL injection tasks
        tasks_data = [
            {
                "name": "Introduction to SQL Injection",
                "description": "Learn the basics of SQL injection vulnerabilities and how they occur.",
                "task_type": "theory",
                "order": 1,
                "theory_content": """
                <h2>What is SQL Injection?</h2>
                <p>SQL injection is a code injection technique that exploits a security vulnerability in an application's software. The vulnerability occurs when user input is either incorrectly filtered for string literal escape characters or user input is not strongly typed and unexpectedly executed.</p>
                
                <h3>How SQL Injection Works</h3>
                <p>SQL injection attacks work by inserting malicious SQL code into application queries. When the application executes these modified queries, it can result in:</p>
                <ul>
                    <li>Unauthorized access to data</li>
                    <li>Data theft or modification</li>
                    <li>Authentication bypass</li>
                    <li>Complete system compromise</li>
                </ul>
                
                <h3>Example Vulnerable Code</h3>
                <pre><code>
                String query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'";
                </code></pre>
                """,
                "mcq_question": "What makes an application vulnerable to SQL injection?",
                "mcq_options": [
                    "A) Improper input validation and sanitization",
                    "B) Using strong passwords",
                    "C) Having too many database tables",
                    "D) Using encrypted connections",
                ],
                "correct_answer": "A",
            },
            {
                "name": "Identifying SQL Injection Points",
                "description": "Learn how to identify potential SQL injection vulnerabilities in web applications.",
                "task_type": "theory",
                "order": 2,
                "theory_content": """
                <h2>Finding SQL Injection Vulnerabilities</h2>
                <p>SQL injection vulnerabilities can be found in various parts of web applications:</p>
                
                <h3>Common Injection Points</h3>
                <ul>
                    <li><strong>Login forms:</strong> Username and password fields</li>
                    <li><strong>Search boxes:</strong> Query parameters</li>
                    <li><strong>URL parameters:</strong> GET request parameters</li>
                    <li><strong>Form inputs:</strong> POST request data</li>
                    <li><strong>Cookies:</strong> Session data</li>
                    <li><strong>HTTP headers:</strong> User-Agent, Referer, etc.</li>
                </ul>
                
                <h3>Testing Techniques</h3>
                <p>Use these payloads to test for SQL injection:</p>
                <ul>
                    <li>Single quote (') - Look for database errors</li>
                    <li>Double quote (") - Alternative string delimiter</li>
                    <li>SQL comments (-- or /*) - Comment out rest of query</li>
                    <li>Boolean conditions (1=1, 1=2) - Test logic manipulation</li>
                </ul>
                """,
                "mcq_question": "Which of the following is NOT a common SQL injection testing payload?",
                "mcq_options": [
                    "A) Single quote (')",
                    "B) Boolean condition (1=1)",
                    "C) HTML tags (<script>)",
                    "D) SQL comment (--)",
                ],
                "correct_answer": "C",
            },
            {
                "name": "Basic SQL Injection - Login Bypass",
                "description": "Practice bypassing login authentication using SQL injection.",
                "task_type": "simulation",
                "order": 3,
                "simulation_config": {
                    "type": "login_bypass",
                    "scenario": "vulnerable_login",
                    "target_url": "/vulnerable-login",
                    "vulnerable_parameters": ["username", "password"],
                    "success_payload": "admin' --",
                    "hints": [
                        "Try using SQL comments to bypass password check",
                        "The application uses single quotes around the username",
                        "Remember that -- comments out the rest of the SQL query",
                    ],
                    "expected_result": "Successfully logged in as admin without knowing the password",
                },
            },
            {
                "name": "Union-Based SQL Injection",
                "description": "Learn about Union-based SQL injection attacks to extract data.",
                "task_type": "theory",
                "order": 4,
                "theory_content": """
                <h2>Union-Based SQL Injection</h2>
                <p>Union-based SQL injection is a technique that leverages the UNION SQL operator to combine the results of two or more SELECT statements into a single result.</p>
                
                <h3>Requirements for UNION Attacks</h3>
                <ul>
                    <li>Same number of columns in both SELECT statements</li>
                    <li>Compatible data types in corresponding columns</li>
                    <li>Application must display query results</li>
                </ul>
                
                <h3>Finding Column Count</h3>
                <p>Use ORDER BY to determine the number of columns:</p>
                <pre><code>
                ' ORDER BY 1--
                ' ORDER BY 2--
                ' ORDER BY 3--
                </code></pre>
                
                <h3>Union Attack Example</h3>
                <pre><code>
                ' UNION SELECT username, password FROM users--
                </code></pre>
                """,
                "mcq_question": "What is required for a successful UNION-based SQL injection?",
                "mcq_options": [
                    "A) The application must be written in PHP",
                    "B) Same number of columns and compatible data types",
                    "C) The database must be MySQL",
                    "D) The user must have admin privileges",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Union Attack - Data Extraction",
                "description": "Practice extracting sensitive data using Union-based SQL injection.",
                "task_type": "simulation",
                "order": 5,
                "simulation_config": {
                    "type": "union_injection",
                    "scenario": "data_extraction",
                    "target_url": "/vulnerable-search",
                    "vulnerable_parameters": ["search"],
                    "table_structure": {
                        "users": ["id", "username", "password", "email"],
                        "products": ["id", "name", "price", "description"],
                        "success_payload": "' UNION SELECT id, username, password, email FROM users--",
                    },
                    "success_criteria": "Extract all usernames and passwords from users table",
                    "hints": [
                        "First determine the number of columns using ORDER BY",
                        "Use UNION SELECT to combine with your malicious query",
                        "The original query selects 4 columns from products table",
                    ],
                },
            },
            {
                "name": "Boolean-Based Blind SQL Injection",
                "description": "Learn about blind SQL injection when no data is returned directly.",
                "task_type": "theory",
                "order": 6,
                "theory_content": """
                <h2>Boolean-Based Blind SQL Injection</h2>
                <p>Blind SQL injection occurs when an application is vulnerable to SQL injection but HTTP responses don't contain query results or database errors.</p>
                
                <h3>Characteristics</h3>
                <ul>
                    <li>No direct database output in response</li>
                    <li>Application behavior changes based on query truth</li>
                    <li>Requires inference techniques</li>
                    <li>Time-consuming but effective</li>
                </ul>
                
                <h3>Testing Technique</h3>
                <p>Use conditional statements to infer information:</p>
                <pre><code>
                ' AND 1=1--     (Should return normal response)
                ' AND 1=2--     (Should return different response)
                </code></pre>
                
                <h3>Data Extraction Example</h3>
                <pre><code>
                ' AND (SELECT SUBSTRING(username,1,1) FROM users WHERE id=1)='a'--
                </code></pre>
                """,
                "mcq_question": "In Boolean-based blind SQL injection, how do you extract data?",
                "mcq_options": [
                    "A) By reading error messages",
                    "B) By analyzing response differences for true/false conditions",
                    "C) By viewing database tables directly",
                    "D) By measuring response timing only",
                ],
                "correct_answer": "B",
            },
            {
                "name": "Blind SQL Injection - Character Extraction",
                "description": "Practice extracting data character by character using blind techniques.",
                "task_type": "simulation",
                "order": 7,
                "simulation_config": {
                    "type": "blind_injection",
                    "scenario": "character_extraction",
                    "target_url": "/vulnerable-profile",
                    "vulnerable_parameters": ["user_id"],
                    "blind_type": "boolean",
                    "target_data": "admin_password",
                    "success_payload": "' AND (SELECT SUBSTRING(password,1,1) FROM users WHERE username='admin')='p'--",
                    "success_criteria": "Extract the first 5 characters of admin password",
                    "hints": [
                        "Use AND conditions to test character values",
                        "Compare response content for true/false conditions",
                        "Use SUBSTRING or SUBSTR to extract individual characters",
                        "ASCII values can help with character comparison",
                    ],
                    "expected_approach": "Boolean-based character-by-character extraction",
                },
            },
            {
                "name": "Time-Based Blind SQL Injection",
                "description": "Learn about time-based blind SQL injection techniques.",
                "task_type": "theory",
                "order": 8,
                "theory_content": """
                <h2>Time-Based Blind SQL Injection</h2>
                <p>Time-based blind SQL injection is used when Boolean-based techniques don't work. It relies on injecting SQL queries that cause the database to wait for a specified amount of time.</p>
                
                <h3>Common Time Functions</h3>
                <ul>
                    <li><strong>MySQL:</strong> SLEEP(5)</li>
                    <li><strong>PostgreSQL:</strong> pg_sleep(5)</li>
                    <li><strong>SQL Server:</strong> WAITFOR DELAY '00:00:05'</li>
                    <li><strong>Oracle:</strong> dbms_pipe.receive_message(('a'),5)</li>
                </ul>
                
                <h3>Testing Example</h3>
                <pre><code>
                ' AND IF(1=1, SLEEP(5), 0)--
                ' AND IF((SELECT COUNT(*) FROM users)>5, SLEEP(5), 0)--
                </code></pre>
                
                <h3>Data Extraction</h3>
                <pre><code>
                ' AND IF((SELECT SUBSTRING(password,1,1) FROM users WHERE username='admin')='p', SLEEP(5), 0)--
                </code></pre>
                """,
                "mcq_question": "What is the main indicator of successful time-based SQL injection?",
                "mcq_options": [
                    "A) Error messages in the response",
                    "B) Changed content in the response",
                    "C) Increased response time",
                    "D) HTTP status code changes",
                ],
                "correct_answer": "C",
            },
            {
                "name": "Time-Based Attack Simulation",
                "description": "Practice time-based blind SQL injection to extract sensitive information.",
                "task_type": "simulation",
                "order": 9,
                "simulation_config": {
                    "type": "time_based_injection",
                    "scenario": "password_extraction",
                    "target_url": "/vulnerable-news",
                    "vulnerable_parameters": ["article_id"],
                    "database_type": "mysql",
                    "time_function": "SLEEP",
                    "target_data": "admin_password_length",
                    "success_payload": "' AND IF((SELECT LENGTH(password) FROM users WHERE username='admin')=8, SLEEP(5), 0)--",
                    "success_criteria": "Determine the length of admin password using time delays",
                    "hints": [
                        "Use SLEEP(5) to create time delays",
                        "Test different password lengths using LENGTH() function",
                        "Measure response times to detect successful conditions",
                        "A 5-second delay indicates a true condition",
                    ],
                },
            },
            {
                "name": "Advanced SQL Injection Prevention",
                "description": "Learn comprehensive strategies to prevent SQL injection attacks.",
                "task_type": "theory",
                "order": 10,
                "theory_content": """
                <h2>SQL Injection Prevention</h2>
                <p>Preventing SQL injection requires a multi-layered approach combining secure coding practices and proper application architecture.</p>
                
                <h3>Primary Defense: Prepared Statements</h3>
                <pre><code>
                // Secure example (Java)
                String query = "SELECT * FROM users WHERE username = ? AND password = ?";
                PreparedStatement stmt = connection.prepareStatement(query);
                stmt.setString(1, username);
                stmt.setString(2, password);
                </code></pre>
                
                <h3>Additional Defenses</h3>
                <ul>
                    <li><strong>Input validation:</strong> Whitelist allowed characters</li>
                    <li><strong>Stored procedures:</strong> When properly implemented</li>
                    <li><strong>Escaping:</strong> As a secondary defense</li>
                    <li><strong>Least privilege:</strong> Minimal database permissions</li>
                    <li><strong>WAF:</strong> Web Application Firewall</li>
                </ul>
                
                <h3>Best Practices</h3>
                <ul>
                    <li>Never trust user input</li>
                    <li>Use parameterized queries exclusively</li>
                    <li>Implement proper error handling</li>
                    <li>Regular security testing</li>
                    <li>Keep software updated</li>
                </ul>
                """,
                "mcq_question": "What is the most effective primary defense against SQL injection?",
                "mcq_options": [
                    "A) Input validation and filtering",
                    "B) Using a Web Application Firewall",
                    "C) Prepared statements with parameterized queries",
                    "D) Encrypting database connections",
                ],
                "correct_answer": "C",
            },
        ]

        # Create tasks and their content
        for task_data in tasks_data:
            task, created = Tasks.objects.get_or_create(
                lab=sql_lab,
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
                self.stdout.write(self.style.SUCCESS(f'Created content for: "{task.name}"'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated content for: "{task.name}"'))

        sql_lab.update_total_tasks()
        self.stdout.write(self.style.SUCCESS(f"Updated SQL Injection lab with {sql_lab.total_tasks} tasks"))
