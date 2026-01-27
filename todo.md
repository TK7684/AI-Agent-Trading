# Crypto Project Auditor - TODO

## Phase 1: Database Schema
- [x] ออกแบบ schema สำหรับเก็บข้อมูลโปรเจกต์
- [x] ออกแบบ schema สำหรับเก็บผลการตรวจสอบ (audit reports)
- [x] Push database schema

## Phase 2: GitHub & Code Analysis
- [x] API สำหรับดึงข้อมูล GitHub repository
- [x] วิเคราะห์ commits, contributors, และ activity
- [x] ตรวจสอบ code quality และ security issues
- [x] คำนวณคะแนน GitHub metrics

## Phase 3: Tokenomics & Contract Risk
- [x] API สำหรับวิเคราะห์ tokenomics (supply, distribution)
- [x] ตรวจสอบ smart contract risks
- [x] วิเคราะห์ holder distribution
- [x] คำนวณคะแนน tokenomics และ contract risk

## Phase 4: Social Media Analysis
- [x] API สำหรับตรวจสอบ Twitter/X
- [x] API สำหรับตรวจสอบ Telegram
- [x] API สำหรับตรวจสอบ Discord
- [x] วิเคราะห์ engagement และ sentiment
- [x] คำนวณคะแนนชุมชน

## Phase 5: AI Analysis System
- [x] สร้างระบบ AI สำหรับวิเคราะห์ข้อมูลรวม
- [x] คำนวณคะแนนรวมจากทุกด้าน
- [x] สร้าง risk assessment report
- [x] ให้คำแนะนำและข้อสรุป

## Phase 6: Frontend UI
- [x] หน้าแรก (landing page)
- [x] ฟอร์มกรอกข้อมูลโปรเจกต์
- [x] หน้าแสดงผลการวิเคราะห์
- [x] Dashboard แสดงประวัติการตรวจสอบ
- [x] หน้ารายละเอียดแต่ละโปรเจกต์

## Phase 7: Testing & Deployment
- [x] ทดสอบทุก API endpoints
- [x] ทดสอบ UI/UX
- [x] ทดสอบกับโปรเจกต์จริง
- [x] สร้าง checkpoint สุดท้าย

## New Feature: Auto Discovery
- [x] สร้าง API สำหรับค้นหาโปรเจกต์คริปโตยอดนิยม
- [x] ดึงข้อมูลจาก CoinGecko/CoinMarketCap trending
- [x] แสดงรายการโปรเจกต์พร้อมข้อมูลสรุป
- [x] เพิ่มปุ่ม "Audit This Project" สำหรับแต่ละโปรเจกต์
- [x] สร้างหน้า Discover Projects UI

## Enhancement: Discover Projects v2
- [x] เพิ่มโปรเจกต์ Early Stage จาก CoinGecko/Dextools API
- [x] เพิ่มหลายหมวดหมู่: DeFi, Layer 1, Layer 2, NFT, Gaming, Metaverse, RWA, AI
- [x] แปลอินเทอร์ทั้งหมดเป็นภาษาไทย
- [x] เพิ่มสรุปย่อสำหรับแต่ละโปรเจกต์
- [x] สร้าง Filters: Category, Market Cap Range, Score Range, Status (Trending/New/Hot)
- [x] เพิ่ม Email Notification System
- [x] ปรับปรุง Performance และ Caching
- [x] เพิ่ม Watchlist Feature
- [x] เพิ่ม Trending Alerts


## Level 1: Basic Features Enhancement
- [x] สร้าง Watchlist table ใน database
- [x] API สำหรับ Add/Remove/List Watchlist
- [x] UI สำหรับ Watchlist page
- [x] Comparison Tool: Side-by-side comparison
- [x] Export Report: PDF generation
- [x] Export Report: JSON export

## Level 2: Real APIs Integration
- [x] Etherscan API integration (Contract verification)
- [x] BscScan API integration (BSC contracts)
- [x] GoPlus Security API (Honeypot detection)
- [x] CoinGecko API optimization (Rate limit handling)
- [x] Contract risk scoring improvement

## Level 3: Advanced Features
- [x] AI Chat Bot backend (tRPC endpoint)
- [x] AI Chat Bot frontend UI
- [x] Sentiment Analysis service
- [x] Automated price/score alerts
- [x] Alert notification system

## Level 4: Business & Growth
- [x] Premium subscription model (role-based)
- [x] Public API documentation
- [x] API rate limiting
- [x] Responsive mobile design
- [x] Analytics dashboard
