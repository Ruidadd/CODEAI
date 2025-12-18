/**
 * Microsoft Authentication Helper
 * Handles Microsoft account authentication with proper error handling for sub status 6008
 */

export enum AuthErrorCode {
  INVALID_CREDENTIAL = 6008,
  ACCOUNT_LOCKED = 6009,
  PASSWORD_EXPIRED = 6010,
  MFA_REQUIRED = 50076,
  CONDITIONAL_ACCESS_BLOCKED = 53003,
}

export interface AuthError {
  message: string;
  subStatus: number;
  correlationId: string;
  errorCode?: number;
  timestamp?: string;
}

export interface ErrorResponse {
  status: string;
  errorType: string;
  errorCode?: number;
  subStatus: number;
  message: string;
  correlationId: string;
  timestamp: string;
  suggestions: string[];
  troubleshootingSteps?: TroubleshootingStep[];
  supportInfo?: SupportInfo;
}

export interface TroubleshootingStep {
  step: number;
  action: string;
  description: string;
}

export interface SupportInfo {
  url: string;
  note: string;
}

export class MicrosoftAuthError extends Error {
  public subStatus: number;
  public correlationId: string;
  public errorCode: number;
  public timestamp: string;

  constructor(
    message: string,
    subStatus: number,
    correlationId: string,
    errorCode: number = 2150171662,
    timestamp: string = new Date().toISOString()
  ) {
    super(message);
    this.name = 'MicrosoftAuthError';
    this.subStatus = subStatus;
    this.correlationId = correlationId;
    this.errorCode = errorCode;
    this.timestamp = timestamp;
  }

  toString(): string {
    return `${this.name}(code=${this.errorCode}, sub_status=${this.subStatus}, correlation_id=${this.correlationId}): ${this.message}`;
  }
}

export class MicrosoftAuthHelper {
  private logLevel: string;

  constructor(logLevel: string = 'info') {
    this.logLevel = logLevel;
  }

  /**
   * Handle Microsoft authentication errors with specific handling for sub status 6008
   */
  public handleAuthError(
    error: Error | MicrosoftAuthError,
    correlationId?: string
  ): ErrorResponse {
    // Extract error details
    const authError = error as MicrosoftAuthError;
    const subStatus = authError.subStatus || 0;
    const errorCode = authError.errorCode || 0;
    const corrId = correlationId || authError.correlationId || 'N/A';

    console.error(
      `Authentication error - Code: ${errorCode}, ` +
      `Sub Status: ${subStatus}, ` +
      `Correlation ID: ${corrId}`
    );

    // Handle sub status 6008 specifically
    if (subStatus === 6008 || subStatus === AuthErrorCode.INVALID_CREDENTIAL) {
      return this.handleInvalidCredentialError(corrId, error);
    }

    // Handle other common errors
    const errorHandlers: { [key: number]: (id: string, err: Error) => ErrorResponse } = {
      [AuthErrorCode.ACCOUNT_LOCKED]: this.handleAccountLockedError.bind(this),
      [AuthErrorCode.PASSWORD_EXPIRED]: this.handlePasswordExpiredError.bind(this),
      [AuthErrorCode.MFA_REQUIRED]: this.handleMfaRequiredError.bind(this),
      [AuthErrorCode.CONDITIONAL_ACCESS_BLOCKED]: this.handleConditionalAccessBlockedError.bind(this),
    };

    const handler = errorHandlers[subStatus];
    if (handler) {
      return handler(corrId, error);
    }

    // Generic error handling
    return this.handleGenericError(corrId, error);
  }

  /**
   * Handle invalid credential error (sub status 6008)
   */
  private handleInvalidCredentialError(
    correlationId: string,
    error: Error
  ): ErrorResponse {
    console.error('Invalid credential error detected (Sub Status 6008)');

    const suggestions = [
      'Verify that your username and password are correct',
      'Check if your account has been locked or disabled',
      'Clear cached credentials and try again',
      'Reset your password at https://account.live.com/password/reset',
      'Verify your account at https://account.microsoft.com',
      'Check if MFA (Multi-Factor Authentication) is configured correctly',
      'If in an organization, contact your IT administrator',
      'Try using a different browser or incognito mode',
      'Ensure your system time is synchronized correctly',
    ];

    const troubleshootingSteps: TroubleshootingStep[] = [
      {
        step: 1,
        action: 'Reset Password',
        description: 'Visit https://account.live.com/password/reset',
      },
      {
        step: 2,
        action: 'Check Account Status',
        description: 'Verify account is not locked at https://account.microsoft.com',
      },
      {
        step: 3,
        action: 'Clear Credentials',
        description: 'Clear cached credentials and browser cookies',
      },
      {
        step: 4,
        action: 'Verify MFA',
        description: 'Check MFA settings at https://account.microsoft.com/security',
      },
    ];

    return {
      status: 'error',
      errorType: 'INVALID_CREDENTIAL',
      errorCode: 2150171662,
      subStatus: 6008,
      message: 'The credential is invalid. Unexpected sub status (6008)',
      correlationId,
      timestamp: new Date().toISOString(),
      suggestions,
      troubleshootingSteps,
      supportInfo: {
        url: 'https://support.microsoft.com',
        note: 'Provide correlation ID when contacting support',
      },
    };
  }

  /**
   * Handle account locked error
   */
  private handleAccountLockedError(
    correlationId: string,
    error: Error
  ): ErrorResponse {
    return {
      status: 'error',
      errorType: 'ACCOUNT_LOCKED',
      subStatus: 6009,
      message: 'Account is locked',
      correlationId,
      timestamp: new Date().toISOString(),
      suggestions: [
        'Wait 30 minutes and try again',
        'Contact your administrator',
        'Visit https://account.microsoft.com to unlock',
      ],
    };
  }

  /**
   * Handle password expired error
   */
  private handlePasswordExpiredError(
    correlationId: string,
    error: Error
  ): ErrorResponse {
    return {
      status: 'error',
      errorType: 'PASSWORD_EXPIRED',
      subStatus: 6010,
      message: 'Password has expired',
      correlationId,
      timestamp: new Date().toISOString(),
      suggestions: [
        'Reset your password',
        'Visit https://account.live.com/password/reset',
      ],
    };
  }

  /**
   * Handle MFA required error
   */
  private handleMfaRequiredError(
    correlationId: string,
    error: Error
  ): ErrorResponse {
    return {
      status: 'error',
      errorType: 'MFA_REQUIRED',
      subStatus: 50076,
      message: 'Multi-factor authentication is required',
      correlationId,
      timestamp: new Date().toISOString(),
      suggestions: [
        'Complete MFA challenge',
        'Check your authenticator app or phone',
        'Ensure you have access to your MFA method',
      ],
    };
  }

  /**
   * Handle conditional access blocked error
   */
  private handleConditionalAccessBlockedError(
    correlationId: string,
    error: Error
  ): ErrorResponse {
    return {
      status: 'error',
      errorType: 'CONDITIONAL_ACCESS_BLOCKED',
      subStatus: 53003,
      message: 'Access blocked by conditional access policy',
      correlationId,
      timestamp: new Date().toISOString(),
      suggestions: [
        'Contact your IT administrator',
        'Verify your device is compliant',
        'Check if you are using an approved network/location',
        'Ensure your browser/application is approved',
      ],
    };
  }

  /**
   * Handle generic authentication error
   */
  private handleGenericError(
    correlationId: string,
    error: Error
  ): ErrorResponse {
    return {
      status: 'error',
      errorType: 'GENERIC_AUTH_ERROR',
      subStatus: 0,
      message: error.message,
      correlationId,
      timestamp: new Date().toISOString(),
      suggestions: [
        'Check your internet connection',
        'Try again later',
        'Contact support with correlation ID',
      ],
    };
  }

  /**
   * Log error details to console in a formatted way
   */
  public logErrorDetails(errorResponse: ErrorResponse): void {
    console.log('\n' + '='.repeat(80));
    console.log('Microsoft Authentication Error Analysis');
    console.log('='.repeat(80));
    console.log(JSON.stringify(errorResponse, null, 2));
    console.log('='.repeat(80));
    console.log(`\nCorrelation ID for support: ${errorResponse.correlationId}`);
  }

  /**
   * Save error details to local storage (for browser environments)
   */
  public saveErrorToLocalStorage(errorResponse: ErrorResponse): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      const errors = JSON.parse(localStorage.getItem('auth_errors') || '[]');
      errors.push(errorResponse);
      localStorage.setItem('auth_errors', JSON.stringify(errors));
      console.log('Error saved to localStorage');
    }
  }

  /**
   * Retry authentication with exponential backoff
   */
  public async retryWithBackoff<T>(
    fn: () => Promise<T>,
    maxRetries: number = 3,
    initialDelay: number = 1000
  ): Promise<T> {
    let lastError: Error | undefined;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error as Error;

        if (attempt < maxRetries - 1) {
          const delay = initialDelay * Math.pow(2, attempt);
          console.log(`Retry attempt ${attempt + 1}/${maxRetries} after ${delay}ms`);
          await this.sleep(delay);
        }
      }
    }

    throw lastError || new Error('Max retries exceeded');
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Example usage
if (typeof require !== 'undefined' && require.main === module) {
  // Simulate the error from the user's report
  const authHelper = new MicrosoftAuthHelper();

  // Create a simulated error with sub status 6008
  const simulatedError = new MicrosoftAuthError(
    'The credential is invalid. Unexpected sub status (6008).',
    6008,
    '10672792-8bca-4953-b9de-297cd77572c5',
    2150171662,
    '2025-12-18T02:41:06.000Z'
  );

  // Handle the error
  const errorResponse = authHelper.handleAuthError(
    simulatedError,
    '10672792-8bca-4953-b9de-297cd77572c5'
  );

  // Log the detailed error response
  authHelper.logErrorDetails(errorResponse);
}

export default MicrosoftAuthHelper;
