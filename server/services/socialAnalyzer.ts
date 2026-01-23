import { invokeLLM } from "../_core/llm";

interface TwitterData {
  followers?: number;
  tweets?: number;
  engagement?: number;
  verified?: boolean;
  accountAge?: number; // days
  lastTweetDate?: string;
  avgLikes?: number;
  avgRetweets?: number;
}

interface TelegramData {
  members?: number;
  activeMembers?: number;
  messagesPerDay?: number;
  adminActive?: boolean;
  hasBot?: boolean;
  spamLevel?: string;
}

interface DiscordData {
  members?: number;
  onlineMembers?: number;
  channels?: number;
  activeChannels?: number;
  moderators?: number;
  verificationLevel?: string;
}

interface SocialAnalysisResult {
  score: number; // 0-100
  data: TwitterData | TelegramData | DiscordData;
  analysis: string;
  concerns: string[];
  positives: string[];
}

/**
 * วิเคราะห์ Twitter/X
 */
export async function analyzeTwitter(twitterUrl: string): Promise<SocialAnalysisResult> {
  try {
    // Extract username from URL
    const match = twitterUrl.match(/twitter\.com\/([^\/\?]+)|x\.com\/([^\/\?]+)/);
    if (!match) {
      throw new Error("Invalid Twitter URL");
    }

    // Mock data - ในระบบจริงควรใช้ Twitter API หรือ scraping
    const mockData: TwitterData = {
      followers: 15420,
      tweets: 3240,
      engagement: 2.5, // percentage
      verified: false,
      accountAge: 450, // days
      lastTweetDate: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      avgLikes: 85,
      avgRetweets: 23,
    };

    // คำนวณคะแนน
    let score = 50;

    // Followers (max 25 points)
    if (mockData.followers && mockData.followers >= 100000) score += 25;
    else if (mockData.followers && mockData.followers >= 50000) score += 20;
    else if (mockData.followers && mockData.followers >= 10000) score += 15;
    else if (mockData.followers && mockData.followers >= 5000) score += 10;
    else if (mockData.followers && mockData.followers >= 1000) score += 5;
    else score -= 10; // Too few followers

    // Engagement (max 20 points)
    if (mockData.engagement && mockData.engagement >= 5) score += 20;
    else if (mockData.engagement && mockData.engagement >= 3) score += 15;
    else if (mockData.engagement && mockData.engagement >= 2) score += 10;
    else if (mockData.engagement && mockData.engagement >= 1) score += 5;

    // Account age (max 15 points)
    if (mockData.accountAge && mockData.accountAge >= 365) score += 15;
    else if (mockData.accountAge && mockData.accountAge >= 180) score += 10;
    else if (mockData.accountAge && mockData.accountAge >= 90) score += 5;
    else score -= 10; // Very new account

    // Recent activity (max 15 points)
    if (mockData.lastTweetDate) {
      const daysSinceLastTweet = Math.floor(
        (Date.now() - new Date(mockData.lastTweetDate).getTime()) / (1000 * 60 * 60 * 24)
      );
      if (daysSinceLastTweet <= 1) score += 15;
      else if (daysSinceLastTweet <= 7) score += 12;
      else if (daysSinceLastTweet <= 30) score += 8;
      else if (daysSinceLastTweet <= 90) score += 3;
      else score -= 10; // Inactive
    }

    // Verified (10 points)
    if (mockData.verified) score += 10;

    // Tweet count (max 15 points)
    if (mockData.tweets && mockData.tweets >= 1000) score += 15;
    else if (mockData.tweets && mockData.tweets >= 500) score += 10;
    else if (mockData.tweets && mockData.tweets >= 100) score += 5;

    score = Math.max(0, Math.min(100, score));

    // AI Analysis
    const aiResponse = await invokeLLM({
      messages: [
        {
          role: "system",
          content: "You are a social media analyst. Analyze Twitter presence for crypto projects."
        },
        {
          role: "user",
          content: `Analyze this crypto project's Twitter account:

Followers: ${mockData.followers}
Total Tweets: ${mockData.tweets}
Engagement Rate: ${mockData.engagement}%
Verified: ${mockData.verified}
Account Age: ${mockData.accountAge} days
Last Tweet: ${mockData.lastTweetDate}
Avg Likes: ${mockData.avgLikes}
Avg Retweets: ${mockData.avgRetweets}

Provide brief analysis:
1. Community engagement quality
2. Account credibility
3. Activity consistency
4. Red flags or concerns`
        }
      ]
    });

    const aiAnalysis = typeof aiResponse.choices[0]?.message?.content === "string"
      ? aiResponse.choices[0].message.content
      : "AI analysis unavailable";

    const concerns: string[] = [];
    const positives: string[] = [];

    if (mockData.followers && mockData.followers < 1000) concerns.push("Low follower count");
    if (mockData.accountAge && mockData.accountAge < 90) concerns.push("Very new account");
    if (mockData.engagement && mockData.engagement < 1) concerns.push("Low engagement rate");
    if (mockData.lastTweetDate) {
      const daysSinceLastTweet = Math.floor(
        (Date.now() - new Date(mockData.lastTweetDate).getTime()) / (1000 * 60 * 60 * 24)
      );
      if (daysSinceLastTweet > 30) concerns.push("Inactive account");
    }

    if (mockData.verified) positives.push("Verified account");
    if (mockData.followers && mockData.followers >= 10000) positives.push("Strong follower base");
    if (mockData.engagement && mockData.engagement >= 2) positives.push("Good engagement");
    if (mockData.accountAge && mockData.accountAge >= 365) positives.push("Established account");

    return {
      score,
      data: mockData,
      analysis: aiAnalysis,
      concerns,
      positives,
    };
  } catch (error) {
    console.error("Error analyzing Twitter:", error);
    return {
      score: 0,
      data: {},
      analysis: "Unable to analyze Twitter account.",
      concerns: ["Analysis failed"],
      positives: [],
    };
  }
}

/**
 * วิเคราะห์ Telegram
 */
export async function analyzeTelegram(telegramUrl: string): Promise<SocialAnalysisResult> {
  try {
    // Mock data - ในระบบจริงควรใช้ Telegram API
    const mockData: TelegramData = {
      members: 8540,
      activeMembers: 1200,
      messagesPerDay: 450,
      adminActive: true,
      hasBot: true,
      spamLevel: "low",
    };

    let score = 50;

    // Members (max 25 points)
    if (mockData.members && mockData.members >= 50000) score += 25;
    else if (mockData.members && mockData.members >= 20000) score += 20;
    else if (mockData.members && mockData.members >= 10000) score += 15;
    else if (mockData.members && mockData.members >= 5000) score += 10;
    else if (mockData.members && mockData.members >= 1000) score += 5;

    // Active members ratio (max 25 points)
    if (mockData.members && mockData.activeMembers) {
      const activeRatio = (mockData.activeMembers / mockData.members) * 100;
      if (activeRatio >= 20) score += 25;
      else if (activeRatio >= 15) score += 20;
      else if (activeRatio >= 10) score += 15;
      else if (activeRatio >= 5) score += 10;
    }

    // Messages per day (max 20 points)
    if (mockData.messagesPerDay && mockData.messagesPerDay >= 500) score += 20;
    else if (mockData.messagesPerDay && mockData.messagesPerDay >= 200) score += 15;
    else if (mockData.messagesPerDay && mockData.messagesPerDay >= 100) score += 10;
    else if (mockData.messagesPerDay && mockData.messagesPerDay >= 50) score += 5;

    // Admin active (15 points)
    if (mockData.adminActive) score += 15;
    else score -= 10;

    // Spam level (15 points)
    if (mockData.spamLevel === "low") score += 15;
    else if (mockData.spamLevel === "medium") score += 5;
    else score -= 15;

    score = Math.max(0, Math.min(100, score));

    const aiResponse = await invokeLLM({
      messages: [
        {
          role: "system",
          content: "You are a community analyst. Analyze Telegram group health for crypto projects."
        },
        {
          role: "user",
          content: `Analyze this Telegram group:

Total Members: ${mockData.members}
Active Members: ${mockData.activeMembers}
Messages/Day: ${mockData.messagesPerDay}
Admin Active: ${mockData.adminActive}
Has Bot: ${mockData.hasBot}
Spam Level: ${mockData.spamLevel}

Provide brief analysis:
1. Community health
2. Engagement quality
3. Moderation effectiveness
4. Concerns or red flags`
        }
      ]
    });

    const aiAnalysis = typeof aiResponse.choices[0]?.message?.content === "string"
      ? aiResponse.choices[0].message.content
      : "AI analysis unavailable";

    const concerns: string[] = [];
    const positives: string[] = [];

    if (mockData.members && mockData.members < 1000) concerns.push("Small community");
    if (!mockData.adminActive) concerns.push("Inactive admins");
    if (mockData.spamLevel === "high") concerns.push("High spam level");
    if (mockData.messagesPerDay && mockData.messagesPerDay < 50) concerns.push("Low activity");

    if (mockData.members && mockData.members >= 10000) positives.push("Large community");
    if (mockData.adminActive) positives.push("Active moderation");
    if (mockData.spamLevel === "low") positives.push("Well-moderated");
    if (mockData.hasBot) positives.push("Has utility bot");

    return {
      score,
      data: mockData,
      analysis: aiAnalysis,
      concerns,
      positives,
    };
  } catch (error) {
    console.error("Error analyzing Telegram:", error);
    return {
      score: 0,
      data: {},
      analysis: "Unable to analyze Telegram group.",
      concerns: ["Analysis failed"],
      positives: [],
    };
  }
}

/**
 * วิเคราะห์ Discord
 */
export async function analyzeDiscord(discordUrl: string): Promise<SocialAnalysisResult> {
  try {
    // Mock data - ในระบบจริงควรใช้ Discord API
    const mockData: DiscordData = {
      members: 12340,
      onlineMembers: 2450,
      channels: 25,
      activeChannels: 12,
      moderators: 8,
      verificationLevel: "medium",
    };

    let score = 50;

    // Members (max 25 points)
    if (mockData.members && mockData.members >= 50000) score += 25;
    else if (mockData.members && mockData.members >= 20000) score += 20;
    else if (mockData.members && mockData.members >= 10000) score += 15;
    else if (mockData.members && mockData.members >= 5000) score += 10;
    else if (mockData.members && mockData.members >= 1000) score += 5;

    // Online ratio (max 25 points)
    if (mockData.members && mockData.onlineMembers) {
      const onlineRatio = (mockData.onlineMembers / mockData.members) * 100;
      if (onlineRatio >= 25) score += 25;
      else if (onlineRatio >= 20) score += 20;
      else if (onlineRatio >= 15) score += 15;
      else if (onlineRatio >= 10) score += 10;
      else if (onlineRatio >= 5) score += 5;
    }

    // Moderators (max 15 points)
    if (mockData.moderators && mockData.moderators >= 10) score += 15;
    else if (mockData.moderators && mockData.moderators >= 5) score += 10;
    else if (mockData.moderators && mockData.moderators >= 3) score += 5;
    else score -= 5;

    // Verification level (15 points)
    if (mockData.verificationLevel === "high") score += 15;
    else if (mockData.verificationLevel === "medium") score += 10;
    else if (mockData.verificationLevel === "low") score += 5;

    // Active channels ratio (20 points)
    if (mockData.channels && mockData.activeChannels) {
      const activeRatio = (mockData.activeChannels / mockData.channels) * 100;
      if (activeRatio >= 60) score += 20;
      else if (activeRatio >= 40) score += 15;
      else if (activeRatio >= 30) score += 10;
      else if (activeRatio >= 20) score += 5;
    }

    score = Math.max(0, Math.min(100, score));

    const aiResponse = await invokeLLM({
      messages: [
        {
          role: "system",
          content: "You are a Discord community analyst. Analyze server health for crypto projects."
        },
        {
          role: "user",
          content: `Analyze this Discord server:

Total Members: ${mockData.members}
Online Members: ${mockData.onlineMembers}
Channels: ${mockData.channels}
Active Channels: ${mockData.activeChannels}
Moderators: ${mockData.moderators}
Verification Level: ${mockData.verificationLevel}

Provide brief analysis:
1. Server organization
2. Community engagement
3. Moderation quality
4. Overall health assessment`
        }
      ]
    });

    const aiAnalysis = typeof aiResponse.choices[0]?.message?.content === "string"
      ? aiResponse.choices[0].message.content
      : "AI analysis unavailable";

    const concerns: string[] = [];
    const positives: string[] = [];

    if (mockData.members && mockData.members < 1000) concerns.push("Small server");
    if (mockData.moderators && mockData.moderators < 3) concerns.push("Insufficient moderators");
    if (mockData.verificationLevel === "none") concerns.push("No verification");
    if (mockData.onlineMembers && mockData.members) {
      const onlineRatio = (mockData.onlineMembers / mockData.members) * 100;
      if (onlineRatio < 5) concerns.push("Low online presence");
    }

    if (mockData.members && mockData.members >= 10000) positives.push("Large community");
    if (mockData.moderators && mockData.moderators >= 5) positives.push("Good moderation team");
    if (mockData.verificationLevel === "high") positives.push("Strong verification");
    if (mockData.onlineMembers && mockData.members) {
      const onlineRatio = (mockData.onlineMembers / mockData.members) * 100;
      if (onlineRatio >= 15) positives.push("Active community");
    }

    return {
      score,
      data: mockData,
      analysis: aiAnalysis,
      concerns,
      positives,
    };
  } catch (error) {
    console.error("Error analyzing Discord:", error);
    return {
      score: 0,
      data: {},
      analysis: "Unable to analyze Discord server.",
      concerns: ["Analysis failed"],
      positives: [],
    };
  }
}
