# GitHub Commands

OWASP BLT supports special commands that can be used in GitHub issue comments to automate various tasks. These commands are processed when they are entered as comments on issues.

## Available Commands

### `/plan`

The `/plan` command generates a structured action plan based on the issue's title and description. This can help break down complex issues into actionable tasks.

#### How to Use

1. Navigate to any issue in a repository that has the OWASP BLT GitHub app installed
2. Add a new comment with just the text `/plan`
3. The system will automatically generate a plan based on the issue content and post it as a reply

#### Example

If an issue is titled "Implement user authentication" with a description outlining requirements, commenting with `/plan` might generate:

```
## Action Plan

- [ ] Analyze requirements and create detailed specifications
- [ ] Design solution architecture
- [ ] Implement user registration functionality
- [ ] Implement login/logout functionality
- [ ] Add password reset capability
- [ ] Write tests for all authentication flows
- [ ] Review code and address feedback
```

#### Notes

- The plan is generated based on the content of the issue description
- If the issue description contains bullet points or structured sections, these will be included in the plan
- The generated plan is posted as a markdown checklist that can be used to track progress