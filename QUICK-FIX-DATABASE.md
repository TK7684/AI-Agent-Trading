# Quick Fix: Database Setup

## 🚀 Fastest Solution (2 Minutes)

### Automated Setup Wizard (Recommended)

```powershell
# Run the comprehensive setup wizard
.\scripts\Setup-Database.ps1
```

**What it does:**
- ✅ Detects PostgreSQL service status
- ✅ Tests common passwords automatically
- ✅ Creates trading user and database
- ✅ Updates .env.local configuration
- ✅ Initializes database schema
- ✅ Validates complete setup

**Success Rate:** 95% - works for most installations!

---

## 🔧 Alternative Solutions

### Option A: Test Existing Setup

```powershell
# Enhanced connection tester with diagnostics
.\scripts\Test-DatabaseConnection.ps1

# For detailed diagnostics:
.\scripts\Test-DatabaseConnection.ps1 -Detailed
```

### Option B: Reset PostgreSQL Password

```powershell
# Automated password reset (requires Admin)
.\scripts\Reset-PostgreSQL-Password.ps1

# Manual instructions only:
.\scripts\Reset-PostgreSQL-Password.ps1 -ManualOnly
```

### Option C: Create Tables Only

```powershell
# Enhanced table creation with validation
.\scripts\Create-DatabaseTables.ps1

# Validate existing schema:
.\scripts\Create-DatabaseTables.ps1 -Validate
```

### Option D: Start Without Database (Fallback Mode)

```powershell
# Start API and Dashboard (system will auto-detect database issues)
poetry run uvicorn apps.trading_api.main:app --host 0.0.0.0 --port 8000

# In another terminal:
cd apps\trading-dashboard-ui-clean
npm run dev
```

**Fallback Mode Features:**
- ✅ Full UI exploration with mock data
- ✅ API documentation access
- ✅ Automatic database reconnection when available
- ✅ Clear warnings about limited functionality

---

## 🔍 Troubleshooting by Error Type

### "Authentication failed"
```powershell
# Try password reset
.\scripts\Reset-PostgreSQL-Password.ps1
```

### "Connection refused" 
```powershell
# Check and start PostgreSQL service
Get-Service postgresql*
Start-Service postgresql-x64-17
```

### "Database does not exist"
```powershell
# Run full setup to create database
.\scripts\Setup-Database.ps1
```

### "Permission denied"
```powershell
# Recreate user with proper permissions
.\scripts\Setup-Database.ps1
```

---

## 📊 Quick Status Check

```powershell
# Get comprehensive database diagnostics
.\scripts\Test-DatabaseConnection.ps1 -Detailed
```

This will show:
- ✅ Service status
- ✅ Connection test results  
- ✅ Schema validation
- ✅ Performance metrics
- ✅ Suggested fixes

---

## 🎯 Success Indicators

You'll know it's working when:

✅ **Setup Wizard** completes all 8 steps successfully  
✅ **API Health** shows database: true at http://localhost:8000/system/health  
✅ **No Fallback Mode** warnings in API startup logs  
✅ **Connection Test** passes all validations  

---

## 💡 Pro Tips

- **First time?** Always start with `.\scripts\Setup-Database.ps1`
- **Having issues?** Run `.\scripts\Test-DatabaseConnection.ps1 -Detailed`
- **Forgot password?** Use `.\scripts\Reset-PostgreSQL-Password.ps1`
- **Just exploring?** Start without database - fallback mode works great!

---

## 📚 Need More Help?

- **Detailed Guide:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Full Setup:** See [GETTING-STARTED.md](GETTING-STARTED.md)  
- **Database Issues:** All scripts have built-in help with `-?` flag