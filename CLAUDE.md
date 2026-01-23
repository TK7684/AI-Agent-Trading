# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Crypto Project Auditor - A full-stack web application that analyzes cryptocurrency projects across multiple dimensions (GitHub repository health, tokenomics, smart contract risks, social media sentiment) and provides comprehensive risk assessment and scoring.

## Commands

### Development
- `pnpm dev` - Start development server (auto-finds available port 3000-3020)
- `pnpm build` - Build both frontend (Vite) and backend (esbuild)
- `pnpm start` - Start production server
- `pnpm check` - TypeScript type checking without emitting files

### Database
- `pnpm db:push` - Generate and run database migrations (Drizzle Kit)

### Code Quality
- `pnpm format` - Format code with Prettier
- `pnpm test` - Run tests (Vitest) - currently no tests exist

## Architecture

### Tech Stack
- **Frontend**: React 19 + TypeScript + Vite + TailwindCSS + shadcn/ui
- **Backend**: Express.js + tRPC + Drizzle ORM + MySQL
- **API**: tRPC for end-to-end type safety
- **Auth**: Manus OAuth (JWT-based)
- **Package Manager**: pnpm (v10.4.1)

### Directory Structure
```
client/                 # React frontend
  src/
    components/         # React components
    pages/             # Page components
    _core/             # Core utilities (useAuth.ts)
    hooks/             # Custom React hooks
    contexts/          # React contexts (ThemeContext)
    lib/               # Utilities (trpc.ts, utils.ts)
    i18n/              # Internationalization (Thai)

server/                # Backend API
  _core/               # Core server utilities (context, trpc, oauth, llm)
  services/            # Business logic (githubAnalyzer, contractAnalyzer, socialAnalyzer, discoveryService, emailService, exportService)
  db.ts                # Database operations
  db-features.ts       # Feature-specific DB operations (watchlist, comparisons, alerts)
  routers.ts           # tRPC router definitions

shared/                # Shared types and constants
drizzle/               # Database schema and migrations
patches/               # Dependency patches (wouter@3.7.1)
```

### Database Schema (drizzle/schema.ts)
Key tables:
- **users** - User auth with Manus OAuth, role-based (user/admin)
- **projects** - Project metadata with audit status (pending/analyzing/completed/failed)
- **auditReports** - Analysis scores (GitHub, tokenomics, contract risk, social media) + AI summary
- **watchlist** - User's watched projects with alerts
- **comparisons** - Side-by-side project comparisons
- **alertSettings** - Price/score change alerts

### tRPC Router Structure (server/routers.ts)
- `system` - System health and info
- `auth` - Authentication (me, logout)
- `project` - CRUD and analysis (create, list, getById, analyze)
- `discovery` - Project discovery (trending, categories, notifications)
- `watchlist` - Add/remove/list/check
- `comparison` - Create/list/get/delete comparisons
- `export` - JSON/PDF report export
- `alerts` - Price and score change alerts

### Analysis Pipeline
When `project.analyze` is called:
1. Update project status to "analyzing"
2. Run GitHub analysis (commits, contributors, code quality)
3. Run tokenomics analysis (supply, distribution)
4. Run contract risk analysis (security checks)
5. Run social media analysis (Twitter, Telegram, Discord)
6. Calculate overall score (0-100) and risk level (low/medium/high/critical)
7. Generate AI summary via LLM
8. Update project status to "completed" or "failed"

### Key Services
- `githubAnalyzer` - GitHub repo analysis
- `contractAnalyzer` - Tokenomics and smart contract risk
- `socialAnalyzer` - Social media sentiment analysis
- `discoveryService` - Discover trending crypto projects
- `emailService` - Email notifications
- `exportService` - PDF/JSON report generation

### Frontend Routing
Uses Wouter for client-side routing. Pages include landing page, audit form, results display, dashboard, and discover projects.

### Authentication Flow
- Manus OAuth callback sets JWT cookie
- `protectedProcedure` requires auth, `publicProcedure` does not
- User context available via `ctx.user` in procedures

### Environment Variables
- `NODE_ENV` - development/production
- `PORT` - Preferred port (default 3000)
- `DATABASE_URL` - MySQL connection string
- `VITE_FRONTEND_FORGE_API_URL` - Frontend URL for links
- Manus SDK config for OAuth
- OpenAI API key for LLM analysis
