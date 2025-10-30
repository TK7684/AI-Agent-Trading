//! Pattern recognition structures.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use super::enums::{PatternType, Timeframe};

/// Detected pattern with confidence and metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatternHit {
    pub pattern_id: String,
    pub pattern_type: PatternType,
    pub symbol: String,
    pub timeframe: Timeframe,
    pub timestamp: DateTime<Utc>,
    
    // Pattern confidence and scoring
    pub confidence: f64,
    pub strength: f64,
    
    // Price levels
    pub entry_price: Option<f64>,
    pub stop_loss: Option<f64>,
    pub take_profit: Option<f64>,
    
    // Support/Resistance levels
    pub support_levels: Vec<f64>,
    pub resistance_levels: Vec<f64>,
    
    // Pattern-specific data
    pub pattern_data: HashMap<String, serde_json::Value>,
    
    // Validation context
    pub bars_analyzed: u32,
    pub lookback_period: u32,
    
    // Performance tracking
    pub historical_win_rate: Option<f64>,
    pub avg_return: Option<f64>,
}

impl PatternHit {
    /// Validate pattern data.
    pub fn validate(&self) -> Result<(), String> {
        // Validate confidence range
        if !(0.0..=1.0).contains(&self.confidence) {
            return Err("Confidence must be between 0 and 1".to_string());
        }
        
        // Validate strength range
        if !(0.0..=10.0).contains(&self.strength) {
            return Err("Strength must be between 0 and 10".to_string());
        }
        
        // Validate positive prices
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
        
        // Validate price levels are positive and sorted
        for level in &self.support_levels {
            if *level <= 0.0 {
                return Err("Support levels must be positive".to_string());
            }
        }
        
        for level in &self.resistance_levels {
            if *level <= 0.0 {
                return Err("Resistance levels must be positive".to_string());
            }
        }
        
        // Check if levels are sorted
        let mut sorted_support = self.support_levels.clone();
        sorted_support.sort_by(|a, b| a.partial_cmp(b).unwrap());
        if sorted_support != self.support_levels {
            return Err("Support levels must be sorted".to_string());
        }
        
        let mut sorted_resistance = self.resistance_levels.clone();
        sorted_resistance.sort_by(|a, b| a.partial_cmp(b).unwrap());
        if sorted_resistance != self.resistance_levels {
            return Err("Resistance levels must be sorted".to_string());
        }
        
        // Validate historical win rate
        if let Some(win_rate) = self.historical_win_rate {
            if !(0.0..=1.0).contains(&win_rate) {
                return Err("Historical win rate must be between 0 and 1".to_string());
            }
        }
        
        // Validate analysis parameters
        if self.bars_analyzed == 0 {
            return Err("Bars analyzed must be greater than 0".to_string());
        }
        
        if self.lookback_period == 0 {
            return Err("Lookback period must be greater than 0".to_string());
        }
        
        Ok(())
    }
}

/// Collection of patterns for a symbol/timeframe.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatternCollection {
    pub symbol: String,
    pub timeframe: Timeframe,
    pub timestamp: DateTime<Utc>,
    
    pub patterns: Vec<PatternHit>,
    
    // Summary statistics
    pub total_patterns: u32,
    pub avg_confidence: f64,
    pub strongest_pattern: Option<String>,
}

impl PatternCollection {
    /// Create a new pattern collection.
    pub fn new(symbol: String, timeframe: Timeframe) -> Self {
        Self {
            symbol,
            timeframe,
            timestamp: Utc::now(),
            patterns: Vec::new(),
            total_patterns: 0,
            avg_confidence: 0.0,
            strongest_pattern: None,
        }
    }
    
    /// Add a pattern to the collection.
    pub fn add_pattern(&mut self, pattern: PatternHit) {
        self.patterns.push(pattern);
        self.update_stats();
    }
    
    /// Update summary statistics.
    fn update_stats(&mut self) {
        self.total_patterns = self.patterns.len() as u32;
        
        if !self.patterns.is_empty() {
            self.avg_confidence = self.patterns.iter()
                .map(|p| p.confidence)
                .sum::<f64>() / self.patterns.len() as f64;
            
            if let Some(strongest) = self.patterns.iter()
                .max_by(|a, b| a.strength.partial_cmp(&b.strength).unwrap()) {
                self.strongest_pattern = Some(strongest.pattern_id.clone());
            }
        } else {
            self.avg_confidence = 0.0;
            self.strongest_pattern = None;
        }
    }
    
    /// Get patterns of a specific type.
    pub fn get_patterns_by_type(&self, pattern_type: PatternType) -> Vec<&PatternHit> {
        self.patterns.iter()
            .filter(|p| p.pattern_type == pattern_type)
            .collect()
    }
    
    /// Get patterns above confidence threshold.
    pub fn get_high_confidence_patterns(&self, min_confidence: f64) -> Vec<&PatternHit> {
        self.patterns.iter()
            .filter(|p| p.confidence >= min_confidence)
            .collect()
    }
}