"""
Microsoft Authentication Helper
Handles Microsoft account authentication with proper error handling for sub status 6008
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum


class AuthErrorCode(Enum):
    """Microsoft authentication error codes"""
    INVALID_CREDENTIAL = 6008
    ACCOUNT_LOCKED = 6009
    PASSWORD_EXPIRED = 6010
    MFA_REQUIRED = 50076
    CONDITIONAL_ACCESS_BLOCKED = 53003


class MicrosoftAuthError(Exception):
    """Custom exception for Microsoft authentication errors"""

    def __init__(
        self,
        message: str,
        sub_status: int,
        correlation_id: str,
        error_code: Optional[int] = None,
        timestamp: Optional[str] = None
    ):
        self.message = message
        self.sub_status = sub_status
        self.correlation_id = correlation_id
        self.error_code = error_code or 2150171662
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        super().__init__(self.message)

    def __str__(self):
        return (
            f"MicrosoftAuthError(code={self.error_code}, "
            f"sub_status={self.sub_status}, "
            f"correlation_id={self.correlation_id}): {self.message}"
        )


class MicrosoftAuthHelper:
    """Helper class for Microsoft authentication with comprehensive error handling"""

    def __init__(self, log_level=logging.INFO):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def handle_auth_error(
        self,
        error: Exception,
        correlation_id: Optional[str] = None
    ) -> Dict:
        """
        Handle Microsoft authentication errors with specific handling for sub status 6008

        Args:
            error: The exception raised during authentication
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dict containing error details and suggested actions
        """
        # Extract error details
        sub_status = getattr(error, 'sub_status', None)
        error_code = getattr(error, 'error_code', None)
        correlation_id = correlation_id or getattr(error, 'correlation_id', 'N/A')

        self.logger.error(
            f"Authentication error - Code: {error_code}, "
            f"Sub Status: {sub_status}, "
            f"Correlation ID: {correlation_id}"
        )

        # Handle sub status 6008 specifically
        if sub_status == 6008 or sub_status == AuthErrorCode.INVALID_CREDENTIAL.value:
            return self._handle_invalid_credential_error(correlation_id, error)

        # Handle other common errors
        error_handlers = {
            6009: self._handle_account_locked_error,
            6010: self._handle_password_expired_error,
            50076: self._handle_mfa_required_error,
            53003: self._handle_conditional_access_blocked_error
        }

        handler = error_handlers.get(sub_status)
        if handler:
            return handler(correlation_id, error)

        # Generic error handling
        return self._handle_generic_error(correlation_id, error)

    def _handle_invalid_credential_error(
        self,
        correlation_id: str,
        error: Exception
    ) -> Dict:
        """Handle invalid credential error (sub status 6008)"""
        self.logger.error("Invalid credential error detected (Sub Status 6008)")

        suggestions = [
            "Verify that your username and password are correct",
            "Check if your account has been locked or disabled",
            "Clear cached credentials and try again",
            "Reset your password at https://account.live.com/password/reset",
            "Verify your account at https://account.microsoft.com",
            "Check if MFA (Multi-Factor Authentication) is configured correctly",
            "If in an organization, contact your IT administrator",
            "Try using a different browser or incognito mode",
            "Ensure your system time is synchronized correctly"
        ]

        troubleshooting_steps = [
            {
                "step": 1,
                "action": "Reset Password",
                "description": "Visit https://account.live.com/password/reset"
            },
            {
                "step": 2,
                "action": "Check Account Status",
                "description": "Verify account is not locked at https://account.microsoft.com"
            },
            {
                "step": 3,
                "action": "Clear Credentials",
                "description": "Clear cached credentials and browser cookies"
            },
            {
                "step": 4,
                "action": "Verify MFA",
                "description": "Check MFA settings at https://account.microsoft.com/security"
            }
        ]

        return {
            'status': 'error',
            'error_type': 'INVALID_CREDENTIAL',
            'error_code': 2150171662,
            'sub_status': 6008,
            'message': 'The credential is invalid. Unexpected sub status (6008)',
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'suggestions': suggestions,
            'troubleshooting_steps': troubleshooting_steps,
            'support_info': {
                'url': 'https://support.microsoft.com',
                'note': 'Provide correlation ID when contacting support'
            }
        }

    def _handle_account_locked_error(
        self,
        correlation_id: str,
        error: Exception
    ) -> Dict:
        """Handle account locked error"""
        return {
            'status': 'error',
            'error_type': 'ACCOUNT_LOCKED',
            'sub_status': 6009,
            'message': 'Account is locked',
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'suggestions': [
                'Wait 30 minutes and try again',
                'Contact your administrator',
                'Visit https://account.microsoft.com to unlock'
            ]
        }

    def _handle_password_expired_error(
        self,
        correlation_id: str,
        error: Exception
    ) -> Dict:
        """Handle password expired error"""
        return {
            'status': 'error',
            'error_type': 'PASSWORD_EXPIRED',
            'sub_status': 6010,
            'message': 'Password has expired',
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'suggestions': [
                'Reset your password',
                'Visit https://account.live.com/password/reset'
            ]
        }

    def _handle_mfa_required_error(
        self,
        correlation_id: str,
        error: Exception
    ) -> Dict:
        """Handle MFA required error"""
        return {
            'status': 'error',
            'error_type': 'MFA_REQUIRED',
            'sub_status': 50076,
            'message': 'Multi-factor authentication is required',
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'suggestions': [
                'Complete MFA challenge',
                'Check your authenticator app or phone',
                'Ensure you have access to your MFA method'
            ]
        }

    def _handle_conditional_access_blocked_error(
        self,
        correlation_id: str,
        error: Exception
    ) -> Dict:
        """Handle conditional access blocked error"""
        return {
            'status': 'error',
            'error_type': 'CONDITIONAL_ACCESS_BLOCKED',
            'sub_status': 53003,
            'message': 'Access blocked by conditional access policy',
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'suggestions': [
                'Contact your IT administrator',
                'Verify your device is compliant',
                'Check if you are using an approved network/location',
                'Ensure your browser/application is approved'
            ]
        }

    def _handle_generic_error(
        self,
        correlation_id: str,
        error: Exception
    ) -> Dict:
        """Handle generic authentication error"""
        return {
            'status': 'error',
            'error_type': 'GENERIC_AUTH_ERROR',
            'message': str(error),
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'suggestions': [
                'Check your internet connection',
                'Try again later',
                'Contact support with correlation ID'
            ]
        }

    def log_error_to_file(self, error_details: Dict, filename: str = 'auth_errors.log'):
        """Log error details to a file for debugging"""
        try:
            with open(filename, 'a') as f:
                f.write(json.dumps(error_details, indent=2))
                f.write('\n---\n')
            self.logger.info(f"Error logged to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to log error to file: {e}")


# Example usage
if __name__ == "__main__":
    # Simulate the error from the user's report
    auth_helper = MicrosoftAuthHelper()

    # Create a simulated error with sub status 6008
    simulated_error = MicrosoftAuthError(
        message="The credential is invalid. Unexpected sub status (6008).",
        sub_status=6008,
        correlation_id="10672792-8bca-4953-b9de-297cd77572c5",
        error_code=2150171662,
        timestamp="2025-12-18T02:41:06.000Z"
    )

    # Handle the error
    error_response = auth_helper.handle_auth_error(
        simulated_error,
        correlation_id="10672792-8bca-4953-b9de-297cd77572c5"
    )

    # Print the detailed error response
    print("\n" + "="*80)
    print("Microsoft Authentication Error Analysis")
    print("="*80)
    print(json.dumps(error_response, indent=2, ensure_ascii=False))
    print("="*80)

    # Log to file
    auth_helper.log_error_to_file(error_response)

    print("\nError details have been logged to 'auth_errors.log'")
    print(f"\nCorrelation ID for support: {error_response['correlation_id']}")
