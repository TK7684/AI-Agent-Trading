"""
Unicorn Hunter - FastAPI Server
Multi-agent CrewAI system for finding high-potential crypto assets.
"""

import os
import sys
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unicorn_hunter.config import settings
from unicorn_hunter.agents.scanner import ScannerAgent
from unicorn_hunter.agents.researcher import ResearcherAgent
from unicorn_hunter.agents.sniper import SniperAgent


# Pydantic models for API
class ScanRequest(BaseModel):
    scan_type: str = Field(default="crypto", description="Type of scan: crypto, stocks, or all")
    min_market_cap: Optional[int] = Field(default=10000000, description="Minimum market cap in USD")
    max_market_cap: Optional[int] = Field(default=100000000, description="Maximum market cap in USD")
    min_price_drop: Optional[int] = Field(default=80, description="Minimum price drop from ATH (%)")
    min_volume_spike: Optional[int] = Field(default=300, description="Minimum volume spike (%)")
    use_trending: Optional[bool] = Field(default=True, description="Use CoinGecko trending data")
    use_onchain: Optional[bool] = Field(default=False, description="Use Dune/Glassnode on-chain data (requires API keys)")


class ScanStatus(BaseModel):
    scan_id: str
    status: str
    message: str


class ScanResult(BaseModel):
    scan_id: str
    status: str
    candidates: list


# Global state for scan tracking
scans = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    print("Starting Unicorn Hunter API...")
    yield
    print("Shutting down Unicorn Hunter API...")


# Initialize FastAPI app
app = FastAPI(
    title="Unicorn Hunter API",
    description="Multi-agent AI system for finding high-potential crypto assets",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "unicorn-hunter"}


@app.post("/analyze", response_model=ScanStatus)
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    Start a new unicorn hunt scan.

    This triggers multi-agent CrewAI system to:
    1. Scanner: Find assets meeting bottom criteria
    2. Researcher: Validate fundamentals
    3. Sniper: Confirm technical entry signals
    """
    import uuid
    scan_id = str(uuid.uuid4())

    # Initialize scan status
    scans[scan_id] = {
        "status": "pending",
        "scan_type": request.scan_type,
        "progress": 0,
        "message": "Scan initialized",
    }

    # Add background task
    background_tasks.add_task(run_scan, scan_id, request)

    return ScanStatus(
        scan_id=scan_id,
        status="pending",
        message=f"Scan started with ID: {scan_id}"
    )


@app.get("/status/{scan_id}", response_model=ScanStatus)
async def get_scan_status(scan_id: str):
    """Get status of a running scan."""
    if scan_id not in scans:
        raise HTTPException(status_code=404, detail="Scan not found")

    scan_data = scans[scan_id]
    return ScanStatus(
        scan_id=scan_id,
        status=scan_data["status"],
        message=scan_data.get("message", ""),
    )


@app.get("/results/{scan_id}")
async def get_scan_results(scan_id: str):
    """Get results of a completed scan."""
    if scan_id not in scans:
        raise HTTPException(status_code=404, detail="Scan not found")

    scan_data = scans[scan_id]
    if scan_data["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Scan not completed. Current status: {scan_data['status']}"
        )

    return {
        "scan_id": scan_id,
        "status": scan_data["status"],
        "candidates": scan_data.get("candidates", []),
        "summary": scan_data.get("summary", {}),
    }


async def run_scan(scan_id: str, request: ScanRequest):
    """Run unicorn hunt scan using CrewAI agents."""
    try:
        # Update status
        scans[scan_id]["status"] = "running"
        scans[scan_id]["progress"] = 10
        scans[scan_id]["message"] = "Initializing Scanner Agent..."

        # Choose scanner based on data source preferences
        if request.use_trending or request.use_onchain:
            from unicorn_hunter.agents.scanner_optimized import OptimizedScannerAgent
            scanner = OptimizedScannerAgent(
                coingecko_api_key=settings.COINGECKO_API_KEY,
                dune_api_key=settings.DUNE_API_KEY,
                covalent_api_key=settings.COVALENT_API_KEY,
                ethplorer_api_key=settings.ETHPLORER_API_KEY,
            )
            scans[scan_id]["message"] = "Using optimized scanner with FREE data sources..."
        else:
            from unicorn_hunter.agents.scanner import ScannerAgent
            scanner = ScannerAgent()

        researcher = ResearcherAgent()
        sniper = SniperAgent()

        # Phase 1: Scanner - Find candidates
        scans[scan_id]["message"] = "Scanning market for candidates..."

        scan_kwargs = {
            "scan_type": request.scan_type,
            "min_market_cap": request.min_market_cap,
            "max_market_cap": request.max_market_cap,
            "min_price_drop": request.min_price_drop,
            "min_volume_spike": request.min_volume_spike,
        }

        # Add optimized scanner parameters if using OptimizedScannerAgent
        if request.use_trending or request.use_onchain:
            scan_kwargs["use_trending"] = request.use_trending
            scan_kwargs["use_onchain"] = request.use_onchain

        scanner_results = await scanner.scan(**scan_kwargs)

        if not scanner_results.get("candidates"):
            scans[scan_id] = {
                "status": "completed",
                "progress": 100,
                "message": "No candidates found matching criteria",
                "candidates": [],
                "summary": {"total_scanned": 0, "candidates_found": 0},
            }
            return

        scans[scan_id]["progress"] = 40
        scans[scan_id]["message"] = f"Found {len(scanner_results['candidates'])} candidates. Researching..."

        # Phase 2: Researcher - Validate fundamentals
        researched_candidates = []
        for i, candidate in enumerate(scanner_results["candidates"]):
            scans[scan_id]["message"] = f"Researching {candidate['symbol']} ({i+1}/{len(scanner_results['candidates'])})..."
            research_result = await researcher.research(candidate)
            candidate.update(research_result)
            researched_candidates.append(candidate)

        scans[scan_id]["progress"] = 70
        scans[scan_id]["message"] = "Analyzing technical entry signals..."

        # Phase 3: Sniper - Confirm entry signals
        final_candidates = []
        for i, candidate in enumerate(researched_candidates):
            scans[scan_id]["message"] = f"Analyzing {candidate['symbol']} for entry ({i+1}/{len(researched_candidates)})..."
            sniper_result = await sniper.analyze(candidate)

            # Only include candidates with positive recommendations
            if sniper_result.get("recommendation") in ["BUY", "STRONG_BUY"]:
                candidate.update(sniper_result)
                final_candidates.append(candidate)

        scans[scan_id]["progress"] = 100
        scans[scan_id] = {
            "status": "completed",
            "progress": 100,
            "message": f"Scan complete. Found {len(final_candidates)} unicorn candidates.",
            "candidates": final_candidates,
            "summary": {
                "total_scanned": scanner_results.get("total_scanned", 0),
                "candidates_found": len(final_candidates),
                "scan_type": request.scan_type,
            },
        }

    except Exception as e:
        scans[scan_id] = {
            "status": "failed",
            "progress": scans[scan_id].get("progress", 0),
            "message": f"Scan failed: {str(e)}",
            "candidates": [],
            "error": str(e),
        }


def main():
    """Run FastAPI server."""
    uvicorn.run(
        "unicorn_hunter.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()