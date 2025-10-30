use async_trait::async_trait;
use rust_common::{OrderRequest, TradingError, OrderStatus};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};

/// Result from exchange adapter order placement
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdapterOrderResult {
    pub order_id: String,
    pub status: OrderStatus,
    pub filled_quantity: f64,
    pub average_price: Option<f64>,
    pub commission: f64,
    pub filled_at: Option<DateTime<Utc>>,
    pub partial_fills: Vec<HashMap<String, serde_json::Value>>,
}

/// Exchange-specific trading rules and constraints
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExchangeInfo {
    pub name: String,
    pub tick_size: f64,
    pub lot_size: f64,
    pub min_order_size: f64,
    pub max_order_size: f64,
    pub min_price: f64,
    pub max_price: f64,
    pub trading_hours: Vec<TradingHours>,
    pub supported_order_types: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradingHours {
    pub day_of_week: u8, // 0 = Sunday, 6 = Saturday
    pub open_time: String, // "09:30:00"
    pub close_time: String, // "16:00:00"
    pub timezone: String, // "America/New_York"
}

/// Exchange adapter trait for different trading platforms
#[async_trait]
pub trait ExchangeAdapter {
    /// Get exchange information and trading rules
    async fn get_exchange_info(&self, symbol: &str) -> Result<ExchangeInfo, TradingError>;
    
    /// Place an order on the exchange
    async fn place_order(&self, order: OrderRequest) -> Result<AdapterOrderResult, TradingError>;
    
    /// Cancel an existing order
    async fn cancel_order(&self, order_id: &str) -> Result<(), TradingError>;
    
    /// Get order status
    async fn get_order_status(&self, order_id: &str) -> Result<OrderStatus, TradingError>;
    
    /// Amend an existing order (change price/quantity)
    async fn amend_order(&self, order_id: &str, new_price: Option<f64>, new_quantity: Option<f64>) -> Result<(), TradingError>;
    
    /// Get account balance and positions
    async fn get_account_info(&self) -> Result<AccountInfo, TradingError>;
    
    /// Validate order before submission
    async fn validate_order(&self, order: &OrderRequest) -> Result<(), TradingError>;
    
    /// Round price to exchange tick size
    fn round_price(&self, price: f64, tick_size: f64) -> f64;
    
    /// Round quantity to exchange lot size
    fn round_quantity(&self, quantity: f64, lot_size: f64) -> f64;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountInfo {
    pub account_id: String,
    pub total_balance: f64,
    pub available_balance: f64,
    pub margin_used: f64,
    pub margin_available: f64,
    pub positions: Vec<Position>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub symbol: String,
    pub side: String, // "long" or "short"
    pub size: f64,
    pub entry_price: f64,
    pub current_price: f64,
    pub unrealized_pnl: f64,
    pub margin_used: f64,
}

/// Mock exchange adapter for testing
pub struct MockExchangeAdapter {
    pub exchange_info: ExchangeInfo,
    pub should_fail: bool,
    pub delay_ms: u64,
    pub partial_fill_ratio: f64, // 0.0 to 1.0
}

impl MockExchangeAdapter {
    pub fn new() -> Self {
        Self {
            exchange_info: ExchangeInfo {
                name: "MockExchange".to_string(),
                tick_size: 0.01,
                lot_size: 0.001,
                min_order_size: 0.001,
                max_order_size: 1000.0,
                min_price: 0.01,
                max_price: 1000000.0,
                trading_hours: vec![
                    TradingHours {
                        day_of_week: 1, // Monday
                        open_time: "00:00:00".to_string(),
                        close_time: "23:59:59".to_string(),
                        timezone: "UTC".to_string(),
                    }
                ],
                supported_order_types: vec![
                    "market".to_string(),
                    "limit".to_string(),
                    "stop_loss".to_string(),
                    "take_profit".to_string(),
                ],
            },
            should_fail: false,
            delay_ms: 100,
            partial_fill_ratio: 0.0,
        }
    }

    pub fn with_failure(mut self, should_fail: bool) -> Self {
        self.should_fail = should_fail;
        self
    }

    pub fn with_delay(mut self, delay_ms: u64) -> Self {
        self.delay_ms = delay_ms;
        self
    }

    pub fn with_partial_fills(mut self, ratio: f64) -> Self {
        self.partial_fill_ratio = ratio.clamp(0.0, 1.0);
        self
    }
}

impl Default for MockExchangeAdapter {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ExchangeAdapter for MockExchangeAdapter {
    async fn get_exchange_info(&self, _symbol: &str) -> Result<ExchangeInfo, TradingError> {
        if self.should_fail {
            return Err(TradingError::ExecutionError {
                message: "Mock exchange info failure".to_string(),
            });
        }
        
        tokio::time::sleep(std::time::Duration::from_millis(self.delay_ms)).await;
        Ok(self.exchange_info.clone())
    }

    async fn place_order(&self, order: OrderRequest) -> Result<AdapterOrderResult, TradingError> {
        if self.should_fail {
            return Err(TradingError::ExecutionError {
                message: "Mock order placement failure".to_string(),
            });
        }

        // Simulate network delay
        tokio::time::sleep(std::time::Duration::from_millis(self.delay_ms)).await;

        // Validate order
        self.validate_order(&order).await?;

        let mut result = AdapterOrderResult {
            order_id: order.id.to_string(),
            status: OrderStatus::Filled,
            filled_quantity: order.size,
            average_price: order.price,
            commission: order.size * order.price.unwrap_or(0.0) * 0.001, // 0.1% commission
            filled_at: Some(Utc::now()),
            partial_fills: Vec::new(),
        };

        // Simulate partial fills if configured
        if self.partial_fill_ratio > 0.0 {
            let partial_quantity = order.size * self.partial_fill_ratio;
            let remaining_quantity = order.size - partial_quantity;

            if partial_quantity > 0.0 {
                result.status = OrderStatus::PartiallyFilled;
                result.filled_quantity = partial_quantity;
                
                let mut partial_fill = HashMap::new();
                partial_fill.insert("fill_id".to_string(), serde_json::Value::String(uuid::Uuid::new_v4().to_string()));
                partial_fill.insert("quantity".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(partial_quantity).unwrap()));
                partial_fill.insert("price".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(order.price.unwrap_or(0.0)).unwrap()));
                partial_fill.insert("commission".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(partial_quantity * order.price.unwrap_or(0.0) * 0.001).unwrap()));
                
                result.partial_fills.push(partial_fill);
            }
        }

        Ok(result)
    }

    async fn cancel_order(&self, _order_id: &str) -> Result<(), TradingError> {
        if self.should_fail {
            return Err(TradingError::ExecutionError {
                message: "Mock order cancellation failure".to_string(),
            });
        }

        tokio::time::sleep(std::time::Duration::from_millis(self.delay_ms)).await;
        Ok(())
    }

    async fn get_order_status(&self, _order_id: &str) -> Result<OrderStatus, TradingError> {
        if self.should_fail {
            return Err(TradingError::ExecutionError {
                message: "Mock order status failure".to_string(),
            });
        }

        tokio::time::sleep(std::time::Duration::from_millis(self.delay_ms)).await;
        Ok(OrderStatus::Filled)
    }

    async fn amend_order(&self, _order_id: &str, _new_price: Option<f64>, _new_quantity: Option<f64>) -> Result<(), TradingError> {
        if self.should_fail {
            return Err(TradingError::ExecutionError {
                message: "Mock order amendment failure".to_string(),
            });
        }

        tokio::time::sleep(std::time::Duration::from_millis(self.delay_ms)).await;
        Ok(())
    }

    async fn get_account_info(&self) -> Result<AccountInfo, TradingError> {
        if self.should_fail {
            return Err(TradingError::ExecutionError {
                message: "Mock account info failure".to_string(),
            });
        }

        tokio::time::sleep(std::time::Duration::from_millis(self.delay_ms)).await;
        
        Ok(AccountInfo {
            account_id: "mock_account".to_string(),
            total_balance: 100000.0,
            available_balance: 90000.0,
            margin_used: 10000.0,
            margin_available: 90000.0,
            positions: Vec::new(),
        })
    }

    async fn validate_order(&self, order: &OrderRequest) -> Result<(), TradingError> {
        // Validate order size
        if order.size < self.exchange_info.min_order_size {
            return Err(TradingError::ExecutionError {
                message: format!("Order size {} below minimum {}", order.size, self.exchange_info.min_order_size),
            });
        }

        if order.size > self.exchange_info.max_order_size {
            return Err(TradingError::ExecutionError {
                message: format!("Order size {} above maximum {}", order.size, self.exchange_info.max_order_size),
            });
        }

        // Validate price if provided
        if let Some(price) = order.price {
            if price < self.exchange_info.min_price {
                return Err(TradingError::ExecutionError {
                    message: format!("Order price {} below minimum {}", price, self.exchange_info.min_price),
                });
            }

            if price > self.exchange_info.max_price {
                return Err(TradingError::ExecutionError {
                    message: format!("Order price {} above maximum {}", price, self.exchange_info.max_price),
                });
            }
        }

        Ok(())
    }

    fn round_price(&self, price: f64, tick_size: f64) -> f64 {
        if tick_size <= 0.0 {
            return price;
        }
        (price / tick_size).round() * tick_size
    }

    fn round_quantity(&self, quantity: f64, lot_size: f64) -> f64 {
        if lot_size <= 0.0 {
            return quantity;
        }
        (quantity / lot_size).floor() * lot_size
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rust_common::{OrderSide, OrderType};
    use uuid::Uuid;

    #[tokio::test]
    async fn test_mock_adapter_successful_order() {
        let adapter = MockExchangeAdapter::new();
        
        let order = OrderRequest {
            id: Uuid::new_v4(),
            symbol: "BTCUSD".to_string(),
            side: OrderSide::Buy,
            size: 0.1,
            price: Some(50000.0),
            order_type: OrderType::Limit,
            timestamp: Utc::now(),
        };

        let result = adapter.place_order(order).await;
        assert!(result.is_ok());
        
        let order_result = result.unwrap();
        assert_eq!(order_result.status, OrderStatus::Filled);
        assert_eq!(order_result.filled_quantity, 0.1);
    }

    #[tokio::test]
    async fn test_mock_adapter_failure() {
        let adapter = MockExchangeAdapter::new().with_failure(true);
        
        let order = OrderRequest {
            id: Uuid::new_v4(),
            symbol: "BTCUSD".to_string(),
            side: OrderSide::Buy,
            size: 0.1,
            price: Some(50000.0),
            order_type: OrderType::Limit,
            timestamp: Utc::now(),
        };

        let result = adapter.place_order(order).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_mock_adapter_partial_fills() {
        let adapter = MockExchangeAdapter::new().with_partial_fills(0.5);
        
        let order = OrderRequest {
            id: Uuid::new_v4(),
            symbol: "BTCUSD".to_string(),
            side: OrderSide::Buy,
            size: 1.0,
            price: Some(50000.0),
            order_type: OrderType::Limit,
            timestamp: Utc::now(),
        };

        let result = adapter.place_order(order).await;
        assert!(result.is_ok());
        
        let order_result = result.unwrap();
        assert_eq!(order_result.status, OrderStatus::PartiallyFilled);
        assert_eq!(order_result.filled_quantity, 0.5);
        assert_eq!(order_result.partial_fills.len(), 1);
    }

    #[test]
    fn test_price_rounding() {
        let adapter = MockExchangeAdapter::new();
        
        assert_eq!(adapter.round_price(50000.123, 0.01), 50000.12);
        assert_eq!(adapter.round_price(50000.126, 0.01), 50000.13);
        assert_eq!(adapter.round_price(50000.125, 0.01), 50000.12); // Banker's rounding
    }

    #[test]
    fn test_quantity_rounding() {
        let adapter = MockExchangeAdapter::new();
        
        assert_eq!(adapter.round_quantity(0.1234, 0.001), 0.123);
        assert_eq!(adapter.round_quantity(0.1239, 0.001), 0.123);
        assert_eq!(adapter.round_quantity(1.5, 0.1), 1.5);
    }

    #[tokio::test]
    async fn test_order_validation() {
        let adapter = MockExchangeAdapter::new();
        
        // Valid order
        let valid_order = OrderRequest {
            id: Uuid::new_v4(),
            symbol: "BTCUSD".to_string(),
            side: OrderSide::Buy,
            size: 0.1,
            price: Some(50000.0),
            order_type: OrderType::Limit,
            timestamp: Utc::now(),
        };
        
        assert!(adapter.validate_order(&valid_order).await.is_ok());
        
        // Order too small
        let small_order = OrderRequest {
            id: Uuid::new_v4(),
            symbol: "BTCUSD".to_string(),
            side: OrderSide::Buy,
            size: 0.0001, // Below min_order_size of 0.001
            price: Some(50000.0),
            order_type: OrderType::Limit,
            timestamp: Utc::now(),
        };
        
        assert!(adapter.validate_order(&small_order).await.is_err());
    }
}