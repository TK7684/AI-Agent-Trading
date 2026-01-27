/**
 * FREE JWT-based Authentication System
 * Replaces Manus OAuth with self-hosted JWT authentication
 */

import { COOKIE_NAME, ONE_YEAR_MS } from "@shared/const";
import type { Request, Response } from "express";
import { SignJWT, jwtVerify } from "jose";
import * as db from "../db";
import { ENV } from "./env";
import { getUserByOpenId, upsertUser } from "../db";
import type { User } from "../../drizzle/schema";
import { ForbiddenError } from "@shared/_core/errors";

// Types
export interface LoginInput {
  email: string;
  password: string;
}

export interface RegisterInput {
  email: string;
  password: string;
  name?: string;
}

export interface AuthTokens {
  sessionToken: string;
  user: User;
}

// In-memory user storage (in production, use database with bcrypt)
// This is a simple implementation for the free stack
const USERS_STORE = new Map<string, { email: string; passwordHash: string; name?: string }>();

// Simple password hashing (use bcrypt in production)
function hashPassword(password: string): string {
  // This is a simple hash for demonstration
  // In production, use bcrypt: await bcrypt.hash(password, 10)
  const encoder = new TextEncoder();
  const data = encoder.encode(password + ENV.cookieSecret);
  const uint8Array = new Uint8Array(data);
  let result = "";
  for (let i = 0; i < uint8Array.length; i++) {
    result += String.fromCharCode(uint8Array[i]!);
  }
  return btoa(result);
}

function verifyPassword(password: string, hash: string): boolean {
  const passwordHash = hashPassword(password);
  return passwordHash === hash;
}

// Generate a simple openId from email
function emailToOpenId(email: string): string {
  // Convert email to a simple openId format
  const normalized = email.toLowerCase().trim();
  const hash = hashPassword(normalized);
  return `user_${hash.substring(0, 16)}`;
}

/**
 * Register a new user
 */
export async function registerUser(input: RegisterInput): Promise<AuthTokens> {
  const { email, password, name } = input;

  // Check if user already exists
  const existingUser = await getUserByEmail(email);
  if (existingUser) {
    throw new Error("User already exists");
  }

  // Hash password and store
  const passwordHash = hashPassword(password);
  USERS_STORE.set(email.toLowerCase(), {
    email: email.toLowerCase(),
    passwordHash,
    name: name || email.split("@")[0],
  });

  // Create user in database
  const openId = emailToOpenId(email);
  await upsertUser({
    openId,
    email: email.toLowerCase(),
    name: name || email.split("@")[0],
    loginMethod: "email",
    lastSignedIn: new Date(),
  });

  const user = await getUserByOpenId(openId);
  if (!user) {
    throw new Error("Failed to create user");
  }

  // Create session token
  const sessionToken = await createSessionToken(user.openId, user.name || "");

  return { sessionToken, user };
}

/**
 * Login with email and password
 */
export async function loginUser(input: LoginInput): Promise<AuthTokens> {
  const { email, password } = input;

  // Get stored user
  const storedUser = USERS_STORE.get(email.toLowerCase());
  if (!storedUser) {
    throw new Error("Invalid credentials");
  }

  // Verify password
  if (!verifyPassword(password, storedUser.passwordHash)) {
    throw new Error("Invalid credentials");
  }

  // Get or create database user
  const openId = emailToOpenId(email);
  let user = await getUserByOpenId(openId);

  if (!user) {
    await upsertUser({
      openId,
      email: storedUser.email,
      name: storedUser.name || storedUser.email.split("@")[0],
      loginMethod: "email",
      lastSignedIn: new Date(),
    });
    user = await getUserByOpenId(openId);
  }

  if (!user) {
    throw new Error("Failed to authenticate user");
  }

  // Update last signed in
  await upsertUser({
    openId: user.openId,
    lastSignedIn: new Date(),
  });

  // Create session token
  const sessionToken = await createSessionToken(user.openId, user.name || "");

  return { sessionToken, user };
}

/**
 * Get user by email from database
 */
async function getUserByEmail(email: string): Promise<User | undefined> {
  const openId = emailToOpenId(email);
  return getUserByOpenId(openId);
}

/**
 * Create a session JWT token
 */
export async function createSessionToken(
  openId: string,
  name: string,
  expiresInMs: number = ONE_YEAR_MS
): Promise<string> {
  const secretKey = getSessionSecret();
  const issuedAt = Date.now();
  const expirationSeconds = Math.floor((issuedAt + expiresInMs) / 1000);

  return new SignJWT({
    openId,
    appId: ENV.appId,
    name,
  })
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setExpirationTime(expirationSeconds)
    .sign(secretKey);
}

/**
 * Verify a session JWT token
 */
export async function verifySessionToken(
  token: string | undefined | null
): Promise<{ openId: string; appId: string; name: string } | null> {
  if (!token) {
    return null;
  }

  try {
    const secretKey = getSessionSecret();
    const { payload } = await jwtVerify(token, secretKey, {
      algorithms: ["HS256"],
    });

    const { openId, appId, name } = payload as {
      openId?: unknown;
      appId?: unknown;
      name?: unknown;
    };

    if (!openId || !appId || typeof name !== "string") {
      return null;
    }

    return { openId: String(openId), appId: String(appId), name };
  } catch {
    return null;
  }
}

/**
 * Get session secret from environment
 */
function getSessionSecret() {
  const secret = process.env.JWT_SECRET || ENV.cookieSecret;
  if (!secret || secret.length < 32) {
    throw new Error("JWT_SECRET must be at least 32 characters");
  }
  return new TextEncoder().encode(secret);
}

/**
 * Authenticate a request and return the user
 * This replaces sdk.authenticateRequest
 */
export async function authenticateRequest(req: Request): Promise<User> {
  const cookies = parseCookies(req.headers.cookie);
  const sessionCookie = cookies.get(COOKIE_NAME);
  const session = await verifySessionToken(sessionCookie);

  if (!session) {
    throw ForbiddenError("Invalid session cookie");
  }

  const user = await getUserByOpenId(session.openId);

  if (!user) {
    throw ForbiddenError("User not found");
  }

  // Update last signed in
  await upsertUser({
    openId: user.openId,
    lastSignedIn: new Date(),
  });

  return user;
}

/**
 * Parse cookies from request header
 */
function parseCookies(cookieHeader: string | undefined) {
  if (!cookieHeader) {
    return new Map<string, string>();
  }

  const cookies = new Map<string, string>();
  cookieHeader.split(";").forEach((cookie) => {
    const [name, value] = cookie.trim().split("=");
    if (name && value) {
      cookies.set(name, value);
    }
  });

  return cookies;
}

/**
 * Register auth routes
 */
export function registerAuthRoutes(app: any) {
  // Register endpoint
  app.post("/api/auth/register", async (req: Request, res: Response) => {
    try {
      const { email, password, name } = req.body;

      if (!email || !password) {
        return res.status(400).json({ error: "Email and password are required" });
      }

      if (password.length < 8) {
        return res.status(400).json({ error: "Password must be at least 8 characters" });
      }

      const { sessionToken, user } = await registerUser({ email, password, name });

      // Set cookie
      res.cookie(COOKIE_NAME, sessionToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: ONE_YEAR_MS,
        path: "/",
      });

      res.json({
        success: true,
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role,
        },
      });
    } catch (error) {
      console.error("[Auth] Register failed", error);
      res.status(400).json({
        error: error instanceof Error ? error.message : "Registration failed",
      });
    }
  });

  // Login endpoint
  app.post("/api/auth/login", async (req: Request, res: Response) => {
    try {
      const { email, password } = req.body;

      if (!email || !password) {
        return res.status(400).json({ error: "Email and password are required" });
      }

      const { sessionToken, user } = await loginUser({ email, password });

      // Set cookie
      res.cookie(COOKIE_NAME, sessionToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: ONE_YEAR_MS,
        path: "/",
      });

      res.json({
        success: true,
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role,
        },
      });
    } catch (error) {
      console.error("[Auth] Login failed", error);
      res.status(401).json({
        error: error instanceof Error ? error.message : "Login failed",
      });
    }
  });

  // Me endpoint (get current user)
  app.get("/api/auth/me", async (req: Request, res: Response) => {
    try {
      const user = await authenticateRequest(req);
      res.json({
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role,
        },
      });
    } catch (error) {
      res.status(401).json({ error: "Not authenticated" });
    }
  });
}

/**
 * Create a default admin user
 * Call this during server startup if no users exist
 */
export async function createDefaultAdminIfNotExists() {
  const adminEmail = process.env.DEFAULT_ADMIN_EMAIL || "admin@crypto.local";
  const adminPassword = process.env.DEFAULT_ADMIN_PASSWORD || "Asdfghjkl;'";

  const existingUser = await getUserByEmail(adminEmail);
  if (!existingUser) {
    console.log("[Auth] Creating default admin user...");
    try {
      await registerUser({
        email: adminEmail,
        password: adminPassword,
        name: "Admin",
      });
      console.log(`[Auth] Default admin created: ${adminEmail} / ${adminPassword}`);
      console.log("[Auth] IMPORTANT: Change the default admin password immediately!");
    } catch (error) {
      console.error("[Auth] Failed to create default admin:", error);
    }
  }
}
