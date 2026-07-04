from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Protocol
from urllib.parse import urljoin

from .errors import (
    PrivateApiAuthError,
    PrivateApiForbiddenError,
    PrivateApiNetworkError,
    PrivateApiRateLimitedError,
    PrivateApiUnsupportedResponseError,
)
from .models import AccountRemoteInfo, AuthMaterial, QuotaInfo


class PrivateApiProvider(Protocol):
    def get_quota(self, auth: AuthMaterial) -> QuotaInfo:
        ...

    def refresh_account(self, auth: AuthMaterial) -> AccountRemoteInfo:
        ...


class ConfiguredHttpPrivateApiProvider:
    def __init__(
        self,
        *,
        base_url: str | None,
        quota_endpoint: str | None,
        account_endpoint: str | None,
        timeout_seconds: int,
        user_agent: str,
    ) -> None:
        self.base_url = base_url
        self.quota_endpoint = quota_endpoint
        self.account_endpoint = account_endpoint
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def get_quota(self, auth: AuthMaterial) -> QuotaInfo:
        if not self.base_url or not self.quota_endpoint:
            raise PrivateApiUnsupportedResponseError("quota endpoint is not configured")
        data = self.request_json(self.quota_endpoint, auth)
        return quota_from_response(data)

    def refresh_account(self, auth: AuthMaterial) -> AccountRemoteInfo:
        if not self.base_url or not self.account_endpoint:
            quota = self.get_quota(auth) if self.quota_endpoint else None
            return AccountRemoteInfo(quota=quota)
        data = self.request_json(self.account_endpoint, auth)
        remote = AccountRemoteInfo(
            email=pick(data, "email"),
            account_id=pick(data, "account_id", "accountId", "account"),
            user_id=pick(data, "user_id", "userId", "sub"),
            organization_id=pick(data, "organization_id", "organizationId", "org_id", "orgId"),
            plan=pick(data, "plan", "tier", "subscription"),
        )
        if self.quota_endpoint:
            remote.quota = self.get_quota(auth)
        return remote

    def request_json(self, endpoint: str, auth: AuthMaterial) -> dict:
        if not auth.access_token:
            raise PrivateApiAuthError("missing access token")
        request = urllib.request.Request(urljoin(self.base_url.rstrip("/") + "/", endpoint.lstrip("/")))
        request.add_header("User-Agent", self.user_agent)
        request.add_header("Accept", "application/json")
        request.add_header("Authorization", "Bearer " + auth.access_token)
        attempts = 0
        while True:
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = response.read().decode("utf-8")
                data = json.loads(payload)
                if not isinstance(data, dict):
                    raise PrivateApiUnsupportedResponseError("response is not a JSON object")
                return data
            except urllib.error.HTTPError as exc:
                if exc.code == 401:
                    raise PrivateApiAuthError("unauthorized") from exc
                if exc.code == 403:
                    raise PrivateApiForbiddenError("forbidden") from exc
                if exc.code == 429 and attempts < 1:
                    attempts += 1
                    time.sleep(1)
                    continue
                if exc.code == 429:
                    raise PrivateApiRateLimitedError("rate limited") from exc
                if exc.code >= 500:
                    raise PrivateApiNetworkError(f"server error {exc.code}") from exc
                raise PrivateApiUnsupportedResponseError(f"unsupported HTTP status {exc.code}") from exc
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                raise PrivateApiNetworkError("network error or timeout") from exc
            except json.JSONDecodeError as exc:
                raise PrivateApiUnsupportedResponseError("response is not valid JSON") from exc


def quota_from_response(data: dict) -> QuotaInfo:
    quota_data = data.get("quota") if isinstance(data.get("quota"), dict) else data
    used_percent = first_number(quota_data, "used_percent", "usedPercent", "used_pct", "usage_percent")
    remaining_percent = first_number(quota_data, "remaining_percent", "remainingPercent", "remaining_pct")
    used = first_int(quota_data, "used")
    limit = first_int(quota_data, "limit")
    remaining = first_int(quota_data, "remaining")
    if remaining_percent is None and used_percent is not None:
        remaining_percent = max(0.0, 100.0 - used_percent)
    return QuotaInfo(
        status=str(quota_data.get("status") or "ok"),
        used_percent=used_percent,
        remaining_percent=remaining_percent,
        used=used,
        limit=limit,
        remaining=remaining,
        reset_at=pick(quota_data, "reset_at", "resetAt", "resets_at"),
        window_duration_mins=first_int(quota_data, "window_duration_mins", "windowDurationMins", "window_mins"),
        plan=pick(quota_data, "plan", "tier", "subscription"),
    )


def pick(data: dict, *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def first_number(data: dict, *keys: str) -> float | None:
    for key in keys:
        try:
            if data.get(key) is not None:
                return float(data[key])
        except (TypeError, ValueError):
            pass
    return None


def first_int(data: dict, *keys: str) -> int | None:
    for key in keys:
        try:
            if data.get(key) is not None:
                return int(data[key])
        except (TypeError, ValueError):
            pass
    return None
