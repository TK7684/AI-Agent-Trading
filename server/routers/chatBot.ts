/**
 * Chat Bot Router
 * Exposes AI chat endpoints for Q&A about crypto projects
 */

import { z } from 'zod';
import { protectedProcedure, publicProcedure, router } from '../_core/trpc';
import { chatBotService } from '../services/chatBot';

export const chatBotRouter = router({
  // Send a chat message and get a response
  chat: protectedProcedure
    .input(z.object({
      message: z.string().min(1).max(2000),
      projectId: z.number().optional(),
      conversationId: z.string().optional(),
    }))
    .mutation(async ({ ctx, input }) => {
      const result = await chatBotService.chat(
        ctx.user.id.toString(),
        input.message,
        {
          projectId: input.projectId,
          conversationId: input.conversationId,
        }
      );

      return result;
    }),

  // Get conversation history
  getHistory: protectedProcedure
    .input(z.object({
      conversationId: z.string().optional(),
    }))
    .query(async ({ ctx, input }) => {
      return chatBotService.getHistory(
        ctx.user.id.toString(),
        input.conversationId
      );
    }),

  // Clear conversation history
  clearHistory: protectedProcedure
    .input(z.object({
      conversationId: z.string().optional(),
    }))
    .mutation(async ({ ctx, input }) => {
      chatBotService.clearConversation(
        ctx.user.id.toString(),
        input.conversationId
      );
      return { success: true };
    }),

  // Get suggested questions
  suggestedQuestions: publicProcedure
    .input(z.object({
      projectId: z.number().optional(),
    }))
    .query(async ({ input }) => {
      return {
        questions: chatBotService.getSuggestedQuestions(input.projectId),
      };
    }),

  // Stream chat response (returns full response for now - could be upgraded to SSE)
  chatStream: protectedProcedure
    .input(z.object({
      message: z.string().min(1).max(2000),
      projectId: z.number().optional(),
      conversationId: z.string().optional(),
    }))
    .mutation(async ({ ctx, input }) => {
      // For streaming, we'd typically use Server-Sent Events or WebSocket
      // For now, we'll return the full response
      // In a full implementation, this would use SSE or WebSocket

      const chunks: string[] = [];

      for await (const chunk of chatBotService.chatStream(
        ctx.user.id.toString(),
        input.message,
        {
          projectId: input.projectId,
          conversationId: input.conversationId,
        }
      )) {
        chunks.push(chunk);
      }

      return {
        response: chunks.join(''),
        streamed: true,
      };
    }),
});
