"""
GitHub Tools - GitHub API integration
"""

import httpx
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class GitHubTools:
    """Tools for fetching GitHub repository data."""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    async def search_repos(self, query: str, sort: str = "stars", order: str = "desc") -> List[Dict]:
        """Search for repositories matching query."""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "q": query,
                    "sort": sort,
                    "order": order,
                    "per_page": 10,
                }

                response = await client.get(
                    f"{self.base_url}/search/repositories",
                    params=params,
                    headers=self.headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("items", [])
                else:
                    print(f"[GitHubTools] Search failed: {response.status_code}")
                    return []

        except Exception as e:
            print(f"[GitHubTools] Search error: {e}")
            return []

    async def get_repo_stats(self, repo_full_name: str) -> Dict:
        """Get repository statistics."""
        try:
            async with httpx.AsyncClient() as client:
                # Get basic repo info
                response = await client.get(
                    f"{self.base_url}/repos/{repo_full_name}",
                    headers=self.headers,
                )

                if response.status_code == 200:
                    repo = response.json()

                    # Get contributors count
                    contributors = await self._get_contributors_count(repo_full_name)

                    return {
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "open_issues": repo.get("open_issues_count", 0),
                        "watchers": repo.get("subscribers_count", 0),
                        "contributors": contributors,
                        "language": repo.get("language"),
                        "created_at": repo.get("created_at"),
                        "updated_at": repo.get("updated_at"),
                    }
                else:
                    return {}

        except Exception as e:
            print(f"[GitHubTools] Stats error: {e}")
            return {}

    async def get_recent_commits(self, repo_full_name: str, since: datetime) -> List[Dict]:
        """Get commits since a specific date."""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "since": since.isoformat(),
                    "per_page": 100,
                }

                response = await client.get(
                    f"{self.base_url}/repos/{repo_full_name}/commits",
                    params=params,
                    headers=self.headers,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return []

        except Exception as e:
            print(f"[GitHubTools] Commits error: {e}")
            return []

    async def _get_contributors_count(self, repo_full_name: str) -> int:
        """Get number of contributors to a repository."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{repo_full_name}/contributors",
                    params={"per_page": 1},
                    headers=self.headers,
                )

                # The Link header contains the total count
                link_header = response.headers.get("Link", "")
                if link_header and 'page=' in link_header:
                    # Parse the last page number
                    for part in link_header.split(","):
                        if 'rel="last"' in part:
                            import re
                            match = re.search(r'page=(\d+)', part)
                            if match:
                                return int(match.group(1))

                # Fallback: fetch and count
                response = await client.get(
                    f"{self.base_url}/repos/{repo_full_name}/contributors",
                    params={"per_page": 100},
                    headers=self.headers,
                )

                if response.status_code == 200:
                    return len(response.json())

                return 0

        except Exception as e:
            print(f"[GitHubTools] Contributors error: {e}")
            return 0

    async def check_repo_activity(self, repo_full_name: str, days: int = 30) -> Dict:
        """Check if repository has been active in the last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        commits = await self.get_recent_commits(repo_full_name, since)

        return {
            "active": len(commits) > 0,
            "commit_count": len(commits),
            "days_checked": days,
        }
