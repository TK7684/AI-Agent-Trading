/**
 * Email Service - ส่งการแจ้งเตือนไปยังอีเมลของผู้ใช้
 */

import { invokeLLM } from "../_core/llm";

export interface EmailNotification {
  userId: number;
  email: string;
  projectName: string;
  projectSymbol: string;
  score: number;
  category: string;
  marketCap: number;
  priceChange24h: number;
  briefSummary: string;
  tags: string[];
  auditUrl: string;
}

/**
 * ส่งอีเมลแจ้งเตือนเมื่อมีโปรเจกต์ใหม่ที่น่าสนใจ
 */
export async function sendProjectNotificationEmail(notification: EmailNotification): Promise<boolean> {
  try {
    // สร้าง HTML email template
    const emailHtml = generateEmailTemplate(notification);
    
    // ใช้ Manus Notification API เพื่อส่งอีเมล
    const response = await fetch(
      `${process.env.BUILT_IN_FORGE_API_URL}/notification/email`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${process.env.BUILT_IN_FORGE_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          to: notification.email,
          subject: `🚀 ${notification.projectName} (${notification.projectSymbol}) - คะแนน ${notification.score}/100`,
          html: emailHtml,
        }),
      }
    );

    if (!response.ok) {
      console.error("Failed to send email:", await response.text());
      return false;
    }

    return true;
  } catch (error) {
    console.error("Error sending email notification:", error);
    return false;
  }
}

/**
 * ส่งอีเมลเมื่อการวิเคราะห์เสร็จสิ้น
 */
export async function sendAuditCompletionEmail(
  email: string,
  projectName: string,
  projectSymbol: string,
  overallScore: number,
  riskLevel: string,
  auditUrl: string
): Promise<boolean> {
  try {
    const emailHtml = `
      <!DOCTYPE html>
      <html dir="ltr" lang="th">
      <head>
        <meta charset="UTF-8">
        <style>
          body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }
          .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
          .score-box { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; border-left: 4px solid #667eea; }
          .score-value { font-size: 48px; font-weight: bold; color: #667eea; }
          .risk-level { font-size: 18px; color: #666; margin-top: 10px; }
          .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; border-radius: 5px; text-decoration: none; margin: 20px 0; }
          .footer { text-align: center; color: #999; font-size: 12px; margin-top: 30px; }
          .tag { display: inline-block; background: #e0e7ff; color: #667eea; padding: 5px 10px; border-radius: 20px; margin: 5px 5px 5px 0; font-size: 12px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>✅ การวิเคราะห์เสร็จสิ้น!</h1>
            <p>รายงาน Audit สำหรับ ${projectName} (${projectSymbol}) พร้อมแล้ว</p>
          </div>
          
          <div class="content">
            <h2>สรุปผลการวิเคราะห์</h2>
            
            <div class="score-box">
              <div class="score-value">${overallScore}</div>
              <div class="risk-level">คะแนนรวม / 100</div>
              <div style="margin-top: 15px; font-size: 16px;">
                ระดับความเสี่ยง: <strong>${getRiskLevelLabel(riskLevel)}</strong>
              </div>
            </div>
            
            <p>รายงาน Audit ที่ครอบคลุมสำหรับ <strong>${projectName}</strong> ได้รับการวิเคราะห์แล้ว โดยครอบคลุม:</p>
            <ul>
              <li>📊 การวิเคราะห์ GitHub (commits, contributors, activity)</li>
              <li>💰 การวิเคราะห์ Tokenomics (supply, distribution)</li>
              <li>⚠️ การประเมินความเสี่ยงของสัญญา (contract risks)</li>
              <li>👥 การวิเคราะห์ชุมชน (Twitter, Telegram, Discord)</li>
              <li>🤖 คะแนน AI และคำแนะนำ</li>
            </ul>
            
            <a href="${auditUrl}" class="button">ดูรายงาน Audit ฉบับเต็ม →</a>
            
            <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
              ขอบคุณที่ใช้ Crypto Project Auditor! หากคุณมีคำถามใด ๆ โปรดติดต่อเรา
            </p>
          </div>
          
          <div class="footer">
            <p>© 2024 Crypto Project Auditor - AI-Powered Crypto Security Analysis</p>
          </div>
        </div>
      </body>
      </html>
    `;

    const response = await fetch(
      `${process.env.BUILT_IN_FORGE_API_URL}/notification/email`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${process.env.BUILT_IN_FORGE_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          to: email,
          subject: `✅ Audit สำเร็จ: ${projectName} (${projectSymbol}) - คะแนน ${overallScore}/100`,
          html: emailHtml,
        }),
      }
    );

    if (!response.ok) {
      console.error("Failed to send completion email:", await response.text());
      return false;
    }

    return true;
  } catch (error) {
    console.error("Error sending audit completion email:", error);
    return false;
  }
}

/**
 * ส่งอีเมลแจ้งเตือนเมื่อมีโปรเจกต์ Hot ใหม่
 */
export async function sendHotProjectAlert(
  email: string,
  projects: Array<{
    name: string;
    symbol: string;
    score: number;
    priceChange24h: number;
    category: string;
    briefSummary: string;
  }>
): Promise<boolean> {
  try {
    const projectsList = projects
      .map(p => `
        <div style="background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #ff6b6b;">
          <h3 style="margin: 0 0 10px 0; color: #ff6b6b;">🔥 ${p.name} (${p.symbol})</h3>
          <p style="margin: 5px 0; color: #666;"><strong>คะแนน:</strong> ${p.score}/100</p>
          <p style="margin: 5px 0; color: ${p.priceChange24h >= 0 ? '#51cf66' : '#ff6b6b'};"><strong>ราคา 24h:</strong> ${p.priceChange24h >= 0 ? '+' : ''}${p.priceChange24h.toFixed(2)}%</p>
          <p style="margin: 5px 0; color: #666;"><strong>หมวดหมู่:</strong> ${p.category}</p>
          <p style="margin: 10px 0; color: #666; font-size: 14px;">${p.briefSummary}</p>
        </div>
      `)
      .join("");

    const emailHtml = `
      <!DOCTYPE html>
      <html dir="ltr" lang="th">
      <head>
        <meta charset="UTF-8">
        <style>
          body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: linear-gradient(135deg, #ff6b6b 0%, #ff8787 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }
          .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
          .button { display: inline-block; background: #ff6b6b; color: white; padding: 12px 30px; border-radius: 5px; text-decoration: none; margin: 20px 0; }
          .footer { text-align: center; color: #999; font-size: 12px; margin-top: 30px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>🔥 โปรเจกต์ Hot ใหม่!</h1>
            <p>พบโปรเจกต์คริปโตที่น่าสนใจ ${projects.length} รายการ</p>
          </div>
          
          <div class="content">
            <h2>โปรเจกต์ที่น่าสนใจในตอนนี้</h2>
            <p>เราพบโปรเจกต์คริปโตที่มีการเปลี่ยนแปลงสำคัญและน่าสนใจ ตามการวิเคราะห์ของระบบ AI ของเรา:</p>
            
            ${projectsList}
            
            <a href="https://your-domain.com/discover" class="button">ดูโปรเจกต์ทั้งหมด →</a>
            
            <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
              คุณได้รับอีเมลนี้เพราะคุณสมัครรับการแจ้งเตือนเกี่ยวกับโปรเจกต์ Hot ใหม่
            </p>
          </div>
          
          <div class="footer">
            <p>© 2024 Crypto Project Auditor - AI-Powered Crypto Security Analysis</p>
          </div>
        </div>
      </body>
      </html>
    `;

    const response = await fetch(
      `${process.env.BUILT_IN_FORGE_API_URL}/notification/email`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${process.env.BUILT_IN_FORGE_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          to: email,
          subject: `🔥 โปรเจกต์ Hot ใหม่: ${projects[0]?.name} และอื่น ๆ`,
          html: emailHtml,
        }),
      }
    );

    if (!response.ok) {
      console.error("Failed to send hot project alert:", await response.text());
      return false;
    }

    return true;
  } catch (error) {
    console.error("Error sending hot project alert:", error);
    return false;
  }
}

/**
 * สร้าง HTML template สำหรับอีเมลแจ้งเตือนโปรเจกต์
 */
function generateEmailTemplate(notification: EmailNotification): string {
  const riskColor = notification.score >= 80 ? "#51cf66" : notification.score >= 60 ? "#4dabf7" : notification.score >= 40 ? "#ffd43b" : "#ff6b6b";
  
  return `
    <!DOCTYPE html>
    <html dir="ltr" lang="th">
    <head>
      <meta charset="UTF-8">
      <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .project-card { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid ${riskColor}; }
        .score-box { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; border: 2px solid ${riskColor}; }
        .score-value { font-size: 48px; font-weight: bold; color: ${riskColor}; }
        .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; border-radius: 5px; text-decoration: none; margin: 20px 0; }
        .tag { display: inline-block; background: #e0e7ff; color: #667eea; padding: 5px 10px; border-radius: 20px; margin: 5px 5px 5px 0; font-size: 12px; }
        .footer { text-align: center; color: #999; font-size: 12px; margin-top: 30px; }
        .metric { display: inline-block; margin-right: 20px; }
        .metric-label { color: #999; font-size: 12px; }
        .metric-value { font-size: 18px; font-weight: bold; color: #333; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>🚀 โปรเจกต์ใหม่ที่น่าสนใจ!</h1>
          <p>พบโปรเจกต์คริปโตที่อาจสนใจคุณ</p>
        </div>
        
        <div class="content">
          <div class="project-card">
            <h2 style="margin-top: 0;">${notification.projectName} <span style="color: #999; font-size: 18px;">(${notification.projectSymbol})</span></h2>
            
            <p style="color: #666; margin: 10px 0;">${notification.briefSummary}</p>
            
            <div class="score-box">
              <div class="score-value">${notification.score}</div>
              <div style="color: #666; margin-top: 10px;">คะแนน AI Recommendation / 100</div>
            </div>
            
            <h3 style="margin-top: 20px;">📊 ข้อมูลสำคัญ</h3>
            <div>
              <div class="metric">
                <div class="metric-label">มูลค่าตลาด</div>
                <div class="metric-value">$${(notification.marketCap / 1000000000).toFixed(2)}B</div>
              </div>
              <div class="metric">
                <div class="metric-label">ราคา 24h</div>
                <div class="metric-value" style="color: ${notification.priceChange24h >= 0 ? '#51cf66' : '#ff6b6b'};">
                  ${notification.priceChange24h >= 0 ? '+' : ''}${notification.priceChange24h.toFixed(2)}%
                </div>
              </div>
              <div class="metric">
                <div class="metric-label">หมวดหมู่</div>
                <div class="metric-value">${notification.category}</div>
              </div>
            </div>
            
            <h3 style="margin-top: 20px;">🏷️ Tags</h3>
            <div>
              ${notification.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
            </div>
            
            <a href="${notification.auditUrl}" class="button">ตรวจสอบโปรเจกต์นี้ →</a>
            
            <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
              คุณได้รับอีเมลนี้เพราะคุณสมัครรับการแจ้งเตือนเกี่ยวกับโปรเจกต์คริปโตใหม่ที่น่าสนใจ
            </p>
          </div>
        </div>
        
        <div class="footer">
          <p>© 2024 Crypto Project Auditor - AI-Powered Crypto Security Analysis</p>
        </div>
      </div>
    </body>
    </html>
  `;
}

/**
 * แปลงระดับความเสี่ยงเป็นป้ายกำกับภาษาไทย
 */
function getRiskLevelLabel(riskLevel: string): string {
  switch (riskLevel) {
    case "very_low": return "ต่ำมาก ✅";
    case "low": return "ต่ำ ✅";
    case "medium": return "ปานกลาง ⚠️";
    case "high": return "สูง 🔴";
    case "very_high": return "สูงมาก 🔴";
    default: return "ไม่ทราบ";
  }
}
