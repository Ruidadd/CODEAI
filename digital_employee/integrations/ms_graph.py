"""
Microsoft Graph API base client.
Handles authentication (OAuth2) and provides a base HTTP client
for Email, Teams, and Calendar integrations.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class MSGraphAuthError(Exception):
    pass


class MSGraphClient:
    """
    Base Microsoft Graph API client.
    Supports OAuth2 client credentials flow (app-only auth)
    and delegated user auth (on-behalf-of flow).
    """

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    def __init__(self, config: dict):
        self.tenant_id = config["ms_tenant_id"]
        self.client_id = config["ms_client_id"]
        self.client_secret = config["ms_client_secret"]
        self.user_email = config.get("employee_email", "")

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

        self._http = httpx.Client(timeout=30.0)

    # ─────────────────────────────────────────────
    # Authentication
    # ─────────────────────────────────────────────

    def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        token_url = self.TOKEN_URL_TEMPLATE.format(tenant_id=self.tenant_id)
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }

        response = self._http.post(token_url, data=data)
        if response.status_code != 200:
            raise MSGraphAuthError(
                f"Failed to get access token: {response.status_code} {response.text}"
            )

        token_data = response.json()
        self._access_token = token_data["access_token"]
        self._token_expires_at = time.time() + token_data.get("expires_in", 3600)
        logger.debug("Access token refreshed successfully")
        return self._access_token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

    # ─────────────────────────────────────────────
    # HTTP Methods
    # ─────────────────────────────────────────────

    def get(self, path: str, params: dict = None) -> dict:
        url = f"{self.GRAPH_BASE}{path}"
        response = self._http.get(url, headers=self._headers(), params=params)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, body: dict) -> dict:
        url = f"{self.GRAPH_BASE}{path}"
        response = self._http.post(url, headers=self._headers(), json=body)
        response.raise_for_status()
        return response.json()

    def patch(self, path: str, body: dict) -> dict:
        url = f"{self.GRAPH_BASE}{path}"
        response = self._http.patch(url, headers=self._headers(), json=body)
        response.raise_for_status()
        return response.json()

    def delete(self, path: str) -> None:
        url = f"{self.GRAPH_BASE}{path}"
        response = self._http.delete(url, headers=self._headers())
        response.raise_for_status()

    def paginate(self, path: str, params: dict = None, max_items: int = 200) -> list[dict]:
        """Fetch all pages of a paginated Graph API response."""
        items = []
        url = f"{self.GRAPH_BASE}{path}"
        headers = self._headers()

        while url and len(items) < max_items:
            response = self._http.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            items.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
            params = None  # nextLink already contains params

        return items[:max_items]

    def subscribe_webhook(
        self,
        resource: str,
        change_types: list[str],
        notification_url: str,
        expiry_hours: int = 72,
    ) -> dict:
        """
        Create a Microsoft Graph change notification subscription (webhook).
        """
        expiry = (datetime.utcnow() + timedelta(hours=expiry_hours)).strftime(
            "%Y-%m-%dT%H:%M:%S.0000000Z"
        )
        body = {
            "changeType": ",".join(change_types),
            "notificationUrl": notification_url,
            "resource": resource,
            "expirationDateTime": expiry,
            "clientState": "digital-employee-secret",
        }
        return self.post("/subscriptions", body)

    def renew_subscription(self, subscription_id: str, expiry_hours: int = 72) -> dict:
        """Renew an existing webhook subscription."""
        expiry = (datetime.utcnow() + timedelta(hours=expiry_hours)).strftime(
            "%Y-%m-%dT%H:%M:%S.0000000Z"
        )
        return self.patch(
            f"/subscriptions/{subscription_id}",
            {"expirationDateTime": expiry}
        )

    def close(self):
        self._http.close()
