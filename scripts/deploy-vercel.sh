#!/bin/bash

# AI Trading System - Vercel Deployment Script
# This script automates the deployment process to Vercel

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting AI Trading System deployment to Vercel${NC}"

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo -e "${YELLOW}Vercel CLI not found. Installing...${NC}"
    npm i -g vercel
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js is required but not installed. Please install Node.js first.${NC}"
    exit 1
fi

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}Git repository not initialized. Initializing...${NC}"
    git init
    git add .
    git commit -m "Initial commit"
fi

# Create .env.local for local development
if [ ! -f ".env.local" ]; then
    echo -e "${YELLOW}Creating .env.local template...${NC}"
    cat > .env.local << EOF
# Environment Configuration
ENVIRONMENT=development

# Database Configuration (replace with your values)
DATABASE_URL=postgresql://username:password@host:port/database
REDIS_URL=redis://host:port/0

# LLM API Keys (replace with your keys)
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Exchange API Keys (replace with your keys)
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key

# Market Data API Keys (replace with your keys)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
COINGECKO_API_KEY=your_coingecko_api_key
EOF
    echo -e "${YELLOW}Please update .env.local with your actual API keys${NC}"
fi

# Create vercel.json if it doesn't exist
if [ ! -f "vercel.json" ]; then
    echo -e "${RED}vercel.json not found. Please ensure you have the correct configuration file.${NC}"
    exit 1
fi

# Check if Vercel is linked to project
if ! vercel ls --scope "$VERCEL_ORG_ID" 2>/dev/null | grep -q "ai-trading-system"; then
    echo -e "${YELLOW}Linking project to Vercel...${NC}"
    vercel link --confirm
fi

# Pull latest changes if on a branch
if [ -n "$(git symbolic-ref --short HEAD 2>/dev/null)" ]; then
    echo -e "${YELLOW}Pulling latest changes...${NC}"
    git pull origin "$(git symbolic-ref --short HEAD 2>/dev/null)"
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
npm install

# Run tests if available
if [ -f "package.json" ] && grep -q "test" package.json; then
    echo -e "${YELLOW}Running tests...${NC}"
    npm test
fi

# Build the application
echo -e "${YELLOW}Building application...${NC}"
npm run build

# Deploy to Vercel
echo -e "${GREEN}Deploying to Vercel...${NC}"
vercel --prod

# Check deployment status
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Deployment successful!${NC}"

    # Get the deployed URL
    DEPLOY_URL=$(vercel ls --scope "$VERCEL_ORG_ID" 2>/dev/null | grep "ai-trading-system" | head -1 | awk '{print $2}')

    echo -e "${GREEN}Your AI Trading System is now live at: ${DEPLOY_URL}${NC}"
    echo -e "${GREEN}Health check endpoint: ${DEPLOY_URL}/api/health${NC}"

    # Verify deployment with health check
    echo -e "${YELLOW}Verifying deployment with health check...${NC}"
    sleep 5  # Wait for deployment to be fully active

    HEALTH_CHECK=$(curl -s "${DEPLOY_URL}/api/health" | jq -r '.status' 2>/dev/null)

    if [ "$HEALTH_CHECK" = "healthy" ]; then
        echo -e "${GREEN}Health check passed! System is operational.${NC}"
    else
        echo -e "${YELLOW}Health check returned: $HEALTH_CHECK${NC}"
        echo -e "${YELLOW}Please check your environment variables and configuration.${NC}"
    fi
else
    echo -e "${RED}Deployment failed. Please check the logs for errors.${NC}"
    exit 1
fi

# Show next steps
echo -e "${GREEN}Deployment complete! Next steps:${NC}"
echo -e "${YELLOW}1. Configure environment variables in Vercel dashboard${NC}"
echo -e "${YELLOW}2. Set up your database and run migrations${NC}"
echo -e "${YELLOW}3. Monitor your trading system performance${NC}"
echo -e "${YELLOW}4. Set up alerts for system health${NC}"

exit 0
