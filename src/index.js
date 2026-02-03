/**
 * CODEAI - Windows Git Bash Support Module
 *
 * Main entry point for the Windows git-bash support functionality.
 * This module provides cross-platform shell execution with special
 * handling for Windows systems that require git-bash.
 */

const windowsBash = require('./windows-bash');

/**
 * Initialize the bash configuration
 * This should be called early in the application lifecycle
 * @throws {Error} If on Windows and git-bash cannot be found
 */
function initialize() {
  const result = windowsBash.detectGitBash();

  if (!result.success) {
    throw new Error(result.error);
  }

  console.log(`Bash configured: ${result.bashPath} (source: ${result.source || 'default'})`);
  return result;
}

/**
 * Check if the current environment is properly configured for shell execution
 * @returns {boolean} True if the environment is ready
 */
function isReady() {
  const result = windowsBash.detectGitBash();
  return result.success;
}

/**
 * Get diagnostic information about the current configuration
 * @returns {object} Diagnostic information
 */
function getDiagnostics() {
  const result = windowsBash.detectGitBash();

  return {
    platform: process.platform,
    isWindows: windowsBash.isWindows(),
    bashDetected: result.success,
    bashPath: result.bashPath || null,
    bashSource: result.source || null,
    error: result.error || null,
    envVar: windowsBash.CLAUDE_CODE_GIT_BASH_PATH_ENV,
    envVarValue: windowsBash.getEnvBashPath(),
    commonPaths: windowsBash.COMMON_GIT_BASH_PATHS
  };
}

/**
 * Execute a bash command with proper platform handling
 * @param {string} command - The command to execute
 * @param {object} options - Execution options
 * @returns {Promise<{stdout: string, stderr: string, exitCode: number}>}
 */
async function execBash(command, options = {}) {
  const { spawn } = require('child_process');
  const bashCmd = windowsBash.getBashCommand(command);

  return new Promise((resolve, reject) => {
    const proc = spawn(bashCmd.command, bashCmd.args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      ...options
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    proc.on('close', (exitCode) => {
      resolve({ stdout, stderr, exitCode });
    });

    proc.on('error', (err) => {
      reject(err);
    });
  });
}

// CLI handling when run directly
if (require.main === module) {
  const args = process.argv.slice(2);

  if (args.includes('--check') || args.includes('-c')) {
    // Check mode - verify git-bash configuration
    const diagnostics = getDiagnostics();
    console.log('Windows Git-Bash Configuration Check');
    console.log('====================================');
    console.log(`Platform: ${diagnostics.platform}`);
    console.log(`Is Windows: ${diagnostics.isWindows}`);
    console.log(`Bash Detected: ${diagnostics.bashDetected}`);

    if (diagnostics.bashPath) {
      console.log(`Bash Path: ${diagnostics.bashPath}`);
      console.log(`Detection Source: ${diagnostics.bashSource}`);
    }

    if (diagnostics.envVarValue) {
      console.log(`Env Var (${diagnostics.envVar}): ${diagnostics.envVarValue}`);
    }

    if (diagnostics.error) {
      console.error(`Error: ${diagnostics.error}`);
      process.exit(1);
    }

    console.log('\nConfiguration OK!');
    process.exit(0);
  }

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Windows Git-Bash Support Module

Usage:
  node src/index.js [options]

Options:
  --check, -c    Check git-bash configuration
  --help, -h     Show this help message

Environment Variables:
  ${windowsBash.CLAUDE_CODE_GIT_BASH_PATH_ENV}
    Custom path to git-bash executable (bash.exe)
    Example: ${windowsBash.CLAUDE_CODE_GIT_BASH_PATH_ENV}=C:\\Program Files\\Git\\bin\\bash.exe

Common Installation Paths:
${windowsBash.COMMON_GIT_BASH_PATHS.map(p => `  - ${p}`).join('\n')}
`);
    process.exit(0);
  }

  // Default: run diagnostics
  console.log(JSON.stringify(getDiagnostics(), null, 2));
}

module.exports = {
  initialize,
  isReady,
  getDiagnostics,
  execBash,
  ...windowsBash
};
