"""
Configuration Manager with Optimization Features

This module provides a high-performance configuration management system with:
- Environment-based configuration
- Hot reloading capabilities
- Validation and type safety
- Caching and optimization
- Secure secret management
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Optional, TypeVar

import toml
import yaml
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from pydantic import BaseModel
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

# Load .env file for native deployment support
# Tries .env.local first, then .env, then .env.native
for env_file in ['.env.local', '.env', '.env.native']:
    if Path(env_file).exists():
        load_dotenv(env_file, override=True)
        logger.info(f"Loaded environment from {env_file}")
        break

T = TypeVar('T', bound=BaseModel)


def cache_result(ttl_seconds: int = 300):
    """Decorator to cache function results with TTL."""
    def decorator(func):
        cache = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            current_time = time.time()

            # Check if cached result is still valid
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < ttl_seconds:
                    return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)

            # Clean up expired cache entries
            expired_keys = [k for k, (_, ts) in cache.items() if current_time - ts >= ttl_seconds]
            for k in expired_keys:
                del cache[k]

            return result

        return wrapper
    return decorator


@dataclass
class DatabaseConfig(BaseModel):
    """Database configuration with connection pooling."""
    host: str = "localhost"
    port: int = 5432
    database: str = "trading_system"
    username: str = "trading_user"
    password: str = ""
    max_connections: int = 20
    min_connections: int = 5
    connection_timeout: int = 30
    idle_timeout: int = 300
    max_lifetime: int = 3600

    @property
    def connection_string(self) -> str:
        """Get database connection string."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class RedisConfig(BaseModel):
    """Redis configuration with clustering support."""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: str = ""
    max_connections: int = 50
    connection_timeout: int = 5
    read_timeout: int = 30
    write_timeout: int = 30
    retry_on_timeout: bool = True
    health_check_interval: int = 30

    @property
    def connection_url(self) -> str:
        """Get Redis connection URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.database}"
        return f"redis://{self.host}:{self.port}/{self.database}"


@dataclass
class LLMConfig(BaseModel):
    """LLM provider configuration."""
    providers: dict[str, dict[str, Any]] = field(default_factory=dict)
    default_model: str = "claude-3-sonnet"
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout_seconds: int = 30
    retry_attempts: int = 3
    rate_limit_per_minute: int = 60
    enable_caching: bool = True
    cache_ttl_seconds: int = 300


@dataclass
class TradingConfig(BaseModel):
    """Trading system configuration."""
    symbols: list[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    timeframes: list[str] = field(default_factory=lambda: ["15m", "1h", "4h", "1d"])
    base_check_interval: int = 1800
    max_concurrent_analyses: int = 5
    enable_paper_trading: bool = True
    max_position_size: float = 0.1
    daily_loss_limit: float = 0.05
    enable_risk_management: bool = True


@dataclass
class SecurityConfig(BaseModel):
    """Security configuration."""
    secret_key: str = ""
    jwt_secret: str = ""
    encryption_key: str = ""
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 100
    enable_ssl: bool = True
    allowed_origins: list[str] = field(default_factory=lambda: ["*"])
    session_timeout_minutes: int = 60


@dataclass
class MonitoringConfig(BaseModel):
    """Monitoring and observability configuration."""
    enable_metrics: bool = True
    metrics_port: int = 9090
    enable_logging: bool = True
    log_level: str = "INFO"
    log_file: str = "trading_system.log"
    enable_tracing: bool = True
    enable_health_checks: bool = True
    health_check_interval: int = 30


@dataclass
class SystemConfig(BaseModel):
    """Complete system configuration."""
    environment: str = "development"
    debug: bool = False
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    # Performance settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    max_cache_size: int = 1000
    enable_compression: bool = True
    enable_connection_pooling: bool = True

    class Config:
        validate_assignment = True
        extra = "forbid"


class SecretManager:
    """Secure secret management with encryption."""

    def __init__(self, encryption_key: Optional[str] = None):
        if encryption_key:
            self.fernet = Fernet(encryption_key.encode())
        else:
            # Generate a new key if none provided
            key = Fernet.generate_key()
            self.fernet = Fernet(key)
            logger.warning(f"Generated new encryption key: {key.decode()}")

    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password with salt."""
        if not salt:
            salt = base64.b64encode(os.urandom(16)).decode()

        # Use HMAC with SHA-256 for password hashing
        hash_obj = hmac.new(
            salt.encode(),
            password.encode(),
            hashlib.sha256
        )
        hashed = base64.b64encode(hash_obj.digest()).decode()

        return hashed, salt

    def verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """Verify password against hash."""
        expected_hash, _ = self.hash_password(password, salt)
        return hmac.compare_digest(hashed, expected_hash)


class ConfigurationValidator:
    """Configuration validation with detailed error reporting."""

    @staticmethod
    def validate_database_config(config: DatabaseConfig) -> list[str]:
        """Validate database configuration."""
        errors = []

        if not config.host:
            errors.append("Database host cannot be empty")

        if not (1 <= config.port <= 65535):
            errors.append("Database port must be between 1 and 65535")

        if config.max_connections < config.min_connections:
            errors.append("Max connections cannot be less than min connections")

        if config.connection_timeout <= 0:
            errors.append("Connection timeout must be positive")

        return errors

    @staticmethod
    def validate_redis_config(config: RedisConfig) -> list[str]:
        """Validate Redis configuration."""
        errors = []

        if not config.host:
            errors.append("Redis host cannot be empty")

        if not (1 <= config.port <= 65535):
            errors.append("Redis port must be between 1 and 65535")

        if config.max_connections <= 0:
            errors.append("Max connections must be positive")

        return errors

    @staticmethod
    def validate_trading_config(config: TradingConfig) -> list[str]:
        """Validate trading configuration."""
        errors = []

        if not config.symbols:
            errors.append("At least one trading symbol must be specified")

        if not config.timeframes:
            errors.append("At least one timeframe must be specified")

        if config.base_check_interval <= 0:
            errors.append("Base check interval must be positive")

        if config.max_position_size <= 0 or config.max_position_size > 1:
            errors.append("Max position size must be between 0 and 1")

        if config.daily_loss_limit <= 0 or config.daily_loss_limit > 1:
            errors.append("Daily loss limit must be between 0 and 1")

        return errors

    @staticmethod
    def validate_security_config(config: SecurityConfig) -> list[str]:
        """Validate security configuration."""
        errors = []

        if not config.secret_key:
            errors.append("Secret key cannot be empty")

        if not config.jwt_secret:
            errors.append("JWT secret cannot be empty")

        if config.max_requests_per_minute <= 0:
            errors.append("Max requests per minute must be positive")

        if config.session_timeout_minutes <= 0:
            errors.append("Session timeout must be positive")

        return errors

    @staticmethod
    def validate_system_config(config: SystemConfig) -> list[str]:
        """Validate complete system configuration."""
        errors = []

        # Validate sub-configurations
        errors.extend(ConfigurationValidator.validate_database_config(config.database))
        errors.extend(ConfigurationValidator.validate_redis_config(config.redis))
        errors.extend(ConfigurationValidator.validate_trading_config(config.trading))
        errors.extend(ConfigurationValidator.validate_security_config(config.security))

        # Validate system-level settings
        if config.cache_ttl_seconds <= 0:
            errors.append("Cache TTL must be positive")

        if config.max_cache_size <= 0:
            errors.append("Max cache size must be positive")

        return errors


class ConfigurationWatcher(FileSystemEventHandler):
    """File system watcher for configuration changes."""

    def __init__(self, config_manager: 'ConfigurationManager'):
        self.config_manager = config_manager
        self.last_modified = 0

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        if event.src_path.endswith(('.toml', '.yaml', '.yml', '.json')):
            current_time = time.time()
            if current_time - self.last_modified > 1:  # Debounce
                self.last_modified = current_time
                logger.info(f"Configuration file changed: {event.src_path}")
                asyncio.create_task(self.config_manager.reload_configuration())


class ConfigurationManager:
    """High-performance configuration manager with hot reloading."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config: Optional[SystemConfig] = None
        self.secret_manager = SecretManager()
        self.validator = ConfigurationValidator()

        # Caching
        self._config_cache: dict[str, Any] = {}
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes

        # Hot reloading
        self._observer = None
        self._watcher = None
        self._reload_lock = asyncio.Lock()

        # Load initial configuration
        self._load_configuration()

        # Start file watcher if enabled
        if self.config and self.config.monitoring.enable_health_checks:
            self._start_file_watcher()

    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        # Check common locations
        possible_paths = [
            "config.toml",
            "config.yaml",
            "config.yml",
            "config.json",
            "config/config.toml",
            "config/config.yaml",
            "config/config.yml",
            "config/config.json"
        ]

        for path in possible_paths:
            if Path(path).exists():
                return path

        # Return default TOML path
        return "config.toml"

    def _load_configuration(self) -> None:
        """Load configuration from file and environment variables."""
        try:
            # Load from file
            file_config = self._load_from_file()

            # Override with environment variables
            env_config = self._load_from_environment()

            # Merge configurations
            merged_config = self._merge_configurations(file_config, env_config)

            # Validate configuration
            errors = self.validator.validate_system_config(merged_config)
            if errors:
                logger.error("Configuration validation errors:")
                for error in errors:
                    logger.error(f"  - {error}")
                raise ValueError(f"Configuration validation failed: {errors}")

            # Decrypt sensitive values
            self._decrypt_sensitive_values(merged_config)

            self.config = merged_config
            self._cache_timestamp = time.time()

            logger.info("Configuration loaded successfully")

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Load default configuration
            self.config = SystemConfig()
            logger.warning("Using default configuration")

    def _load_from_file(self) -> dict[str, Any]:
        """Load configuration from file."""
        config_path = Path(self.config_path)

        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            return {}

        try:
            if config_path.suffix == '.toml':
                return toml.load(config_path)
            elif config_path.suffix in ('.yaml', '.yml'):
                with open(config_path) as f:
                    return yaml.safe_load(f)
            elif config_path.suffix == '.json':
                with open(config_path) as f:
                    return json.load(f)
            else:
                logger.warning(f"Unsupported configuration file format: {config_path.suffix}")
                return {}

        except Exception as e:
            logger.error(f"Error reading configuration file: {e}")
            return {}

    def _load_from_environment(self) -> dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}

        # Database configuration - support both DATABASE_URL and individual vars
        if database_url := os.getenv('DATABASE_URL'):
            # Parse postgresql://user:password@host:port/database
            import re
            match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
            if match:
                env_config.setdefault('database', {})['username'] = match.group(1)
                env_config.setdefault('database', {})['password'] = match.group(2)
                env_config.setdefault('database', {})['host'] = match.group(3)
                env_config.setdefault('database', {})['port'] = int(match.group(4))
                env_config.setdefault('database', {})['database'] = match.group(5)

        # Individual database vars (override DATABASE_URL if present)
        if db_host := os.getenv('POSTGRES_HOST') or os.getenv('DB_HOST'):
            env_config.setdefault('database', {})['host'] = db_host
        if db_port := os.getenv('POSTGRES_PORT') or os.getenv('DB_PORT'):
            env_config.setdefault('database', {})['port'] = int(db_port)
        if db_name := os.getenv('POSTGRES_DB') or os.getenv('DB_NAME'):
            env_config.setdefault('database', {})['database'] = db_name
        if db_user := os.getenv('POSTGRES_USER') or os.getenv('DB_USER'):
            env_config.setdefault('database', {})['username'] = db_user
        if db_pass := os.getenv('POSTGRES_PASSWORD') or os.getenv('DB_PASSWORD'):
            env_config.setdefault('database', {})['password'] = db_pass

        # Redis configuration - support both REDIS_URL and individual vars
        if redis_url := os.getenv('REDIS_URL'):
            # Parse redis://[:password@]host:port/database
            import re
            match = re.match(r'redis://(?::([^@]+)@)?([^:]+):(\d+)/(\d+)', redis_url)
            if match:
                if match.group(1):  # password is optional
                    env_config.setdefault('redis', {})['password'] = match.group(1)
                env_config.setdefault('redis', {})['host'] = match.group(2)
                env_config.setdefault('redis', {})['port'] = int(match.group(3))
                env_config.setdefault('redis', {})['database'] = int(match.group(4))

        # Individual Redis vars (override REDIS_URL if present)
        if redis_host := os.getenv('REDIS_HOST'):
            env_config.setdefault('redis', {})['host'] = redis_host
        if redis_port := os.getenv('REDIS_PORT'):
            env_config.setdefault('redis', {})['port'] = int(redis_port)
        if redis_db := os.getenv('REDIS_DB'):
            env_config.setdefault('redis', {})['database'] = int(redis_db)
        if redis_pass := os.getenv('REDIS_PASSWORD'):
            env_config.setdefault('redis', {})['password'] = redis_pass

        # LLM configuration
        if openai_key := os.getenv('OPENAI_API_KEY'):
            env_config.setdefault('llm', {}).setdefault('providers', {})['openai'] = {
                'api_key': openai_key,
                'enabled': True
            }
        if anthropic_key := os.getenv('ANTHROPIC_API_KEY'):
            env_config.setdefault('llm', {}).setdefault('providers', {})['anthropic'] = {
                'api_key': anthropic_key,
                'enabled': True
            }

        # Security configuration
        if secret_key := os.getenv('SECRET_KEY'):
            env_config.setdefault('security', {})['secret_key'] = secret_key
        if jwt_secret := os.getenv('JWT_SECRET'):
            env_config.setdefault('security', {})['jwt_secret'] = jwt_secret

        # Environment
        if env := os.getenv('ENVIRONMENT'):
            env_config['environment'] = env
        if debug := os.getenv('DEBUG'):
            env_config['debug'] = debug.lower() in ('true', '1', 'yes')

        return env_config

    def _merge_configurations(self, file_config: dict[str, Any], env_config: dict[str, Any]) -> dict[str, Any]:
        """Merge file and environment configurations."""
        merged = file_config.copy()

        def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base

        return deep_merge(merged, env_config)

    def _decrypt_sensitive_values(self, config: dict[str, Any]) -> None:
        """Decrypt sensitive configuration values."""
        # This would decrypt values that were encrypted during storage
        # Implementation depends on your encryption strategy
        pass

    def _start_file_watcher(self) -> None:
        """Start file system watcher for configuration changes."""
        try:
            config_dir = Path(self.config_path).parent
            self._watcher = ConfigurationWatcher(self)
            self._observer = Observer()
            self._observer.schedule(self._watcher, str(config_dir), recursive=False)
            self._observer.start()
            logger.info("Configuration file watcher started")
        except Exception as e:
            logger.error(f"Error starting file watcher: {e}")

    async def reload_configuration(self) -> None:
        """Reload configuration from file."""
        async with self._reload_lock:
            try:
                logger.info("Reloading configuration...")
                self._load_configuration()
                logger.info("Configuration reloaded successfully")
            except Exception as e:
                logger.error(f"Error reloading configuration: {e}")

    @cache_result(ttl_seconds=300)
    def get_config(self) -> SystemConfig:
        """Get current configuration with caching."""
        if not self.config:
            raise RuntimeError("Configuration not loaded")
        return self.config

    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self.get_config().database

    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration."""
        return self.get_config().redis

    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration."""
        return self.get_config().llm

    def get_trading_config(self) -> TradingConfig:
        """Get trading configuration."""
        return self.get_config().trading

    def get_security_config(self) -> SecurityConfig:
        """Get security configuration."""
        return self.get_config().security

    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration."""
        return self.get_config().monitoring

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key."""
        if not self.config:
            return default

        keys = key.split('.')
        value = self.config

        try:
            for k in keys:
                value = getattr(value, k)
            return value
        except AttributeError:
            return default

    def set_value(self, key: str, value: Any) -> bool:
        """Set configuration value by dot notation key."""
        if not self.config:
            return False

        keys = key.split('.')
        target = self.config

        try:
            # Navigate to parent object
            for k in keys[:-1]:
                target = getattr(target, k)

            # Set the value
            setattr(target, keys[-1], value)
            return True
        except AttributeError:
            return False

    def export_config(self, format: str = 'toml') -> str:
        """Export configuration to specified format."""
        if not self.config:
            return ""

        config_dict = asdict(self.config)

        if format == 'toml':
            return toml.dumps(config_dict)
        elif format == 'yaml':
            return yaml.dump(config_dict, default_flow_style=False)
        elif format == 'json':
            return json.dumps(config_dict, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def validate_config(self) -> list[str]:
        """Validate current configuration."""
        if not self.config:
            return ["Configuration not loaded"]

        return self.validator.validate_system_config(self.config)

    def update_database_url(self, password: str, user: str = "trading",
                           host: str = "localhost", port: int = 5432,
                           database: str = "trading") -> bool:
        """
        Update database URL in .env.local file.

        Args:
            password: Database password
            user: Database user (default: trading)
            host: Database host (default: localhost)
            port: Database port (default: 5432)
            database: Database name (default: trading)

        Returns:
            True if update successful
        """
        try:
            env_file = Path('.env.local')

            # Backup existing file
            if env_file.exists():
                backup_path = self.backup_config()
                logger.info(f"Backed up .env.local to {backup_path}")

            # Read existing content
            lines = []
            if env_file.exists():
                with open(env_file) as f:
                    lines = f.readlines()

            # Update or add DATABASE_URL
            database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            url_line = f"DATABASE_URL={database_url}\n"

            # Find and replace DATABASE_URL line
            found = False
            for i, line in enumerate(lines):
                if line.startswith('DATABASE_URL='):
                    lines[i] = url_line
                    found = True
                    break

            # Add if not found
            if not found:
                lines.append(url_line)

            # Write back to file
            with open(env_file, 'w') as f:
                f.writelines(lines)

            logger.info("Updated DATABASE_URL in .env.local")

            # Reload configuration
            self._load_configuration()

            return True

        except Exception as e:
            logger.error(f"Error updating database URL: {e}")
            return False

    def backup_config(self) -> Path:
        """
        Backup current .env.local file.

        Returns:
            Path to backup file
        """
        import shutil
        from datetime import datetime

        env_file = Path('.env.local')
        if not env_file.exists():
            raise FileNotFoundError(".env.local file not found")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = Path(f'.env.local.backup_{timestamp}')

        shutil.copy2(env_file, backup_path)
        logger.info(f"Created backup: {backup_path}")

        return backup_path

    def restore_config(self, backup_path: Path) -> bool:
        """
        Restore configuration from backup file.

        Args:
            backup_path: Path to backup file

        Returns:
            True if restore successful
        """
        try:
            import shutil

            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False

            env_file = Path('.env.local')
            shutil.copy2(backup_path, env_file)

            logger.info(f"Restored configuration from {backup_path}")

            # Reload configuration
            self._load_configuration()

            return True

        except Exception as e:
            logger.error(f"Error restoring configuration: {e}")
            return False

    def validate_database_connection(self) -> dict[str, Any]:
        """
        Validate database connection using current configuration.

        Returns:
            Dictionary with validation results
        """
        try:
            from .db_validator import DatabaseValidator

            db_config = self.get_database_config()
            connection_string = db_config.connection_string

            validator = DatabaseValidator()
            result = validator.test_connection(connection_string)

            return {
                "success": result.success,
                "error_type": result.error_type,
                "error_message": result.error_message,
                "suggested_fix": result.suggested_fix,
                "connection_time_ms": result.connection_time_ms
            }

        except Exception as e:
            logger.error(f"Error validating database connection: {e}")
            return {
                "success": False,
                "error_type": "unknown",
                "error_message": str(e),
                "suggested_fix": "Check configuration and run Setup-Database.ps1"
            }

    def get_database_url(self) -> Optional[str]:
        """
        Get database URL from configuration.

        Returns:
            Database connection URL or None if not configured
        """
        try:
            db_config = self.get_database_config()
            return db_config.connection_string
        except Exception:
            return None

    def validate_config(self) -> list[dict[str, str]]:
        """
        Validate current configuration with detailed error reporting.

        Returns:
            List of configuration issues with severity levels
        """
        if not self.config:
            return [{
                "severity": "error",
                "component": "system",
                "message": "Configuration not loaded",
                "suggested_fix": "Check configuration file and restart application"
            }]

        issues = []

        # Validate using existing validator
        validation_errors = self.validator.validate_system_config(self.config)
        for error in validation_errors:
            issues.append({
                "severity": "error",
                "component": "config",
                "message": error,
                "suggested_fix": "Fix configuration and restart application"
            })

        # Additional database-specific validation
        db_config = self.get_database_config()

        if not db_config.password:
            issues.append({
                "severity": "error",
                "component": "database",
                "message": "Database password not configured",
                "suggested_fix": "Run: .\\scripts\\Setup-Database.ps1"
            })

        if db_config.password in ["YOUR_PASSWORD_HERE", "password", "admin"]:
            issues.append({
                "severity": "warning",
                "component": "database",
                "message": "Database password appears to be a default/placeholder value",
                "suggested_fix": "Set a secure password using Setup-Database.ps1"
            })

        # Check if .env.local exists
        env_file = Path('.env.local')
        if not env_file.exists():
            issues.append({
                "severity": "warning",
                "component": "config",
                "message": ".env.local file not found",
                "suggested_fix": "Create .env.local file or run Setup-Database.ps1"
            })

        return issues

    def update_individual_database_vars(self, password: str, user: str = "trading",
                                      host: str = "localhost", port: int = 5432,
                                      database: str = "trading") -> bool:
        """
        Update individual database variables in .env.local file.

        Args:
            password: Database password
            user: Database user (default: trading)
            host: Database host (default: localhost)
            port: Database port (default: 5432)
            database: Database name (default: trading)

        Returns:
            True if update successful
        """
        try:
            env_file = Path('.env.local')

            # Backup existing file
            if env_file.exists():
                backup_path = self.backup_config()
                logger.info(f"Backed up .env.local to {backup_path}")

            # Read existing content
            lines = []
            if env_file.exists():
                with open(env_file) as f:
                    lines = f.readlines()

            # Variables to update
            variables = {
                'POSTGRES_HOST': host,
                'POSTGRES_PORT': str(port),
                'POSTGRES_DB': database,
                'POSTGRES_USER': user,
                'POSTGRES_PASSWORD': password
            }

            # Update or add each variable
            for var_name, var_value in variables.items():
                var_line = f"{var_name}={var_value}\n"

                # Find and replace existing line
                found = False
                for i, line in enumerate(lines):
                    if line.startswith(f'{var_name}='):
                        lines[i] = var_line
                        found = True
                        break

                # Add if not found
                if not found:
                    lines.append(var_line)

            # Write back to file
            with open(env_file, 'w') as f:
                f.writelines(lines)

            logger.info("Updated individual database variables in .env.local")

            # Reload configuration
            self._load_configuration()

            return True

        except Exception as e:
            logger.error(f"Error updating individual database variables: {e}")
            return False

    def get_connection_diagnostics(self) -> dict[str, Any]:
        """
        Get comprehensive connection diagnostics.

        Returns:
            Dictionary with diagnostic information
        """
        try:
            diagnostics = {
                "timestamp": time.time(),
                "config_loaded": self.config is not None,
                "config_file_exists": Path(self.config_path).exists(),
                "env_file_exists": Path('.env.local').exists()
            }

            if self.config:
                # Configuration validation
                config_issues = self.validate_config()
                diagnostics["config_issues"] = config_issues
                diagnostics["config_valid"] = len([i for i in config_issues if i["severity"] == "error"]) == 0

                # Database connection test
                db_validation = self.validate_database_connection()
                diagnostics["database_connection"] = db_validation

                # Database configuration
                db_config = self.get_database_config()
                diagnostics["database_config"] = {
                    "host": db_config.host,
                    "port": db_config.port,
                    "database": db_config.database,
                    "username": db_config.username,
                    "password_configured": bool(db_config.password and db_config.password != "YOUR_PASSWORD_HERE")
                }

            return diagnostics

        except Exception as e:
            logger.error(f"Error getting connection diagnostics: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }

    def get_config_summary(self) -> dict[str, Any]:
        """Get configuration summary for monitoring."""
        if not self.config:
            return {"status": "not_loaded"}

        return {
            "status": "loaded",
            "environment": self.config.environment,
            "debug": self.config.debug,
            "database_host": self.config.database.host,
            "redis_host": self.config.redis.host,
            "symbols_count": len(self.config.trading.symbols),
            "timeframes_count": len(self.config.trading.timeframes),
            "llm_providers_count": len(self.config.llm.providers),
            "cache_enabled": self.config.enable_caching,
            "compression_enabled": self.config.enable_compression,
            "last_modified": self._cache_timestamp
        }

    async def close(self) -> None:
        """Close configuration manager and cleanup resources."""
        if self._observer:
            self._observer.stop()
            self._observer.join()

        # Clear cache
        self._config_cache.clear()
        self._cache_timestamp = 0


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def get_config() -> SystemConfig:
    """Get current system configuration."""
    return get_config_manager().get_config()


def get_database_config() -> DatabaseConfig:
    """Get database configuration."""
    return get_config_manager().get_database_config()


def get_redis_config() -> RedisConfig:
    """Get Redis configuration."""
    return get_config_manager().get_redis_config()


def get_llm_config() -> LLMConfig:
    """Get LLM configuration."""
    return get_config_manager().get_llm_config()


def get_trading_config() -> TradingConfig:
    """Get trading configuration."""
    return get_config_manager().get_trading_config()


def get_security_config() -> SecurityConfig:
    """Get security configuration."""
    return get_config_manager().get_security_config()


def get_monitoring_config() -> MonitoringConfig:
    """Get monitoring configuration."""
    return get_config_manager().get_monitoring_config()


# Alias for backwards compatibility
ConfigManager = ConfigurationManager
