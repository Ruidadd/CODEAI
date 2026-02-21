# CLAUDE.md — AI Assistant Guide for CODEAI

This file provides context, conventions, and workflows for AI assistants (Claude and others)
working inside this repository.

---

## Project Overview

**Repository:** CODEAI
**Owner:** Ruidadd
**Description:** Trial project for video coding / AI-assisted development exploration.
**Status:** Early-stage / bootstrapping — minimal code exists yet.

---

## Repository Structure

```
CODEAI/
├── CLAUDE.md        ← You are here: AI assistant guide
└── README.md        ← Project description placeholder
```

The repository is in its initial state. As the project grows, this file should be
updated to reflect new directories, services, and conventions.

---

## Git Workflow

### Branches

| Branch | Purpose |
|--------|---------|
| `main` / `master` | Stable, production-ready code |
| `claude/<description>-<id>` | AI-generated feature branches |

### Branch Naming Convention

- AI-generated branches must follow: `claude/<short-description>-<sessionId>`
- Human feature branches: `feature/<ticket-or-description>`
- Hotfix branches: `hotfix/<description>`

### Commit Message Convention

Use concise, imperative commit messages:

```
<type>: <short summary>

[Optional body explaining *why*, not what]
```

**Types:**
- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `refactor:` — code restructuring without behavior change
- `test:` — adding or updating tests
- `chore:` — build tooling, dependencies, CI/CD

**Examples:**
```
feat: add video encoding pipeline
fix: handle null frame in decoder
docs: update CLAUDE.md with build instructions
```

### Push Instructions

Always push with tracking:
```bash
git push -u origin <branch-name>
```

AI assistant branches **must** start with `claude/` — pushes to other branches may be rejected.

---

## Development Setup

> This section should be updated when a stack/language is chosen.

Until the project stack is defined:

1. Clone the repository:
   ```bash
   git clone <remote-url>
   cd CODEAI
   ```

2. Check out the feature branch you'll work on:
   ```bash
   git checkout -b claude/<description>-<id>
   ```

3. Make changes, commit, and push:
   ```bash
   git add <files>
   git commit -m "feat: describe what you did"
   git push -u origin claude/<description>-<id>
   ```

---

## Coding Conventions

These apply as code is added to the project. Update this section when the stack is decided.

### General Principles

- **Minimal surface area:** Only add what's needed for the current task. No speculative abstractions.
- **No dead code:** Remove unused variables, imports, and functions entirely.
- **Readable over clever:** Prefer straightforward implementations.
- **No unnecessary comments:** Only comment non-obvious logic; skip obvious descriptions.

### Security

- Never commit secrets, tokens, API keys, or credentials.
- Use environment variables for all sensitive configuration.
- Validate all input at system boundaries (user input, external APIs).
- Avoid command injection, SQL injection, XSS, and other OWASP Top 10 vulnerabilities.

### File Naming

- Use lowercase with hyphens for directories: `src/video-encoder/`
- Match file names to their primary export: `VideoEncoder.ts` exports `VideoEncoder`.
- Configuration files live at the project root.

---

## Testing

> To be filled in once a testing framework is chosen.

**Conventions to follow when tests are added:**

- Tests live alongside source files or in a dedicated `tests/` directory.
- Test files are named `<module>.test.<ext>` or `<module>_test.<ext>`.
- Each test should cover one behavior; avoid testing implementation details.
- Run tests before pushing: `<test command here>`

---

## Environment Variables

> To be filled in when the project has configuration requirements.

Use a `.env.example` file at the project root to document all required environment variables
(without real values). Never commit `.env` files.

---

## AI Assistant Instructions

When working in this repository as an AI assistant:

### Do
- Read files before editing them.
- Use the existing CLAUDE.md as the source of truth for conventions.
- Update CLAUDE.md when you introduce new tools, patterns, or workflows.
- Make focused, minimal changes — only what the task requires.
- Write clear, descriptive commit messages explaining *why* a change was made.
- Push to a `claude/`-prefixed branch.

### Do Not
- Introduce new dependencies without explaining the rationale.
- Refactor code that isn't related to the current task.
- Add features, comments, or error handling beyond what was requested.
- Commit `.env`, credentials, or generated build artifacts.
- Push directly to `main`/`master` without explicit permission.

### When the Stack Is Unknown

If no language/framework has been chosen and you need to implement something:
1. Ask the user which stack they prefer before proceeding.
2. If no preference is given, use the simplest appropriate tool for the task.
3. Document the choice in this file and in `README.md`.

---

## Updating This File

This file should be updated whenever:
- A new language, framework, or major dependency is added.
- New build, test, or lint commands become available.
- Directory structure changes significantly.
- New conventions are adopted by the team.

Keep this file accurate — AI assistants rely on it as ground truth.
