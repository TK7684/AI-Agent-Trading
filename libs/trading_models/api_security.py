"""
API security components including request validation, rate limiting, and secure communication.
"""

import hashlib
import hmac
import json
import logging
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import wraps
from typing import Any, Optional

from .security import Permission, RateLimiter, SecurityError, SecurityManager

logger = logging.getLogger(__name__)


@dataclass
class APIRequest:
    """API request structure for validation."""
    method: str
    path: str
    headers: dict[str, str]
    body: Optional[str] = None
    client_ip: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


@dataclass
class ValidationRule:
    """Request validation rule."""
    field_name: str
    required: bool = True
    data_type: type = str
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[list[Any]] = None
    pattern: Optional[str] = None


class RequestValidator:
    """Validates API requests against defined rules."""

    def __init__(self):
        self.validation_rules = self._initialize_validation_rules()

    def _initialize_validation_rules(self) -> dict[str, list[ValidationRule]]:
        """Initialize validation rules for different endpoints."""
        return {
            "/api/v1/trades": [
                ValidationRule("symbol", required=True, data_type=str, min_length=1, max_length=20),
                ValidationRule("side", required=True, allowed_values=["BUY", "SELL"]),
                ValidationRule("quantity", required=True, data_type=float),
                ValidationRule("price", required=False, data_type=float),
                ValidationRule("order_type", required=True, allowed_values=["MARKET", "LIMIT", "STOP"]),
            ],
            "/api/v1/positions": [
                ValidationRule("symbol", required=False, data_type=str, max_length=20),
            ],
            "/api/v1/config": [
                ValidationRule("key", required=True, data_type=str, min_length=1, max_length=100),
                ValidationRule("value", required=True),
            ],
            "/api/v1/risk": [
                ValidationRule("max_position_size", required=False, data_type=float),
                ValidationRule("max_daily_loss", required=False, data_type=float),
                ValidationRule("leverage_limit", required=False, data_type=float),
            ]
        }

    def validate_request(self, request: APIRequest) -> dict[str, Any]:
        """Validate API request and return validation result."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Basic request validation
        if not request.method:
            result["valid"] = False
            result["errors"].append("Missing HTTP method")

        if not request.path:
            result["valid"] = False
            result["errors"].append("Missing request path")

        # Content-Type validation for POST/PUT requests
        if request.method in ["POST", "PUT"] and request.body:
            content_type = request.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                result["warnings"].append("Expected application/json content type")

        # Path-specific validation
        rules = self.validation_rules.get(request.path, [])
        if rules and request.body:
            try:
                body_data = json.loads(request.body) if request.body else {}
                self._validate_body(body_data, rules, result)
            except json.JSONDecodeError:
                result["valid"] = False
                result["errors"].append("Invalid JSON in request body")

        # Security headers validation
        self._validate_security_headers(request.headers, result)

        return result

    def _validate_body(self, body_data: dict[str, Any], rules: list[ValidationRule], result: dict[str, Any]):
        """Validate request body against rules."""
        for rule in rules:
            field_value = body_data.get(rule.field_name)

            # Required field check
            if rule.required and field_value is None:
                result["valid"] = False
                result["errors"].append(f"Required field '{rule.field_name}' is missing")
                continue

            if field_value is None:
                continue

            # Type validation
            if not isinstance(field_value, rule.data_type):
                result["valid"] = False
                result["errors"].append(f"Field '{rule.field_name}' must be of type {rule.data_type.__name__}")
                continue

            # String length validation
            if rule.data_type == str:
                if rule.min_length and len(field_value) < rule.min_length:
                    result["valid"] = False
                    result["errors"].append(f"Field '{rule.field_name}' must be at least {rule.min_length} characters")

                if rule.max_length and len(field_value) > rule.max_length:
                    result["valid"] = False
                    result["errors"].append(f"Field '{rule.field_name}' must be at most {rule.max_length} characters")

            # Allowed values validation
            if rule.allowed_values and field_value not in rule.allowed_values:
                result["valid"] = False
                result["errors"].append(f"Field '{rule.field_name}' must be one of: {rule.allowed_values}")

            # Numeric validation
            if rule.data_type in [int, float]:
                if isinstance(field_value, (int, float)) and field_value < 0:
                    result["warnings"].append(f"Field '{rule.field_name}' has negative value")

    def _validate_security_headers(self, headers: dict[str, str], result: dict[str, Any]):
        """Validate security-related headers."""
        # Check for required security headers
        required_headers = ["Authorization", "X-Request-ID"]
        for header in required_headers:
            if header not in headers:
                result["warnings"].append(f"Missing recommended header: {header}")

        # Validate Authorization header format
        auth_header = headers.get("Authorization", "")
        if auth_header and not (auth_header.startswith("Bearer ") or auth_header.startswith("Basic ")):
            result["warnings"].append("Authorization header should use Bearer or Basic scheme")


class APISecurityMiddleware:
    """Security middleware for API endpoints."""

    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
        self.validator = RequestValidator()
        self.blocked_ips: set = set()
        self.suspicious_activity: dict[str, list[float]] = {}

    def process_request(self, request: APIRequest) -> dict[str, Any]:
        """Process incoming request through security checks."""
        result = {
            "allowed": True,
            "status_code": 200,
            "message": "OK",
            "headers": {}
        }

        # IP blocking check
        if request.client_ip in self.blocked_ips:
            result.update({
                "allowed": False,
                "status_code": 403,
                "message": "IP address blocked"
            })
            return result

        # Rate limiting
        client_id = request.client_ip or "unknown"
        if not self.rate_limiter.is_allowed(client_id):
            result.update({
                "allowed": False,
                "status_code": 429,
                "message": "Rate limit exceeded",
                "headers": {
                    "Retry-After": "60",
                    "X-RateLimit-Remaining": "0"
                }
            })
            self._log_suspicious_activity(client_id, "rate_limit_exceeded")
            return result

        # Add rate limit headers
        remaining = self.rate_limiter.get_remaining_requests(client_id)
        result["headers"]["X-RateLimit-Remaining"] = str(remaining)

        # Request validation
        validation_result = self.validator.validate_request(request)
        if not validation_result["valid"]:
            result.update({
                "allowed": False,
                "status_code": 400,
                "message": "Invalid request",
                "validation_errors": validation_result["errors"]
            })
            return result

        # Authentication and authorization
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            result.update({
                "allowed": False,
                "status_code": 401,
                "message": "Authentication required"
            })
            return result

        # Extract and validate token/credentials
        user = self._authenticate_request(auth_header, request.path)
        if not user:
            result.update({
                "allowed": False,
                "status_code": 401,
                "message": "Invalid authentication"
            })
            self._log_suspicious_activity(client_id, "invalid_auth")
            return result

        # Add user context to result
        result["user"] = user
        result["headers"]["X-User-ID"] = user.user_id

        return result

    def _authenticate_request(self, auth_header: str, path: str):
        """Authenticate request and check permissions."""
        # Extract token from header
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # In production, validate JWT token
            # For now, use simple token-based auth
            if token == "admin_token":
                return self.security_manager.rbac_manager.users.get("admin")

        return None

    def _log_suspicious_activity(self, client_id: str, activity_type: str):
        """Log and track suspicious activity."""
        now = time.time()

        if client_id not in self.suspicious_activity:
            self.suspicious_activity[client_id] = []

        self.suspicious_activity[client_id].append(now)

        # Clean old entries (last hour)
        self.suspicious_activity[client_id] = [
            timestamp for timestamp in self.suspicious_activity[client_id]
            if now - timestamp < 3600
        ]

        # Block IP if too many suspicious activities
        if len(self.suspicious_activity[client_id]) > 10:
            self.blocked_ips.add(client_id)
            logger.warning(f"Blocked IP {client_id} due to suspicious activity: {activity_type}")

    def unblock_ip(self, ip_address: str):
        """Manually unblock an IP address."""
        self.blocked_ips.discard(ip_address)
        if ip_address in self.suspicious_activity:
            del self.suspicious_activity[ip_address]


class SecureCommunication:
    """Secure communication utilities for inter-service communication."""

    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
        self.service_keys = {}
        self._initialize_service_keys()

    def _initialize_service_keys(self):
        """Initialize service-to-service authentication keys."""
        services = ["orchestrator", "execution-gateway", "risk-manager", "data-engine"]

        for service in services:
            key_name = f"{service.upper()}_SERVICE_KEY"
            service_key = self.security_manager.secret_manager.get_secret(key_name)

            if not service_key:
                # Generate new service key
                import secrets
                service_key = secrets.token_urlsafe(32)
                self.security_manager.secret_manager.set_secret(key_name, service_key)

            self.service_keys[service] = service_key

    def create_service_token(self, service_name: str, target_service: str, expires_in: int = 3600) -> str:
        """Create JWT token for service-to-service communication."""
        if service_name not in self.service_keys:
            raise SecurityError(f"Unknown service: {service_name}")

        import jwt

        payload = {
            "iss": service_name,
            "aud": target_service,
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in,
            "service": True
        }

        token = jwt.encode(payload, self.service_keys[service_name], algorithm="HS256")
        return token

    def verify_service_token(self, token: str, expected_service: str) -> bool:
        """Verify service-to-service JWT token."""
        try:
            import jwt

            # Decode without verification first to get issuer
            unverified = jwt.decode(token, options={"verify_signature": False})
            issuer = unverified.get("iss")

            if issuer not in self.service_keys:
                return False

            # Verify with service key
            payload = jwt.decode(token, self.service_keys[issuer], algorithms=["HS256"])

            # Check if token is for expected service
            if payload.get("aud") != expected_service:
                return False

            # Check if it's a service token
            if not payload.get("service"):
                return False

            return True
        except jwt.InvalidTokenError:
            return False

    def create_signed_request(self, service_name: str, method: str, url: str, body: str = "") -> dict[str, str]:
        """Create signed HTTP request headers."""
        if service_name not in self.service_keys:
            raise SecurityError(f"Unknown service: {service_name}")

        timestamp = str(int(time.time()))
        nonce = str(time.time_ns())

        # Create signature
        message = f"{method}\n{url}\n{body}\n{timestamp}\n{nonce}"
        signature = hmac.new(
            self.service_keys[service_name].encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return {
            "X-Service-Name": service_name,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature,
            "Content-Type": "application/json"
        }

    def verify_signed_request(self, headers: dict[str, str], method: str, url: str, body: str = "") -> bool:
        """Verify signed HTTP request."""
        service_name = headers.get("X-Service-Name")
        timestamp = headers.get("X-Timestamp")
        nonce = headers.get("X-Nonce")
        signature = headers.get("X-Signature")

        if not all([service_name, timestamp, nonce, signature]):
            return False

        if service_name not in self.service_keys:
            return False

        # Check timestamp (prevent replay attacks)
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - request_time) > 300:  # 5 minutes tolerance
                return False
        except ValueError:
            return False

        # Verify signature
        message = f"{method}\n{url}\n{body}\n{timestamp}\n{nonce}"
        expected_signature = hmac.new(
            self.service_keys[service_name].encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def create_tls_context(self, cert_file: Optional[str] = None, key_file: Optional[str] = None) -> ssl.SSLContext:
        """Create secure TLS context for HTTPS communication."""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

        # Configure security settings
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')

        # Load certificates if provided
        if cert_file and key_file:
            context.load_cert_chain(cert_file, key_file)

        return context


def require_permission(permission: Permission):
    """Decorator to require specific permission for API endpoints."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user from request context
            # This would be set by the middleware
            user = kwargs.get('user')
            if not user or not user.has_permission(permission):
                raise SecurityError(f"Permission {permission.value} required")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """Decorator to add rate limiting to API endpoints."""
    limiter = RateLimiter(max_requests, window_seconds)

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_id = kwargs.get('client_ip', 'unknown')
            if not limiter.is_allowed(client_id):
                raise SecurityError("Rate limit exceeded")
            return func(*args, **kwargs)
        return wrapper
    return decorator
