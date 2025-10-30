//! Trading signal structures.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use super::{
    enums::{Direction, MarketRegime, Timeframe},
    market_data::IndicatorSnapshot,
    patterns::PatternHit,
};

/// Analysis results for a specific timeframe.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeframeAnalysis {
    pub timeframe: Timeframe,
    pub timestamp: DateTime<Utc>,
    
    // Technical analysis scores
    pub trend_score: f64,
    pub momentum_score: f64,
    pub volatility_score: f64,
    pub volume_score: f64,
    
    // Pattern analysis
    pub pattern_count: u32,
    pub strongest_pattern_confidence: f64,
    
    // Indicator summary
    pub bullish_indicators: u32,
    pub bearish_indicators: u32,
    pub neutral_indicators: u32,
    
    // Weight for confluence calculation
    pub timeframe_weight: f64,
}

impl TimeframeAnalysis {
    /// Validate analysis scores.
    pub fn validate(&self) -> Result<(), String> {
        // Validate score ranges
        if !(-10.0..=10.0).contains(&self.trend_score) {
            return Err("Trend score must be between -10 and 10".to_string());
        }
        
        if !(-10.0..=10.0).contains(&self.momentum_score) {
            return Err("Momentum score must be between -10 and 10".to_string());
        }
        
        if !(0.0..=10.0).contains(&self.volatility_score) {
            return Err("Volatility score must be between 0 and 10".to_string());
        }
        
        if !(0.0..=10.0).contains(&self.volume_score) {
            return Err("Volume score must be between 0 and 10".to_string());
        }
        
        // Validate confidence range
        if !(0.0..=1.0).contains(&self.strongest_pattern_confidence) {
            return Err("Pattern confidence must be between 0 and 1".to_string());
        }
        
        // Validate timeframe weight
        if !(0.0..=1.0).contains(&self.timeframe_weight) || self.timeframe_weight == 0.0 {
            return Err("Timeframe weight must be between 0 (exclusive) and 1".to_string());
        }
        
        Ok(())
    }
}

/// LLM analysis results.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmAnalysis {
    pub model_id: String,
    pub timestamp: DateTime<Utc>,
    
    // Analysis results
    pub market_sentiment: String,
    pub key_insights: Vec<String>,
    pub risk_factors: Vec<String>,
    
    // Scoring
    pub bullish_score: f64,
    pub bearish_score: f64,
    pub confidence: f64,
    
    // Performance metrics
    pub tokens_used: u32,
    pub latency_ms: u32,
    pub cost_usd: f64,
}

impl LlmAnalysis {
    /// Validate LLM analysis data.
    pub fn validate(&self) -> Result<(), String> {
        // Validate score ranges
        if !(0.0..=10.0).contains(&self.bullish_score) {
            return Err("Bullish score must be between 0 and 10".to_string());
        }
        
        if !(0.0..=10.0).contains(&self.bearish_score) {
            return Err("Bearish score must be between 0 and 10".to_string());
        }
        
        if !(0.0..=1.0).contains(&self.confidence) {
            return Err("Confidence must be between 0 and 1".to_string());
        }
        
        // Validate performance metrics
        if self.tokens_used == 0 {
            return Err("Tokens used must be greater than 0".to_string());
        }
        
        if self.latency_ms == 0 {
            return Err("Latency must be greater than 0".to_string());
        }
        
        if self.cost_usd < 0.0 {
            return Err("Cost must be non-negative".to_string());
        }
        
        Ok(())
    }
}

/// Trading signal with confluence analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Signal {
    pub signal_id: String,
    pub symbol: String,
    pub timestamp: DateTime<Utc>,
    
    // Signal direction and strength
    pub direction: Direction,
    pub confluence_score: f64,
    pub confidence: f64,
    
    // Market context
    pub market_regime: MarketRegime,
    pub primary_timeframe: Timeframe,
    
    // Analysis components
    pub timeframe_analysis: HashMap<Timeframe, TimeframeAnalysis>,
    pub patterns: Vec<PatternHit>,
    pub indicators: HashMap<Timeframe, IndicatorSnapshot>,
    pub llm_analysis: Option<LlmAnalysis>,
    
    // Price targets
    pub entry_price: Option<f64>,
    pub stop_loss: Option<f64>,
    pub take_profit: Option<f64>,
    
    // Risk metrics
    pub risk_reward_ratio: Option<f64>,
    pub max_risk_pct: Option<f64>,
    
    // Signal reasoning
    pub reasoning: String,
    pub key_factors: Vec<String>,
    
    // Metadata
    pub expires_at: Option<DateTime<Utc>>,
    pub priority: u8,
}

impl Signal {
    /// Validate signal data.
    pub fn validate(&self) -> Result<(), String> {
        // Validate confluence score
        if !(0.0..=100.0).contains(&self.confluence_score) {
            return Err("Confluence score must be between 0 and 100".to_string());
        }
        
        // Validate confidence
        if !(0.0..=1.0).contains(&self.confidence) {
            return Err("Confidence must be between 0 and 1".to_string());
        }
        
        // High confluence should have high confidence
        if self.confluence_score > 90.0 && self.confidence < 0.8 {
            return Err("High confluence score requires high confidence".to_string());
        }
        
        // Validate price levels
        if let Some(entry) = self.entry_price {
            if entry <= 0.0 {
                return Err("Entry price must be positive".to_string());
            }
        }
        
        if let Some(stop) = self.stop_loss {
            if stop <= 0.0 {
                return Err("Stop loss must be positive".to_string());
            }
        }
        
        if let Some(target) = self.take_profit {
            if target <= 0.0 {
                return Err("Take profit must be positive".to_string());
            }
        }
        
        // Validate risk/reward ratio
        if let Some(rr) = self.risk_reward_ratio {
            if rr <= 0.0 {
                return Err("Risk/reward ratio must be positive".to_string());
            }
            
            // Validate against price levels if available
            if let (Some(entry), Some(stop), Some(target)) = (self.entry_price, self.stop_loss, self.take_profit) {
                let (risk, reward) = match self.direction {
                    Direction::Long => (entry - stop, target - entry),
                    Direction::Short => (stop - entry, entry - target),
                };
                
                if risk > 0.0 {
                    let calculated_rr = reward / risk;
                    if (calculated_rr - rr).abs() > 0.1 {
                        return Err("Risk/reward ratio doesn't match price levels".to_string());
                    }
                }
            }
        }
        
        // Validate max risk percentage
        if let Some(max_risk) = self.max_risk_pct {
            if !(0.0..=10.0).contains(&max_risk) {
                return Err("Max risk percentage must be between 0 and 10".to_string());
            }
        }
        
        // Validate priority
        if !(1..=5).contains(&self.priority) {
            return Err("Priority must be between 1 and 5".to_string());
        }
        
        // Validate timeframe analyses
        for analysis in self.timeframe_analysis.values() {
            analysis.validate()?;
        }
        
        // Validate patterns
        for pattern in &self.patterns {
            pattern.validate()?;
        }
        
        // Validate indicators
        for indicator in self.indicators.values() {
            indicator.validate()?;
        }
        
        // Validate LLM analysis if present
        if let Some(llm) = &self.llm_analysis {
            llm.validate()?;
        }
        
        Ok(())
    }
    
    /// Calculate weighted confluence score from timeframe analyses.
    pub fn get_weighted_confluence(&self) -> f64 {
        if self.timeframe_analysis.is_empty() {
            return self.confluence_score;
        }
        
        let total_weight: f64 = self.timeframe_analysis.values()
            .map(|ta| ta.timeframe_weight)
            .sum();
        
        if total_weight == 0.0 {
            return self.confluence_score;
        }
        
        let weighted_sum: f64 = self.timeframe_analysis.values()
            .map(|ta| (ta.trend_score + ta.momentum_score) * ta.timeframe_weight)
            .sum();
        
        // Normalize to 0-100 scale
        let normalized_score = (weighted_sum / total_weight + 10.0) * 5.0;
        normalized_score.max(0.0).min(100.0)
    }
}