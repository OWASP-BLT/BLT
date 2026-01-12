# Path-Specific Copilot Instructions

This directory contains path-specific instructions for GitHub Copilot coding agent. These instructions provide targeted guidance for different parts of the codebase.

## Structure

- **frontend.instructions.md** - Instructions for HTML templates, JavaScript, and CSS files
  - Applies to: `website/templates/**/*.html`, `website/static/**/*.js`, `website/static/**/*.css`
  - Focus: Tailwind CSS, template best practices, JavaScript organization

- **backend.instructions.md** - Instructions for Django backend code
  - Applies to: `website/**/*.py`, `blt/**/*.py` (excluding tests and migrations)
  - Focus: Django views, models, security, API development, code quality

- **tests.instructions.md** - Instructions for test files
  - Applies to: `website/tests/**/*.py`, `**/test_*.py`
  - Focus: Test structure, performance, best practices, common patterns

## How Path-Specific Instructions Work

Each instruction file has YAML frontmatter with an `applyTo` field that specifies glob patterns. GitHub Copilot will apply these instructions when working with files that match the patterns.

### Example

```yaml
---
applyTo: 
  - "website/templates/**/*.html"
  - "website/static/**/*.js"
---
```

### Glob Pattern Syntax

- `*` - Matches any characters within a path segment
- `**` - Matches any characters across multiple path segments
- `!pattern` - Excludes files matching the pattern

## Benefits

1. **Contextual Guidance** - Copilot receives specific instructions relevant to the type of file being edited
2. **Reduced Noise** - Frontend developers don't see backend-specific rules and vice versa
3. **Better Specialization** - More detailed guidance for specific domains
4. **Maintainability** - Easier to update instructions for specific areas without affecting others

## Parent Instructions

The main `.github/copilot-instructions.md` file contains general instructions that apply to the entire repository. Path-specific instructions supplement (not replace) the main instructions.

## Adding New Instructions

To add new path-specific instructions:

1. Create a new `.instructions.md` file in this directory
2. Add YAML frontmatter with `applyTo` glob patterns
3. Write clear, actionable instructions for that specific context
4. Document the new file in this README

## References

- [GitHub Copilot Custom Instructions Documentation](https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
- [Main Copilot Instructions](../copilot-instructions.md)
- [Contributing Guide](../../CONTRIBUTING.md)
