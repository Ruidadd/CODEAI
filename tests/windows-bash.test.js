/**
 * Tests for Windows Git Bash Support Module
 */

const assert = require('assert');
const path = require('path');

// Import the module
const windowsBash = require('../src/windows-bash');
const codeai = require('../src/index');

// Test helper
function test(name, fn) {
  try {
    fn();
    console.log(`✓ ${name}`);
    return true;
  } catch (err) {
    console.error(`✗ ${name}`);
    console.error(`  Error: ${err.message}`);
    return false;
  }
}

// Run tests
console.log('Windows Git Bash Support Tests');
console.log('==============================\n');

let passed = 0;
let failed = 0;

// Test: isWindows function exists and returns boolean
if (test('isWindows() returns a boolean', () => {
  const result = windowsBash.isWindows();
  assert.strictEqual(typeof result, 'boolean');
})) passed++; else failed++;

// Test: CLAUDE_CODE_GIT_BASH_PATH_ENV is defined
if (test('CLAUDE_CODE_GIT_BASH_PATH_ENV is defined', () => {
  assert.strictEqual(
    windowsBash.CLAUDE_CODE_GIT_BASH_PATH_ENV,
    'CLAUDE_CODE_GIT_BASH_PATH'
  );
})) passed++; else failed++;

// Test: COMMON_GIT_BASH_PATHS is an array
if (test('COMMON_GIT_BASH_PATHS is an array with paths', () => {
  assert(Array.isArray(windowsBash.COMMON_GIT_BASH_PATHS));
  assert(windowsBash.COMMON_GIT_BASH_PATHS.length > 0);
})) passed++; else failed++;

// Test: detectGitBash returns an object with success property
if (test('detectGitBash() returns object with success property', () => {
  const result = windowsBash.detectGitBash();
  assert(typeof result === 'object');
  assert('success' in result);
  assert(typeof result.success === 'boolean');
})) passed++; else failed++;

// Test: getGitBashRequiredError returns proper error message
if (test('getGitBashRequiredError() returns formatted error', () => {
  const error = windowsBash.getGitBashRequiredError();
  assert(error.includes('Claude Code on Windows requires git-bash'));
  assert(error.includes('https://git-scm.com/downloads/win'));
  assert(error.includes('CLAUDE_CODE_GIT_BASH_PATH'));
})) passed++; else failed++;

// Test: fileExists function works
if (test('fileExists() returns false for non-existent file', () => {
  const result = windowsBash.fileExists('/nonexistent/path/file.exe');
  assert.strictEqual(result, false);
})) passed++; else failed++;

// Test: validateBashPath returns error for empty path
if (test('validateBashPath() rejects empty path', () => {
  const result = windowsBash.validateBashPath('');
  assert.strictEqual(result.valid, false);
  assert(result.error.includes('empty'));
})) passed++; else failed++;

// Test: validateBashPath returns error for non-existent path
if (test('validateBashPath() rejects non-existent path', () => {
  const result = windowsBash.validateBashPath('/nonexistent/bash.exe');
  assert.strictEqual(result.valid, false);
  assert(result.error.includes('not found'));
})) passed++; else failed++;

// Test: getEnvBashPath returns null when env var not set
if (test('getEnvBashPath() handles missing env var', () => {
  const originalValue = process.env.CLAUDE_CODE_GIT_BASH_PATH;
  delete process.env.CLAUDE_CODE_GIT_BASH_PATH;
  const result = windowsBash.getEnvBashPath();
  assert(result === null || result === undefined);
  if (originalValue) {
    process.env.CLAUDE_CODE_GIT_BASH_PATH = originalValue;
  }
})) passed++; else failed++;

// Test: WindowsBashConfig class exists and works
if (test('WindowsBashConfig class can be instantiated', () => {
  const config = new windowsBash.WindowsBashConfig();
  assert(config !== null);
  assert(typeof config.init === 'function');
  assert(typeof config.isConfigured === 'function');
  assert(typeof config.toJSON === 'function');
})) passed++; else failed++;

// Test: WindowsBashConfig.toJSON returns expected structure
if (test('WindowsBashConfig.toJSON() returns expected structure', () => {
  const config = new windowsBash.WindowsBashConfig();
  const json = config.toJSON();
  assert('platform' in json);
  assert('isWindows' in json);
  assert('bashPath' in json);
  assert('envVar' in json);
  assert('configured' in json);
})) passed++; else failed++;

// Test: codeai module exports expected functions
if (test('Main module exports expected functions', () => {
  assert(typeof codeai.initialize === 'function');
  assert(typeof codeai.isReady === 'function');
  assert(typeof codeai.getDiagnostics === 'function');
  assert(typeof codeai.execBash === 'function');
})) passed++; else failed++;

// Test: getDiagnostics returns comprehensive info
if (test('getDiagnostics() returns comprehensive info', () => {
  const diag = codeai.getDiagnostics();
  assert('platform' in diag);
  assert('isWindows' in diag);
  assert('bashDetected' in diag);
  assert('commonPaths' in diag);
  assert('envVar' in diag);
})) passed++; else failed++;

// Test: isReady returns boolean
if (test('isReady() returns boolean', () => {
  const result = codeai.isReady();
  assert(typeof result === 'boolean');
})) passed++; else failed++;

// Platform-specific tests
if (!windowsBash.isWindows()) {
  // On non-Windows, bash should be detected at /bin/bash
  if (test('[Non-Windows] detectGitBash finds /bin/bash', () => {
    const result = windowsBash.detectGitBash();
    assert(result.success === true);
    assert(result.bashPath === '/bin/bash');
  })) passed++; else failed++;

  if (test('[Non-Windows] getBashCommand uses /bin/bash', () => {
    const cmd = windowsBash.getBashCommand('echo test');
    assert(cmd.command === '/bin/bash');
    assert.deepStrictEqual(cmd.args, ['-c', 'echo test']);
  })) passed++; else failed++;
}

// Summary
console.log('\n==============================');
console.log(`Results: ${passed} passed, ${failed} failed`);
console.log(`Total: ${passed + failed} tests`);

process.exit(failed > 0 ? 1 : 0);
