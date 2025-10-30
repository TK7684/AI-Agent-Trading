# Design Document

## Overview

This design creates a robust, user-friendly database setup system for the autonomous trading platform. The solution provides automated password detection, interactive configuration, graceful degradation without database connectivity, and clear error messaging to eliminate the current friction in database setup.

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Database Setup System                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐      ┌──────────────────────────┐    │
│  │  Setup Wizard    │─────▶│  Connection Validator    │    │
│  │  (Interactive)   │      │  (Test & Verify)         │    │
│  └──────────────────┘      └──────────────────────────┘    │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌──────────────────┐      ┌──────────────────────────┐    │
│  │  Config Manager  │      │  Schema Initializer      │    │
│  │  (.env.local)    │      │  (Auto-create tables)    │    │
│  └──────────────────┘      └──────────────────────────┘    │
│           │                            │                     │
│           └────────────┬───────────────┘                     │
│                        ▼                                     │
│              ┌──────────────────┐                           │
│              │  Fallback Mode   │                           │
│              │  (No Database)   │                           │
│              └──────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Setup Wizard**: Interactive PowerShell script that guides users through configuration
2. **Connection Validator**: Tests database connectivity with multiple strategies
3. **Config Manager**: Manages .env.local file updates
4. **Schema Initializer**: Automatically creates database tables on first connection
5. **Fallback Mode**: Allows system to run without database for exploration

## Components and Interfaces

### 1. Setup Wizard (`Setup-Database.ps1`)

**Purpose**: Interactive script that guides users through database configuration

**Interface**:
```powershell
function Start-DatabaseSetup {
    # Test PostgreSQL service status
    # Try common passwords
    # Prompt for custom password if needed
    # Validate connection
    # Update .env.local
    # Initialize schema
    # Verify full setup
}
```


**Key Features**:
- Detects PostgreSQL service status
- Tests common passwords automatically
- Provides password reset instructions
- Creates trading user if missing
- Updates configuration files
- Validates complete setup

### 2. Connection Validator (`libs/trading_models/db_validator.py`)

**Purpose**: Python module for testing and validating database connections

**Interface**:
```python
class DatabaseValidator:
    def test_connection(self, connection_string: str) -> ConnectionResult
    def test_service_running(self) -> bool
    def validate_schema(self, connection_string: str) -> SchemaValidation
    def get_connection_diagnostics(self) -> Dict[str, Any]
```

**ConnectionResult Model**:
```python
class ConnectionResult(BaseModel):
    success: bool
    error_type: Optional[str]  # "auth", "service", "network", "schema"
    error_message: Optional[str]
    suggested_fix: Optional[str]
    connection_time_ms: Optional[float]
```

### 3. Config Manager (`libs/trading_models/config_manager.py`)

**Purpose**: Manages environment configuration with validation

**Enhanced Interface**:
```python
class ConfigManager:
    def update_database_url(self, password: str) -> bool
    def validate_config(self) -> List[ConfigIssue]
    def get_database_config(self) -> DatabaseConfig
    def backup_config(self) -> Path
    def restore_config(self, backup_path: Path) -> bool
```

### 4. Schema Initializer (Enhanced `persistence.py`)

**Purpose**: Automatically creates and validates database schema

**Enhanced Interface**:
```python
class DatabaseManager:
    def initialize_schema(self) -> InitializationResult
    def validate_schema_version(self) -> SchemaVersion
    def migrate_if_needed(self) -> MigrationResult
    def create_tables_safe(self) -> bool  # Idempotent
```

### 5. Fallback Mode Handler (`libs/trading_models/fallback_mode.py`)

**Purpose**: Enables system operation without database

**Interface**:
```python
class FallbackMode:
    def is_enabled(self) -> bool
    def get_mock_data(self, data_type: str) -> Any
    def log_warning(self, operation: str) -> None
    def check_database_available(self) -> bool
```

## Data Models

### Configuration Models

```python
class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    database: str = "trading"
    user: str = "trading"
    password: str
    connection_url: str
    
class ConfigIssue(BaseModel):
    severity: str  # "error", "warning", "info"
    component: str
    message: str
    suggested_fix: str
```



### Initialization Models

```python
class InitializationResult(BaseModel):
    success: bool
    tables_created: List[str]
    tables_skipped: List[str]
    errors: List[str]
    duration_ms: float
    
class SchemaVersion(BaseModel):
    current_version: str
    expected_version: str
    compatible: bool
    migration_needed: bool
```

## Error Handling

### Error Classification

1. **Service Errors**: PostgreSQL service not running
2. **Authentication Errors**: Invalid password or user
3. **Network Errors**: Cannot reach database host
4. **Schema Errors**: Missing or incompatible schema
5. **Permission Errors**: Insufficient database privileges

### Error Response Strategy

```python
class DatabaseError(Exception):
    error_type: str
    message: str
    suggested_fix: str
    recovery_steps: List[str]
    
    def get_user_message(self) -> str:
        """Returns formatted message for user display"""
        
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Returns detailed diagnostic information"""
```

### Error Messages

Each error type has a specific, actionable message:

**Authentication Error**:
```
❌ Database authentication failed

The password for user 'trading' is incorrect.

Suggested fixes:
1. Run: .\scripts\Setup-Database.ps1
2. Or manually update .env.local with correct password
3. Or reset password: .\scripts\Reset-PostgreSQL-Password.ps1

Need help? See: QUICK-FIX-DATABASE.md
```

**Service Not Running**:
```
❌ PostgreSQL service is not running

The database service needs to be started.

To start PostgreSQL:
1. Open Services (services.msc)
2. Find "postgresql-x64-17"
3. Click "Start"

Or run: Start-Service postgresql-x64-17
```

## Testing Strategy

### Unit Tests

1. **Connection Validator Tests**
   - Test successful connection
   - Test authentication failure
   - Test service not running
   - Test network timeout
   - Test schema validation

2. **Config Manager Tests**
   - Test config file updates
   - Test config validation
   - Test backup/restore
   - Test malformed config handling

3. **Schema Initializer Tests**
   - Test table creation
   - Test idempotent operations
   - Test schema version detection
   - Test migration detection

### Integration Tests

1. **End-to-End Setup Flow**
   - Fresh installation scenario
   - Password change scenario
   - Schema migration scenario
   - Fallback mode activation

2. **Error Recovery Tests**
   - Recovery from auth failure
   - Recovery from service stop
   - Recovery from schema corruption

### Manual Testing Scenarios

1. **Fresh Install**: No database configured
2. **Wrong Password**: Existing config with wrong password
3. **Service Stopped**: PostgreSQL not running
4. **Missing Tables**: Database exists but no schema
5. **Fallback Mode**: Run without database



## Implementation Flow

### Setup Wizard Flow

```
Start Setup
    │
    ├─▶ Check PostgreSQL Service
    │   ├─ Running? ─▶ Continue
    │   └─ Stopped? ─▶ Offer to start ─▶ Start service
    │
    ├─▶ Test Common Passwords
    │   ├─ Success? ─▶ Use found password
    │   └─ All fail? ─▶ Prompt for password
    │
    ├─▶ Validate Connection
    │   ├─ Success? ─▶ Continue
    │   └─ Fail? ─▶ Show reset instructions ─▶ Retry
    │
    ├─▶ Check/Create Trading User
    │   ├─ Exists? ─▶ Continue
    │   └─ Missing? ─▶ Create user
    │
    ├─▶ Update .env.local
    │   └─ Backup existing ─▶ Write new config
    │
    ├─▶ Initialize Schema
    │   ├─ Tables exist? ─▶ Validate
    │   └─ Missing? ─▶ Create tables
    │
    └─▶ Verify Complete Setup
        ├─ Success? ─▶ Show success message
        └─ Issues? ─▶ Show diagnostics
```

### Application Startup Flow

```
Application Start
    │
    ├─▶ Load Configuration
    │   └─ Parse .env.local
    │
    ├─▶ Validate Database Config
    │   ├─ Valid? ─▶ Continue
    │   └─ Invalid? ─▶ Show setup instructions
    │
    ├─▶ Test Database Connection
    │   ├─ Success? ─▶ Continue
    │   └─ Fail? ─▶ Enable Fallback Mode
    │
    ├─▶ Validate Schema
    │   ├─ Valid? ─▶ Continue
    │   └─ Invalid? ─▶ Offer to initialize
    │
    └─▶ Start Services
        ├─ With Database ─▶ Full functionality
        └─ Fallback Mode ─▶ Limited functionality
```

## Design Decisions

### 1. Interactive vs Automated Setup

**Decision**: Provide both interactive wizard and automated detection

**Rationale**: 
- Interactive wizard for first-time setup and troubleshooting
- Automated detection for experienced users and CI/CD
- Flexibility for different user preferences

### 2. Fallback Mode Strategy

**Decision**: Allow system to run without database in read-only mode

**Rationale**:
- Users can explore UI and API immediately
- Reduces friction for evaluation
- Clear warnings prevent confusion
- Easy to enable full mode later

### 3. Password Storage

**Decision**: Store password in .env.local file (not committed to git)

**Rationale**:
- Standard practice for local development
- .env.local is in .gitignore
- Easy to update and manage
- Compatible with existing config system

### 4. Schema Initialization

**Decision**: Auto-create tables on first connection

**Rationale**:
- Eliminates manual SQL script execution
- Idempotent operations prevent errors
- Uses existing SQLAlchemy models
- Consistent with modern ORM practices

### 5. Error Message Design

**Decision**: Provide specific, actionable error messages with recovery steps

**Rationale**:
- Reduces support burden
- Empowers users to self-solve
- Clear path to resolution
- Links to detailed documentation

## Security Considerations

1. **Password Handling**
   - Never log passwords
   - Secure file permissions on .env.local
   - Clear password from memory after use
   - Warn about default passwords

2. **Connection Security**
   - Support SSL connections
   - Validate certificates in production
   - Use connection pooling limits
   - Implement connection timeouts

3. **User Permissions**
   - Create trading user with minimal required privileges
   - Separate admin and application users
   - Document permission requirements

## Performance Considerations

1. **Connection Pooling**
   - Reuse existing connection pool configuration
   - Set appropriate pool size limits
   - Implement connection health checks

2. **Schema Validation**
   - Cache schema validation results
   - Only validate on startup or explicit request
   - Use lightweight queries for checks

3. **Fallback Mode**
   - Minimal overhead when database available
   - Fast detection of database availability
   - Efficient mock data generation

## Monitoring and Observability

1. **Connection Metrics**
   - Track connection success/failure rates
   - Monitor connection pool utilization
   - Log connection timing

2. **Setup Analytics**
   - Track common failure points
   - Identify most used recovery paths
   - Monitor setup completion rates

3. **Error Tracking**
   - Log all database errors with context
   - Track error patterns
   - Alert on repeated failures
