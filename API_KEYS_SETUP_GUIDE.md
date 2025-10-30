# 🔑 **API KEYS SETUP GUIDE**

## 🚀 **COMPLETE GUIDE TO GET ALL API KEYS FOR YOUR AI TRADING AGENT**

Your AI trading agent needs several API keys to function at full capacity. Here's exactly how to get each one!

---

## 🧠 **AI/LLM API KEYS (Required for Intelligence)**

### **1. 🤖 OpenAI API Key (GPT-4 Turbo)**
**Cost**: $0.01 per 1K tokens (~$10-50/month for trading)

#### **How to Get:**
1. **Visit**: https://platform.openai.com/
2. **Sign Up/Login** to your OpenAI account
3. **Go to**: API Keys section
4. **Click**: "Create new secret key"
5. **Copy**: Your key (starts with `sk-...`)
6. **Add Credits**: Minimum $5 to start

#### **Set Environment Variable:**
```bash
# Windows
set OPENAI_API_KEY=sk-your-key-here

# Linux/Mac
export OPENAI_API_KEY=sk-your-key-here
```

---

### **2. 🧠 Anthropic API Key (Claude)**
**Cost**: $0.008 per 1K tokens (~$8-40/month for trading)

#### **How to Get:**
1. **Visit**: https://console.anthropic.com/
2. **Sign Up** with your email
3. **Go to**: API Keys section
4. **Click**: "Create Key"
5. **Copy**: Your key (starts with `sk-ant-...`)
6. **Add Credits**: $5 minimum

#### **Set Environment Variable:**
```bash
# Windows
set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Linux/Mac
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

### **3. 🌟 Google Gemini API Key**
**Cost**: Free tier available, then $0.0015 per 1K tokens

#### **How to Get:**
1. **Visit**: https://makersuite.google.com/app/apikey
2. **Sign In** with Google account
3. **Click**: "Create API Key"
4. **Copy**: Your key (starts with `AIza...`)

#### **Set Environment Variable:**
```bash
# Windows
set GOOGLE_API_KEY=AIza-your-key-here

# Linux/Mac
export GOOGLE_API_KEY=AIza-your-key-here
```

---

### **4. 🚀 Mistral API Key (Mixtral)**
**Cost**: $0.0007 per 1K tokens (very cost-effective)

#### **How to Get:**
1. **Visit**: https://console.mistral.ai/
2. **Create Account**
3. **Go to**: API Keys
4. **Generate**: New API key
5. **Copy**: Your key

#### **Set Environment Variable:**
```bash
# Windows
set MISTRAL_API_KEY=your-key-here

# Linux/Mac
export MISTRAL_API_KEY=your-key-here
```

---

### **5. 🦙 Meta Llama API Key (via Together.ai)**
**Cost**: $0.0008 per 1K tokens

#### **How to Get:**
1. **Visit**: https://api.together.xyz/
2. **Sign Up** for account
3. **Go to**: API Keys section
4. **Create**: New API key
5. **Copy**: Your key

#### **Set Environment Variable:**
```bash
# Windows
set TOGETHER_API_KEY=your-key-here

# Linux/Mac
export TOGETHER_API_KEY=your-key-here
```

---

## 💹 **TRADING/BROKER API KEYS (Required for Live Trading)**

### **6. 🏦 Binance API Keys**
**Cost**: Free (trading fees apply)

#### **How to Get:**
1. **Visit**: https://www.binance.com/
2. **Create Account** and complete KYC verification
3. **Go to**: Profile → API Management
4. **Create API**: Enable "Spot & Margin Trading"
5. **Copy**: API Key and Secret Key
6. **Enable**: "Enable Trading" permission
7. **Set IP Restriction**: Add your server IP for security

#### **Set Environment Variables:**
```bash
# Windows
set BINANCE_API_KEY=your-api-key
set BINANCE_SECRET_KEY=your-secret-key

# Linux/Mac
export BINANCE_API_KEY=your-api-key
export BINANCE_SECRET_KEY=your-secret-key
```

#### **⚠️ IMPORTANT Security Settings:**
- ✅ Enable "Spot & Margin Trading"
- ✅ Enable "Futures Trading" (if needed)
- ❌ Disable "Enable Withdrawals" (for security)
- ✅ Set IP restrictions to your server IP
- ✅ Use API key only for trading, not withdrawals

---

### **7. 📈 Alternative Brokers (Choose One)**

#### **🇺🇸 Alpaca (US Stocks/Crypto)**
1. **Visit**: https://alpaca.markets/
2. **Sign Up** for account
3. **Go to**: Paper Trading → API Keys
4. **Generate**: Live/Paper API keys

```bash
# Windows
set ALPACA_API_KEY=your-key
set ALPACA_SECRET_KEY=your-secret
set ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Paper trading

# Linux/Mac
export ALPACA_API_KEY=your-key
export ALPACA_SECRET_KEY=your-secret
export ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

#### **🌍 Interactive Brokers (Global)**
1. **Visit**: https://www.interactivebrokers.com/
2. **Open Account** (minimum $10,000)
3. **Enable**: API access in account settings
4. **Download**: TWS or IB Gateway
5. **Configure**: API settings

---

## 📊 **MARKET DATA API KEYS (Optional but Recommended)**

### **8. 📈 Alpha Vantage (Financial Data)**
**Cost**: Free tier (500 calls/day), Premium $49.99/month

#### **How to Get:**
1. **Visit**: https://www.alphavantage.co/
2. **Get Free API Key**
3. **Copy**: Your key

```bash
# Windows
set ALPHA_VANTAGE_API_KEY=your-key

# Linux/Mac
export ALPHA_VANTAGE_API_KEY=your-key
```

---

### **9. 📊 Polygon.io (Real-time Data)**
**Cost**: Free tier available, Premium $99/month

#### **How to Get:**
1. **Visit**: https://polygon.io/
2. **Sign Up** for account
3. **Get**: API key from dashboard

```bash
# Windows
set POLYGON_API_KEY=your-key

# Linux/Mac
export POLYGON_API_KEY=your-key
```

---

## 🔧 **INFRASTRUCTURE API KEYS (Optional)**

### **10. ☁️ AWS (for Cloud Deployment)**
1. **Visit**: https://aws.amazon.com/
2. **Create Account**
3. **Go to**: IAM → Users → Create User
4. **Attach Policies**: EC2, RDS, CloudWatch
5. **Generate**: Access keys

```bash
# Windows
set AWS_ACCESS_KEY_ID=your-access-key
set AWS_SECRET_ACCESS_KEY=your-secret-key

# Linux/Mac
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
```

---

## 🛡️ **SECURITY & CONFIGURATION**

### **11. 🔐 Generate Security Keys**
```bash
# Generate JWT secret (Windows)
set JWT_SECRET=your-super-secret-jwt-key-2024

# Generate system secret
set SECRET_KEY=your-system-secret-key-2024

# Linux/Mac
export JWT_SECRET=your-super-secret-jwt-key-2024
export SECRET_KEY=your-system-secret-key-2024
```

---

## 📝 **COMPLETE ENVIRONMENT SETUP**

### **Create `.env` File in Your Project Root:**
```bash
# AI/LLM APIs
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
GOOGLE_API_KEY=AIza-your-google-key
MISTRAL_API_KEY=your-mistral-key
TOGETHER_API_KEY=your-together-key

# Trading APIs
BINANCE_API_KEY=your-binance-api-key
BINANCE_SECRET_KEY=your-binance-secret-key

# Market Data APIs
ALPHA_VANTAGE_API_KEY=your-alphavantage-key
POLYGON_API_KEY=your-polygon-key

# Security
JWT_SECRET=your-jwt-secret-key-2024
SECRET_KEY=your-system-secret-key-2024

# Database (if using cloud)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_db
DB_USER=trading_user
DB_PASSWORD=your-db-password

# Redis (if using)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Environment
ENVIRONMENT=development
DEBUG=true
```

---

## 💰 **COST BREAKDOWN**

### **🧠 AI APIs (Monthly Estimates for Active Trading):**
- **OpenAI GPT-4**: $20-50/month
- **Anthropic Claude**: $15-40/month  
- **Google Gemini**: $5-15/month (has free tier)
- **Mistral Mixtral**: $3-10/month (cheapest)
- **Meta Llama**: $3-10/month
- **Total AI Costs**: $46-125/month

### **💹 Trading APIs:**
- **Binance**: Free (trading fees 0.1%)
- **Alpaca**: Free
- **Interactive Brokers**: $10/month + commissions

### **📊 Market Data:**
- **Alpha Vantage**: Free tier or $50/month
- **Polygon.io**: Free tier or $99/month

### **💡 Budget-Friendly Approach:**
**Minimum viable setup (~$25/month):**
- OpenAI GPT-4: $20/month
- Mistral Mixtral: $5/month  
- Binance: Free
- Alpha Vantage: Free tier
- **Total**: ~$25/month

---

## 🚀 **QUICK SETUP SCRIPT**

### **Create `setup_env.bat` (Windows):**
```batch
@echo off
echo Setting up AI Trading Agent environment variables...

REM AI APIs
set /p OPENAI_KEY="Enter OpenAI API Key: "
set OPENAI_API_KEY=%OPENAI_KEY%

set /p ANTHROPIC_KEY="Enter Anthropic API Key: "
set ANTHROPIC_API_KEY=%ANTHROPIC_KEY%

set /p BINANCE_API="Enter Binance API Key: "
set BINANCE_API_KEY=%BINANCE_API%

set /p BINANCE_SECRET="Enter Binance Secret Key: "
set BINANCE_SECRET_KEY=%BINANCE_SECRET%

REM Generate random secrets
set JWT_SECRET=jwt-secret-%RANDOM%-%RANDOM%-2024
set SECRET_KEY=system-secret-%RANDOM%-%RANDOM%-2024

echo Environment variables set successfully!
echo You can now run your AI trading agent.
pause
```

---

## ✅ **VERIFICATION CHECKLIST**

### **🧠 AI APIs Ready:**
- [ ] OpenAI API key obtained and funded
- [ ] Anthropic API key obtained and funded  
- [ ] Google Gemini API key obtained
- [ ] Environment variables set correctly

### **💹 Trading APIs Ready:**
- [ ] Binance account created and verified
- [ ] Binance API keys generated with trading permissions
- [ ] IP restrictions configured for security
- [ ] Test connection successful

### **🔐 Security Configured:**
- [ ] JWT secret generated
- [ ] System secret key set
- [ ] API keys stored securely
- [ ] Environment variables configured

### **🚀 System Ready:**
- [ ] All environment variables set
- [ ] API connections tested
- [ ] Dashboard launches successfully
- [ ] AI analysis working

---

## 🎊 **YOU'RE ALL SET!**

### **🏆 What You Now Have:**
✅ **Complete AI Intelligence** - 5 AI models for market analysis  
✅ **Live Trading Capability** - Connected to real exchanges  
✅ **Real-time Market Data** - Live price feeds  
✅ **Secure Configuration** - Properly protected API keys  
✅ **Professional Setup** - Production-ready environment  

### **🚀 Next Steps:**
1. **Set all environment variables** using the guide above
2. **Test API connections** with small amounts first
3. **Start with paper trading** to verify everything works
4. **Launch your AI agent** and watch it trade!

**Your AI trading agent is now ready to make money 24/7!** 🤖💰🚀✨

### **💡 Pro Tips:**
- Start with **paper trading** first
- Use **small amounts** initially  
- Monitor **API usage costs**
- Keep **API keys secure**
- **Rotate keys** regularly for security
