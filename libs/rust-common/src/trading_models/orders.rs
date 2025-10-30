//! Order and execution structures.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

use super::enums::{Direction, OrderStatus, OrderType, Timeframe};

/// Trading order decision with risk management.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderDecision {
    pub decision_id: String,
    pub signal_id: String,
    pub symbol: String,
    pub timestamp: DateTime<Utc>,
    
    // Order details
    pub direction: Direction,
    pub order_type: OrderType,
    
    // Position sizing
    pub base_quantity: f64,
    pub risk_adjusted_quantity: f64,
    pub max_position_value: f64,
    
    // Price levels
    pub entry_price: f64,
    pub stop_loss: f64,
    pub take_profit: Option<f64>,
    
    // Risk management
    pub risk_amount: f64,
    pub risk_percentage: f64,
    pub leverage: f64,
    
    // Portfolio context
    pub portfolio_value: f64,
    pub available_margin: f64,
    pub current_exposure: f64,
    
    // Decision factors
    pub confidence_score: f64,
    pub confluence_score: f64,
    pub risk_reward_ratio: f64,
    
    // Execution parameters
    pub slippage_tolerance: f64,
    pub max_execution_time: u32,
    pub partial_fill_acceptable: bool,
    
    // Decision reasoning
    pub decision_reason: String,
    pub risk_factors: Vec<String>,
    pub supporting_factors: Vec<String>,
    
    // Metadata
    pub timeframe_context: Timeframe,
    pub market_conditions: HashMap<String, serde_json::Value>,
}

impl OrderDecision {
    /// Create a new order decision with generated ID.
    pub fn new(signal_id: String, symbol: String) -> Self {
        Self {
            decision_id: Uuid::new_v4().to_string(),
            signal_id,
            symbol,
            timestamp: Utc::now(),
            direction: Direction::Long,
            order_type: OrderType::Market,
            base_quantity: 0.0,
            risk_adjusted_quantity: 0.0,
            max_position_value: 0.0,
            entry_price: 0.0,
            stop_loss: 0.0,
            take_profit: None,
            risk_amount: 0.0,
            risk_percentage: 0.0,
            leverage: 1.0,
            portfolio_value: 0.0,
            available_margin: 0.0,
            current_exposure: 0.0,
            confidence_score: 0.0,
            confluence_score: 0.0,
            risk_reward_ratio: 0.0,
            slippage_tolerance: 0.001,
            max_execution_time: 300,
            partial_fill_acceptable: true,
            decision_reason: String::new(),
            risk_factors: Vec::new(),
            supporting_factors: Vec::new(),
            timeframe_context: Timeframe::H1,
            market_conditions: HashMap::new(),
        }
    }
    
    /// Validate order decision data.
    pub fn validate(&self) -> Result<(), String> {
        // Validate positive values
        if self.base_quantity <= 0.0 {
            return Err("Base quantity must be positive".to_string());
        }
        
        if self.risk_adjusted_quantity <= 0.0 {
            return Err("Risk adjusted quantity must be positive".to_string());
        }
        
        if self.max_position_value <= 0.0 {
            return Err("Max position value must be positive".to_string());
        }
        
        if self.entry_price <= 0.0 {
            return Err("Entry price must be positive".to_string());
        }
        
        if self.stop_loss <= 0.0 {
            return Err("Stop loss must be positive".to_string());
        }
        
        if let Some(tp) = self.take_profit {
            if tp <= 0.0 {
                return Err("Take profit must be positive".to_string());
            }
        }
        
        if self.risk_amount <= 0.0 {
            return Err("Risk amount must be positive".to_string());
        }
        
        if self.portfolio_value <= 0.0 {
            return Err("Portfolio value must be positive".to_string());
        }
        
        // Validate ranges
        if !(0.0..=10.0).contains(&self.risk_percentage) {
            return Err("Risk percentage must be between 0 and 10".to_string());
        }
        
        if !(0.0..=50.0).contains(&self.leverage) || self.leverage == 0.0 {
            return Err("Leverage must be between 0 (exclusive) and 50".to_string());
        }
        
        if !(0.0..=1.0).contains(&self.current_exposure) {
            return Err("Current exposure must be between 0 and 1".to_string());
        }
        
        if !(0.0..=1.0).contains(&self.confidence_score) {
            return Err("Confidence score must be between 0 and 1".to_string());
        }
        
        if !(0.0..=100.0).contains(&self.confluence_score) {
            return Err("Confluence score must be between 0 and 100".to_string());
        }
        
        if self.risk_reward_ratio <= 0.0 {
            return Err("Risk reward ratio must be positive".to_string());
        }
        
        if !(0.0..=0.1).contains(&self.slippage_tolerance) {
            return Err("Slippage tolerance must be between 0 and 0.1".to_string());
        }
        
        // Validate risk adjustment
        if self.risk_adjusted_quantity > self.base_quantity * 2.0 {
            return Err("Risk adjusted quantity cannot exceed 2x base quantity".to_string());
        }
        
        if self.risk_adjusted_quantity < self.base_quantity * 0.1 {
            return Err("Risk adjusted quantity cannot be less than 10% of base".to_string());
        }
        
        // Validate portfolio risk
        let total_risk = self.risk_percentage + (self.current_exposure * 100.0);
        if total_risk > 20.0 {
            return Err("Total portfolio risk would exceed 20%".to_string());
        }
        
        // Validate leverage vs risk
        if self.leverage > 10.0 {
            return Err("Leverage cannot exceed 10x".to_string());
        }
        
        let max_risk_for_leverage = 5.0 / self.leverage;
        if self.risk_percentage > max_risk_for_leverage {
            return Err("Risk percentage too high for leverage level".to_string());
        }
        
        // Validate stop loss placement
        match self.direction {
            Direction::Long => {
                if self.stop_loss >= self.entry_price {
                    return Err("Stop loss must be below entry price for long positions".to_string());
                }
            }
            Direction::Short => {
                if self.stop_loss <= self.entry_price {
                    return Err("Stop loss must be above entry price for short positions".to_string());
                }
            }
        }
        
        // Validate stop loss distance (max 20% from entry)
        let stop_diff_pct = (self.stop_loss - self.entry_price).abs() / self.entry_price;
        if stop_diff_pct > 0.2 {
            return Err("Stop loss too far from entry (>20%)".to_string());
        }
        
        // Validate take profit placement
        if let Some(tp) = self.take_profit {
            match self.direction {
                Direction::Long => {
                    if tp <= self.entry_price {
                        return Err("Take profit must be above entry price for long positions".to_string());
                    }
                }
                Direction::Short => {
                    if tp >= self.entry_price {
                        return Err("Take profit must be below entry price for short positions".to_string());
                    }
                }
            }
        }
        
        Ok(())
    }
    
    /// Calculate total position value including leverage.
    pub fn calculate_position_value(&self) -> f64 {
        self.risk_adjusted_quantity * self.entry_price * self.leverage
    }
    
    /// Calculate margin required for position.
    pub fn calculate_margin_required(&self) -> f64 {
        self.calculate_position_value() / self.leverage
    }
    
    /// Check if sufficient margin is available.
    pub fn validate_margin_requirements(&self) -> bool {
        let required_margin = self.calculate_margin_required();
        self.available_margin >= required_margin
    }
    
    /// Get comprehensive risk metrics.
    pub fn get_risk_metrics(&self) -> HashMap<String, f64> {
        let position_value = self.calculate_position_value();
        let margin_utilization = if self.available_margin > 0.0 {
            (self.calculate_margin_required() / self.available_margin) * 100.0
        } else {
            0.0
        };
        
        let mut metrics = HashMap::new();
        metrics.insert("position_size_pct".to_string(), (position_value / self.portfolio_value) * 100.0);
        metrics.insert("risk_amount".to_string(), self.risk_amount);
        metrics.insert("risk_percentage".to_string(), self.risk_percentage);
        metrics.insert("leverage".to_string(), self.leverage);
        metrics.insert("risk_reward_ratio".to_string(), self.risk_reward_ratio);
        metrics.insert("margin_utilization".to_string(), margin_utilization);
        
        metrics
    }
}

/// Result of order execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub execution_id: String,
    pub decision_id: String,
    pub order_id: String,
    
    // Execution details
    pub status: OrderStatus,
    pub filled_quantity: f64,
    pub average_price: Option<f64>,
    
    // Timing
    pub submitted_at: DateTime<Utc>,
    pub filled_at: Option<DateTime<Utc>>,
    
    // Costs
    pub commission: f64,
    pub slippage: Option<f64>,
    
    // Execution quality
    pub execution_time_ms: Option<u32>,
    pub partial_fills: Vec<HashMap<String, serde_json::Value>>,
    
    // Error handling
    pub error_message: Option<String>,
    pub retry_count: u32,
}

impl ExecutionResult {
    /// Create a new execution result.
    pub fn new(decision_id: String, order_id: String) -> Self {
        Self {
            execution_id: Uuid::new_v4().to_string(),
            decision_id,
            order_id,
            status: OrderStatus::Pending,
            filled_quantity: 0.0,
            average_price: None,
            submitted_at: Utc::now(),
            filled_at: None,
            commission: 0.0,
            slippage: None,
            execution_time_ms: None,
            partial_fills: Vec::new(),
            error_message: None,
            retry_count: 0,
        }
    }
    
    /// Check if order is fully filled.
    pub fn is_fully_filled(&self) -> bool {
        self.status == OrderStatus::Filled
    }
    
    /// Check if order is partially filled.
    pub fn is_partially_filled(&self) -> bool {
        self.status == OrderStatus::PartiallyFilled
    }
    
    /// Get fill percentage.
    pub fn get_fill_percentage(&self, original_quantity: f64) -> f64 {
        if original_quantity <= 0.0 {
            return 0.0;
        }
        (self.filled_quantity / original_quantity) * 100.0
    }
}