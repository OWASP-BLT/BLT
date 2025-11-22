from django.core.management.base import BaseCommand

from website.models import Adventure, AdventureTask, Badge


class Command(BaseCommand):
    help = "Seeds the database with OWASP BLT Adventures"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding OWASP BLT Adventures...")

        adventures_data = [
            # OWASP Security Adventures
            {
                "title": "Secure the Fortress",
                "description": """Master web application security with OWASP ZAP and the Security Knowledge Framework.

This adventure will teach you how to identify and document common vulnerabilities, and suggest effective mitigations using industry best practices.

**OWASP Projects Used:**
- OWASP ZAP: https://owasp.org/www-project-zap/
- OWASP Security Knowledge Framework: https://owasp.org/www-project-security-knowledge-framework/""",
                "category": "owasp_security",
                "difficulty": "intermediate",
                "badge_emoji": "🛡️",
                "badge_title": "Fortress Defender",
                "estimated_time": "4-6 hours",
                "tasks": [
                    {
                        "title": "Scan a Vulnerable Application",
                        "description": "Use OWASP ZAP (https://owasp.org/www-project-zap/) to perform a comprehensive scan of a vulnerable web application. Download ZAP from https://www.zaproxy.org/download/\n\nSet up ZAP, configure the scan parameters, and execute a full automated scan. You can use OWASP WebGoat (https://owasp.org/www-project-webgoat/) or DVWA as test applications.",
                    },
                    {
                        "title": "Identify and Document 3 Vulnerabilities",
                        "description": "From your scan results, identify at least 3 distinct security vulnerabilities. Document each vulnerability with:\n- Vulnerability type\n- Risk level\n- Location in the application\n- Potential impact\n- Steps to reproduce",
                    },
                    {
                        "title": "Reference OWASP Security Knowledge Framework for Mitigations",
                        "description": "Using the OWASP Security Knowledge Framework (https://owasp.org/www-project-security-knowledge-framework/), research and document appropriate mitigation strategies for each of the 3 vulnerabilities you identified.\n\nAccess SKF at: https://www.securityknowledgeframework.org/",
                    },
                    {
                        "title": "Submit a Comprehensive Report",
                        "description": "Create and submit a detailed security assessment report that includes:\n- Executive summary\n- All identified vulnerabilities with evidence\n- Recommended mitigations from SKF\n- Remediation timeline suggestions\n\nShare your report via a blog post, GitHub gist, or document.",
                    },
                ],
            },
            {
                "title": "Break the Code",
                "description": """Dive deep into web application security by solving challenges in OWASP Juice Shop.

Learn about common vulnerabilities through hands-on exploitation and understand defensive strategies using OWASP Cheat Sheets.

**OWASP Projects Used:**
- OWASP Juice Shop: https://owasp.org/www-project-juice-shop/
- OWASP Cheat Sheet Series: https://owasp.org/www-project-cheat-sheets/""",
                "category": "owasp_security",
                "difficulty": "beginner",
                "badge_emoji": "🔓",
                "badge_title": "Code Breaker",
                "estimated_time": "6-8 hours",
                "tasks": [
                    {
                        "title": "Complete 5 Security Challenges in OWASP Juice Shop",
                        "description": "Set up OWASP Juice Shop (https://owasp.org/www-project-juice-shop/) locally and complete at least 5 security challenges. Install from: https://github.com/juice-shop/juice-shop\n\nFocus on different vulnerability types such as:\n- SQL Injection\n- XSS\n- Broken Authentication\n- Sensitive Data Exposure\n- Security Misconfiguration",
                    },
                    {
                        "title": "Explain Vulnerabilities Using OWASP Cheat Sheets",
                        "description": "For each of the 5 challenges you solved, reference the relevant OWASP Cheat Sheet (https://cheatsheetseries.owasp.org/) to explain:\n- The vulnerability type\n- How it works\n- Why it's dangerous\n- How to prevent it\n\nCreate a write-up or blog post with your explanations.",
                    },
                    {
                        "title": "Propose a New Challenge for Juice Shop",
                        "description": "Create a pull request to the OWASP Juice Shop repository (https://github.com/juice-shop/juice-shop) with:\n- A new challenge idea\n- Description of the vulnerability\n- Suggested difficulty level\n- Implementation approach\n\nEven if not merged, this demonstrates your understanding!",
                    },
                ],
            },
            {
                "title": "Cryptography Conundrum",
                "description": """Master cryptographic security practices by auditing applications against OWASP ASVS standards.

Learn to identify weak cryptographic implementations and apply industry-standard fixes.

**OWASP Projects Used:**
- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- OWASP Cryptographic Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html""",
                "category": "owasp_security",
                "difficulty": "advanced",
                "badge_emoji": "🔐",
                "badge_title": "Crypto Custodian",
                "estimated_time": "5-7 hours",
                "tasks": [
                    {
                        "title": "Audit Application Against ASVS Cryptographic Requirements",
                        "description": "Select a sample application (or create one) and audit it against the OWASP ASVS (https://owasp.org/www-project-application-security-verification-standard/) cryptographic requirements from Section V6. Download ASVS from: https://github.com/OWASP/ASVS\n\nDocument:\n- Which ASVS requirements are met\n- Which requirements are not met\n- Specific gaps in cryptographic implementation",
                    },
                    {
                        "title": "Implement Cryptographic Improvements",
                        "description": "Based on your audit and the OWASP Cryptographic Storage Cheat Sheet (https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html), implement improvements such as:\n- Strong encryption algorithms\n- Proper key management\n- Secure random number generation\n- Password hashing with bcrypt/Argon2\n\nSubmit your code changes as a pull request or GitHub repository.",
                    },
                    {
                        "title": "Write a Summary or Blog Post",
                        "description": "Document your findings and improvements in a detailed write-up that includes:\n- Initial vulnerabilities found\n- Cryptographic best practices applied\n- Before and after comparison\n- Lessons learned\n\nPublish as a blog post or technical document.",
                    },
                ],
            },
            {
                "title": "APIs Under Fire",
                "description": """Secure modern APIs by testing against the OWASP API Security Top 10.

Learn to identify API-specific vulnerabilities and implement robust security controls.

**OWASP Projects Used:**
- OWASP API Security Project: https://owasp.org/www-project-api-security/
- OWASP ZAP: https://owasp.org/www-project-zap/""",
                "category": "owasp_security",
                "difficulty": "intermediate",
                "badge_emoji": "📡",
                "badge_title": "API Defender",
                "estimated_time": "4-6 hours",
                "tasks": [
                    {
                        "title": "Scan API Endpoints with OWASP ZAP",
                        "description": "Use OWASP ZAP (https://www.zaproxy.org/) to scan and test API endpoints. Configure ZAP for API testing and perform:\n- Authentication testing\n- Authorization testing\n- Input validation testing\n- Rate limiting checks",
                    },
                    {
                        "title": "Test for OWASP API Security Top 10 Vulnerabilities",
                        "description": "Systematically test the API for vulnerabilities from the OWASP API Security Top 10 (https://owasp.org/API-Security/editions/2023/en/0x11-t10/), including:\n- Broken Object Level Authorization\n- Broken Authentication\n- Excessive Data Exposure\n- Lack of Resources & Rate Limiting\n- Broken Function Level Authorization\n\nDocument your findings with evidence.",
                    },
                    {
                        "title": "Document Remediation Strategies",
                        "description": "For each vulnerability found, suggest specific remediation strategies based on OWASP guidance. Create a detailed report with:\n- Vulnerability descriptions\n- Proof of concept\n- Risk assessment\n- Remediation steps\n- Code examples where applicable",
                    },
                ],
            },
            {
                "title": "Hunting Secrets",
                "description": """Identify and fix vulnerable dependencies in open source projects.

Master dependency analysis and vulnerability management using OWASP Dependency-Check.

**OWASP Projects Used:**
- OWASP Dependency-Check: https://owasp.org/www-project-dependency-check/
- OWASP Top 10: https://owasp.org/www-project-top-ten/""",
                "category": "owasp_security",
                "difficulty": "intermediate",
                "badge_emoji": "🔍",
                "badge_title": "Vulnerability Hunter",
                "estimated_time": "3-5 hours",
                "tasks": [
                    {
                        "title": "Run OWASP Dependency-Check on a Project",
                        "description": "Select an open source project and run OWASP Dependency-Check (https://owasp.org/www-project-dependency-check/) to identify vulnerable dependencies. Download from: https://github.com/jeremylong/DependencyCheck/releases\n\nGenerate a comprehensive report showing:\n- All dependencies scanned\n- Vulnerabilities found\n- CVE details\n- Severity levels",
                    },
                    {
                        "title": "Map Findings to OWASP Top 10",
                        "description": "Analyze the vulnerabilities found and map them to relevant OWASP Top 10 (https://owasp.org/Top10/) categories. Create a document explaining:\n- Which vulnerabilities map to which OWASP Top 10 items\n- The risk they pose\n- Priority for remediation",
                    },
                    {
                        "title": "Fix a Vulnerability via Pull Request",
                        "description": "Select one identified vulnerability and create a pull request to fix it. Your PR should include:\n- Updated dependency versions\n- Testing to ensure no breaking changes\n- Documentation of the fix\n- Reference to the CVE",
                    },
                ],
            },
            {
                "title": "Threat Modeling Journey",
                "description": """Learn systematic threat modeling using OWASP Threat Dragon.

Identify security risks early in the development lifecycle and validate against ASVS standards.

**OWASP Projects Used:**
- OWASP Threat Dragon: https://owasp.org/www-project-threat-dragon/
- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/""",
                "category": "owasp_security",
                "difficulty": "advanced",
                "badge_emoji": "🌐",
                "badge_title": "Threat Architect",
                "estimated_time": "6-8 hours",
                "tasks": [
                    {
                        "title": "Create a Threat Model with OWASP Threat Dragon",
                        "description": "Use OWASP Threat Dragon (https://owasp.org/www-project-threat-dragon/) to create a comprehensive threat model for a sample application. Access the tool at: https://www.threatdragon.com/ or download from GitHub: https://github.com/OWASP/threat-dragon\n\nInclude:\n- System architecture diagram\n- Trust boundaries\n- Data flows\n- Identified threats using STRIDE\n- Mitigation strategies",
                    },
                    {
                        "title": "Perform Gap Analysis Using OWASP ASVS",
                        "description": "Evaluate your application against OWASP ASVS requirements (https://github.com/OWASP/ASVS). Document:\n- Current security controls\n- ASVS requirements not met\n- Risk assessment for each gap\n- Recommended improvements",
                    },
                    {
                        "title": "Present to the Community",
                        "description": "Share your threat model with the security community. This could be:\n- A presentation at a local security meetup\n- A detailed blog post or video\n- A workshop or training session\n- A pull request adding threat modeling to an OSS project\n\nProvide evidence of your community engagement.",
                    },
                ],
            },
            {
                "title": "Secure the CI/CD Pipeline",
                "description": """Integrate security into your development workflow.

Build a secure CI/CD pipeline with automated security testing using OWASP tools.

**OWASP Projects Used:**
- OWASP ZAP: https://owasp.org/www-project-zap/
- OWASP DevSecOps Guideline: https://owasp.org/www-project-devsecops-guideline/""",
                "category": "owasp_security",
                "difficulty": "advanced",
                "badge_emoji": "🏗️",
                "badge_title": "Pipeline Protector",
                "estimated_time": "5-7 hours",
                "tasks": [
                    {
                        "title": "Integrate OWASP ZAP into CI/CD Pipeline",
                        "description": "Set up OWASP ZAP (https://www.zaproxy.org/) in a CI/CD pipeline (GitHub Actions, GitLab CI, Jenkins, etc.). Use the official ZAP Docker images: https://www.zaproxy.org/docs/docker/\n\nConfigure:\n- Automated baseline scans\n- Full scans on branches\n- Scan result reporting\n- Build failure on critical findings",
                    },
                    {
                        "title": "Run and Document Automated Scans",
                        "description": "Execute multiple builds with automated security scans. Document:\n- Scan configurations used\n- Vulnerabilities detected\n- False positives identified\n- Time impact on build process\n- Scan result trends over time",
                    },
                    {
                        "title": "Apply OWASP DevSecOps Guidelines",
                        "description": "Implement additional security controls based on OWASP DevSecOps guidelines (https://owasp.org/www-project-devsecops-guideline/):\n- Dependency scanning (OWASP Dependency-Check)\n- Secret detection\n- SAST tools\n- Container security scanning\n- Security gates in deployment\n\nProvide configuration files and documentation.",
                    },
                ],
            },
            {
                "title": "Web Crawler Challenge",
                "description": """Master web application reconnaissance and testing.

Use OWASP ZAP's spidering capabilities combined with systematic testing methodologies.

**OWASP Projects Used:**
- OWASP ZAP: https://owasp.org/www-project-zap/
- OWASP Web Security Testing Guide: https://owasp.org/www-project-web-security-testing-guide/""",
                "category": "owasp_security",
                "difficulty": "beginner",
                "badge_emoji": "🕸️",
                "badge_title": "Web Explorer",
                "estimated_time": "3-4 hours",
                "tasks": [
                    {
                        "title": "Spider a Web Application with OWASP ZAP",
                        "description": "Use OWASP ZAP's (https://www.zaproxy.org/) spidering feature to comprehensively map a web application. Configure and run:\n- Traditional spider\n- Ajax spider for modern applications\n- Authenticated spidering\n\nExport and document the site map.",
                    },
                    {
                        "title": "Apply OWASP Web Security Testing Guide Tests",
                        "description": "Using the OWASP Web Security Testing Guide (https://owasp.org/www-project-web-security-testing-guide/), perform manual tests on the discovered endpoints. Download the guide: https://github.com/OWASP/wstg/releases\n\nFocus on:\n- Input validation\n- Authentication mechanisms\n- Session management\n- Access controls\n- Business logic\n\nDocument your testing methodology and findings.",
                    },
                    {
                        "title": "Report and Fix an Issue",
                        "description": "Identify at least one security issue from your testing:\n- Create a detailed vulnerability report\n- If testing your own application, fix the issue\n- If testing with permission, responsibly disclose\n- Document the full process from discovery to resolution",
                    },
                ],
            },
            {
                "title": "Privacy Shield",
                "description": """Protect user privacy through comprehensive privacy risk assessment.

Implement privacy controls and secure headers based on OWASP recommendations.

**OWASP Projects Used:**
- OWASP Top 10 Privacy Risks: https://owasp.org/www-project-top-10-privacy-risks/
- OWASP Secure Headers Project: https://owasp.org/www-project-secure-headers/""",
                "category": "owasp_security",
                "difficulty": "intermediate",
                "badge_emoji": "🔒",
                "badge_title": "Privacy Protector",
                "estimated_time": "4-5 hours",
                "tasks": [
                    {
                        "title": "Audit Website for Privacy Risks",
                        "description": "Use the OWASP Top 10 Privacy Risks Project (https://owasp.org/www-project-top-10-privacy-risks/) methodology to audit a website. Identify:\n- Personal data collection points\n- Data storage locations\n- Third-party data sharing\n- Privacy policy compliance\n- GDPR/CCPA considerations",
                    },
                    {
                        "title": "Implement Secure Headers",
                        "description": "Based on the OWASP Secure Headers Project (https://owasp.org/www-project-secure-headers/), implement recommended security headers:\n- Content-Security-Policy\n- Strict-Transport-Security\n- X-Frame-Options\n- X-Content-Type-Options\n- Referrer-Policy\n- Permissions-Policy\n\nProvide configuration and code changes.",
                    },
                    {
                        "title": "Demonstrate Improvements with Before/After Scans",
                        "description": "Use security header analysis tools to scan the website before and after implementing changes. Document:\n- Initial header configuration and security score\n- Changes made\n- Final header configuration and security score\n- Improvement metrics and impact",
                    },
                ],
            },
            {
                "title": "Mobile Security Odyssey",
                "description": """Secure mobile applications using OWASP mobile security resources.

Test mobile apps against the Mobile Application Security Verification Standard.

**OWASP Projects Used:**
- OWASP Mobile Security Testing Guide: https://owasp.org/www-project-mobile-security-testing-guide/
- OWASP MASVS: https://owasp.org/www-project-mobile-app-security/""",
                "category": "owasp_security",
                "difficulty": "advanced",
                "badge_emoji": "📱",
                "badge_title": "Mobile Defender",
                "estimated_time": "8-10 hours",
                "tasks": [
                    {
                        "title": "Perform Mobile Security Tests",
                        "description": "Using the OWASP Mobile Security Testing Guide (https://owasp.org/www-project-mobile-security-testing-guide/), perform security testing on a mobile application. Access the guide: https://mobile-security.gitbook.io/mobile-security-testing-guide/\n\nTest for:\n- Insecure data storage\n- Weak cryptography\n- Insecure communication\n- Authentication/authorization issues\n- Code quality issues\n- Reverse engineering protections\n\nDocument your testing setup and methodology.",
                    },
                    {
                        "title": "Cross-Reference with OWASP MASVS",
                        "description": "Map your findings to the OWASP Mobile Application Security Verification Standard (https://github.com/OWASP/owasp-masvs). Create a compliance report showing:\n- MASVS requirements tested\n- Pass/fail status for each requirement\n- Evidence for findings\n- Risk assessment",
                    },
                    {
                        "title": "Propose Fixes for Vulnerabilities",
                        "description": "For at least one identified vulnerability, propose a detailed fix including:\n- Root cause analysis\n- Proof of concept exploitation\n- Recommended remediation with code examples\n- Testing procedures to verify the fix\n\nIf possible, implement the fix and submit as a PR.",
                    },
                ],
            },
            # Broader Open-Source Coding Adventures
            {
                "title": "Bug Fixer's Path",
                "description": """Start your open source contribution journey.

Find, fix, and test bugs in open source projects while learning collaborative development practices.""",
                "category": "open_source",
                "difficulty": "beginner",
                "badge_emoji": "🛠️",
                "badge_title": "Bug Fixer",
                "estimated_time": "3-5 hours",
                "tasks": [
                    {
                        "title": "Find a Good First Issue",
                        "description": "Find an open source project with issues labeled 'good first issue' or 'help wanted'. Look for:\n- Active maintainers\n- Clear contribution guidelines\n- Welcoming community\n- Technology you're comfortable with\n\nComment on the issue to claim it and understand requirements.",
                    },
                    {
                        "title": "Fix the Bug and Submit a Pull Request",
                        "description": "Review the code, identify the bug, and implement a fix. Your PR should include:\n- Clear description of the bug\n- Explanation of your fix\n- Any relevant discussion or research\n- Following project code style and conventions",
                    },
                    {
                        "title": "Write Test Cases",
                        "description": "Add test cases to verify your fix and prevent regression. Include:\n- Unit tests for the specific bug\n- Integration tests if applicable\n- Documentation of test scenarios\n- Ensure all existing tests still pass",
                    },
                ],
            },
            {
                "title": "Secure the Dependencies",
                "description": """Improve open source security by managing dependencies.

Identify outdated and vulnerable dependencies, update them safely, and submit improvements.""",
                "category": "open_source",
                "difficulty": "intermediate",
                "badge_emoji": "🔍",
                "badge_title": "Dependency Defender",
                "estimated_time": "3-4 hours",
                "tasks": [
                    {
                        "title": "Run Dependency Scanner on a Project",
                        "description": "Use a dependency scanner (OWASP Dependency-Check, Snyk, npm audit, etc.) on an open source project. Generate a report showing:\n- All dependencies analyzed\n- Outdated dependencies\n- Known vulnerabilities (CVEs)\n- Severity levels\n- Recommended updates",
                    },
                    {
                        "title": "Identify and Update Vulnerable Dependencies",
                        "description": "Research the vulnerable dependencies found. For each:\n- Check if updates are available\n- Review breaking changes in changelogs\n- Test the application with updated dependencies\n- Verify no functionality is broken",
                    },
                    {
                        "title": "Submit Pull Request with Updates",
                        "description": "Create a comprehensive PR that includes:\n- Updated dependency versions\n- Summary of security improvements\n- Testing results\n- Any code changes needed for compatibility\n- Documentation updates if required",
                    },
                ],
            },
            {
                "title": "Refactor Hero",
                "description": """Improve code quality through strategic refactoring.

Tackle technical debt, improve maintainability, and enhance code performance.""",
                "category": "open_source",
                "difficulty": "intermediate",
                "badge_emoji": "🌀",
                "badge_title": "Refactor Hero",
                "estimated_time": "5-7 hours",
                "tasks": [
                    {
                        "title": "Identify Technical Debt",
                        "description": "Find an open source project with identified technical debt (code smells, deprecated patterns, etc.). Document:\n- Areas needing refactoring\n- Impact on maintainability\n- Potential risks of refactoring\n- Benefits of improvements",
                    },
                    {
                        "title": "Refactor and Improve Code",
                        "description": "Perform a refactoring that improves performance, readability, or maintainability. Focus on:\n- Extracting complex functions\n- Removing code duplication\n- Applying design patterns\n- Improving naming and structure\n- Optimizing algorithms\n\nEnsure backward compatibility where needed.",
                    },
                    {
                        "title": "Document Changes and Benefits",
                        "description": "Create comprehensive documentation of your refactoring:\n- Before/after code comparison\n- Performance metrics if applicable\n- Benefits to maintainability\n- How changes enhance the project\n- Migration guide if APIs changed\n\nSubmit as a PR with detailed description.",
                    },
                ],
            },
            {
                "title": "Internationalization Expert",
                "description": """Make software accessible worldwide.

Add internationalization support and contribute translations to open source projects.""",
                "category": "open_source",
                "difficulty": "beginner",
                "badge_emoji": "🌍",
                "badge_title": "i18n Champion",
                "estimated_time": "4-6 hours",
                "tasks": [
                    {
                        "title": "Find Project Needing i18n Support",
                        "description": "Identify an open source project lacking internationalization support. Evaluate:\n- Current state of localization\n- User interface strings\n- Hardcoded text\n- Date, number, and currency formatting\n- Community interest in i18n",
                    },
                    {
                        "title": "Add Internationalization Support",
                        "description": "Implement i18n infrastructure for one or more languages:\n- Extract hardcoded strings to resource files\n- Implement i18n framework (gettext, i18next, etc.)\n- Add locale handling\n- Provide translations for at least one language\n- Handle pluralization and formatting",
                    },
                    {
                        "title": "Submit PR and Collaborate with Maintainers",
                        "description": "Create a detailed pull request that includes:\n- i18n implementation\n- Translation files\n- Documentation on adding new languages\n- Examples of usage\n- Migration guide for developers\n\nWork with maintainers to integrate the changes.",
                    },
                ],
            },
            {
                "title": "Performance Booster",
                "description": """Optimize application performance.

Profile applications, identify bottlenecks, and implement measurable performance improvements.""",
                "category": "open_source",
                "difficulty": "advanced",
                "badge_emoji": "⚡",
                "badge_title": "Performance Booster",
                "estimated_time": "6-8 hours",
                "tasks": [
                    {
                        "title": "Profile Application for Bottlenecks",
                        "description": "Use profiling tools (Chrome DevTools, Lighthouse, cProfile, etc.) to analyze an open source project. Document:\n- Performance metrics collected\n- Identified bottlenecks\n- Resource-heavy functions or components\n- Load time analysis\n- Memory usage patterns",
                    },
                    {
                        "title": "Optimize Performance Bottleneck",
                        "description": "Implement optimization for at least one identified bottleneck:\n- Optimize algorithms (Big O improvements)\n- Add caching where appropriate\n- Lazy loading or code splitting\n- Database query optimization\n- Asset optimization\n- Reduce bundle size",
                    },
                    {
                        "title": "Validate and Share Improvements",
                        "description": "Measure and document performance improvements:\n- Before and after metrics\n- Percentage improvements\n- Testing methodology\n- Trade-offs considered\n- Recommendations for further optimization\n\nSubmit PR with performance analysis report.",
                    },
                ],
            },
            {
                "title": "Open Source Tester",
                "description": """Improve software quality through testing.

Add comprehensive test coverage to open source projects and enhance testing infrastructure.""",
                "category": "open_source",
                "difficulty": "intermediate",
                "badge_emoji": "🧪",
                "badge_title": "Testing Prodigy",
                "estimated_time": "5-7 hours",
                "tasks": [
                    {
                        "title": "Find Project with Insufficient Test Coverage",
                        "description": "Identify an open source project needing better test coverage. Analyze:\n- Current test coverage percentage\n- Untested critical paths\n- Missing test types (unit, integration, e2e)\n- Testing infrastructure present\n- Areas most in need of tests",
                    },
                    {
                        "title": "Write and Submit Test Cases",
                        "description": "Add comprehensive test cases to improve coverage:\n- Unit tests for individual functions/methods\n- Integration tests for component interactions\n- End-to-end tests for user workflows\n- Edge cases and error conditions\n- Follow project's testing conventions\n\nAim for meaningful coverage improvement (10%+).",
                    },
                    {
                        "title": "Run Tests and Submit Results",
                        "description": "Execute all tests and document results:\n- Coverage report before and after\n- All tests passing\n- Test execution time\n- Any bugs discovered during testing\n- Suggestions for improving testing infrastructure\n\nSubmit PR with comprehensive test documentation.",
                    },
                ],
            },
            {
                "title": "Documentation Maven",
                "description": """Make projects more accessible through excellent documentation.

Write clear, comprehensive documentation that helps users and contributors.""",
                "category": "open_source",
                "difficulty": "beginner",
                "badge_emoji": "📘",
                "badge_title": "Documentation Maven",
                "estimated_time": "4-6 hours",
                "tasks": [
                    {
                        "title": "Find Project with Documentation Gaps",
                        "description": "Identify an open source project with outdated or incomplete documentation. Look for:\n- Missing or outdated README\n- Lack of API documentation\n- No contribution guidelines\n- Missing examples or tutorials\n- Unclear setup instructions\n- Outdated screenshots or references",
                    },
                    {
                        "title": "Write or Update Documentation",
                        "description": "Create comprehensive documentation improvements:\n- Clear README with project overview\n- Step-by-step installation guide\n- Usage examples and tutorials\n- API documentation with examples\n- Troubleshooting section\n- Screenshots and diagrams where helpful\n- Links to additional resources",
                    },
                    {
                        "title": "Propose Additional Improvements",
                        "description": "Suggest and document additional documentation enhancements:\n- Contributing guidelines\n- Code of conduct\n- Architecture documentation\n- FAQ section\n- Video tutorials\n- Interactive examples\n\nSubmit PR with documentation updates and improvement suggestions.",
                    },
                ],
            },
            {
                "title": "Secure by Default",
                "description": """Improve security posture of open source projects.

Implement secure defaults and security features that protect users.""",
                "category": "open_source",
                "difficulty": "intermediate",
                "badge_emoji": "🔒",
                "badge_title": "Security Advocate",
                "estimated_time": "4-6 hours",
                "tasks": [
                    {
                        "title": "Identify Security Misconfiguration or Missing Feature",
                        "description": "Find a security gap in an open source project:\n- Insecure default configurations\n- Missing HTTPS enforcement\n- Absent security headers\n- Weak input validation\n- Insufficient authentication\n- Missing rate limiting\n\nDocument the security risk and impact.",
                    },
                    {
                        "title": "Implement Secure Default Configuration",
                        "description": "Add or improve security features:\n- Enable HTTPS by default\n- Add security headers\n- Implement input validation\n- Add authentication/authorization\n- Enable security logging\n- Add security configuration examples\n\nEnsure backward compatibility where needed.",
                    },
                    {
                        "title": "Submit PR with Security Benefits Explanation",
                        "description": "Create a detailed pull request that includes:\n- Description of security improvement\n- Benefits to users\n- Configuration examples\n- Security testing performed\n- Documentation updates\n- Migration guide if needed\n\nExplain why security by default matters.",
                    },
                ],
            },
            {
                "title": "Accessibility Guru",
                "description": """Make software accessible to everyone.

Audit and fix accessibility issues to ensure inclusive user experiences.""",
                "category": "open_source",
                "difficulty": "intermediate",
                "badge_emoji": "🧑‍🦽",
                "badge_title": "Accessibility Guru",
                "estimated_time": "5-7 hours",
                "tasks": [
                    {
                        "title": "Audit for Accessibility Issues",
                        "description": "Use accessibility tools (Lighthouse, Axe, WAVE, screen readers) to audit a project. Check for:\n- Proper heading hierarchy\n- Alt text for images\n- ARIA labels and roles\n- Keyboard navigation\n- Color contrast ratios\n- Form label associations\n- Focus indicators\n- Screen reader compatibility",
                    },
                    {
                        "title": "Fix Accessibility Issue",
                        "description": "Implement at least one accessibility improvement:\n- Add proper ARIA attributes\n- Fix heading hierarchy\n- Improve color contrast\n- Enable keyboard navigation\n- Add alt text to images\n- Improve form accessibility\n- Add focus indicators\n- Fix tab order",
                    },
                    {
                        "title": "Document Usability Improvements",
                        "description": "Create comprehensive documentation showing:\n- Accessibility issues found (with screenshots)\n- Standards violated (WCAG criteria)\n- Fixes implemented\n- Before/after comparison\n- Testing methodology\n- How improvements help users with disabilities\n\nSubmit PR with accessibility documentation.",
                    },
                ],
            },
            {
                "title": "Open-Source Mentor",
                "description": """Give back to the community by helping others.

Guide newcomers through their first contributions and share your knowledge.""",
                "category": "open_source",
                "difficulty": "intermediate",
                "badge_emoji": "🤝",
                "badge_title": "Open Source Mentor",
                "estimated_time": "6-10 hours (spread over time)",
                "tasks": [
                    {
                        "title": "Help Newcomers in Community Forums",
                        "description": "Actively participate in helping newcomers navigate an open source project:\n- Answer questions in issues/discussions\n- Help in Discord/Slack channels\n- Explain project structure and conventions\n- Guide through setup problems\n- Clarify contribution guidelines\n\nProvide links to at least 5 instances of helping others.",
                    },
                    {
                        "title": "Pair with a Newcomer on Their First Contribution",
                        "description": "Actively mentor someone through their first contribution:\n- Help them set up development environment\n- Guide them in selecting an appropriate issue\n- Review their code and provide constructive feedback\n- Explain project conventions and best practices\n- Celebrate their success\n\nDocument the mentoring experience.",
                    },
                    {
                        "title": "Document and Share Mentoring Tips",
                        "description": "Create a resource to help future contributors:\n- Write a 'First Contribution Guide' for the project\n- Create a video walkthrough of making a contribution\n- Document common pitfalls and solutions\n- Share tips for successful collaboration\n- Explain how to get unstuck\n\nShare your mentoring guide publicly (blog, video, PR).",
                    },
                ],
            },
        ]

        # Create adventures
        for adventure_data in adventures_data:
            tasks_data = adventure_data.pop("tasks")

            adventure, created = Adventure.objects.update_or_create(
                title=adventure_data["title"],
                defaults=adventure_data,
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created adventure: {adventure.title}"))

                # Create tasks for the adventure
                for i, task_data in enumerate(tasks_data, start=1):
                    task_data["order"] = i
                    AdventureTask.objects.create(adventure=adventure, **task_data)
                    self.stdout.write(f"  - Added task {i}: {task_data['title']}")

                # Create badge if it doesn't exist
                Badge.objects.get_or_create(
                    title=adventure.badge_title,
                    defaults={
                        "description": f"Earned by completing the {adventure.title} adventure",
                        "type": "manual",
                    },
                )
            else:
                self.stdout.write(self.style.WARNING(f"Adventure already exists: {adventure.title}"))

        self.stdout.write(self.style.SUCCESS("\nSuccessfully seeded adventures!"))
        self.stdout.write(f"Total adventures: {Adventure.objects.count()}")
        self.stdout.write(f"Total tasks: {AdventureTask.objects.count()}")
