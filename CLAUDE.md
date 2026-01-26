# CLAUDE.md - AI Assistant Guidelines for CODEAI

This document provides guidance for AI assistants (like Claude) working on the CODEAI project.

## Project Overview

**CODEAI** is a project focused on video coding experimentation. The repository is in its initial setup phase and is ready for development.

### Current State
- **Status**: New project, initial setup phase
- **Structure**: Minimal - only README.md exists
- **Technology Stack**: Not yet established

## Repository Structure

```
CODEAI/
├── README.md          # Project description
├── CLAUDE.md          # AI assistant guidelines (this file)
└── .git/              # Git version control
```

As the project grows, the following structure is recommended:
```
CODEAI/
├── src/               # Source code
├── tests/             # Test files
├── docs/              # Documentation
├── scripts/           # Build and utility scripts
├── config/            # Configuration files
├── README.md
├── CLAUDE.md
├── .gitignore
└── package.json / pyproject.toml / Cargo.toml (depending on stack)
```

## Development Workflow

### Git Practices
- **Main Branch**: Use for stable, production-ready code
- **Feature Branches**: Use `feature/<name>` for new features
- **Bug Fix Branches**: Use `fix/<name>` for bug fixes
- **Claude Branches**: AI-generated work uses `claude/<session-id>` format

### Commit Message Convention
Follow conventional commits format:
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks

### Code Quality Standards
When code is added to this project:
1. Write clean, readable, and maintainable code
2. Include appropriate comments for complex logic
3. Follow the established coding style of the chosen language
4. Write tests for new functionality
5. Update documentation as needed

## Commands Reference

### Git Operations
```bash
# Check status
git status

# Stage changes
git add <file>

# Commit changes
git commit -m "type(scope): description"

# Push to remote
git push -u origin <branch-name>

# Pull latest changes
git pull origin <branch-name>
```

### Future Commands (to be added when stack is chosen)
```bash
# Install dependencies
# npm install / pip install -r requirements.txt / cargo build

# Run tests
# npm test / pytest / cargo test

# Build project
# npm run build / python setup.py build / cargo build --release

# Start development server
# npm run dev / python app.py / cargo run
```

## AI Assistant Guidelines

### When Working on This Project

1. **Explore Before Acting**
   - Read existing files before making changes
   - Understand the context and purpose of code
   - Check for related files that might be affected

2. **Make Minimal Changes**
   - Only modify what's necessary for the task
   - Avoid over-engineering solutions
   - Don't add features beyond what's requested

3. **Maintain Consistency**
   - Follow existing code patterns and conventions
   - Use consistent naming conventions
   - Match the style of surrounding code

4. **Document Changes**
   - Write clear commit messages
   - Update documentation when adding features
   - Comment complex logic when necessary

5. **Test Your Changes**
   - Verify changes work as expected
   - Run existing tests to check for regressions
   - Add tests for new functionality

### Code Style Preferences
- Use meaningful variable and function names
- Keep functions focused on a single responsibility
- Prefer explicit over implicit behavior
- Handle errors appropriately
- Avoid magic numbers and strings (use constants)

### Security Considerations
- Never commit sensitive data (API keys, passwords, etc.)
- Validate user input at system boundaries
- Be cautious with file system operations
- Avoid command injection vulnerabilities

## Project Setup (For Future Development)

When establishing the technology stack, consider:

### If Node.js/TypeScript:
1. Initialize with `npm init -y`
2. Add TypeScript: `npm install -D typescript @types/node`
3. Create `tsconfig.json` with strict mode
4. Add ESLint and Prettier for code quality
5. Set up Jest or Vitest for testing

### If Python:
1. Create virtual environment: `python -m venv venv`
2. Initialize with `pyproject.toml` or `setup.py`
3. Add requirements.txt or use Poetry/pip-tools
4. Set up pytest for testing
5. Add Black, isort, and flake8 for code quality

### If Rust:
1. Initialize with `cargo init`
2. Configure Cargo.toml with dependencies
3. Set up clippy for linting
4. Use rustfmt for formatting

## Getting Help

- Check existing documentation in `docs/` directory (when created)
- Review test files for usage examples
- Read inline code comments
- Check commit history for context on changes

## Notes

- This document should be updated as the project evolves
- Add specific conventions as patterns emerge from development
- Keep this file as the primary reference for AI assistants

---

*Last updated: January 2026*
*Project status: Initial setup*
