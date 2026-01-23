import { COOKIE_NAME, ONE_YEAR_MS } from "@shared/const";
import { z } from "zod";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { protectedProcedure, publicProcedure, router } from "./_core/trpc";
import { createProject, getProjectsByUserId, getProjectById, updateProjectStatus, createAuditReport, getAuditReportByProjectId, updateAuditReport, getDb } from "./db";
import { projects, auditReports, users } from "../drizzle/schema";
import { eq } from "drizzle-orm";
import { analyzeGitHub } from "./services/githubAnalyzer";
import { analyzeTokenomics, analyzeContractRisk } from "./services/contractAnalyzer";
import { analyzeTwitter, analyzeTelegram, analyzeDiscord } from "./services/socialAnalyzer";
import { invokeLLM } from "./_core/llm";
import { discoverTrendingProjects } from "./services/discoveryService";
import { sendProjectNotificationEmail, sendAuditCompletionEmail, sendHotProjectAlert } from "./services/emailService";
import { TRPCError } from "@trpc/server";
import { addToWatchlist, removeFromWatchlist, getUserWatchlist, isInWatchlist, createComparison, getUserComparisons, getComparison, updateComparison, deleteComparison, createAlertSetting, getUserAlertSettings, updateAlertSetting, disableAlertSetting } from "./db-features";
import { exportToJSON, exportToPDF } from "./services/exportService";
import { startUnicornScan, pollScanCompletion, healthCheck, processAndSaveScanResults } from "./services/unicornHunter";
import { createUnicornScan, getScanById, getScansByUserId, getCandidatesByScanId, updateScanStatus } from "./db-unicorn";
import { loginUser, registerUser, createSessionToken } from "./_core/auth";
import { marketDataRouter } from "./routers/marketData";
import { tradingViewRouter } from "./routers/tradingview";
import { geminiAnalyzer } from "./services/geminiAnalyzer";

export const appRouter = router({
    // if you need to use socket.io, read and register route in server/_core/index.ts, all api should start with '/api/' so that the gateway can route correctly
  system: systemRouter,
  marketData: marketDataRouter,
  tradingView: tradingViewRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),

    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),

    // Register new user (FREE JWT-based auth)
    register: publicProcedure
      .input(z.object({
        email: z.string().email(),
        password: z.string().min(8),
        name: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        const { sessionToken, user } = await registerUser(input);

        // Set cookie
        const cookieOptions = getSessionCookieOptions(ctx.req);
        ctx.res.cookie(COOKIE_NAME, sessionToken, { ...cookieOptions, maxAge: ONE_YEAR_MS });

        return {
          success: true,
          user: {
            id: user.id,
            email: user.email,
            name: user.name,
            role: user.role,
          },
        };
      }),

    // Login with email/password (FREE JWT-based auth)
    login: publicProcedure
      .input(z.object({
        email: z.string().email(),
        password: z.string(),
      }))
      .mutation(async ({ ctx, input }) => {
        const { sessionToken, user } = await loginUser(input);

        // Set cookie
        const cookieOptions = getSessionCookieOptions(ctx.req);
        ctx.res.cookie(COOKIE_NAME, sessionToken, { ...cookieOptions, maxAge: ONE_YEAR_MS });

        return {
          success: true,
          user: {
            id: user.id,
            email: user.email,
            name: user.name,
            role: user.role,
          },
        };
      }),
  }),

  project: router({
    // สร้างโปรเจกต์ใหม่
    create: protectedProcedure
      .input(z.object({
        name: z.string().min(1),
        description: z.string().optional(),
        githubUrl: z.string().optional(),
        contractAddress: z.string().optional(),
        chain: z.string().optional(),
        websiteUrl: z.string().optional(),
        twitterUrl: z.string().optional(),
        telegramUrl: z.string().optional(),
        discordUrl: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        const projectId = await createProject({
          userId: ctx.user.id,
          ...input,
        });
        
        // สร้าง audit report เปล่า
        const reportId = await createAuditReport({
          projectId: Number(projectId),
        });
        
        return { projectId, reportId };
      }),
    
    // ดึงรายการโปรเจกต์ของผู้ใช้
    list: protectedProcedure.query(async ({ ctx }) => {
      return getProjectsByUserId(ctx.user.id);
    }),
    
    // ดึงข้อมูลโปรเจกต์และรายงาน
    getById: protectedProcedure
      .input(z.object({ id: z.number() }))
      .query(async ({ input }) => {
        const project = await getProjectById(input.id);
        if (!project) return null;
        
        const report = await getAuditReportByProjectId(input.id);
        return { project, report };
      }),
    
    // เริ่มการวิเคราะห์
    analyze: protectedProcedure
      .input(z.object({ projectId: z.number() }))
      .mutation(async ({ input }) => {
        const project = await getProjectById(input.projectId);
        if (!project) {
          throw new Error("Project not found");
        }
        
        // อัพเดทสถานะเป็น analyzing
        await updateProjectStatus(input.projectId, "analyzing");
        
        try {
          // วิเคราะห์ GitHub (ถ้ามี)
          let githubScore = null;
          let githubData = null;
          
          if (project.githubUrl) {
            const githubResult = await analyzeGitHub(project.githubUrl);
            githubScore = githubResult.score;
            githubData = JSON.stringify({
              ...githubResult.data,
              analysis: githubResult.analysis,
              issues: githubResult.issues,
              strengths: githubResult.strengths,
            });
          }
          
          // อัพเดทรายงาน
          const report = await getAuditReportByProjectId(input.projectId);
          if (report) {
            await updateAuditReport(report.id, {
              githubScore,
              githubData,
            });
          }
          
          // วิเคราะห์ Tokenomics และ Contract Risk (ถ้ามี contract address)
          let tokenomicsScore = null;
          let tokenomicsData = null;
          let contractRiskScore = null;
          let contractRiskData = null;
          
          if (project.contractAddress) {
            const tokenomicsResult = await analyzeTokenomics(
              project.contractAddress,
              project.chain || "ethereum"
            );
            tokenomicsScore = tokenomicsResult.score;
            tokenomicsData = JSON.stringify({
              ...tokenomicsResult.data,
              analysis: tokenomicsResult.analysis,
              issues: tokenomicsResult.issues,
              strengths: tokenomicsResult.strengths,
            });
            
            const contractRiskResult = await analyzeContractRisk(
              project.contractAddress,
              project.chain || "ethereum"
            );
            contractRiskScore = contractRiskResult.score;
            contractRiskData = JSON.stringify({
              ...contractRiskResult.data,
              analysis: contractRiskResult.analysis,
              risks: contractRiskResult.risks,
              safetyFeatures: contractRiskResult.safetyFeatures,
            });
          }
          
          // วิเคราะห์ Social Media
          let twitterScore = null;
          let twitterData = null;
          let telegramScore = null;
          let telegramData = null;
          let discordScore = null;
          let discordData = null;
          
          if (project.twitterUrl) {
            const twitterResult = await analyzeTwitter(project.twitterUrl);
            twitterScore = twitterResult.score;
            twitterData = JSON.stringify({
              ...twitterResult.data,
              analysis: twitterResult.analysis,
              concerns: twitterResult.concerns,
              positives: twitterResult.positives,
            });
          }
          
          if (project.telegramUrl) {
            const telegramResult = await analyzeTelegram(project.telegramUrl);
            telegramScore = telegramResult.score;
            telegramData = JSON.stringify({
              ...telegramResult.data,
              analysis: telegramResult.analysis,
              concerns: telegramResult.concerns,
              positives: telegramResult.positives,
            });
          }
          
          if (project.discordUrl) {
            const discordResult = await analyzeDiscord(project.discordUrl);
            discordScore = discordResult.score;
            discordData = JSON.stringify({
              ...discordResult.data,
              analysis: discordResult.analysis,
              concerns: discordResult.concerns,
              positives: discordResult.positives,
            });
          }
          
          // คำนวณคะแนนรวมและ Risk Level
          const scores = [
            githubScore,
            tokenomicsScore,
            contractRiskScore,
            twitterScore,
            telegramScore,
            discordScore,
          ].filter((s): s is number => s !== null);
          
          const overallScore = scores.length > 0
            ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
            : 0;
          
          let riskLevel: "low" | "medium" | "high" | "critical";
          if (overallScore >= 80) riskLevel = "low";
          else if (overallScore >= 60) riskLevel = "medium";
          else if (overallScore >= 40) riskLevel = "high";
          else riskLevel = "critical";
          
          // สร้างรายงานสรุปด้วย AI (ใช้ Gemini)
          const aiAnalysis = await geminiAnalyzer.generateAuditSummary({
            projectName: project.name,
            description: project.description || undefined,
            scores: {
              github: githubScore,
              tokenomics: tokenomicsScore,
              contractRisk: contractRiskScore,
              twitter: twitterScore,
              telegram: telegramScore,
              discord: discordScore,
            },
            overallScore,
            riskLevel,
          });
          
          // อัพเดทรายงานด้วยข้อมูลทั้งหมด
          if (report) {
            await updateAuditReport(report.id, {
              githubScore,
              githubData,
              tokenomicsScore,
              tokenomicsData,
              contractRiskScore,
              contractRiskData,
              twitterScore,
              twitterData,
              telegramScore,
              telegramData,
              discordScore,
              discordData,
              overallScore,
              riskLevel,
              aiAnalysis,
            });
          }
          
          // อัพเดทสถานะเป็น completed
          await updateProjectStatus(input.projectId, "completed");
          
          return { 
            success: true, 
            overallScore,
            riskLevel,
            scores: {
              github: githubScore,
              tokenomics: tokenomicsScore,
              contractRisk: contractRiskScore,
              twitter: twitterScore,
              telegram: telegramScore,
              discord: discordScore,
            }
          };
        } catch (error) {
          await updateProjectStatus(input.projectId, "failed");
          throw error;
        }
      }),
  }),

  discovery: router({
    // ค้นหาโปรเจกต์ยอดนิยม
    trending: publicProcedure
      .input(z.object({
        category: z.string().optional(),
        status: z.enum(["trending", "new", "hot", "established"]).optional(),
        minScore: z.number().optional(),
        maxMarketCap: z.number().optional(),
      }).optional())
      .query(async ({ input }) => {
        return discoverTrendingProjects(input);
      }),
    
    // ดึงหมวดหมู่หมวดสำหรับฟิลเตอร์
    getCategories: publicProcedure.query(async () => {
      const projects = await discoverTrendingProjects();
      const categorySet = new Set(projects.map(p => p.category));
      const categories = Array.from(categorySet).sort();
      return categories;
    }),
    
    // ส่งการแจ้งเตือนอีเมลสำหรับโปรเจกต์ใหม่
    sendNotification: protectedProcedure
      .input(z.object({
        projectId: z.string(),
        projectName: z.string(),
        projectSymbol: z.string(),
        score: z.number(),
        category: z.string(),
        marketCap: z.number(),
        priceChange24h: z.number(),
        briefSummary: z.string(),
        tags: z.array(z.string()),
      }))
      .mutation(async ({ ctx, input }) => {
        if (!ctx.user.email) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "User email not found" });
        }

        const auditUrl = `${process.env.VITE_FRONTEND_FORGE_API_URL}/audit/${input.projectId}`;
        const success = await sendProjectNotificationEmail({
          userId: ctx.user.id,
          email: ctx.user.email,
          projectName: input.projectName,
          projectSymbol: input.projectSymbol,
          score: input.score,
          category: input.category,
          marketCap: input.marketCap,
          priceChange24h: input.priceChange24h,
          briefSummary: input.briefSummary,
          tags: input.tags,
          auditUrl,
        });

        return { success };
      }),

    // ส่งการแจ้งเตือนเมื่อการวิเคราะห์เสร็จสิ้น
    sendCompletionEmail: protectedProcedure
      .input(z.object({
        projectName: z.string(),
        projectSymbol: z.string(),
        overallScore: z.number(),
        riskLevel: z.string(),
        projectId: z.number(),
      }))
      .mutation(async ({ ctx, input }) => {
        if (!ctx.user.email) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "User email not found" });
        }

        const auditUrl = `${process.env.VITE_FRONTEND_FORGE_API_URL}/audit/${input.projectId}`;
        const success = await sendAuditCompletionEmail(
          ctx.user.email,
          input.projectName,
          input.projectSymbol,
          input.overallScore,
          input.riskLevel,
          auditUrl
        );

        return { success };
      }),

  }),

  // ============ WATCHLIST ROUTER ============
  watchlist: router({
    add: protectedProcedure
      .input(z.object({
        projectId: z.number(),
        notes: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        try {
          await addToWatchlist(ctx.user.id, input.projectId, input.notes);
          return { success: true };
        } catch (error) {
          throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to add to watchlist" });
        }
      }),

    remove: protectedProcedure
      .input(z.object({ projectId: z.number() }))
      .mutation(async ({ ctx, input }) => {
        try {
          await removeFromWatchlist(ctx.user.id, input.projectId);
          return { success: true };
        } catch (error) {
          throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to remove from watchlist" });
        }
      }),

    list: protectedProcedure.query(async ({ ctx }) => {
      try {
        return await getUserWatchlist(ctx.user.id);
      } catch (error) {
        throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to fetch watchlist" });
      }
    }),

    isInWatchlist: protectedProcedure
      .input(z.object({ projectId: z.number() }))
      .query(async ({ ctx, input }) => {
        try {
          return await isInWatchlist(ctx.user.id, input.projectId);
        } catch (error) {
          return false;
        }
      }),
  }),

  // ============ COMPARISON ROUTER ============
  comparison: router({
    create: protectedProcedure
      .input(z.object({
        name: z.string(),
        projectIds: z.array(z.number()),
      }))
      .mutation(async ({ ctx, input }) => {
        try {
          await createComparison(ctx.user.id, input.name, input.projectIds);
          return { success: true };
        } catch (error) {
          throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to create comparison" });
        }
      }),

    list: protectedProcedure.query(async ({ ctx }) => {
      try {
        return await getUserComparisons(ctx.user.id);
      } catch (error) {
        throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to fetch comparisons" });
      }
    }),

    get: protectedProcedure
      .input(z.object({ comparisonId: z.number() }))
      .query(async ({ ctx, input }) => {
        try {
          return await getComparison(input.comparisonId, ctx.user.id);
        } catch (error) {
          throw new TRPCError({ code: "NOT_FOUND", message: "Comparison not found" });
        }
      }),

    delete: protectedProcedure
      .input(z.object({ comparisonId: z.number() }))
      .mutation(async ({ ctx, input }) => {
        try {
          await deleteComparison(input.comparisonId);
          return { success: true };
        } catch (error) {
          throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to delete comparison" });
        }
      }),
  }),

  // ============ EXPORT ROUTER ============
  export: router({
    json: publicProcedure
      .input(z.object({
        projectId: z.number(),
      }))
      .query(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Database not available" });

        const report = await db.select().from(auditReports).where(eq(auditReports.projectId, input.projectId)).limit(1);
        if (report.length === 0) throw new TRPCError({ code: "NOT_FOUND", message: "Audit report not found" });

        const project = await db.select().from(projects).where(eq(projects.id, input.projectId)).limit(1);
        if (project.length === 0) throw new TRPCError({ code: "NOT_FOUND", message: "Project not found" });

        const jsonData = exportToJSON({
          projectName: project[0].name,
          projectSymbol: project[0].description || "",
          description: project[0].description || "",
          chain: project[0].chain || "unknown",
          githubScore: report[0].githubScore || 0,
          tokenomicsScore: report[0].tokenomicsScore || 0,
          contractRiskScore: report[0].contractRiskScore || 0,
          twitterScore: report[0].twitterScore || 0,
          telegramScore: report[0].telegramScore || 0,
          discordScore: report[0].discordScore || 0,
          overallScore: report[0].overallScore || 0,
          riskLevel: report[0].riskLevel || "unknown",
          githubData: report[0].githubData ? JSON.parse(report[0].githubData) : {},
          tokenomicsData: report[0].tokenomicsData ? JSON.parse(report[0].tokenomicsData) : {},
          contractRiskData: report[0].contractRiskData ? JSON.parse(report[0].contractRiskData) : {},
          socialData: {
            twitter: report[0].twitterData ? JSON.parse(report[0].twitterData) : {},
            telegram: report[0].telegramData ? JSON.parse(report[0].telegramData) : {},
            discord: report[0].discordData ? JSON.parse(report[0].discordData) : {},
          },
          aiAnalysis: report[0].aiAnalysis || "",
          auditDate: report[0].createdAt,
          auditUrl: `https://your-domain.com/audit/${input.projectId}`,
        });

        return { json: jsonData };
      }),

    pdf: publicProcedure
      .input(z.object({ projectId: z.number() }))
      .query(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Database not available" });

        const report = await db.select().from(auditReports).where(eq(auditReports.projectId, input.projectId)).limit(1);
        if (report.length === 0) throw new TRPCError({ code: "NOT_FOUND", message: "Audit report not found" });

        const project = await db.select().from(projects).where(eq(projects.id, input.projectId)).limit(1);
        if (project.length === 0) throw new TRPCError({ code: "NOT_FOUND", message: "Project not found" });

        try {
          const pdfBuffer = await exportToPDF({
            projectName: project[0].name,
            projectSymbol: project[0].description || "",
            description: project[0].description || "",
            chain: project[0].chain || "unknown",
            githubScore: report[0].githubScore || 0,
            tokenomicsScore: report[0].tokenomicsScore || 0,
            contractRiskScore: report[0].contractRiskScore || 0,
            twitterScore: report[0].twitterScore || 0,
            telegramScore: report[0].telegramScore || 0,
            discordScore: report[0].discordScore || 0,
            overallScore: report[0].overallScore || 0,
            riskLevel: report[0].riskLevel || "unknown",
            githubData: report[0].githubData ? JSON.parse(report[0].githubData) : {},
            tokenomicsData: report[0].tokenomicsData ? JSON.parse(report[0].tokenomicsData) : {},
            contractRiskData: report[0].contractRiskData ? JSON.parse(report[0].contractRiskData) : {},
            socialData: {
              twitter: report[0].twitterData ? JSON.parse(report[0].twitterData) : {},
              telegram: report[0].telegramData ? JSON.parse(report[0].telegramData) : {},
              discord: report[0].discordData ? JSON.parse(report[0].discordData) : {},
            },
            aiAnalysis: report[0].aiAnalysis || "",
            auditDate: report[0].createdAt,
            auditUrl: `https://your-domain.com/audit/${input.projectId}`,
          });

          return { pdfBase64: pdfBuffer.toString("base64") };
        } catch (error) {
          throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to generate PDF" });
        }
      }),
  }),

  // ============ ALERTS ROUTER ============
  alerts: router({
    create: protectedProcedure
      .input(z.object({
        projectId: z.number(),
        priceChangePercent: z.number().optional(),
        scoreChangePoints: z.number().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        try {
          await createAlertSetting(ctx.user.id, input.projectId, input.priceChangePercent, input.scoreChangePoints);
          return { success: true };
        } catch (error) {
          throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to create alert" });
        }
      }),

    list: protectedProcedure.query(async ({ ctx }) => {
      try {
        return await getUserAlertSettings(ctx.user.id);
      } catch (error) {
        throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to fetch alerts" });
      }
    }),
  }),

  // ============ UNICORN HUNTER ROUTER ============
  unicorn: router({
    // Health check for Python service
    health: publicProcedure.query(async () => {
      const isHealthy = await healthCheck();
      return { healthy: isHealthy, service: "unicorn-hunter" };
    }),

    // Start a new unicorn hunt scan
    startScan: protectedProcedure
      .input(z.object({
        scanType: z.enum(["crypto", "stocks", "all"]),
        minMarketCap: z.number().optional(),
        maxMarketCap: z.number().optional(),
        minPriceDrop: z.number().optional(),
        minVolumeSpike: z.number().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        try {
          // Create database record
          const dbScanId = await createUnicornScan({
            userId: ctx.user.id,
            scanType: input.scanType,
          });

          // Start Python scan
          const result = await startUnicornScan({
            scanType: input.scanType,
            minMarketCap: input.minMarketCap,
            maxMarketCap: input.maxMarketCap,
            minPriceDrop: input.minPriceDrop,
            minVolumeSpike: input.minVolumeSpike,
          });

          // Store the Python scan ID with our DB scan
          // In production, you'd want to add a pythonScanId column to unicornScans table

          // Update status to running
          await updateScanStatus(dbScanId, "running");

          // Poll for completion (in background, for now we'll do it synchronously)
          // In production, use a job queue like BullMQ
          const pollResult = await pollScanCompletion(result.scanId, 60, 5000);

          if (pollResult.success && pollResult.candidates) {
            await processAndSaveScanResults(result.scanId, dbScanId);
          } else {
            await updateScanStatus(dbScanId, "failed");
            throw new TRPCError({
              code: "INTERNAL_SERVER_ERROR",
              message: pollResult.error || "Scan failed",
            });
          }

          return {
            scanId: dbScanId,
            pythonScanId: result.scanId,
            status: "completed",
            candidatesFound: pollResult.candidates?.length || 0,
          };
        } catch (error) {
          throw new TRPCError({
            code: "INTERNAL_SERVER_ERROR",
            message: error instanceof Error ? error.message : "Failed to start unicorn scan",
          });
        }
      }),

    // Get scan results
    getScan: protectedProcedure
      .input(z.object({ scanId: z.number() }))
      .query(async ({ input, ctx }) => {
        try {
          const scan = await getScanById(input.scanId);

          if (!scan || scan.userId !== ctx.user.id) {
            throw new TRPCError({
              code: "NOT_FOUND",
              message: "Scan not found",
            });
          }

          const candidates = await getCandidatesByScanId(input.scanId);

          return {
            scan,
            candidates,
          };
        } catch (error) {
          throw new TRPCError({
            code: "INTERNAL_SERVER_ERROR",
            message: "Failed to get scan results",
          });
        }
      }),

    // List all scans for user
    listScans: protectedProcedure.query(async ({ ctx }) => {
      try {
        return await getScansByUserId(ctx.user.id);
      } catch (error) {
        throw new TRPCError({
          code: "INTERNAL_SERVER_ERROR",
          message: "Failed to fetch scans",
        });
      }
    }),
  }),

});

export type AppRouter = typeof appRouter;
