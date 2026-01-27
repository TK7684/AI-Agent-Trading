/**
 * AI Chat Bot Service
 * Provides context-aware Q&A about crypto projects
 * Uses audit data, market data, and project analysis
 */

import { getProjectById, getAuditReportByProjectId } from '../db';
import { invokeLLM } from '../_core/llm';

interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
  timestamp?: number;
}

interface ChatContext {
  projectId?: number;
  projectName?: string;
  projectData?: any;
  auditReport?: any;
  marketData?: any;
  conversationHistory: ChatMessage[];
}

interface ChatResponse {
  response: string;
  sources?: string[];
  confidence?: number;
  relatedProjects?: number[];
}

/**
 * AI Chat Bot Service
 */
class ChatBotService {
  private conversations = new Map<string, ChatMessage[]>();
  private MAX_HISTORY = 10; // Keep last 10 messages per conversation

  /**
   * Get or create conversation for a user
   */
  private getConversation(userId: string, conversationId?: string): ChatMessage[] {
    const key = conversationId ? `${userId}:${conversationId}` : userId;

    if (!this.conversations.has(key)) {
      this.conversations.set(key, []);
    }

    return this.conversations.get(key)!;
  }

  /**
   * Add message to conversation history
   */
  private addToConversation(userId: string, message: ChatMessage, conversationId?: string): void {
    const key = conversationId ? `${userId}:${conversationId}` : userId;
    const history = this.getConversation(userId, conversationId);

    history.push(message);

    // Keep only last MAX_HISTORY messages
    if (history.length > this.MAX_HISTORY) {
      history.splice(0, history.length - this.MAX_HISTORY);
    }

    this.conversations.set(key, history);
  }

  /**
   * Clear conversation history
   */
  clearConversation(userId: string, conversationId?: string): void {
    const key = conversationId ? `${userId}:${conversationId}` : userId;
    this.conversations.delete(key);
  }

  /**
   * Build system prompt with project context
   */
  private buildSystemPrompt(context: ChatContext): string {
    let prompt = `You are a helpful crypto project analyst assistant for "Investment Auditor". ` +
      `You help users understand cryptocurrency projects, their risks, and investment potential. ` +
      `Always be objective, factual, and highlight both positives and risks. ` +
      `Never give financial advice - always suggest users do their own research (DYOR).\n\n`;

    if (context.projectId) {
      prompt += `Current Project Context:\n`;
      prompt += `- Project: ${context.projectName || 'Unknown'}\n`;

      if (context.projectData) {
        prompt += `- Description: ${context.projectData.description || 'N/A'}\n`;
        prompt += `- GitHub: ${context.projectData.githubUrl || 'N/A'}\n`;
        prompt += `- Contract: ${context.projectData.contractAddress || 'N/A'} (${context.projectData.chain || 'ethereum'})\n`;
        prompt += `- Website: ${context.projectData.websiteUrl || 'N/A'}\n`;
      }

      if (context.auditReport) {
        prompt += `\nAudit Results:\n`;
        prompt += `- Overall Score: ${context.auditReport.overallScore || 0}/100\n`;
        prompt += `- Risk Level: ${context.auditReport.riskLevel || 'unknown'}\n`;
        prompt += `- GitHub Score: ${context.auditReport.githubScore || 0}/100\n`;
        prompt += `- Tokenomics Score: ${context.auditReport.tokenomicsScore || 0}/100\n`;
        prompt += `- Contract Risk Score: ${context.auditReport.contractRiskScore || 0}/100\n`;
        prompt += `- Social Score: ${context.auditReport.twitterScore || 0}/100\n`;

        if (context.auditReport.aiAnalysis) {
          prompt += `\nAI Analysis Summary:\n${context.auditReport.aiAnalysis}\n`;
        }
      }

      if (context.marketData) {
        prompt += `\nCurrent Market Data:\n`;
        prompt += `- Price: $${context.marketData.price || 'N/A'}\n`;
        prompt += `- 24h Change: ${context.marketData.change24h || 0}%\n`;
        prompt += `- Market Cap: $${((context.marketData.marketCap || 0) / 1000000).toFixed(2)}M\n`;
        prompt += `- 24h Volume: $${((context.marketData.volume24h || 0) / 1000000).toFixed(2)}M\n`;
      }

      prompt += `\nAnswer questions about this project based on the audit data above. `;
      prompt += `If you don't have specific information, say so honestly.\n`;
    } else {
      prompt += `No specific project context. Answer general crypto questions and help users ` +
        `understand how to analyze cryptocurrency projects safely.\n`;
    }

    return prompt;
  }

  /**
   * Build context-aware response
   */
  private async buildContext(context: ChatContext): Promise<ChatContext> {
    if (!context.projectId) {
      return context;
    }

    // Fetch project data if not provided
    if (!context.projectData) {
      try {
        context.projectData = await getProjectById(context.projectId);
      } catch (error) {
        console.error('[ChatBot] Error fetching project:', error);
      }
    }

    // Fetch audit report if not provided
    if (!context.auditReport && context.projectId) {
      try {
        context.auditReport = await getAuditReportByProjectId(context.projectId);
      } catch (error) {
        console.error('[ChatBot] Error fetching audit report:', error);
      }
    }

    return context;
  }

  /**
   * Process chat message and return response
   */
  async chat(
    userId: string,
    message: string,
    context: Partial<ChatContext> = {}
  ): Promise<ChatResponse> {
    // Build full context
    const fullContext = await this.buildContext({
      ...context,
      conversationHistory: this.getConversation(userId, context.conversationId),
    });

    // Get conversation history
    const history = fullContext.conversationHistory;

    // Build messages for LLM
    const messages: ChatMessage[] = [
      {
        role: 'system',
        content: this.buildSystemPrompt(fullContext),
      },
      ...history,
      {
        role: 'user',
        content: message,
      },
    ];

    try {
      // Call LLM
      const response = await invokeLLM({ messages });

      const assistantMessage = response.choices[0]?.message?.content || 'Sorry, I could not generate a response.';

      // Add user message and assistant response to history
      this.addToConversation(
        userId,
        { role: 'user', content: message, timestamp: Date.now() },
        context.conversationId
      );
      this.addToConversation(
        userId,
        { role: 'assistant', content: assistantMessage, timestamp: Date.now() },
        context.conversationId
      );

      // Extract sources and confidence if available
      const sources = this.extractSources(assistantMessage);
      const confidence = this.extractConfidence(assistantMessage);

      return {
        response: assistantMessage,
        sources,
        confidence,
      };
    } catch (error) {
      console.error('[ChatBot] Error calling LLM:', error);

      // Fallback response
      return {
        response: 'I apologize, but I\'m having trouble processing your request right now. Please try again.',
        confidence: 0,
      };
    }
  }

  /**
   * Streaming chat response (for better UX)
   */
  async *chatStream(
    userId: string,
    message: string,
    context: Partial<ChatContext> = {}
  ): AsyncGenerator<string, void, unknown> {
    // Build full context
    const fullContext = await this.buildContext({
      ...context,
      conversationHistory: this.getConversation(userId, context.conversationId),
    });

    // Build messages for LLM
    const messages: ChatMessage[] = [
      {
        role: 'system',
        content: this.buildSystemPrompt(fullContext),
      },
      ...fullContext.conversationHistory,
      {
        role: 'user',
        content: message,
      },
    ];

    try {
      // Note: This assumes invokeLLM supports streaming
      // If not, we'll fall back to non-streaming
      const response = await invokeLLM({ messages });

      const assistantMessage = response.choices[0]?.message?.content || '';

      // Simulate streaming by yielding chunks
      const chunkSize = 50;
      for (let i = 0; i < assistantMessage.length; i += chunkSize) {
        yield assistantMessage.slice(i, i + chunkSize);
        // Small delay to simulate streaming
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      // Add to history
      this.addToConversation(
        userId,
        { role: 'user', content: message, timestamp: Date.now() },
        context.conversationId
      );
      this.addToConversation(
        userId,
        { role: 'assistant', content: assistantMessage, timestamp: Date.now() },
        context.conversationId
      );
    } catch (error) {
      console.error('[ChatBot] Error in stream:', error);
      yield 'Error processing request. Please try again.';
    }
  }

  /**
   * Get conversation history
   */
  getHistory(userId: string, conversationId?: string): ChatMessage[] {
    return this.getConversation(userId, conversationId);
  }

  /**
   * Extract sources from response (simple heuristic)
   */
  private extractSources(response: string): string[] {
    const sources: string[] = [];

    // Look for common source patterns
    if (response.includes('audit report')) sources.push('Audit Report');
    if (response.includes('market data')) sources.push('Market Data');
    if (response.includes('GitHub')) sources.push('GitHub Analysis');
    if (response.includes('contract')) sources.push('Contract Analysis');

    return sources;
  }

  /**
   * Extract confidence from response (simple heuristic)
   */
  private extractConfidence(response: string): number {
    // Look for confidence indicators
    const lower = response.toLowerCase();

    if (lower.includes('certain') || lower.includes('definitely')) return 90;
    if (lower.includes('likely') || lower.includes('probably')) return 70;
    if (lower.includes('possibly') || lower.includes('may')) return 50;
    if (lower.includes('unsure') || lower.includes('uncertain')) return 30;
    if (lower.includes('cannot') || lower.includes('unable to determine')) return 10;

    return 60; // Default confidence
  }

  /**
   * Get suggested questions for a project
   */
  getSuggestedQuestions(projectId?: number): string[] {
    if (projectId) {
      return [
        'What is the overall risk level of this project?',
        'What are the main security concerns?',
        'How does the tokenomics look?',
        'Is the GitHub activity healthy?',
        'What should I be concerned about?',
        'What are the positives of this project?',
        'Would you recommend investing in this?',
        'What further research should I do?',
      ];
    } else {
      return [
        'How do I analyze a crypto project?',
        'What are the red flags to look for?',
        'How do I check if a contract is safe?',
        'What is tokenomics and why does it matter?',
        'How important is GitHub activity?',
        'What social signals should I check?',
      ];
    }
  }
}

// Export singleton instance
export const chatBotService = new ChatBotService();
export type { ChatMessage, ChatContext, ChatResponse };
