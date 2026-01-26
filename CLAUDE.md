# CLAUDE.md - AI Assistant Guidelines for CODEAI

This document provides context and guidelines for AI assistants working on this codebase.

## Project Overview

**CODEAI** is a trial/learning project for video coding demonstrations. This repository serves as a starting foundation for development and educational purposes.

- **Repository**: Ruidadd/CODEAI
- **Purpose**: Trial for video coding demonstrations and learning
- **Status**: Initial setup - ready for development

## Current Codebase Structure

```
/home/user/CODEAI/
├── .git/           # Git version control
├── CLAUDE.md       # AI assistant guidelines (this file)
└── README.md       # Project description
```

This is currently a minimal repository. As the project grows, update this section to reflect the evolving structure.

## Development Environment

### Prerequisites

_To be defined as the project develops. Common requirements might include:_
- Node.js (version TBD)
- Package manager (npm/yarn/pnpm)
- Any language-specific runtimes

### Setup

_No setup steps required yet. Update this section when dependencies are added._

```bash
# Future setup commands will go here
# Example:
# npm install
# cp .env.example .env
```

## Common Commands

_No build or development scripts are configured yet. Update this section as scripts are added._

```bash
# Placeholder for future commands:
# npm run dev        # Start development server
# npm run build      # Build for production
# npm run test       # Run tests
# npm run lint       # Lint code
```

## Architecture

_Architecture documentation will be added as the project structure develops._

### Key Directories (Future)

| Directory | Purpose |
|-----------|---------|
| `src/` | Source code |
| `tests/` | Test files |
| `docs/` | Documentation |
| `config/` | Configuration files |

## Code Style and Conventions

### General Guidelines

1. **Keep it simple**: Prefer straightforward solutions over complex abstractions
2. **Be consistent**: Follow existing patterns in the codebase
3. **Document changes**: Update this file and README when adding significant features
4. **Test thoroughly**: Add tests for new functionality when testing is set up

### Naming Conventions

- Use descriptive, meaningful names
- Follow language-specific conventions (camelCase for JS/TS, snake_case for Python, etc.)
- Prefix private/internal items appropriately

### File Organization

- Group related files together
- Keep files focused on a single responsibility
- Use index files for clean exports when appropriate

## Git Workflow

### Branch Naming

- Feature branches: `feature/description`
- Bug fixes: `fix/description`
- AI assistant branches: `claude/session-id`

### Commit Messages

Write clear, descriptive commit messages:
- Use imperative mood ("Add feature" not "Added feature")
- Keep the first line under 72 characters
- Include context in the body when needed

```
feat: Add user authentication module

- Implement JWT-based auth
- Add login/logout endpoints
- Include password hashing
```

### Pull Requests

- Provide clear descriptions of changes
- Reference related issues
- Ensure all checks pass before merging

## Testing

_Testing framework not yet configured. Update this section when tests are added._

### Running Tests

```bash
# Placeholder
# npm test
# npm run test:coverage
```

### Writing Tests

- Place tests adjacent to source files or in a dedicated `tests/` directory
- Name test files with `.test.` or `.spec.` suffix
- Cover edge cases and error conditions

## Configuration

_No configuration files exist yet. Update this section as config is added._

### Environment Variables

```bash
# Example .env structure (when applicable):
# NODE_ENV=development
# API_URL=http://localhost:3000
# DATABASE_URL=...
```

## Dependencies

_No dependencies installed yet. Update this section when packages are added._

### Adding Dependencies

```bash
# Use exact versions for reproducibility
# npm install --save-exact package-name
```

## Troubleshooting

### Common Issues

_Document common issues and solutions as they arise._

| Issue | Solution |
|-------|----------|
| TBD | TBD |

## AI Assistant Notes

### When Working on This Repository

1. **Read before editing**: Always read files before making changes
2. **Incremental changes**: Make small, focused changes
3. **Update documentation**: Keep this file and README current
4. **Follow existing patterns**: Match the style of existing code
5. **Test changes**: Verify changes work before committing

### Things to Avoid

- Don't add unnecessary dependencies
- Don't over-engineer simple solutions
- Don't leave debug code or console logs
- Don't commit sensitive information (API keys, passwords)
- Don't make changes outside the scope of the request

### Useful Context

- This is a learning/demo project for video coding
- Keep changes well-documented for educational purposes
- Prioritize code clarity and readability

## Changelog

Track significant changes to the project structure:

| Date | Change | Notes |
|------|--------|-------|
| 2025-08-24 | Initial commit | Repository created with README |
| 2026-01-26 | Added CLAUDE.md | AI assistant guidelines established |

---

_Last updated: 2026-01-26_

_This document should be updated as the project evolves. When adding new features, technologies, or changing conventions, reflect those changes here._
