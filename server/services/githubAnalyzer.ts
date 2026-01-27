import { invokeLLM } from "../_core/llm";
import { getCachedGitHubAnalysis, setCachedGitHubAnalysis } from "./analysisCache";

interface GitHubRepoData {
  stars: number;
  forks: number;
  openIssues: number;
  watchers: number;
  commits: number;
  contributors: number;
  lastCommitDate: string;
  createdAt: string;
  updatedAt: string;
  hasLicense: boolean;
  hasReadme: boolean;
  languages: Record<string, number>;
  description: string;
}

interface GitHubAnalysisResult {
  score: number; // 0-100
  data: GitHubRepoData;
  analysis: string;
  issues: string[];
  strengths: string[];
}

/**
 * ดึงข้อมูล GitHub repository ผ่าน GitHub API
 */
async function fetchGitHubData(repoUrl: string): Promise<GitHubRepoData | null> {
  try {
    // Extract owner and repo from URL
    const match = repoUrl.match(/github\.com\/([^\/]+)\/([^\/]+)/);
    if (!match) {
      throw new Error("Invalid GitHub URL");
    }
    
    const [, owner, repo] = match;
    const cleanRepo = repo.replace(/\.git$/, "");
    
    // Fetch repo data
    const repoResponse = await fetch(`https://api.github.com/repos/${owner}/${cleanRepo}`, {
      headers: {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Crypto-Project-Auditor"
      }
    });
    
    if (!repoResponse.ok) {
      console.error("GitHub API error:", await repoResponse.text());
      return null;
    }
    
    const repoData = await repoResponse.json();
    
    // Fetch contributors count
    const contributorsResponse = await fetch(`https://api.github.com/repos/${owner}/${cleanRepo}/contributors?per_page=1`, {
      headers: {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Crypto-Project-Auditor"
      }
    });
    
    let contributorsCount = 0;
    if (contributorsResponse.ok) {
      const linkHeader = contributorsResponse.headers.get("Link");
      if (linkHeader) {
        const match = linkHeader.match(/page=(\d+)>; rel="last"/);
        contributorsCount = match ? parseInt(match[1]) : 1;
      } else {
        const contributors = await contributorsResponse.json();
        contributorsCount = Array.isArray(contributors) ? contributors.length : 0;
      }
    }
    
    // Fetch commits count (approximate from recent commits)
    const commitsResponse = await fetch(`https://api.github.com/repos/${owner}/${cleanRepo}/commits?per_page=1`, {
      headers: {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Crypto-Project-Auditor"
      }
    });
    
    let commitsCount = 0;
    if (commitsResponse.ok) {
      const linkHeader = commitsResponse.headers.get("Link");
      if (linkHeader) {
        const match = linkHeader.match(/page=(\d+)>; rel="last"/);
        commitsCount = match ? parseInt(match[1]) : 1;
      }
    }
    
    return {
      stars: repoData.stargazers_count || 0,
      forks: repoData.forks_count || 0,
      openIssues: repoData.open_issues_count || 0,
      watchers: repoData.watchers_count || 0,
      commits: commitsCount,
      contributors: contributorsCount,
      lastCommitDate: repoData.pushed_at || repoData.updated_at,
      createdAt: repoData.created_at,
      updatedAt: repoData.updated_at,
      hasLicense: !!repoData.license,
      hasReadme: true, // GitHub API doesn't directly tell us, assume true if repo exists
      languages: {}, // Would need separate API call
      description: repoData.description || "",
    };
  } catch (error) {
    console.error("Error fetching GitHub data:", error);
    return null;
  }
}

/**
 * คำนวณคะแนนจากข้อมูล GitHub
 */
function calculateGitHubScore(data: GitHubRepoData): number {
  let score = 0;
  
  // Stars (max 20 points)
  if (data.stars >= 1000) score += 20;
  else if (data.stars >= 500) score += 15;
  else if (data.stars >= 100) score += 10;
  else if (data.stars >= 50) score += 5;
  
  // Forks (max 15 points)
  if (data.forks >= 200) score += 15;
  else if (data.forks >= 100) score += 12;
  else if (data.forks >= 50) score += 8;
  else if (data.forks >= 20) score += 5;
  
  // Contributors (max 15 points)
  if (data.contributors >= 20) score += 15;
  else if (data.contributors >= 10) score += 12;
  else if (data.contributors >= 5) score += 8;
  else if (data.contributors >= 2) score += 5;
  
  // Commits (max 15 points)
  if (data.commits >= 500) score += 15;
  else if (data.commits >= 200) score += 12;
  else if (data.commits >= 100) score += 8;
  else if (data.commits >= 50) score += 5;
  
  // Recent activity (max 20 points)
  const daysSinceLastCommit = Math.floor((Date.now() - new Date(data.lastCommitDate).getTime()) / (1000 * 60 * 60 * 24));
  if (daysSinceLastCommit <= 7) score += 20;
  else if (daysSinceLastCommit <= 30) score += 15;
  else if (daysSinceLastCommit <= 90) score += 10;
  else if (daysSinceLastCommit <= 180) score += 5;
  
  // License (max 10 points)
  if (data.hasLicense) score += 10;
  
  // README (max 5 points)
  if (data.hasReadme) score += 5;
  
  return Math.min(score, 100);
}

/**
 * วิเคราะห์ GitHub repository ด้วย AI
 */
export async function analyzeGitHub(githubUrl: string): Promise<GitHubAnalysisResult> {
  // Check cache first
  const cached = await getCachedGitHubAnalysis(githubUrl);
  if (cached) {
    return cached;
  }

  // Fetch GitHub data
  const data = await fetchGitHubData(githubUrl);
  
  if (!data) {
    return {
      score: 0,
      data: {
        stars: 0,
        forks: 0,
        openIssues: 0,
        watchers: 0,
        commits: 0,
        contributors: 0,
        lastCommitDate: "",
        createdAt: "",
        updatedAt: "",
        hasLicense: false,
        hasReadme: false,
        languages: {},
        description: "",
      },
      analysis: "Unable to fetch GitHub repository data. Please check the URL.",
      issues: ["Invalid or inaccessible GitHub repository"],
      strengths: [],
    };
  }
  
  // Calculate score
  const score = calculateGitHubScore(data);
  
  // AI Analysis
  const aiResponse = await invokeLLM({
    messages: [
      {
        role: "system",
        content: "You are a crypto project security analyst. Analyze GitHub repository metrics and provide insights about the project's development health and potential risks."
      },
      {
        role: "user",
        content: `Analyze this crypto project's GitHub repository:

Stars: ${data.stars}
Forks: ${data.forks}
Contributors: ${data.contributors}
Commits: ${data.commits}
Last Commit: ${data.lastCommitDate}
Created: ${data.createdAt}
Open Issues: ${data.openIssues}
Has License: ${data.hasLicense}
Description: ${data.description}

Provide:
1. Brief analysis of development activity
2. Key strengths (if any)
3. Potential concerns or red flags
4. Overall assessment

Keep response concise and focused on security/reliability aspects.`
      }
    ]
  });
  
  const aiAnalysis = typeof aiResponse.choices[0]?.message?.content === "string" 
    ? aiResponse.choices[0].message.content 
    : "AI analysis unavailable";
  
  // Extract issues and strengths
  const issues: string[] = [];
  const strengths: string[] = [];
  
  if (data.contributors < 2) issues.push("Single or very few contributors - centralization risk");
  if (data.commits < 50) issues.push("Low commit count - limited development history");
  const daysSinceLastCommit = Math.floor((Date.now() - new Date(data.lastCommitDate).getTime()) / (1000 * 60 * 60 * 24));
  if (daysSinceLastCommit > 90) issues.push("No recent commits - project may be abandoned");
  if (!data.hasLicense) issues.push("No license - unclear usage rights");
  if (data.openIssues > 50) issues.push("High number of open issues");
  
  if (data.stars >= 100) strengths.push("Good community interest");
  if (data.contributors >= 5) strengths.push("Multiple contributors - decentralized development");
  if (daysSinceLastCommit <= 30) strengths.push("Active development");
  if (data.hasLicense) strengths.push("Proper licensing");
  
  const result = {
    score,
    data,
    analysis: aiAnalysis,
    issues,
    strengths,
  };

  // Cache the result
  await setCachedGitHubAnalysis(githubUrl, result);

  return result;
}
