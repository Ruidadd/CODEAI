# Plan: slugify utility with tests (pipeline trial run)

- Date: 2026-07-02
- Architect: Claude (Fable)
- Status: draft

## Goal

A dependency-free Node.js `slugify` utility with unit tests, used as the first
end-to-end trial of the Fable → Codex → CC pipeline. Done when `node --test`
passes all cases below.

## Context & constraints

- The repository is currently empty (docs and pipeline scaffolding only).
- Use plain Node.js (>= 18) and the built-in `node:test` runner — **zero npm
  dependencies**, no package.json needed for this trial.
- Use ESM (`.mjs`) so no package.json `"type"` field is required.
- Keep it to exactly two files; do not add build tooling, linters, or CI.

## Steps

### Step 1: implement slugify

- Changes: create `src/slugify.mjs` exporting a function `slugify(input)`:
  - lowercases the input,
  - trims leading/trailing whitespace,
  - replaces every run of non-alphanumeric characters with a single `-`,
  - strips leading/trailing `-`,
  - throws `TypeError` if `input` is not a string.
- Acceptance:
  - `node -e "import('./src/slugify.mjs').then(m => console.log(m.slugify('  Hello, World!  ')))"` → prints `hello-world`

### Step 2: add unit tests

- Changes: create `test/slugify.test.mjs` using `node:test` + `node:assert/strict`
  covering at least:
  - `"  Hello, World!  "` → `"hello-world"`
  - `"Fable × Codex --- pipeline"` → `"fable-codex-pipeline"`
  - `"already-slugged"` → `"already-slugged"` (idempotent)
  - `""` → `""`
  - `"!!!"` → `""`
  - non-string input (e.g. `42`) throws `TypeError`
- Acceptance:
  - `node --test` → all tests pass, exit code 0

## Feedback log

## Acceptance record
