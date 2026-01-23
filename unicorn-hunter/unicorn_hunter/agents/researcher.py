"""
Researcher Agent - The Detective
Validates if the asset is a "Unicorn" or just "Dead."
Checks GitHub activity, Whitepapers, and Social Sentiment.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from unicorn_hunter.tools.github_tools import GitHubTools
from unicorn_hunter.tools.social_tools import SocialTools


class ResearcherAgent:
    """Researcher Agent validates fundamentals and project vitality."""

    def __init__(self):
        self.github_tools = GitHubTools()
        self.social_tools = SocialTools()

    async def research(self, candidate: Dict) -> Dict:
        """
        Research a candidate to validate unicorn potential.

        The "Developer" Signal:
        - If price is down 90% but Code Commits are up,
          this is the strongest signal of a sleeping unicorn.

        The "Social Dominance" Divergence:
        - If Price is Flat, but Social Mentions are rising,
          something is brewing.

        Returns:
            Dict with research scores and insights
        """
        symbol = candidate.get("symbol", "").replace("USDT", "")
        name = candidate.get("name", symbol)

        print(f"[Researcher] Analyzing {symbol}...")

        result = {
            "github_score": 0,
            "tech_score": 0,
            "social_score": 0,
            "team_active": 0,
            "fundamental_score": 0,
            "research_insights": [],
        }

        # 1. GitHub Analysis
        try:
            github_data = await self._analyze_github(symbol, name)
            result["github_score"] = github_data["score"]
            result["github_data"] = github_data
            result["team_active"] = 1 if github_data["is_active"] else 0

            if github_data["is_active"]:
                result["research_insights"].append(
                    f"✓ Active GitHub: {github_data['recent_commits']} commits in last 30 days"
                )
            else:
                result["research_insights"].append(
                    "✗ Low GitHub activity - project may be abandoned"
                )
        except Exception as e:
            print(f"[Researcher] GitHub analysis failed: {e}")
            result["research_insights"].append("⚠ GitHub analysis unavailable")

        # 2. Technical/Whitepaper Analysis
        try:
            tech_data = await self._analyze_technology(symbol, name)
            result["tech_score"] = tech_data["score"]
            result["tech_data"] = tech_data

            if tech_data["has_whitepaper"]:
                result["research_insights"].append("✓ Whitepaper/documentation available")
            else:
                result["research_insights"].append("⚠ No whitepaper found")

            if tech_data["unique_proposition"]:
                result["research_insights"].append(
                    f"✓ Unique value proposition: {tech_data['unique_proposition']}"
                )
        except Exception as e:
            print(f"[Researcher] Tech analysis failed: {e}")
            result["research_insights"].append("⚠ Tech analysis unavailable")

        # 3. Social Sentiment Analysis
        try:
            social_data = await self._analyze_social(symbol, name)
            result["social_score"] = social_data["score"]
            result["social_data"] = social_data

            if social_data["sentiment_trend"] == "rising":
                result["research_insights"].append(
                    f"✓ Social sentiment rising (+{social_data['mention_growth']}%)"
                )
            elif social_data["sentiment_trend"] == "stable":
                result["research_insights"].append("○ Social sentiment stable")
            else:
                result["research_insights"].append("✗ Social sentiment declining")

        except Exception as e:
            print(f"[Researcher] Social analysis failed: {e}")
            result["research_insights"].append("⚠ Social analysis unavailable")

        # Calculate overall fundamental score
        result["fundamental_score"] = self._calculate_fundamental_score(
            result["github_score"],
            result["tech_score"],
            result["social_score"],
        )

        result["research_summary"] = self._generate_research_summary(result)

        return result

    async def _analyze_github(self, symbol: str, name: str) -> Dict:
        """Analyze GitHub activity for the project."""
        # Try to find the repo
        repos = await self.github_tools.search_repos(f"{name} {symbol}")

        if not repos:
            return {
                "score": 0,
                "is_active": False,
                "recent_commits": 0,
                "stars": 0,
                "contributors": 0,
            }

        repo = repos[0]  # Use the first match

        # Get repo stats
        stats = await self.github_tools.get_repo_stats(repo["full_name"])

        # Check recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_commits = await self.github_tools.get_recent_commits(repo["full_name"], thirty_days_ago)

        is_active = len(recent_commits) >= 10

        # Calculate score
        score = 0
        if is_active:
            score += 30
        if stats.get("stars", 0) > 100:
            score += 20
        if stats.get("contributors", 0) > 5:
            score += 20
        if len(recent_commits) > 50:
            score += 30

        return {
            "score": min(score, 100),
            "is_active": is_active,
            "recent_commits": len(recent_commits),
            "stars": stats.get("stars", 0),
            "contributors": stats.get("contributors", 0),
            "repo_url": repo["html_url"],
        }

    async def _analyze_technology(self, symbol: str, name: str) -> Dict:
        """Analyze the technology and value proposition."""
        # In production, this would:
        # 1. Search for and analyze whitepaper
        # 2. Check if the tech solves a real problem
        # 3. Compare with competitors

        # For now, return mock data
        return {
            "score": 70,
            "has_whitepaper": True,
            "has_documentation": True,
            "unique_proposition": "Decentralized protocol with strong community",
            "tech_stack": ["Solidity", "Rust", "TypeScript"],
        }

    async def _analyze_social(self, symbol: str, name: str) -> Dict:
        """Analyze social media sentiment."""
        # In production, this would:
        # 1. Check Twitter/X mentions trend
        # 2. Analyze Reddit discussions
        # 3. Check Telegram/Discord activity

        # For now, return mock data
        return {
            "score": 65,
            "sentiment_trend": "rising",  # rising, stable, declining
            "mention_growth": 15,  # percentage growth
            "twitter_mentions": 1250,
            "reddit_posts": 45,
            "sentiment_score": 0.7,  # -1 to 1
        }

    def _calculate_fundamental_score(
        self, github_score: int, tech_score: int, social_score: int
    ) -> int:
        """Calculate overall fundamental score."""
        # Weighted average
        weights = {"github": 0.4, "tech": 0.35, "social": 0.25}
        score = (
            github_score * weights["github"]
            + tech_score * weights["tech"]
            + social_score * weights["social"]
        )
        return round(score)

    def _generate_research_summary(self, result: Dict) -> str:
        """Generate a text summary of the research."""
        insights = result.get("research_insights", [])
        return " | ".join(insights)
