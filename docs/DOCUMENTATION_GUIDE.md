# Documentation Guide

## Overview

This directory contains complete documentation for Event Face Detection MVP. All documentation is written in Markdown and maintained in version control.

## Files

| File | Purpose | Lines | Audience |
|------|---------|-------|----------|
| index.md | Documentation hub | 300+ | Everyone |
| codebase-summary.md | Architecture & modules | 255 | Developers |
| system-architecture.md | Technical design | 327 | Architects, Senior devs |
| code-standards.md | Development guide | 458 | All developers |
| project-overview-pdr.md | Requirements & specs | 436 | PMs, Tech leads |
| api-reference.md | API endpoints | 511 | Integration engineers |
| development-roadmap.md | Project timeline | 281 | Project managers |

**Total:** 2,568 lines | 72 KB

## Reading Order

**First time?** Start here:
1. README.md (root) — 5 min
2. docs/index.md — Choose your role
3. Role-specific docs

**For implementation?**
1. codebase-summary.md — Understand structure
2. code-standards.md — Learn patterns
3. project-overview-pdr.md — Understand requirements

**For API integration?**
1. api-reference.md — Copy examples

**For architecture?**
1. system-architecture.md — Learn design
2. codebase-summary.md — See components

## Quality Standards

All documentation meets these criteria:

- **Accurate:** Verified against actual code
- **Complete:** All components covered
- **Accessible:** Clear language, good structure
- **Actionable:** Ready-to-use examples
- **Maintainable:** Easy to update

## Maintenance

### Update Policy

Update documentation when:
- Code structure changes
- API endpoints change
- Configuration changes
- New dependencies added
- Architecture changes

### Format

- Use Markdown (.md)
- Max line length: 100 chars (for git diffs)
- Code blocks with syntax highlighting
- Tables for structured data
- Links for navigation
- Diagrams in ASCII or reference external

### Review

Before committing documentation:
- [ ] Links work (internal paths exist)
- [ ] Code examples are accurate
- [ ] No secrets or sensitive data
- [ ] Consistent terminology
- [ ] Proper markdown formatting

## Integration

### With Code

Documentation is version-controlled with code.
Update docs in same PR as code changes.

### With CI/CD

No CI validation yet. Recommendations:
- [ ] Markdown linting (markdownlint)
- [ ] Link validation
- [ ] Spell check

### With Team

- Share docs via README.md link
- Use index.md as team onboarding guide
- Reference in code review comments
- Update when designs change

## Structure Template

New documentation should follow:

```markdown
# Title

Brief one-line summary.

## Overview

1-2 paragraph explanation of purpose and scope.

## Table of Contents (if >1000 lines)

## Main Content

### Section 1
Content...

### Section 2
Content...

## Examples

Practical code examples.

## Related Topics

Links to other docs.

## Troubleshooting / FAQ

Common issues and solutions.
```

## Tools

### Viewing

- **IDE:** VS Code, GitHub, etc. (native Markdown support)
- **Hosting:** GitHub Pages, Netlify, or static server
- **Interactive:** OpenAPI/Swagger for API docs (future)

### Editing

- Any text editor (VS Code recommended)
- Git for version control
- Markdown preview extensions

### Validation

- Manual review of links
- Spell check tools (e.g., VS Code extension)
- Link checker (future CI/CD)

## FAQ

**Q: Where should I add new documentation?**
A: Start with index.md to see where it fits, then create in docs/ or update README.md.

**Q: How do I update existing docs?**
A: Edit the .md file, verify links/examples, commit with clear message.

**Q: Can I add diagrams?**
A: Yes! Use ASCII diagrams in Markdown, or link to external images in docs/images/ (future).

**Q: Who maintains documentation?**
A: All developers. Document as you build. Senior devs review in PRs.

**Q: How do I know what's outdated?**
A: Check "Last Updated" date. If >3 months old and there were code changes, likely outdated.

**Q: Should I document everything?**
A: No. Document the "why" and "how", not the "what" (code is self-documenting).

## See Also

- [README](../README.md) — Start here
- [Documentation Index](./index.md) — Hub
- [CLAUDE.md](../CLAUDE.md) — AI instructions
- [Code Standards](./code-standards.md) — Writing guidelines
