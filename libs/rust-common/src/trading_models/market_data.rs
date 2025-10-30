//! Market data structures.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use super::enums::Timeframe;

/// OHLCV market data bar.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketBar {
    pub symbol: String,
    pub timeframe: Timeframe,
    pub timestamp: DateTime<Utc>,
    
    // Price data - using f64 for Rust, will be converted to/from Decimal in Python
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    
    // Volume data
    pub volume: f64,
    pub quote_volume: Option<f64>,
    
    // Additional metadata
    pub trades_count: Option<u64>,
    pub taker_buy_volume: Option<f64>,
}

impl MarketBar {
    /// Validate OHLC price relationships.
    pub fn validate(&self) -> Result<(), String> {
        if self.open <= 0.0 || self.high <= 0.0 || self.low <= 0.0 || self.close <= 0.0 {
            return Err("All prices must be positive".to_string());
        }
        
        let prices = [self.open, self.high, self.low, self.close];
        let max_price = prices.iter().fold(0.0f64, |a, &b| a.max(b));
        let min_price = prices.iter().fold(f64::INFINITY, |a, &b| a.min(b));
        
        if (self.high - max_price).abs() > f64::EPSILON {
            return Err("High must be the highest price".to_string());
        }
        
        if (self.low - min_price).abs() > f64::EPSILON {
            return Err("Low must be the lowest price".to_string());
        }
        
        if self.volume < 0.0 {
            return Err("Volume must be non-negative".to_string());
        }
        
        Ok(())
    }
}

/// Snapshot of technical indicators at a point in time.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndicatorSnapshot {
    pub symbol: String,
    pub timeframe: Timeframe,
    pub timestamp: DateTime<Utc>,
    
    // Trend indicators
    pub rsi: Option<f64>,
    pub ema_20: Option<f64>,
    pub ema_50: Option<f64>,
    pub ema_200: Option<f64>,
    
    // MACD
    pub macd_line: Option<f64>,
    pub macd_signal: Option<f64>,
    pub macd_histogram: Option<f64>,
    
    // Bollinger Bands
    pub bb_upper: Option<f64>,
    pub bb_middle: Option<f64>,
    pub bb_lower: Option<f64>,
    pub bb_width: Option<f64>,
    
    // Volatility
    pub atr: Option<f64>,
    
    // Volume indicators
    pub volume_sma: Option<f64>,
    pub volume_profile: Option<HashMap<String, f64>>,
    
    // Momentum oscillators
    pub stoch_k: Option<f64>,
    pub stoch_d: Option<f64>,
    pub cci: Option<f64>,
    pub mfi: Option<f64>,
}

impl IndicatorSnapshot {
    /// Validate indicator values are within expected ranges.
    pub fn validate(&self) -> Result<(), String> {
        // Validate RSI range
        if let Some(rsi) = self.rsi {
            if !(0.0..=100.0).contains(&rsi) {
                return Err("RSI must be between 0 and 100".to_string());
            }
        }
        
        // Validate Stochastic ranges
        if let Some(stoch_k) = self.stoch_k {
            if !(0.0..=100.0).contains(&stoch_k) {
                return Err("Stochastic %K must be between 0 and 100".to_string());
            }
        }
        
        if let Some(stoch_d) = self.stoch_d {
            if !(0.0..=100.0).contains(&stoch_d) {
                return Err("Stochastic %D must be between 0 and 100".to_string());
            }
        }
        
        // Validate MFI range
        if let Some(mfi) = self.mfi {
            if !(0.0..=100.0).contains(&mfi) {
                return Err("MFI must be between 0 and 100".to_string());
            }
        }
        
        // Validate Bollinger Bands ordering
        if let (Some(upper), Some(middle), Some(lower)) = (self.bb_upper, self.bb_middle, self.bb_lower) {
            if upper <= middle || middle <= lower {
                return Err("Bollinger Bands must be ordered: upper > middle > lower".to_string());
            }
        }
        
        // Validate positive values
        if let Some(atr) = self.atr {
            if atr < 0.0 {
                return Err("ATR must be non-negative".to_string());
            }
        }
        
        if let Some(volume_sma) = self.volume_sma {
            if volume_sma < 0.0 {
                return Err("Volume SMA must be non-negative".to_string());
            }
        }
        
        Ok(())
    }
}