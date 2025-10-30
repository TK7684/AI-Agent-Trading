"""
Security and compliance module for the autonomous trading system.
Provides secure secret management, RBAC, audit trails, and compliance reporting.
"""

import base64
import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import jwt
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class Role(Enum):
    """User roles for RBAC system."""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    AUDITOR = "auditor"


class Permission(Enum):
    """System permissions."""
    READ_TRADES = "read_trades"
    WRITE_TRADES = "write_trades"
    READ_CONFIG = "read_config"
    WRITE_CONFIG = "write_config"
    READ_SECRETS = "read_secrets"
    WRITE_SECRETS = "write_secrets"
    READ_AUDIT = "read_audit"
    EXECUTE_ORDERS = "execute_orders"
    MANAGE_RISK = "manage_risk"
    VIEW_MONITORING = "view_monitoring"


class AuditEventType(Enum):
    """Types of audit events."""
    LOGIN = "login"
    LOGOUT = "logout"
    TRADE_EXECUTED = "trade_executed"
    CONFIG_CHANGED = "config_changed"
    SECRET_ACCESSED = "secret_accessed"
    RISK_LIMIT_CHANGED = "risk_limit_changed"
    SYSTEM_ERROR = "system_error"
    COMPLIANCE_REPORT = "compliance_report"


@dataclass
class AuditEvent:
    """Audit event record."""
    event_id: str
    event_type: AuditEventType
    user_id: str
    timestamp: datetime
    details: dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class User:
    """User account information."""
    user_id: str
    username: str
    role: Role
    permissions: list[Permission]
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions


class SecretManager:
    """Secure secret management using environment variables and optional Vault integration."""

    def __init__(self, vault_url: Optional[str] = None, vault_token: Optional[str] = None):
        self.vault_url = vault_url
        self.vault_token = vault_token
        self._encryption_key = self._get_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key)

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for local secret storage."""
        key_env = os.getenv('TRADING_SYSTEM_ENCRYPTION_KEY')
        if key_env:
            return base64.urlsafe_b64decode(key_env.encode())

        # Generate new key if not found
        key = Fernet.generate_key()
        logger.warning("Generated new encryption key. Set TRADING_SYSTEM_ENCRYPTION_KEY environment variable.")
        return key

    def get_secret(self, secret_name: str) -> Optional[str]:
        """Retrieve secret from environment or Vault."""
        # First try environment variables
        env_value = os.getenv(secret_name)
        if env_value:
            return env_value

        # Try Vault if configured
        if self.vault_url and self.vault_token:
            return self._get_vault_secret(secret_name)

        # Try encrypted local storage
        return self._get_encrypted_secret(secret_name)

    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Store secret securely."""
        try:
            if self.vault_url and self.vault_token:
                return self._set_vault_secret(secret_name, secret_value)
            else:
                return self._set_encrypted_secret(secret_name, secret_value)
        except Exception as e:
            logger.error(f"Failed to set secret {secret_name}: {e}")
            return False

    def _get_vault_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from HashiCorp Vault."""
        # Placeholder for Vault integration
        # In production, use hvac library for Vault API calls
        logger.info(f"Would retrieve {secret_name} from Vault at {self.vault_url}")
        return None

    def _set_vault_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set secret in HashiCorp Vault."""
        # Placeholder for Vault integration
        logger.info(f"Would store {secret_name} in Vault at {self.vault_url}")
        return True

    def _get_encrypted_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from encrypted local storage."""
        secrets_file = Path(".secrets.enc")
        if not secrets_file.exists():
            return None

        try:
            with open(secrets_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self._cipher.decrypt(encrypted_data)
            secrets = json.loads(decrypted_data.decode())
            return secrets.get(secret_name)
        except Exception as e:
            logger.error(f"Failed to decrypt secret {secret_name}: {e}")
            return None

    def _set_encrypted_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set secret in encrypted local storage."""
        secrets_file = Path(".secrets.enc")
        secrets = {}

        # Load existing secrets
        if secrets_file.exists():
            try:
                with open(secrets_file, 'rb') as f:
                    encrypted_data = f.read()
                decrypted_data = self._cipher.decrypt(encrypted_data)
                secrets = json.loads(decrypted_data.decode())
            except Exception as e:
                logger.warning(f"Could not load existing secrets: {e}")

        # Update secret
        secrets[secret_name] = secret_value

        # Encrypt and save
        try:
            encrypted_data = self._cipher.encrypt(json.dumps(secrets).encode())
            with open(secrets_file, 'wb') as f:
                f.write(encrypted_data)
            return True
        except Exception as e:
            logger.error(f"Failed to encrypt and save secrets: {e}")
            return False

    def rotate_secret(self, secret_name: str, new_value: str) -> bool:
        """Rotate a secret with audit logging."""
        old_exists = self.get_secret(secret_name) is not None
        success = self.set_secret(secret_name, new_value)

        if success:
            action = "rotated" if old_exists else "created"
            logger.info(f"Secret {secret_name} {action} successfully")

        return success


class RBACManager:
    """Role-Based Access Control manager."""

    def __init__(self, secret_manager: SecretManager):
        self.secret_manager = secret_manager
        self.users: dict[str, User] = {}
        self.role_permissions = self._initialize_role_permissions()
        self._load_users()

    def _initialize_role_permissions(self) -> dict[Role, list[Permission]]:
        """Initialize default role permissions."""
        return {
            Role.ADMIN: [p for p in Permission],  # All permissions
            Role.TRADER: [
                Permission.READ_TRADES,
                Permission.WRITE_TRADES,
                Permission.READ_CONFIG,
                Permission.EXECUTE_ORDERS,
                Permission.MANAGE_RISK,
                Permission.VIEW_MONITORING,
            ],
            Role.VIEWER: [
                Permission.READ_TRADES,
                Permission.READ_CONFIG,
                Permission.VIEW_MONITORING,
            ],
            Role.AUDITOR: [
                Permission.READ_TRADES,
                Permission.READ_CONFIG,
                Permission.READ_AUDIT,
                Permission.VIEW_MONITORING,
            ],
        }

    def _load_users(self):
        """Load users from configuration."""
        # In production, load from secure database
        # For now, create default admin user
        admin_user = User(
            user_id="admin",
            username="admin",
            role=Role.ADMIN,
            permissions=self.role_permissions[Role.ADMIN],
            created_at=datetime.now(UTC)
        )
        self.users["admin"] = admin_user

    def create_user(self, username: str, role: Role) -> User:
        """Create new user with specified role."""
        user_id = f"user_{int(time.time())}"
        user = User(
            user_id=user_id,
            username=username,
            role=role,
            permissions=self.role_permissions[role],
            created_at=datetime.now(UTC)
        )
        self.users[user_id] = user
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user credentials."""
        # In production, use proper password hashing and verification
        for user in self.users.values():
            if user.username == username and user.is_active:
                user.last_login = datetime.now(UTC)
                return user
        return None

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has specific permission."""
        user = self.users.get(user_id)
        if not user or not user.is_active:
            return False
        return user.has_permission(permission)

    def generate_signed_config(self, config: dict[str, Any], user_id: str) -> str:
        """Generate signed configuration for tamper detection."""
        signing_key = self.secret_manager.get_secret("CONFIG_SIGNING_KEY")
        if not signing_key:
            signing_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
            self.secret_manager.set_secret("CONFIG_SIGNING_KEY", signing_key)

        payload = {
            "config": config,
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        token = jwt.encode(payload, signing_key, algorithm="HS256")
        return token

    def verify_signed_config(self, signed_config: str) -> Optional[dict[str, Any]]:
        """Verify signed configuration integrity."""
        signing_key = self.secret_manager.get_secret("CONFIG_SIGNING_KEY")
        if not signing_key:
            return None

        try:
            payload = jwt.decode(signed_config, signing_key, algorithms=["HS256"])
            return payload.get("config")
        except jwt.InvalidTokenError:
            logger.error("Invalid signed configuration token")
            return None


class AuditLogger:
    """Tamper-evident audit logging system."""

    def __init__(self, log_file: str = "audit.jsonl"):
        self.log_file = Path(log_file)
        self.hash_chain: list[str] = []
        self._load_hash_chain()

    def _load_hash_chain(self):
        """Load existing hash chain for tamper detection."""
        if self.log_file.exists():
            try:
                with open(self.log_file) as f:
                    for line in f:
                        event_data = json.loads(line.strip())
                        if 'hash' in event_data:
                            self.hash_chain.append(event_data['hash'])
            except Exception as e:
                logger.error(f"Failed to load hash chain: {e}")

    def _calculate_hash(self, event: AuditEvent, previous_hash: str = "") -> str:
        """Calculate hash for tamper-evident chain."""
        event_str = json.dumps(event.to_dict(), sort_keys=True)
        combined = f"{previous_hash}{event_str}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def log_event(self, event: AuditEvent) -> bool:
        """Log audit event with hash chain."""
        try:
            previous_hash = self.hash_chain[-1] if self.hash_chain else ""
            event_hash = self._calculate_hash(event, previous_hash)

            log_entry = event.to_dict()
            log_entry['hash'] = event_hash
            log_entry['previous_hash'] = previous_hash

            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

            self.hash_chain.append(event_hash)
            return True
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False

    def verify_integrity(self) -> bool:
        """Verify audit log integrity using hash chain."""
        if not self.log_file.exists():
            return True

        try:
            previous_hash = ""
            with open(self.log_file) as f:
                for line_num, line in enumerate(f, 1):
                    event_data = json.loads(line.strip())
                    stored_hash = event_data.pop('hash', '')
                    stored_previous = event_data.pop('previous_hash', '')

                    # Reconstruct event
                    event = AuditEvent(
                        event_id=event_data['event_id'],
                        event_type=AuditEventType(event_data['event_type']),
                        user_id=event_data['user_id'],
                        timestamp=datetime.fromisoformat(event_data['timestamp']),
                        details=event_data['details'],
                        ip_address=event_data.get('ip_address'),
                        user_agent=event_data.get('user_agent'),
                        session_id=event_data.get('session_id')
                    )

                    calculated_hash = self._calculate_hash(event, previous_hash)

                    if calculated_hash != stored_hash:
                        logger.error(f"Hash mismatch at line {line_num}")
                        return False

                    if stored_previous != previous_hash:
                        logger.error(f"Chain break at line {line_num}")
                        return False

                    previous_hash = stored_hash

            return True
        except Exception as e:
            logger.error(f"Failed to verify audit log integrity: {e}")
            return False


class ComplianceReporter:
    """Generate compliance reports for different jurisdictions."""

    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
        self.jurisdiction_rules = self._load_jurisdiction_rules()

    def _load_jurisdiction_rules(self) -> dict[str, dict[str, Any]]:
        """Load compliance rules for different jurisdictions."""
        return {
            "US": {
                "trade_reporting_required": True,
                "max_retention_days": 2555,  # 7 years
                "required_fields": ["trade_id", "symbol", "quantity", "price", "timestamp", "user_id"],
                "audit_frequency": "daily"
            },
            "EU": {
                "trade_reporting_required": True,
                "max_retention_days": 1825,  # 5 years
                "required_fields": ["trade_id", "symbol", "quantity", "price", "timestamp", "user_id", "mifid_flags"],
                "audit_frequency": "daily"
            },
            "UK": {
                "trade_reporting_required": True,
                "max_retention_days": 2190,  # 6 years
                "required_fields": ["trade_id", "symbol", "quantity", "price", "timestamp", "user_id"],
                "audit_frequency": "weekly"
            }
        }

    def generate_trade_report(self, jurisdiction: str, start_date: datetime, end_date: datetime) -> dict[str, Any]:
        """Generate trade compliance report for specific jurisdiction."""
        rules = self.jurisdiction_rules.get(jurisdiction, {})
        required_fields = rules.get("required_fields", [])

        # Read audit log and filter trade events
        trades = []
        if self.audit_logger.log_file.exists():
            with open(self.audit_logger.log_file) as f:
                for line in f:
                    event_data = json.loads(line.strip())
                    if event_data.get('event_type') == AuditEventType.TRADE_EXECUTED.value:
                        event_time = datetime.fromisoformat(event_data['timestamp'])
                        if start_date <= event_time <= end_date:
                            trade_details = event_data.get('details', {})
                            # Ensure all required fields are present
                            if all(field in trade_details for field in required_fields):
                                trades.append(trade_details)

        report = {
            "jurisdiction": jurisdiction,
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_trades": len(trades),
            "trades": trades,
            "compliance_status": "COMPLIANT" if trades else "NO_TRADES",
            "generated_at": datetime.now(UTC).isoformat(),
            "rules_applied": rules
        }

        return report

    def generate_audit_summary(self, start_date: datetime, end_date: datetime) -> dict[str, Any]:
        """Generate audit summary report."""
        event_counts = {}
        user_activity = {}

        if self.audit_logger.log_file.exists():
            with open(self.audit_logger.log_file) as f:
                for line in f:
                    event_data = json.loads(line.strip())
                    event_time = datetime.fromisoformat(event_data['timestamp'])

                    if start_date <= event_time <= end_date:
                        event_type = event_data.get('event_type', 'unknown')
                        user_id = event_data.get('user_id', 'unknown')

                        event_counts[event_type] = event_counts.get(event_type, 0) + 1

                        if user_id not in user_activity:
                            user_activity[user_id] = {}
                        user_activity[user_id][event_type] = user_activity[user_id].get(event_type, 0) + 1

        return {
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "event_summary": event_counts,
            "user_activity": user_activity,
            "total_events": sum(event_counts.values()),
            "generated_at": datetime.now(UTC).isoformat()
        }


class SecurityManager:
    """Main security manager coordinating all security components."""

    def __init__(self, vault_url: Optional[str] = None, vault_token: Optional[str] = None):
        self.secret_manager = SecretManager(vault_url, vault_token)
        self.rbac_manager = RBACManager(self.secret_manager)
        self.audit_logger = AuditLogger()
        self.compliance_reporter = ComplianceReporter(self.audit_logger)

        # Initialize security
        self._initialize_security()

    def _initialize_security(self):
        """Initialize security components."""
        # Verify audit log integrity on startup
        if not self.audit_logger.verify_integrity():
            logger.error("Audit log integrity check failed!")
            raise SecurityError("Audit log has been tampered with")

        # Log system startup
        startup_event = AuditEvent(
            event_id=f"startup_{int(time.time())}",
            event_type=AuditEventType.SYSTEM_ERROR,  # Using as system event
            user_id="system",
            timestamp=datetime.now(UTC),
            details={"action": "system_startup", "component": "security_manager"}
        )
        self.audit_logger.log_event(startup_event)

    def authenticate_and_authorize(self, username: str, password: str, required_permission: Permission) -> Optional[User]:
        """Authenticate user and check authorization."""
        user = self.rbac_manager.authenticate_user(username, password)
        if not user:
            # Log failed login
            login_event = AuditEvent(
                event_id=f"login_fail_{int(time.time())}",
                event_type=AuditEventType.LOGIN,
                user_id=username,
                timestamp=datetime.now(UTC),
                details={"success": False, "reason": "invalid_credentials"}
            )
            self.audit_logger.log_event(login_event)
            return None

        if not user.has_permission(required_permission):
            # Log unauthorized access attempt
            auth_event = AuditEvent(
                event_id=f"auth_fail_{int(time.time())}",
                event_type=AuditEventType.LOGIN,
                user_id=user.user_id,
                timestamp=datetime.now(UTC),
                details={"success": False, "reason": "insufficient_permissions", "required": required_permission.value}
            )
            self.audit_logger.log_event(auth_event)
            return None

        # Log successful login
        login_event = AuditEvent(
            event_id=f"login_success_{int(time.time())}",
            event_type=AuditEventType.LOGIN,
            user_id=user.user_id,
            timestamp=datetime.now(UTC),
            details={"success": True, "permissions": [p.value for p in user.permissions]}
        )
        self.audit_logger.log_event(login_event)

        return user

    def log_trade_execution(self, user_id: str, trade_details: dict[str, Any]):
        """Log trade execution for audit trail."""
        trade_event = AuditEvent(
            event_id=f"trade_{trade_details.get('trade_id', int(time.time()))}",
            event_type=AuditEventType.TRADE_EXECUTED,
            user_id=user_id,
            timestamp=datetime.now(UTC),
            details=trade_details
        )
        self.audit_logger.log_event(trade_event)

    def log_config_change(self, user_id: str, config_name: str, old_value: Any, new_value: Any):
        """Log configuration changes."""
        config_event = AuditEvent(
            event_id=f"config_{int(time.time())}",
            event_type=AuditEventType.CONFIG_CHANGED,
            user_id=user_id,
            timestamp=datetime.now(UTC),
            details={
                "config_name": config_name,
                "old_value": str(old_value),
                "new_value": str(new_value)
            }
        )
        self.audit_logger.log_event(config_event)

    def generate_compliance_report(self, jurisdiction: str, start_date: datetime, end_date: datetime) -> dict[str, Any]:
        """Generate compliance report and log the action."""
        report = self.compliance_reporter.generate_trade_report(jurisdiction, start_date, end_date)

        # Log report generation
        report_event = AuditEvent(
            event_id=f"report_{int(time.time())}",
            event_type=AuditEventType.COMPLIANCE_REPORT,
            user_id="system",
            timestamp=datetime.now(UTC),
            details={
                "jurisdiction": jurisdiction,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "trade_count": report["total_trades"]
            }
        )
        self.audit_logger.log_event(report_event)

        return report


class SecurityError(Exception):
    """Security-related exception."""
    pass


class RateLimiter:
    """API rate limiting implementation."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = {}

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()

        if client_id not in self.requests:
            self.requests[client_id] = []

        # Remove old requests outside the window
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < self.window_seconds
        ]

        # Check if under limit
        if len(self.requests[client_id]) < self.max_requests:
            self.requests[client_id].append(now)
            return True

        return False

    def get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for client."""
        if client_id not in self.requests:
            return self.max_requests

        now = time.time()
        recent_requests = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < self.window_seconds
        ]

        return max(0, self.max_requests - len(recent_requests))
