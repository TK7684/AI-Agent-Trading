CREATE TABLE "alertSettings" (
	"id" serial PRIMARY KEY NOT NULL,
	"userId" integer NOT NULL,
	"projectId" integer NOT NULL,
	"priceChangePercent" integer,
	"scoreChangePoints" integer,
	"enabled" integer DEFAULT 1 NOT NULL,
	"createdAt" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "auditReports" (
	"id" serial PRIMARY KEY NOT NULL,
	"projectId" integer NOT NULL,
	"githubScore" integer,
	"githubData" text,
	"tokenomicsScore" integer,
	"tokenomicsData" text,
	"contractRiskScore" integer,
	"contractRiskData" text,
	"twitterScore" integer,
	"twitterData" text,
	"telegramScore" integer,
	"telegramData" text,
	"discordScore" integer,
	"discordData" text,
	"overallScore" integer,
	"riskLevel" varchar(20),
	"aiAnalysis" text,
	"createdAt" timestamp DEFAULT now() NOT NULL,
	"updatedAt" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "comparisons" (
	"id" serial PRIMARY KEY NOT NULL,
	"userId" integer NOT NULL,
	"name" varchar(255) NOT NULL,
	"projectIds" text NOT NULL,
	"createdAt" timestamp DEFAULT now() NOT NULL,
	"updatedAt" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "marketData" (
	"id" serial PRIMARY KEY NOT NULL,
	"symbol" varchar(64) NOT NULL,
	"price" varchar(64),
	"change24h" varchar(64),
	"volume24h" varchar(64),
	"marketCap" varchar(64),
	"high24h" varchar(64),
	"low24h" varchar(64),
	"ath" varchar(64),
	"athChange" varchar(64),
	"lastUpdate" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "marketData_symbol_unique" UNIQUE("symbol")
);
--> statement-breakpoint
CREATE TABLE "notifications" (
	"id" serial PRIMARY KEY NOT NULL,
	"userId" integer NOT NULL,
	"type" varchar(20) NOT NULL,
	"title" varchar(255) NOT NULL,
	"message" text NOT NULL,
	"data" text,
	"read" integer DEFAULT 0,
	"createdAt" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "projects" (
	"id" serial PRIMARY KEY NOT NULL,
	"userId" integer NOT NULL,
	"name" varchar(255) NOT NULL,
	"description" text,
	"githubUrl" varchar(512),
	"contractAddress" varchar(128),
	"chain" varchar(64),
	"websiteUrl" varchar(512),
	"twitterUrl" varchar(512),
	"telegramUrl" varchar(512),
	"discordUrl" varchar(512),
	"status" varchar(20) DEFAULT 'pending' NOT NULL,
	"createdAt" timestamp DEFAULT now() NOT NULL,
	"updatedAt" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "tradingSignals" (
	"id" serial PRIMARY KEY NOT NULL,
	"userId" integer NOT NULL,
	"projectId" integer,
	"symbol" varchar(64) NOT NULL,
	"signalType" varchar(20) NOT NULL,
	"tradingViewSignal" integer DEFAULT 0,
	"auditSignal" integer DEFAULT 0,
	"geminiSignal" integer DEFAULT 0,
	"confidence" integer,
	"auditScore" integer,
	"technicalScore" integer,
	"entryPrice" varchar(64),
	"stopLoss" varchar(64),
	"takeProfit" varchar(64),
	"positionSize" varchar(64),
	"reasoning" text,
	"riskLevel" varchar(20),
	"status" varchar(20) DEFAULT 'active',
	"createdAt" timestamp DEFAULT now() NOT NULL,
	"expiresAt" timestamp
);
--> statement-breakpoint
CREATE TABLE "tradingViewAlerts" (
	"id" serial PRIMARY KEY NOT NULL,
	"userId" integer NOT NULL,
	"symbol" varchar(64) NOT NULL,
	"exchange" varchar(64) DEFAULT 'BINANCE',
	"action" varchar(20) NOT NULL,
	"price" varchar(64),
	"indicators" text,
	"message" text,
	"timestamp" timestamp DEFAULT now() NOT NULL,
	"processed" integer DEFAULT 0
);
--> statement-breakpoint
CREATE TABLE "unicornCandidates" (
	"id" serial PRIMARY KEY NOT NULL,
	"scanId" integer NOT NULL,
	"symbol" varchar(64) NOT NULL,
	"name" varchar(255),
	"marketCap" integer,
	"priceFromAth" integer,
	"volumeSpike" integer,
	"currentPrice" varchar(64),
	"githubScore" integer,
	"techScore" integer,
	"socialScore" integer,
	"teamActive" integer DEFAULT 0,
	"rsiDivergence" integer DEFAULT 0,
	"wyckoffSpring" integer DEFAULT 0,
	"entryPrice" varchar(64),
	"stopLoss" varchar(64),
	"takeProfit" varchar(64),
	"scannerScore" integer,
	"fundamentalScore" integer,
	"technicalScore" integer,
	"unicornScore" integer,
	"recommendation" varchar(20),
	"analysis" text,
	"createdAt" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "unicornScans" (
	"id" serial PRIMARY KEY NOT NULL,
	"userId" integer NOT NULL,
	"scanType" varchar(64),
	"status" varchar(20) DEFAULT 'pending' NOT NULL,
	"candidatesFound" integer DEFAULT 0,
	"createdAt" timestamp DEFAULT now() NOT NULL,
	"completedAt" timestamp
);
--> statement-breakpoint
CREATE TABLE "users" (
	"id" serial PRIMARY KEY NOT NULL,
	"openId" varchar(64) NOT NULL,
	"name" text,
	"email" varchar(320),
	"loginMethod" varchar(64),
	"role" varchar(20) DEFAULT 'user' NOT NULL,
	"createdAt" timestamp DEFAULT now() NOT NULL,
	"updatedAt" timestamp DEFAULT now() NOT NULL,
	"lastSignedIn" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "users_openId_unique" UNIQUE("openId")
);
--> statement-breakpoint
CREATE TABLE "watchlist" (
	"id" serial PRIMARY KEY NOT NULL,
	"userId" integer NOT NULL,
	"projectId" integer NOT NULL,
	"addedAt" timestamp DEFAULT now() NOT NULL,
	"notes" text,
	"alertPrice" varchar(64),
	"alertScore" integer
);
