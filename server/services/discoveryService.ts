/**
 * Discovery Service - ค้นหาและแนะนำโปรเจกต์คริปโตที่น่าสนใจ
 */

// In-memory cache for discovery results
const discoveryCache = new Map<string, { data: DiscoveredProject[]; expiry: number }>();
const CACHE_TTL = 300000; // 5 minutes for trending projects

/**
 * Clear the discovery cache (for testing)
 */
export function clearDiscoveryCache(): void {
  discoveryCache.clear();
  console.log('[Discovery] Cache cleared');
}

/**
 * Get cached discovery data
 */
function getCachedDiscovery(filterKey: string): DiscoveredProject[] | null {
  const cached = discoveryCache.get(filterKey);
  if (cached && cached.expiry > Date.now()) {
    console.log(`[Discovery] Cache hit for ${filterKey}`);
    return cached.data;
  }
  if (cached) {
    discoveryCache.delete(filterKey);
  }
  return null;
}

/**
 * Set discovery cache
 */
function setDiscoveryCache(filterKey: string, data: DiscoveredProject[]): void {
  discoveryCache.set(filterKey, {
    data,
    expiry: Date.now() + CACHE_TTL,
  });
  console.log(`[Discovery] Cached ${data.length} projects for ${filterKey}`);
}

export interface DiscoveredProject {
  id: string;
  name: string;
  symbol: string;
  description: string;
  briefSummary?: string;
  marketCap: number;
  price: number;
  priceChange24h: number;
  volume24h: number;
  rank: number;
  category: string;
  status: "trending" | "new" | "hot" | "established";
  
  // Links
  website?: string;
  githubUrl?: string;
  twitterUrl?: string;
  telegramUrl?: string;
  discordUrl?: string;
  
  // Contract info
  contractAddress?: string;
  chain?: string;
  
  // Quick metrics
  holders?: number;
  githubStars?: number;
  twitterFollowers?: number;
  
  // Recommendation score (0-100)
  recommendationScore: number;
  tags: string[];
}

/**
 * ค้นหาโปรเจกต์คริปโตยอดนิยมและ Early Stage
 */
export async function discoverTrendingProjects(filter?: {
  category?: string;
  status?: string;
  minScore?: number;
  maxMarketCap?: number;
}): Promise<DiscoveredProject[]> {
  // Create cache key from filter
  const cacheKey = JSON.stringify(filter || {});

  // Check cache first
  const cached = getCachedDiscovery(cacheKey);
  if (cached) {
    // Apply filters to cached data
    return applyFilters(cached, filter);
  }

  try {
    // ใช้ CoinGecko public API (ไม่ต้อง API key)
    const response = await fetch(
      'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false&price_change_percentage=24h'
    );
    
    if (!response.ok) {
      console.error("CoinGecko API error:", await response.text());
      return getMockProjects();
    }
    
    const data = await response.json();
    
    // แปลงข้อมูลเป็น format ของเรา
    const projects: DiscoveredProject[] = await Promise.all(
      data.slice(0, 15).map(async (coin: any) => {
        // ดึงข้อมูลเพิ่มเติมของแต่ละ coin
        let detailData: any = {};
        try {
          const detailResponse = await fetch(
            `https://api.coingecko.com/api/v3/coins/${coin.id}`
          );
          if (detailResponse.ok) {
            detailData = await detailResponse.json();
          }
        } catch (error) {
          console.error(`Error fetching details for ${coin.id}:`, error);
        }
        
        // คำนวณ recommendation score
        const recommendationScore = calculateRecommendationScore({
          marketCapRank: coin.market_cap_rank,
          priceChange24h: coin.price_change_percentage_24h,
          volume: coin.total_volume,
          marketCap: coin.market_cap,
          hasGithub: !!detailData.links?.repos_url?.github?.[0],
          hasTwitter: !!detailData.links?.twitter_screen_name,
        });
        
        // สร้าง tags
        const tags: string[] = [];
        if (coin.market_cap_rank <= 10) tags.push("Top 10");
        else if (coin.market_cap_rank <= 50) tags.push("Top 50");
        if (coin.price_change_percentage_24h > 10) tags.push("Hot");
        if (coin.price_change_percentage_24h < -10) tags.push("Dip");
        if (detailData.links?.repos_url?.github?.[0]) tags.push("Open Source");
        if (coin.total_volume > 1000000000) tags.push("High Volume");
        
        return {
          id: coin.id,
          name: coin.name,
          symbol: coin.symbol.toUpperCase(),
          description: detailData.description?.en?.substring(0, 200) || `${coin.name} is a cryptocurrency project.`,
          briefSummary: detailData.description?.en?.substring(0, 100) || `${coin.name} cryptocurrency`,
          marketCap: coin.market_cap,
          price: coin.current_price,
          priceChange24h: coin.price_change_percentage_24h,
          volume24h: coin.total_volume,
          rank: coin.market_cap_rank,
          category: detailData.categories?.[0] || "Cryptocurrency",
          status: coin.market_cap_rank <= 50 ? "established" : "trending",
          
          website: detailData.links?.homepage?.[0],
          githubUrl: detailData.links?.repos_url?.github?.[0],
          twitterUrl: detailData.links?.twitter_screen_name 
            ? `https://twitter.com/${detailData.links.twitter_screen_name}`
            : undefined,
          telegramUrl: detailData.links?.telegram_channel_identifier
            ? `https://t.me/${detailData.links.telegram_channel_identifier}`
            : undefined,
          
          contractAddress: detailData.platforms?.ethereum || detailData.contract_address,
          chain: detailData.asset_platform_id || "ethereum",
          
          githubStars: detailData.developer_data?.stars,
          twitterFollowers: detailData.community_data?.twitter_followers,
          
          recommendationScore,
          tags,
        };
      })
    );
    
    // เพิ่มโปรเจกต์ Early Stage
    const earlyStageProjects = getEarlyStageProjects();
    
    // รวมและเรียงตาม recommendation score
    const allProjects = [...projects, ...earlyStageProjects]
      .sort((a, b) => b.recommendationScore - a.recommendationScore);

    // Cache the results
    setDiscoveryCache(cacheKey, allProjects);

    return applyFilters(allProjects, filter);

  } catch (error) {
    console.error("Error discovering projects:", error);
    return getMockProjects();
  }
}

/**
 * Apply filters to projects list
 */
function applyFilters(projects: DiscoveredProject[], filter?: {
  category?: string;
  status?: string;
  minScore?: number;
  maxMarketCap?: number;
}): DiscoveredProject[] {
  let filtered = projects;

  if (filter?.category) {
    filtered = filtered.filter(p => p.category.toLowerCase().includes(filter.category!.toLowerCase()));
  }
  if (filter?.status) {
    filtered = filtered.filter(p => p.status === filter.status);
  }
  if (filter?.minScore) {
    filtered = filtered.filter(p => p.recommendationScore >= filter.minScore!);
  }
  if (filter?.maxMarketCap) {
    filtered = filtered.filter(p => p.marketCap <= filter.maxMarketCap!);
  }

  return filtered;
}

/**
 * คำนวณคะแนนแนะนำ (0-100)
 */
function calculateRecommendationScore(metrics: {
  marketCapRank: number;
  priceChange24h: number;
  volume: number;
  marketCap: number;
  hasGithub: boolean;
  hasTwitter: boolean;
}): number {
  let score = 50; // เริ่มต้นที่ 50
  
  // Market cap rank (max 25 points)
  if (metrics.marketCapRank <= 10) score += 25;
  else if (metrics.marketCapRank <= 50) score += 20;
  else if (metrics.marketCapRank <= 100) score += 15;
  else if (metrics.marketCapRank <= 200) score += 10;
  
  // Price momentum (max 15 points)
  if (metrics.priceChange24h > 20) score += 15;
  else if (metrics.priceChange24h > 10) score += 12;
  else if (metrics.priceChange24h > 5) score += 8;
  else if (metrics.priceChange24h > 0) score += 5;
  else if (metrics.priceChange24h < -20) score -= 10;
  
  // Volume (max 15 points)
  if (metrics.volume > 1000000000) score += 15;
  else if (metrics.volume > 500000000) score += 12;
  else if (metrics.volume > 100000000) score += 8;
  else if (metrics.volume > 50000000) score += 5;
  
  // Transparency (max 15 points)
  if (metrics.hasGithub) score += 10;
  if (metrics.hasTwitter) score += 5;
  
  return Math.max(0, Math.min(100, Math.round(score)));
}

/**
 * ค้นหาโปรเจกต์ Early Stage
 */
function getEarlyStageProjects(): DiscoveredProject[] {
  return [
    {
      id: "arbitrum",
      name: "Arbitrum",
      symbol: "ARB",
      description: "Arbitrum is a Layer 2 scaling solution for Ethereum that enables high-speed, low-cost smart contracts.",
      briefSummary: "Layer 2 scaling solution ที่เพิ่มความเร็วและลดต้นทุนของ Ethereum ด้วยการประมวลผลแบบออฟเชน",
      marketCap: 5000000000,
      price: 1.2,
      priceChange24h: 8.5,
      volume24h: 450000000,
      rank: 25,
      category: "Layer 2",
      status: "established",
      website: "https://arbitrum.io",
      githubUrl: "https://github.com/OffchainLabs/arbitrum",
      twitterUrl: "https://twitter.com/arbitrum",
      contractAddress: "0xB50721BCf8d664c30412Cfbc6cf7a15145234ad1",
      chain: "ethereum",
      githubStars: 3200,
      twitterFollowers: 450000,
      recommendationScore: 85,
      tags: ["Layer 2", "Scaling", "Ethereum"],
    },
    {
      id: "optimism",
      name: "Optimism",
      symbol: "OP",
      description: "Optimism is an EVM-equivalent Layer 2 solution that scales Ethereum with minimal changes to the protocol.",
      briefSummary: "Layer 2 EVM-compatible ที่ปรับขยาย Ethereum ด้วยการเปลี่ยนแปลงขั้นต่ำ",
      marketCap: 3500000000,
      price: 2.8,
      priceChange24h: 6.2,
      volume24h: 280000000,
      rank: 35,
      category: "Layer 2",
      status: "established",
      website: "https://optimism.io",
      githubUrl: "https://github.com/ethereum-optimism",
      twitterUrl: "https://twitter.com/optimismFND",
      contractAddress: "0x4200000000000000000000000000000000000042",
      chain: "ethereum",
      githubStars: 2800,
      twitterFollowers: 380000,
      recommendationScore: 82,
      tags: ["Layer 2", "EVM", "Scaling"],
    },
    {
      id: "sui",
      name: "Sui",
      symbol: "SUI",
      description: "Sui is a Layer 1 blockchain designed for high throughput and low latency with a focus on user experience.",
      briefSummary: "Layer 1 blockchain ที่ออกแบบมาเพื่อความเร็วสูงและความล่าช้าต่ำ พร้อมการใช้งานที่ง่าย",
      marketCap: 2800000000,
      price: 3.5,
      priceChange24h: 12.3,
      volume24h: 320000000,
      rank: 40,
      category: "Layer 1",
      status: "hot",
      website: "https://sui.io",
      githubUrl: "https://github.com/MystenLabs/sui",
      twitterUrl: "https://twitter.com/SuiNetwork",
      contractAddress: "0x0000000000000000000000000000000000000000",
      chain: "sui",
      githubStars: 5600,
      twitterFollowers: 520000,
      recommendationScore: 88,
      tags: ["Layer 1", "Hot", "High Speed"],
    },
    {
      id: "aptos",
      name: "Aptos",
      symbol: "APT",
      description: "Aptos is a Layer 1 blockchain powered by Move language, designed for scalability and safety.",
      briefSummary: "Layer 1 blockchain ที่ใช้ Move language เพื่อความปลอดภัยและการขยายตัวที่ดี",
      marketCap: 2200000000,
      price: 12.5,
      priceChange24h: 9.8,
      volume24h: 250000000,
      rank: 45,
      category: "Layer 1",
      status: "hot",
      website: "https://aptos.dev",
      githubUrl: "https://github.com/aptos-labs/aptos-core",
      twitterUrl: "https://twitter.com/AptosLabs",
      contractAddress: "0x0000000000000000000000000000000000000000",
      chain: "aptos",
      githubStars: 4200,
      twitterFollowers: 420000,
      recommendationScore: 86,
      tags: ["Layer 1", "Hot", "Move Language"],
    },
    {
      id: "worldcoin",
      name: "Worldcoin",
      symbol: "WLD",
      description: "Worldcoin is building a global digital currency and identity system using biometric verification.",
      briefSummary: "สกุลเงินดิจิทัลโลกและระบบตัวตนที่ใช้การยืนยันชีววิทยา",
      marketCap: 1800000000,
      price: 5.2,
      priceChange24h: 15.5,
      volume24h: 180000000,
      rank: 55,
      category: "AI & Identity",
      status: "new",
      website: "https://worldcoin.org",
      twitterUrl: "https://twitter.com/worldcoin",
      contractAddress: "0xdc0d56d2cd919eee60f3eb9273d22658cae6d251",
      chain: "ethereum",
      twitterFollowers: 380000,
      recommendationScore: 75,
      tags: ["New", "AI", "Identity"],
    },
    {
      id: "render",
      name: "Render Token",
      symbol: "RNDR",
      description: "Render is a decentralized GPU rendering network powered by blockchain technology.",
      briefSummary: "เครือข่าย GPU rendering แบบกระจายอำนาจที่ขับเคลื่อนด้วยเทคโนโลยี blockchain",
      marketCap: 1500000000,
      price: 8.5,
      priceChange24h: 18.2,
      volume24h: 150000000,
      rank: 65,
      category: "AI & Compute",
      status: "hot",
      website: "https://render.com",
      githubUrl: "https://github.com/rendernetwork",
      twitterUrl: "https://twitter.com/RenderToken",
      contractAddress: "0x6de037ef9ad2725eb40118bb1702e8135dee7f07",
      chain: "ethereum",
      githubStars: 1200,
      twitterFollowers: 280000,
      recommendationScore: 78,
      tags: ["Hot", "AI", "GPU"],
    },
  ];
}

/**
 * Mock projects สำหรับกรณีที่ API ไม่ทำงาน
 */
function getMockProjects(): DiscoveredProject[] {
  return [
    {
      id: "uniswap",
      name: "Uniswap",
      symbol: "UNI",
      description: "A leading decentralized exchange (DEX) protocol built on Ethereum, enabling automated token swaps through liquidity pools.",
      briefSummary: "โปรโตคอล DEX ชั้นนำที่ช่วยให้สามารถแลกเปลี่ยนโทเค็นอัตโนมัติผ่านแหล่งสภาพคล่อง",
      marketCap: 5000000000,
      price: 8.5,
      priceChange24h: 5.2,
      volume24h: 250000000,
      rank: 15,
      category: "Decentralized Exchange",
      status: "established",
      website: "https://uniswap.org",
      githubUrl: "https://github.com/Uniswap",
      twitterUrl: "https://twitter.com/Uniswap",
      contractAddress: "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
      chain: "ethereum",
      githubStars: 4500,
      twitterFollowers: 850000,
      recommendationScore: 92,
      tags: ["Top 50", "DeFi", "Open Source", "High Volume"],
    },
    {
      id: "chainlink",
      name: "Chainlink",
      symbol: "LINK",
      description: "A decentralized oracle network providing real-world data to smart contracts on blockchain networks.",
      briefSummary: "เครือข่าย Oracle แบบกระจายอำนาจที่ให้ข้อมูลจากโลกจริงแก่สัญญาอัจฉริยะ",
      marketCap: 8000000000,
      price: 14.2,
      priceChange24h: 3.8,
      volume24h: 450000000,
      rank: 12,
      category: "Oracle",
      status: "established",
      website: "https://chain.link",
      githubUrl: "https://github.com/smartcontractkit/chainlink",
      twitterUrl: "https://twitter.com/chainlink",
      contractAddress: "0x514910771AF9Ca656af840dff83E8264EcF986CA",
      chain: "ethereum",
      githubStars: 6200,
      twitterFollowers: 1200000,
      recommendationScore: 95,
      tags: ["Top 50", "Oracle", "Open Source", "High Volume"],
    },
    {
      id: "aave",
      name: "Aave",
      symbol: "AAVE",
      description: "A decentralized lending protocol that allows users to lend and borrow cryptocurrencies without intermediaries.",
      briefSummary: "โปรโตคอลการให้ยืมแบบกระจายอำนาจที่ให้ผู้ใช้สามารถให้ยืมและยืมคริปโตโลยีโดยไม่มีตัวกลาง",
      marketCap: 2500000000,
      price: 165.0,
      priceChange24h: 7.5,
      volume24h: 180000000,
      rank: 35,
      category: "Lending",
      status: "established",
      website: "https://aave.com",
      githubUrl: "https://github.com/aave",
      twitterUrl: "https://twitter.com/AaveAave",
      discordUrl: "https://discord.gg/aave",
      contractAddress: "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
      chain: "ethereum",
      githubStars: 3800,
      twitterFollowers: 650000,
      recommendationScore: 88,
      tags: ["Top 50", "DeFi", "Lending", "Open Source"],
    },
    {
      id: "polygon",
      name: "Polygon",
      symbol: "MATIC",
      description: "A protocol and framework for building Ethereum-compatible blockchain networks and scaling solutions.",
      briefSummary: "โปรโตคอลและเฟรมเวิร์กสำหรับสร้างเครือข่าย blockchain ที่เข้ากันได้กับ Ethereum",
      marketCap: 6500000000,
      price: 0.85,
      priceChange24h: 4.2,
      volume24h: 320000000,
      rank: 18,
      category: "Layer 2",
      status: "established",
      website: "https://polygon.technology",
      githubUrl: "https://github.com/maticnetwork",
      twitterUrl: "https://twitter.com/0xPolygon",
      contractAddress: "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0",
      chain: "ethereum",
      githubStars: 5100,
      twitterFollowers: 980000,
      recommendationScore: 90,
      tags: ["Top 50", "Layer 2", "Scaling", "High Volume"],
    },
    {
      id: "the-sandbox",
      name: "The Sandbox",
      symbol: "SAND",
      description: "A virtual world where players can build, own, and monetize gaming experiences using blockchain technology.",
      briefSummary: "โลกเสมือนที่ผู้เล่นสามารถสร้าง เป็นเจ้าของ และสร้างรายได้จากประสบการณ์เกมโดยใช้เทคโนโลยี blockchain",
      marketCap: 1200000000,
      price: 0.52,
      priceChange24h: 12.5,
      volume24h: 95000000,
      rank: 65,
      category: "Metaverse",
      status: "hot",
      website: "https://www.sandbox.game",
      githubUrl: "https://github.com/thesandboxgame",
      twitterUrl: "https://twitter.com/TheSandboxGame",
      contractAddress: "0x3845badAde8e6dFF049820680d1F14bD3903a5d0",
      chain: "ethereum",
      twitterFollowers: 420000,
      recommendationScore: 78,
      tags: ["Hot", "Metaverse", "Gaming", "NFT"],
    },
  ];
}
