/**
 * Windows Git Bash Detection and Configuration Utility
 *
 * This module handles detection and configuration of git-bash on Windows systems.
 * It provides utilities for:
 * - Detecting the operating system
 * - Finding git-bash installation
 * - Validating bash executable paths
 * - Providing helpful error messages
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Environment variable for custom git-bash path
const CLAUDE_CODE_GIT_BASH_PATH_ENV = 'CLAUDE_CODE_GIT_BASH_PATH';

// Common git-bash installation paths on Windows
const COMMON_GIT_BASH_PATHS = [
  'C:\\Program Files\\Git\\bin\\bash.exe',
  'C:\\Program Files (x86)\\Git\\bin\\bash.exe',
  'C:\\Git\\bin\\bash.exe',
  'C:\\msys64\\usr\\bin\\bash.exe',
  'C:\\cygwin64\\bin\\bash.exe',
  'C:\\cygwin\\bin\\bash.exe',
];

/**
 * Checks if the current platform is Windows
 * @returns {boolean} True if running on Windows
 */
function isWindows() {
  return process.platform === 'win32';
}

/**
 * Checks if a file exists and is executable
 * @param {string} filePath - Path to the file to check
 * @returns {boolean} True if file exists and is accessible
 */
function fileExists(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.F_OK | fs.constants.X_OK);
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Gets the git-bash path from environment variable
 * @returns {string|null} The path from env var or null if not set
 */
function getEnvBashPath() {
  return process.env[CLAUDE_CODE_GIT_BASH_PATH_ENV] || null;
}

/**
 * Attempts to find bash.exe in the system PATH
 * @returns {string|null} Path to bash.exe if found, null otherwise
 */
function findBashInPath() {
  try {
    // On Windows, use 'where' command to find bash
    const result = execSync('where bash.exe', {
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe']
    }).trim();

    // 'where' can return multiple paths, take the first one
    const paths = result.split('\n').map(p => p.trim()).filter(Boolean);

    // Prefer git-bash over other bash implementations
    const gitBashPath = paths.find(p => p.toLowerCase().includes('git'));
    return gitBashPath || paths[0] || null;
  } catch (err) {
    return null;
  }
}

/**
 * Searches common installation directories for git-bash
 * @returns {string|null} Path to bash.exe if found, null otherwise
 */
function findBashInCommonPaths() {
  for (const bashPath of COMMON_GIT_BASH_PATHS) {
    if (fileExists(bashPath)) {
      return bashPath;
    }
  }
  return null;
}

/**
 * Validates that a given bash path is a valid git-bash executable
 * @param {string} bashPath - Path to validate
 * @returns {{valid: boolean, error?: string}} Validation result
 */
function validateBashPath(bashPath) {
  if (!bashPath) {
    return { valid: false, error: 'Bash path is empty or undefined' };
  }

  if (!fileExists(bashPath)) {
    return { valid: false, error: `Bash executable not found at: ${bashPath}` };
  }

  // Try to execute bash --version to verify it works
  try {
    const result = execSync(`"${bashPath}" --version`, {
      encoding: 'utf-8',
      timeout: 5000,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    if (!result.toLowerCase().includes('bash')) {
      return { valid: false, error: 'Executable does not appear to be bash' };
    }

    return { valid: true };
  } catch (err) {
    return { valid: false, error: `Failed to execute bash: ${err.message}` };
  }
}

/**
 * Gets the error message for missing git-bash
 * @returns {string} Formatted error message with instructions
 */
function getGitBashRequiredError() {
  return `Error: Claude Code on Windows requires git-bash (https://git-scm.com/downloads/win). If installed but not in PATH, set environment variable pointing to your bash.exe, similar to: ${CLAUDE_CODE_GIT_BASH_PATH_ENV}=C:\\Program Files\\Git\\bin\\bash.exe`;
}

/**
 * Main function to detect and return a valid git-bash path on Windows
 * @returns {{success: boolean, bashPath?: string, error?: string}} Result object
 */
function detectGitBash() {
  // Not on Windows - no special handling needed
  if (!isWindows()) {
    return {
      success: true,
      bashPath: '/bin/bash',
      message: 'Not on Windows, using default bash'
    };
  }

  // 1. First, check environment variable
  const envPath = getEnvBashPath();
  if (envPath) {
    const validation = validateBashPath(envPath);
    if (validation.valid) {
      return {
        success: true,
        bashPath: envPath,
        source: 'environment'
      };
    } else {
      return {
        success: false,
        error: `${CLAUDE_CODE_GIT_BASH_PATH_ENV} is set but invalid: ${validation.error}`
      };
    }
  }

  // 2. Try to find bash in PATH
  const pathBash = findBashInPath();
  if (pathBash) {
    const validation = validateBashPath(pathBash);
    if (validation.valid) {
      return {
        success: true,
        bashPath: pathBash,
        source: 'PATH'
      };
    }
  }

  // 3. Search common installation directories
  const commonBash = findBashInCommonPaths();
  if (commonBash) {
    const validation = validateBashPath(commonBash);
    if (validation.valid) {
      return {
        success: true,
        bashPath: commonBash,
        source: 'common-paths'
      };
    }
  }

  // 4. Git-bash not found
  return {
    success: false,
    error: getGitBashRequiredError()
  };
}

/**
 * Gets the bash command for executing scripts on the current platform
 * @param {string} script - The script/command to execute
 * @returns {{command: string, args: string[]}} Command and arguments for spawn
 */
function getBashCommand(script) {
  const detection = detectGitBash();

  if (!detection.success) {
    throw new Error(detection.error);
  }

  if (isWindows()) {
    return {
      command: detection.bashPath,
      args: ['-c', script]
    };
  }

  return {
    command: '/bin/bash',
    args: ['-c', script]
  };
}

/**
 * Configuration object for Windows bash settings
 */
class WindowsBashConfig {
  constructor() {
    this._bashPath = null;
    this._detected = false;
  }

  /**
   * Initializes the configuration by detecting git-bash
   * @returns {WindowsBashConfig} this instance for chaining
   */
  init() {
    if (this._detected) {
      return this;
    }

    const result = detectGitBash();
    if (result.success) {
      this._bashPath = result.bashPath;
    }
    this._detected = true;
    return this;
  }

  /**
   * Gets the detected bash path
   * @returns {string|null} The bash path or null if not found
   */
  get bashPath() {
    if (!this._detected) {
      this.init();
    }
    return this._bashPath;
  }

  /**
   * Sets a custom bash path
   * @param {string} path - The path to set
   */
  set bashPath(path) {
    const validation = validateBashPath(path);
    if (!validation.valid) {
      throw new Error(validation.error);
    }
    this._bashPath = path;
  }

  /**
   * Checks if Windows bash is properly configured
   * @returns {boolean} True if bash is available
   */
  isConfigured() {
    return this.bashPath !== null;
  }

  /**
   * Returns configuration as JSON
   * @returns {object} Configuration object
   */
  toJSON() {
    return {
      platform: process.platform,
      isWindows: isWindows(),
      bashPath: this._bashPath,
      envVar: CLAUDE_CODE_GIT_BASH_PATH_ENV,
      configured: this.isConfigured()
    };
  }
}

// Export all utilities
module.exports = {
  // Constants
  CLAUDE_CODE_GIT_BASH_PATH_ENV,
  COMMON_GIT_BASH_PATHS,

  // Detection functions
  isWindows,
  detectGitBash,
  findBashInPath,
  findBashInCommonPaths,

  // Validation functions
  fileExists,
  validateBashPath,

  // Utility functions
  getEnvBashPath,
  getBashCommand,
  getGitBashRequiredError,

  // Configuration class
  WindowsBashConfig,

  // Singleton instance
  config: new WindowsBashConfig()
};
