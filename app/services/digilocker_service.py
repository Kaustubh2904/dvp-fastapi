import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import settings
from app.core.exceptions import (
    BadRequestException,
    DigiLockerException,
    NotFoundException,
    ServiceUnavailableException,
)
from app.models.employee import DigiLockerStatus
from app.repositories.employee_repository import employee_repository
from app.services.audit_service import audit_log_service
from app.services.notification_service import notification_service
from app.utils.encryption import fernet_encryption

logger = logging.getLogger(__name__)

# In-memory state store for OAuth CSRF protection.
# In production, consider using Redis for multi-instance deployments.
_oauth_state_store: dict[str, dict[str, Any]] = {}


class DigiLockerService:
    """Service layer for DigiLocker OAuth 2.0 integration.

    All external API calls are isolated in private methods prefixed with `_`.
    These methods are only reachable when `settings.digilocker_configured` is True,
    ensuring the application works correctly without DigiLocker credentials.
    """

    @staticmethod
    def ensure_configured() -> None:
        """Raise 503 if DigiLocker is not configured."""
        if not settings.digilocker_configured:
            raise ServiceUnavailableException(
                detail="DigiLocker integration is not configured. "
                "Please set DIGILOCKER_CLIENT_ID and DIGILOCKER_CLIENT_SECRET in environment variables."
            )

    @staticmethod
    async def generate_authorization_url(employee_id: int) -> dict[str, str]:
        """Generate the DigiLocker OAuth 2.0 authorization URL with CSRF state."""
        DigiLockerService.ensure_configured()

        state = secrets.token_urlsafe(32)
        _oauth_state_store[state] = {
            "employee_id": employee_id,
            "created_at": datetime.now(timezone.utc),
        }

        params = {
            "response_type": "code",
            "client_id": settings.DIGILOCKER_CLIENT_ID,
            "redirect_uri": settings.DIGILOCKER_REDIRECT_URI,
            "scope": settings.DIGILOCKER_SCOPES,
            "state": state,
        }
        authorization_url = f"{settings.DIGILOCKER_AUTH_URL}?{urlencode(params)}"

        logger.info("Generated DigiLocker authorization URL for employee %d", employee_id)
        return {"authorization_url": authorization_url, "state": state}

    @staticmethod
    async def handle_callback(
        db: AsyncSession, code: str, state: str, actor_id: Optional[int] = None
    ) -> dict[str, Any]:
        """Exchange the authorization code for tokens and store encrypted credentials."""
        DigiLockerService.ensure_configured()

        # Validate state
        state_data = _oauth_state_store.pop(state, None)
        if not state_data:
            raise BadRequestException(detail="Invalid or expired OAuth state parameter.")

        employee_id = state_data["employee_id"]

        # Verify employee exists
        employee = await employee_repository.get(db, employee_id)
        if not employee:
            raise NotFoundException(detail="Employee not found.")

        # Exchange code for tokens
        token_data = await DigiLockerService._exchange_code_for_token(code)

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        digilocker_id = token_data.get("digilocker_id", "")

        if not access_token:
            raise DigiLockerException(detail="DigiLocker token exchange failed: no access token received.")

        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        now = datetime.now(timezone.utc)

        # Store encrypted credentials
        await employee_repository.update_digilocker_credentials(
            db,
            employee_id,
            digilocker_id=fernet_encryption.encrypt_or_none(digilocker_id),
            access_token=fernet_encryption.encrypt(access_token),
            refresh_token=fernet_encryption.encrypt_or_none(refresh_token),
            token_expiry=token_expiry,
            status=DigiLockerStatus.LINKED.value,
            linked_at=now,
        )

        # Audit log
        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id or employee_id,
            action="DIGILOCKER_LINK",
            entity_type="Employee",
            entity_id=employee_id,
            new_value={"digilocker_status": DigiLockerStatus.LINKED.value},
        )

        # Notification
        await notification_service.create_in_app_notification(
            db=db,
            user_id=employee_id,
            title="DigiLocker Linked",
            message="Your DigiLocker account has been successfully linked.",
        )

        logger.info("DigiLocker linked for employee %d", employee_id)
        return {
            "message": "DigiLocker account linked successfully.",
            "employee_id": employee_id,
            "digilocker_status": DigiLockerStatus.LINKED.value,
        }

    @staticmethod
    async def get_link_status(db: AsyncSession, employee_id: int) -> dict[str, Any]:
        """Return the current DigiLocker link status for an employee."""
        DigiLockerService.ensure_configured()

        employee = await employee_repository.get(db, employee_id)
        if not employee:
            raise NotFoundException(detail="Employee not found.")

        is_linked = employee.digilocker_status == DigiLockerStatus.LINKED.value
        token_valid = False
        if is_linked and employee.digilocker_token_expiry:
            token_valid = employee.digilocker_token_expiry > datetime.now(timezone.utc)

        return {
            "is_linked": is_linked,
            "digilocker_id": fernet_encryption.decrypt_or_none(employee.digilocker_id),
            "status": employee.digilocker_status,
            "linked_at": employee.digilocker_linked_at,
            "token_valid": token_valid,
        }

    @staticmethod
    async def fetch_documents(db: AsyncSession, employee_id: int) -> dict[str, Any]:
        """Fetch the list of issued documents from DigiLocker."""
        DigiLockerService.ensure_configured()

        employee = await employee_repository.get(db, employee_id)
        if not employee:
            raise NotFoundException(detail="Employee not found.")

        if employee.digilocker_status != DigiLockerStatus.LINKED.value:
            raise BadRequestException(detail="DigiLocker account is not linked. Please link your account first.")

        if not employee.digilocker_access_token:
            raise BadRequestException(detail="No DigiLocker access token found. Please re-link your account.")

        # Check token expiry
        if employee.digilocker_token_expiry and employee.digilocker_token_expiry <= datetime.now(timezone.utc):
            raise BadRequestException(
                detail="DigiLocker access token has expired. Please refresh your token or re-link."
            )

        access_token = fernet_encryption.decrypt(employee.digilocker_access_token)
        documents = await DigiLockerService._fetch_issued_documents(access_token)

        logger.info("Fetched %d documents from DigiLocker for employee %d", len(documents), employee_id)
        return {"documents": documents, "total": len(documents)}

    @staticmethod
    async def refresh_token(db: AsyncSession, employee_id: int) -> dict[str, Any]:
        """Refresh the DigiLocker access token using the stored refresh token."""
        DigiLockerService.ensure_configured()

        employee = await employee_repository.get(db, employee_id)
        if not employee:
            raise NotFoundException(detail="Employee not found.")

        if employee.digilocker_status != DigiLockerStatus.LINKED.value:
            raise BadRequestException(detail="DigiLocker account is not linked.")

        if not employee.digilocker_refresh_token:
            raise BadRequestException(detail="No refresh token available. Please re-link your DigiLocker account.")

        refresh_tok = fernet_encryption.decrypt(employee.digilocker_refresh_token)
        token_data = await DigiLockerService._refresh_access_token(refresh_tok)

        new_access_token = token_data.get("access_token")
        if not new_access_token:
            raise DigiLockerException(detail="Token refresh failed: no new access token received.")

        expires_in = token_data.get("expires_in", 3600)
        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

        new_refresh_token = token_data.get("refresh_token")
        await employee_repository.update_digilocker_credentials(
            db,
            employee_id,
            access_token=fernet_encryption.encrypt(new_access_token),
            refresh_token=fernet_encryption.encrypt_or_none(new_refresh_token) if new_refresh_token else None,
            token_expiry=token_expiry,
        )

        logger.info("DigiLocker token refreshed for employee %d", employee_id)
        return {
            "message": "DigiLocker access token refreshed successfully.",
            "token_valid": True,
            "expires_at": token_expiry,
        }

    @staticmethod
    async def unlink_account(
        db: AsyncSession, employee_id: int, actor_id: Optional[int] = None
    ) -> dict[str, str]:
        """Unlink a DigiLocker account by clearing all stored credentials."""
        DigiLockerService.ensure_configured()

        employee = await employee_repository.get(db, employee_id)
        if not employee:
            raise NotFoundException(detail="Employee not found.")

        old_status = employee.digilocker_status

        await employee_repository.clear_digilocker_credentials(db, employee_id)

        # Audit log
        await audit_log_service.log_action(
            db=db,
            actor_id=actor_id or employee_id,
            action="DIGILOCKER_UNLINK",
            entity_type="Employee",
            entity_id=employee_id,
            old_value={"digilocker_status": old_status},
            new_value={"digilocker_status": None},
        )

        # Notification
        await notification_service.create_in_app_notification(
            db=db,
            user_id=employee_id,
            title="DigiLocker Unlinked",
            message="Your DigiLocker account has been unlinked from your profile.",
        )

        logger.info("DigiLocker unlinked for employee %d", employee_id)
        return {"message": "DigiLocker account unlinked successfully."}

    # -------------------------------------------------------------------------
    # Private methods — isolated external API calls
    # -------------------------------------------------------------------------

    @staticmethod
    async def _exchange_code_for_token(code: str) -> dict[str, Any]:
        """Exchange an authorization code for access and refresh tokens."""
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.DIGILOCKER_CLIENT_ID,
            "client_secret": settings.DIGILOCKER_CLIENT_SECRET,
            "redirect_uri": settings.DIGILOCKER_REDIRECT_URI,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(settings.DIGILOCKER_TOKEN_URL, data=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("DigiLocker token exchange failed: %s — %s", e.response.status_code, e.response.text)
            raise DigiLockerException(
                detail=f"DigiLocker token exchange failed (HTTP {e.response.status_code})."
            )
        except httpx.RequestError as e:
            logger.error("DigiLocker token exchange request error: %s", str(e))
            raise DigiLockerException(detail="Unable to connect to DigiLocker service.")

    @staticmethod
    async def _refresh_access_token(refresh_token: str) -> dict[str, Any]:
        """Use a refresh token to obtain a new access token."""
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.DIGILOCKER_CLIENT_ID,
            "client_secret": settings.DIGILOCKER_CLIENT_SECRET,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(settings.DIGILOCKER_TOKEN_URL, data=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("DigiLocker token refresh failed: %s — %s", e.response.status_code, e.response.text)
            raise DigiLockerException(
                detail=f"DigiLocker token refresh failed (HTTP {e.response.status_code})."
            )
        except httpx.RequestError as e:
            logger.error("DigiLocker token refresh request error: %s", str(e))
            raise DigiLockerException(detail="Unable to connect to DigiLocker service.")

    @staticmethod
    async def _fetch_issued_documents(access_token: str) -> list[dict[str, Any]]:
        """Fetch the list of issued documents from the DigiLocker API."""
        url = f"{settings.DIGILOCKER_API_BASE_URL}/files/issued"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                # DigiLocker returns documents in an 'items' array
                items = data.get("items", data.get("documents", []))
                return [
                    {
                        "name": item.get("name", "Unknown"),
                        "doc_type": item.get("type", item.get("doctype", "OTHER")),
                        "issuer": item.get("issuer", item.get("issuerid", "Unknown")),
                        "uri": item.get("uri", item.get("id", "")),
                        "date": item.get("date", item.get("issuedon", None)),
                    }
                    for item in items
                ]
        except httpx.HTTPStatusError as e:
            logger.error("DigiLocker document fetch failed: %s — %s", e.response.status_code, e.response.text)
            raise DigiLockerException(
                detail=f"Failed to fetch documents from DigiLocker (HTTP {e.response.status_code})."
            )
        except httpx.RequestError as e:
            logger.error("DigiLocker document fetch request error: %s", str(e))
            raise DigiLockerException(detail="Unable to connect to DigiLocker service.")


digilocker_service = DigiLockerService()
