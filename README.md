# CODEAI

Windows Git Bash Support Module for Claude Code CLI.

## Overview

Claude Code on Windows requires Git Bash to execute shell commands. This module provides automatic detection and configuration of Git Bash on Windows systems.

## Installation

### Prerequisites

**Windows Users:**
1. Download and install Git for Windows from [https://git-scm.com/downloads/win](https://git-scm.com/downloads/win)
2. During installation, ensure "Git Bash" is included (default option)

### Setup

```bash
npm install
```

## Usage

### Automatic Detection

The module automatically searches for Git Bash in the following order:

1. **Environment Variable**: `CLAUDE_CODE_GIT_BASH_PATH`
2. **System PATH**: Searches for `bash.exe` in PATH
3. **Common Installation Paths**:
   - `C:\Program Files\Git\bin\bash.exe`
   - `C:\Program Files (x86)\Git\bin\bash.exe`
   - `C:\Git\bin\bash.exe`
   - `C:\msys64\usr\bin\bash.exe`
   - `C:\cygwin64\bin\bash.exe`
   - `C:\cygwin\bin\bash.exe`

### Setting Custom Path

If Git Bash is installed in a non-standard location, set the environment variable:

**PowerShell:**
```powershell
$env:CLAUDE_CODE_GIT_BASH_PATH = "C:\Custom\Path\Git\bin\bash.exe"
```

**Command Prompt:**
```cmd
set CLAUDE_CODE_GIT_BASH_PATH=C:\Custom\Path\Git\bin\bash.exe
```

**Permanent (System Environment Variable):**
1. Open System Properties > Advanced > Environment Variables
2. Add new variable: `CLAUDE_CODE_GIT_BASH_PATH`
3. Set value to your bash.exe path

### Checking Configuration

```bash
npm run check
```

Or programmatically:

```javascript
const codeai = require('./src/index');

// Check if ready
if (codeai.isReady()) {
  console.log('Git Bash is configured!');
}

// Get detailed diagnostics
const diagnostics = codeai.getDiagnostics();
console.log(diagnostics);
```

### API Reference

#### `initialize()`
Initializes bash configuration. Throws an error if Git Bash cannot be found on Windows.

#### `isReady()`
Returns `true` if the environment is properly configured for shell execution.

#### `getDiagnostics()`
Returns detailed diagnostic information about the current configuration.

#### `execBash(command, options)`
Executes a bash command with proper platform handling.

```javascript
const { execBash } = require('./src/index');

const result = await execBash('echo "Hello from bash"');
console.log(result.stdout);
```

#### `detectGitBash()`
Detects and returns information about Git Bash availability.

```javascript
const { detectGitBash } = require('./src/windows-bash');

const result = detectGitBash();
if (result.success) {
  console.log(`Bash found at: ${result.bashPath}`);
} else {
  console.error(result.error);
}
```

## Error Messages

If Git Bash is not found, you will see:

```
Error: Claude Code on Windows requires git-bash (https://git-scm.com/downloads/win).
If installed but not in PATH, set environment variable pointing to your bash.exe,
similar to: CLAUDE_CODE_GIT_BASH_PATH=C:\Program Files\Git\bin\bash.exe
```

## Testing

```bash
npm test
```

## Troubleshooting

### "Git Bash not found" on Windows

1. Verify Git for Windows is installed
2. Check if `bash.exe` exists in `C:\Program Files\Git\bin\`
3. Set `CLAUDE_CODE_GIT_BASH_PATH` environment variable manually
4. Run `npm run check` to verify configuration

### PATH Issues

If Git Bash is installed but not detected via PATH:
1. Add `C:\Program Files\Git\bin` to your system PATH
2. Or set `CLAUDE_CODE_GIT_BASH_PATH` environment variable

### Non-Windows Systems

On Linux and macOS, the module uses the default `/bin/bash` and requires no additional configuration.

## License

MIT
