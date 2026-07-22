"""Unit tests for the DigiLocker integration module.

All tests use mocks — no real database, external API, or DigiLocker credentials required.
"""

import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Encryption utility tests
# ---------------------------------------------------------------------------

class TestFernetEncryption:
    """Test the Fernet encryption utility."""

    def test_encrypt_decrypt_round_trip(self):
        from cryptography.fernet import Fernet
        from app.utils.encryption import FernetEncryption

        key = Fernet.generate_key().decode()
        enc = FernetEncryption(key=key)

        plaintext = "my-secret-access-token-12345"
        ciphertext = enc.encrypt(plaintext)

        assert ciphertext != plaintext
        assert enc.decrypt(ciphertext) == plaintext

    def test_encrypt_or_none_with_none(self):
        from cryptography.fernet import Fernet
        from app.utils.encryption import FernetEncryption

        key = Fernet.generate_key().decode()
        enc = FernetEncryption(key=key)

        assert enc.encrypt_or_none(None) is None

    def test_decrypt_or_none_with_none(self):
        from cryptography.fernet import Fernet
        from app.utils.encryption import FernetEncryption

        key = Fernet.generate_key().decode()
        enc = FernetEncryption(key=key)

        assert enc.decrypt_or_none(None) is None

    def test_encrypt_or_none_with_value(self):
        from cryptography.fernet import Fernet
        from app.utils.encryption import FernetEncryption

        key = Fernet.generate_key().decode()
        enc = FernetEncryption(key=key)

        result = enc.encrypt_or_none("hello")
        assert result is not None
        assert enc.decrypt(result) == "hello"

    def test_decrypt_with_wrong_key_raises(self):
        from cryptography.fernet import Fernet
        from app.utils.encryption import FernetEncryption

        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()
        enc1 = FernetEncryption(key=key1)
        enc2 = FernetEncryption(key=key2)

        ciphertext = enc1.encrypt("secret")
        with pytest.raises(ValueError, match="Decryption failed"):
            enc2.decrypt(ciphertext)

    def test_auto_generated_key_when_none(self):
        from app.utils.encryption import FernetEncryption

        enc = FernetEncryption(key=None)
        ciphertext = enc.encrypt("test")
        assert enc.decrypt(ciphertext) == "test"


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestDigiLockerSchemas:
    """Test Pydantic schema validation."""

    def test_authorize_response(self):
        from app.schemas.digilocker import DigiLockerAuthorizeResponse

        resp = DigiLockerAuthorizeResponse(
            authorization_url="https://example.com/auth", state="abc123"
        )
        assert resp.authorization_url == "https://example.com/auth"
        assert resp.state == "abc123"

    def test_callback_request(self):
        from app.schemas.digilocker import DigiLockerCallbackRequest

        req = DigiLockerCallbackRequest(code="auth-code", state="state-value")
        assert req.code == "auth-code"

    def test_status_response_defaults(self):
        from app.schemas.digilocker import DigiLockerStatusResponse

        resp = DigiLockerStatusResponse(is_linked=False)
        assert resp.is_linked is False
        assert resp.digilocker_id is None
        assert resp.token_valid is False

    def test_document_item(self):
        from app.schemas.digilocker import DigiLockerDocumentItem

        doc = DigiLockerDocumentItem(
            name="Aadhaar", doc_type="AADHAR", issuer="UIDAI", uri="/doc/123"
        )
        assert doc.name == "Aadhaar"
        assert doc.date is None

    def test_documents_response(self):
        from app.schemas.digilocker import DigiLockerDocumentsResponse, DigiLockerDocumentItem

        docs = DigiLockerDocumentsResponse(
            documents=[
                DigiLockerDocumentItem(
                    name="PAN", doc_type="PAN", issuer="IT Dept", uri="/doc/456"
                )
            ],
            total=1,
        )
        assert docs.total == 1
        assert len(docs.documents) == 1

    def test_token_refresh_response(self):
        from app.schemas.digilocker import DigiLockerTokenRefreshResponse

        resp = DigiLockerTokenRefreshResponse(
            message="Refreshed", token_valid=True, expires_at=datetime.now(timezone.utc)
        )
        assert resp.token_valid is True

    def test_unlink_response(self):
        from app.schemas.digilocker import DigiLockerUnlinkResponse

        resp = DigiLockerUnlinkResponse(message="Unlinked")
        assert resp.message == "Unlinked"


# ---------------------------------------------------------------------------
# Service layer tests
# ---------------------------------------------------------------------------

class TestDigiLockerService:
    """Test the DigiLockerService with mocked dependencies."""

    @patch("app.services.digilocker_service.settings")
    def test_ensure_configured_raises_when_not_configured(self, mock_settings):
        from app.core.exceptions import ServiceUnavailableException
        from app.services.digilocker_service import DigiLockerService

        mock_settings.digilocker_configured = False
        with pytest.raises(ServiceUnavailableException):
            DigiLockerService.ensure_configured()

    @patch("app.services.digilocker_service.settings")
    def test_ensure_configured_passes_when_configured(self, mock_settings):
        from app.services.digilocker_service import DigiLockerService

        mock_settings.digilocker_configured = True
        DigiLockerService.ensure_configured()  # Should not raise

    @pytest.mark.asyncio
    @patch("app.services.digilocker_service.settings")
    async def test_generate_authorization_url(self, mock_settings):
        from app.services.digilocker_service import DigiLockerService

        mock_settings.digilocker_configured = True
        mock_settings.DIGILOCKER_CLIENT_ID = "test-client-id"
        mock_settings.DIGILOCKER_REDIRECT_URI = "http://localhost/callback"
        mock_settings.DIGILOCKER_AUTH_URL = "https://digilocker.example.com/authorize"
        mock_settings.DIGILOCKER_SCOPES = "openid"

        result = await DigiLockerService.generate_authorization_url(employee_id=1)

        assert "authorization_url" in result
        assert "state" in result
        assert "test-client-id" in result["authorization_url"]
        assert "openid" in result["authorization_url"]

    @pytest.mark.asyncio
    @patch("app.services.digilocker_service.notification_service")
    @patch("app.services.digilocker_service.audit_log_service")
    @patch("app.services.digilocker_service.fernet_encryption")
    @patch("app.services.digilocker_service.employee_repository")
    @patch("app.services.digilocker_service.settings")
    async def test_handle_callback_success(
        self, mock_settings, mock_repo, mock_encryption, mock_audit, mock_notification
    ):
        from app.services.digilocker_service import DigiLockerService, _oauth_state_store

        mock_settings.digilocker_configured = True
        mock_settings.DIGILOCKER_CLIENT_ID = "test-id"
        mock_settings.DIGILOCKER_CLIENT_SECRET = "test-secret"
        mock_settings.DIGILOCKER_REDIRECT_URI = "http://localhost/callback"
        mock_settings.DIGILOCKER_TOKEN_URL = "https://digilocker.example.com/token"

        # Set up state store
        state = "test-state-123"
        _oauth_state_store[state] = {
            "employee_id": 42,
            "created_at": datetime.now(timezone.utc),
        }

        # Mock employee
        mock_employee = MagicMock()
        mock_employee.id = 42
        mock_repo.get = AsyncMock(return_value=mock_employee)
        mock_repo.update_digilocker_credentials = AsyncMock(return_value=mock_employee)

        # Mock encryption
        mock_encryption.encrypt = MagicMock(return_value="encrypted")
        mock_encryption.encrypt_or_none = MagicMock(return_value="encrypted")

        # Mock audit and notification
        mock_audit.log_action = AsyncMock()
        mock_notification.create_in_app_notification = AsyncMock()

        # Mock token exchange
        mock_db = AsyncMock()
        with patch.object(
            DigiLockerService,
            "_exchange_code_for_token",
            new_callable=AsyncMock,
            return_value={
                "access_token": "at-123",
                "refresh_token": "rt-456",
                "expires_in": 3600,
                "digilocker_id": "dl-789",
            },
        ):
            result = await DigiLockerService.handle_callback(
                db=mock_db, code="auth-code", state=state
            )

        assert result["digilocker_status"] == "LINKED"
        assert result["employee_id"] == 42
        mock_repo.update_digilocker_credentials.assert_awaited_once()
        mock_audit.log_action.assert_awaited_once()
        mock_notification.create_in_app_notification.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.services.digilocker_service.settings")
    async def test_handle_callback_invalid_state(self, mock_settings):
        from app.core.exceptions import BadRequestException
        from app.services.digilocker_service import DigiLockerService

        mock_settings.digilocker_configured = True
        mock_db = AsyncMock()

        with pytest.raises(BadRequestException):
            await DigiLockerService.handle_callback(
                db=mock_db, code="code", state="invalid-state"
            )

    @pytest.mark.asyncio
    @patch("app.services.digilocker_service.fernet_encryption")
    @patch("app.services.digilocker_service.employee_repository")
    @patch("app.services.digilocker_service.settings")
    async def test_get_link_status_linked(self, mock_settings, mock_repo, mock_encryption):
        from app.services.digilocker_service import DigiLockerService

        mock_settings.digilocker_configured = True

        mock_employee = MagicMock()
        mock_employee.digilocker_status = "LINKED"
        mock_employee.digilocker_id = "encrypted-id"
        mock_employee.digilocker_linked_at = datetime.now(timezone.utc)
        mock_employee.digilocker_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_repo.get = AsyncMock(return_value=mock_employee)
        mock_encryption.decrypt_or_none = MagicMock(return_value="dl-123")

        mock_db = AsyncMock()
        result = await DigiLockerService.get_link_status(db=mock_db, employee_id=1)

        assert result["is_linked"] is True
        assert result["token_valid"] is True
        assert result["digilocker_id"] == "dl-123"

    @pytest.mark.asyncio
    @patch("app.services.digilocker_service.fernet_encryption")
    @patch("app.services.digilocker_service.employee_repository")
    @patch("app.services.digilocker_service.settings")
    async def test_get_link_status_not_linked(self, mock_settings, mock_repo, mock_encryption):
        from app.services.digilocker_service import DigiLockerService

        mock_settings.digilocker_configured = True

        mock_employee = MagicMock()
        mock_employee.digilocker_status = None
        mock_employee.digilocker_id = None
        mock_employee.digilocker_linked_at = None
        mock_employee.digilocker_token_expiry = None
        mock_repo.get = AsyncMock(return_value=mock_employee)
        mock_encryption.decrypt_or_none = MagicMock(return_value=None)

        mock_db = AsyncMock()
        result = await DigiLockerService.get_link_status(db=mock_db, employee_id=1)

        assert result["is_linked"] is False
        assert result["token_valid"] is False

    @pytest.mark.asyncio
    @patch("app.services.digilocker_service.notification_service")
    @patch("app.services.digilocker_service.audit_log_service")
    @patch("app.services.digilocker_service.employee_repository")
    @patch("app.services.digilocker_service.settings")
    async def test_unlink_account(self, mock_settings, mock_repo, mock_audit, mock_notification):
        from app.services.digilocker_service import DigiLockerService

        mock_settings.digilocker_configured = True

        mock_employee = MagicMock()
        mock_employee.digilocker_status = "LINKED"
        mock_repo.get = AsyncMock(return_value=mock_employee)
        mock_repo.clear_digilocker_credentials = AsyncMock(return_value=mock_employee)
        mock_audit.log_action = AsyncMock()
        mock_notification.create_in_app_notification = AsyncMock()

        mock_db = AsyncMock()
        result = await DigiLockerService.unlink_account(db=mock_db, employee_id=1, actor_id=1)

        assert result["message"] == "DigiLocker account unlinked successfully."
        mock_repo.clear_digilocker_credentials.assert_awaited_once()
        mock_audit.log_action.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.services.digilocker_service.employee_repository")
    @patch("app.services.digilocker_service.settings")
    async def test_fetch_documents_not_linked(self, mock_settings, mock_repo):
        from app.core.exceptions import BadRequestException
        from app.services.digilocker_service import DigiLockerService

        mock_settings.digilocker_configured = True

        mock_employee = MagicMock()
        mock_employee.digilocker_status = None
        mock_repo.get = AsyncMock(return_value=mock_employee)

        mock_db = AsyncMock()
        with pytest.raises(BadRequestException):
            await DigiLockerService.fetch_documents(db=mock_db, employee_id=1)

    @pytest.mark.asyncio
    @patch("app.services.digilocker_service.employee_repository")
    @patch("app.services.digilocker_service.settings")
    async def test_fetch_documents_token_expired(self, mock_settings, mock_repo):
        from app.core.exceptions import BadRequestException
        from app.services.digilocker_service import DigiLockerService

        mock_settings.digilocker_configured = True

        mock_employee = MagicMock()
        mock_employee.digilocker_status = "LINKED"
        mock_employee.digilocker_access_token = "encrypted-token"
        mock_employee.digilocker_token_expiry = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_repo.get = AsyncMock(return_value=mock_employee)

        mock_db = AsyncMock()
        with pytest.raises(BadRequestException, match="expired"):
            await DigiLockerService.fetch_documents(db=mock_db, employee_id=1)

    @pytest.mark.asyncio
    @patch("app.services.digilocker_service.employee_repository")
    @patch("app.services.digilocker_service.settings")
    async def test_refresh_token_no_refresh_token(self, mock_settings, mock_repo):
        from app.core.exceptions import BadRequestException
        from app.services.digilocker_service import DigiLockerService

        mock_settings.digilocker_configured = True

        mock_employee = MagicMock()
        mock_employee.digilocker_status = "LINKED"
        mock_employee.digilocker_refresh_token = None
        mock_repo.get = AsyncMock(return_value=mock_employee)

        mock_db = AsyncMock()
        with pytest.raises(BadRequestException, match="No refresh token"):
            await DigiLockerService.refresh_token(db=mock_db, employee_id=1)

    @pytest.mark.asyncio
    @patch("app.services.digilocker_service.employee_repository")
    @patch("app.services.digilocker_service.settings")
    async def test_fetch_documents_employee_not_found(self, mock_settings, mock_repo):
        from app.core.exceptions import NotFoundException
        from app.services.digilocker_service import DigiLockerService

        mock_settings.digilocker_configured = True
        mock_repo.get = AsyncMock(return_value=None)

        mock_db = AsyncMock()
        with pytest.raises(NotFoundException):
            await DigiLockerService.fetch_documents(db=mock_db, employee_id=999)
