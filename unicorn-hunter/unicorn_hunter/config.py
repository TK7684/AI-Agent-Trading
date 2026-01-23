"""
Unicorn Hunter Configuration
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Keys - ALL FREE TIERS (NO PAID SERVICES)
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

    # CoinGecko API (optional - free tier: 50 calls/minute, no credit card)
    # Get from: https://www.coingecko.com/en/developers
    COINGECKO_API_KEY: str = os.getenv("COINGECKO_API_KEY", "")

    # Dune Analytics API (optional - free tier: 1,000 requests/month, no credit card)
    # Get from: https://app.dune.com/apikey
    DUNE_API_KEY: str = os.getenv("DUNE_API_KEY", "")

    # Covalent API (optional - free tier: 300,000 requests/month, no credit card)
    # Get from: https://www.covalenthq.com/
    COVALENT_API_KEY: str = os.getenv("COVALENT_API_KEY", "")

    # Ethplorer API (optional - free tier, no key required for basic usage)
    # Get from: https://ethplorer.io/
    ETHPLORER_API_KEY: str = os.getenv("ETHPLORER_API_KEY", "freekey")

    # Gemini API (required - for AI analysis)
    # This is the ONLY paid API you should need
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # CORS
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173"
    ).split(",")

    # Node.js Integration
    NODE_JS_URL: str = os.getenv("NODE_JS_URL", "http://localhost:3000")

    # CrewAI Settings
    CREWAI_API_KEY: str = os.getenv("CREWAI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
