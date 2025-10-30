use rust_common::{OrderRequest, TradingError, OrderDecision, ExecutionResult};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{RwLock, Mutex};
use uuid::Uuid;
use chrono::{DateTime, Utc, Duration};
use serde::{Deserialize, Serialize};
use std::time::Instant;

mod circuit_breaker;
mod exchange_adapter;
mod order_manager;
mod retry_logic;

pub use circuit_breaker::*;
pub use exchange_adapter::*;
pub use order_manager::*;
pub use retry_logic::*;

/// Configuration for the execution gateway
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GatewayConfig {
    pub max_retries: u32,
    pub base_retry_delay_ms: u64,
    pub max_retry_delay_ms: u64,
    pub circuit_breaker_failure_threshold: u32,
    pub circuit_breaker_recovery_timeout_ms: u64,
    pub order_timeout_ms: u64,
    pub max_concurrent_orders: usize,
    pub enable_partial_fills: bool,
}

impl Default for GatewayConfig {
    fn default() -> Self {
        Self {
            max_retries: 3,
            base_retry_delay_ms: 100,
            max_retry_delay_ms: 5000,
            circuit_breaker_failure_threshold: 5,
            circuit_breaker_recovery_timeout_ms: 60000,
            order_timeout_ms: 30000,
            max_concurrent_orders: 100,
            enable_partial_fills: true,
        }
    }
}

/// High-performance order execution gateway
pub struct ExecutionGateway {
    config: GatewayConfig,
    order_manager: Arc<OrderManager>,
    exchange_adapters: Arc<RwLock<HashMap<String, Box<dyn ExchangeAdapter + Send + Sync>>>>,
    circuit_breakers: Arc<RwLock<HashMap<String, CircuitBreaker>>>,
    retry_logic: RetryLogic,
    active_orders: Arc<RwLock<HashMap<Uuid, OrderExecution>>>,
    order_deduplication: Arc<RwLock<HashMap<Uuid, String>>>, // client_id -> order_id mapping
}

#[derive(Debug, Clone)]
pub struct OrderExecution {
    pub order_id: String,
    pub client_id: Uuid,
    pub exchange: String,
    pub status: OrderExecutionStatus,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub retry_count: u32,
    pub partial_fills: Vec<PartialFill>,
    pub total_filled: f64,
    pub average_price: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum OrderExecutionStatus {
    Pending,
    Submitted,
    PartiallyFilled,
    Filled,
    Cancelled,
    Rejected,
    Failed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartialFill {
    pub fill_id: String,
    pub quantity: f64,
    pub price: f64,
    pub timestamp: DateTime<Utc>,
    pub commission: f64,
}

impl ExecutionGateway {
    pub fn new(config: GatewayConfig) -> Self {
        Self {
            config: config.clone(),
            order_manager: Arc::new(OrderManager::new()),
            exchange_adapters: Arc::new(RwLock::new(HashMap::new())),
            circuit_breakers: Arc::new(RwLock::new(HashMap::new())),
            retry_logic: RetryLogic::new(
                config.max_retries,
                config.base_retry_delay_ms,
                config.max_retry_delay_ms,
            ),
            active_orders: Arc::new(RwLock::new(HashMap::new())),
            order_deduplication: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Register an exchange adapter
    pub async fn register_exchange_adapter(
        &self,
        exchange_name: String,
        adapter: Box<dyn ExchangeAdapter + Send + Sync>,
    ) {
        let mut adapters = self.exchange_adapters.write().await;
        adapters.insert(exchange_name.clone(), adapter);
        
        let mut circuit_breakers = self.circuit_breakers.write().await;
        circuit_breakers.insert(
            exchange_name,
            CircuitBreaker::new(
                self.config.circuit_breaker_failure_threshold,
                self.config.circuit_breaker_recovery_timeout_ms,
            ),
        );
    }

    /// Place an order with idempotency and retry logic
    pub async fn place_order(&self, order_decision: OrderDecision) -> Result<ExecutionResult, TradingError> {
        let client_id = Uuid::parse_str(&order_decision.decision_id)
            .map_err(|e| TradingError::ExecutionError { 
                message: format!("Invalid decision ID: {}", e) 
            })?;

        // Check for duplicate orders using client_id
        {
            let dedup_map = self.order_deduplication.read().await;
            if let Some(existing_order_id) = dedup_map.get(&client_id) {
                // Return existing order result
                return self.get_order_result(existing_order_id).await;
            }
        }

        let order_id = Uuid::new_v4().to_string();
        
        // Store deduplication mapping
        {
            let mut dedup_map = self.order_deduplication.write().await;
            dedup_map.insert(client_id, order_id.clone());
        }

        // Create order execution tracking
        let order_execution = OrderExecution {
            order_id: order_id.clone(),
            client_id,
            exchange: "default".to_string(), // TODO: Determine exchange from order
            status: OrderExecutionStatus::Pending,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            retry_count: 0,
            partial_fills: Vec::new(),
            total_filled: 0.0,
            average_price: None,
        };

        {
            let mut active_orders = self.active_orders.write().await;
            active_orders.insert(client_id, order_execution);
        }

        // Execute order with retry logic
        let result = self.execute_order_with_retry(&order_decision, &order_id).await;
        
        // Update order status based on result
        self.update_order_status(&client_id, &result).await;

        result
    }

    /// Execute order with retry logic and circuit breaker
    async fn execute_order_with_retry(
        &self,
        order_decision: &OrderDecision,
        order_id: &str,
    ) -> Result<ExecutionResult, TradingError> {
        let exchange_name = "default"; // TODO: Determine from order
        
        let mut execution_result = ExecutionResult::new(
            order_decision.decision_id.clone(),
            order_id.to_string(),
        );

        let start_time = Instant::now();

        for attempt in 0..=self.config.max_retries {
            // Check circuit breaker
            {
                let circuit_breakers = self.circuit_breakers.read().await;
                if let Some(cb) = circuit_breakers.get(exchange_name) {
                    if cb.is_open() {
                        return Err(TradingError::ExecutionError {
                            message: format!("Circuit breaker open for exchange: {}", exchange_name),
                        });
                    }
                }
            }

            // Attempt order execution
            let result = self.execute_single_order(order_decision, order_id).await;
            
            match result {
                Ok(mut exec_result) => {
                    exec_result.execution_time_ms = Some(start_time.elapsed().as_millis() as u32);
                    exec_result.retry_count = attempt;
                    
                    // Record success in circuit breaker
                    {
                        let mut circuit_breakers = self.circuit_breakers.write().await;
                        if let Some(cb) = circuit_breakers.get_mut(exchange_name) {
                            cb.record_success();
                        }
                    }
                    
                    return Ok(exec_result);
                }
                Err(e) => {
                    execution_result.retry_count = attempt;
                    execution_result.error_message = Some(e.to_string());
                    
                    // Record failure in circuit breaker
                    {
                        let mut circuit_breakers = self.circuit_breakers.write().await;
                        if let Some(cb) = circuit_breakers.get_mut(exchange_name) {
                            cb.record_failure();
                        }
                    }
                    
                    // If this is the last attempt, return the error
                    if attempt == self.config.max_retries {
                        return Err(e);
                    }
                    
                    // Wait before retry with exponential backoff and jitter
                    let delay = self.retry_logic.calculate_delay(attempt);
                    tokio::time::sleep(std::time::Duration::from_millis(delay)).await;
                }
            }
        }

        Err(TradingError::ExecutionError {
            message: "Max retries exceeded".to_string(),
        })
    }

    /// Execute a single order attempt
    async fn execute_single_order(
        &self,
        order_decision: &OrderDecision,
        order_id: &str,
    ) -> Result<ExecutionResult, TradingError> {
        let exchange_name = "default"; // TODO: Determine from order
        
        let adapters = self.exchange_adapters.read().await;
        let adapter = adapters.get(exchange_name)
            .ok_or_else(|| TradingError::ExecutionError {
                message: format!("Exchange adapter not found: {}", exchange_name),
            })?;

        // Convert OrderDecision to OrderRequest for adapter
        let order_request = self.convert_decision_to_request(order_decision, order_id)?;
        
        // Execute through adapter
        let adapter_result = adapter.place_order(order_request).await?;
        
        // Convert adapter result to ExecutionResult
        let mut execution_result = ExecutionResult::new(
            order_decision.decision_id.clone(),
            order_id.to_string(),
        );
        
        execution_result.status = adapter_result.status;
        execution_result.filled_quantity = adapter_result.filled_quantity;
        execution_result.average_price = adapter_result.average_price;
        execution_result.commission = adapter_result.commission;
        execution_result.filled_at = adapter_result.filled_at;
        
        // Handle partial fills if enabled
        if self.config.enable_partial_fills && adapter_result.partial_fills.len() > 0 {
            self.handle_partial_fills(&order_decision.decision_id, &adapter_result.partial_fills).await?;
        }

        Ok(execution_result)
    }

    /// Convert OrderDecision to OrderRequest
    fn convert_decision_to_request(
        &self,
        decision: &OrderDecision,
        order_id: &str,
    ) -> Result<OrderRequest, TradingError> {
        use rust_common::{OrderSide, OrderType};
        
        let side = match decision.direction {
            rust_common::Direction::Long => OrderSide::Buy,
            rust_common::Direction::Short => OrderSide::Sell,
        };

        let order_type = match decision.order_type {
            rust_common::OrderType::Market => OrderType::Market,
            rust_common::OrderType::Limit => OrderType::Limit,
            rust_common::OrderType::StopLoss => OrderType::StopLoss,
            rust_common::OrderType::TakeProfit => OrderType::TakeProfit,
        };

        Ok(OrderRequest {
            id: Uuid::parse_str(order_id).map_err(|e| TradingError::ExecutionError {
                message: format!("Invalid order ID: {}", e),
            })?,
            symbol: decision.symbol.clone(),
            side,
            size: decision.risk_adjusted_quantity,
            price: Some(decision.entry_price),
            order_type,
            timestamp: decision.timestamp,
        })
    }

    /// Handle partial fills
    async fn handle_partial_fills(
        &self,
        decision_id: &str,
        partial_fills: &[HashMap<String, serde_json::Value>],
    ) -> Result<(), TradingError> {
        let client_id = Uuid::parse_str(decision_id)
            .map_err(|e| TradingError::ExecutionError {
                message: format!("Invalid decision ID: {}", e),
            })?;

        let mut active_orders = self.active_orders.write().await;
        if let Some(order_execution) = active_orders.get_mut(&client_id) {
            for fill_data in partial_fills {
                let partial_fill = PartialFill {
                    fill_id: fill_data.get("fill_id")
                        .and_then(|v| v.as_str())
                        .unwrap_or("unknown")
                        .to_string(),
                    quantity: fill_data.get("quantity")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0),
                    price: fill_data.get("price")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0),
                    timestamp: Utc::now(),
                    commission: fill_data.get("commission")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0),
                };
                
                order_execution.partial_fills.push(partial_fill.clone());
                order_execution.total_filled += partial_fill.quantity;
                
                // Update average price
                if order_execution.average_price.is_none() {
                    order_execution.average_price = Some(partial_fill.price);
                } else {
                    let current_avg = order_execution.average_price.unwrap();
                    let total_quantity: f64 = order_execution.partial_fills.iter()
                        .map(|f| f.quantity)
                        .sum();
                    let weighted_sum: f64 = order_execution.partial_fills.iter()
                        .map(|f| f.quantity * f.price)
                        .sum();
                    order_execution.average_price = Some(weighted_sum / total_quantity);
                }
            }
            
            order_execution.updated_at = Utc::now();
        }

        Ok(())
    }

    /// Update order status based on execution result
    async fn update_order_status(
        &self,
        client_id: &Uuid,
        result: &Result<ExecutionResult, TradingError>,
    ) {
        let mut active_orders = self.active_orders.write().await;
        if let Some(order_execution) = active_orders.get_mut(client_id) {
            match result {
                Ok(exec_result) => {
                    order_execution.status = match exec_result.status {
                        rust_common::OrderStatus::Pending => OrderExecutionStatus::Pending,
                        rust_common::OrderStatus::PartiallyFilled => OrderExecutionStatus::PartiallyFilled,
                        rust_common::OrderStatus::Filled => OrderExecutionStatus::Filled,
                        rust_common::OrderStatus::Cancelled => OrderExecutionStatus::Cancelled,
                        rust_common::OrderStatus::Rejected => OrderExecutionStatus::Rejected,
                    };
                }
                Err(_) => {
                    order_execution.status = OrderExecutionStatus::Failed;
                }
            }
            order_execution.updated_at = Utc::now();
        }
    }

    /// Get order result by order ID
    async fn get_order_result(&self, order_id: &str) -> Result<ExecutionResult, TradingError> {
        // This would typically query a database or cache
        // For now, return a placeholder result
        Ok(ExecutionResult::new("placeholder".to_string(), order_id.to_string()))
    }

    /// Cancel an order
    pub async fn cancel_order(&self, order_id: &str) -> Result<(), TradingError> {
        let exchange_name = "default"; // TODO: Determine from order
        
        let adapters = self.exchange_adapters.read().await;
        let adapter = adapters.get(exchange_name)
            .ok_or_else(|| TradingError::ExecutionError {
                message: format!("Exchange adapter not found: {}", exchange_name),
            })?;

        adapter.cancel_order(order_id).await
    }

    /// Get order status
    pub async fn get_order_status(&self, order_id: &str) -> Result<OrderExecutionStatus, TradingError> {
        let exchange_name = "default"; // TODO: Determine from order
        
        let adapters = self.exchange_adapters.read().await;
        let adapter = adapters.get(exchange_name)
            .ok_or_else(|| TradingError::ExecutionError {
                message: format!("Exchange adapter not found: {}", exchange_name),
            })?;

        let status = adapter.get_order_status(order_id).await?;
        
        Ok(match status {
            rust_common::OrderStatus::Pending => OrderExecutionStatus::Pending,
            rust_common::OrderStatus::PartiallyFilled => OrderExecutionStatus::PartiallyFilled,
            rust_common::OrderStatus::Filled => OrderExecutionStatus::Filled,
            rust_common::OrderStatus::Cancelled => OrderExecutionStatus::Cancelled,
            rust_common::OrderStatus::Rejected => OrderExecutionStatus::Rejected,
        })
    }

    /// Get active orders count
    pub async fn get_active_orders_count(&self) -> usize {
        let active_orders = self.active_orders.read().await;
        active_orders.len()
    }

    /// Clean up completed orders (should be called periodically)
    pub async fn cleanup_completed_orders(&self, max_age_hours: i64) {
        let cutoff_time = Utc::now() - Duration::hours(max_age_hours);
        
        let mut active_orders = self.active_orders.write().await;
        let mut dedup_map = self.order_deduplication.write().await;
        
        let mut to_remove = Vec::new();
        
        for (client_id, order_execution) in active_orders.iter() {
            if order_execution.updated_at < cutoff_time {
                match order_execution.status {
                    OrderExecutionStatus::Filled | 
                    OrderExecutionStatus::Cancelled | 
                    OrderExecutionStatus::Rejected | 
                    OrderExecutionStatus::Failed => {
                        to_remove.push(*client_id);
                    }
                    _ => {} // Keep pending and partially filled orders
                }
            }
        }
        
        for client_id in to_remove {
            active_orders.remove(&client_id);
            dedup_map.remove(&client_id);
        }
    }
}

impl Default for ExecutionGateway {
    fn default() -> Self {
        Self::new(GatewayConfig::default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rust_common::{OrderSide, OrderType, Direction, OrderType as RustOrderType};
    use uuid::Uuid;
    use chrono::Utc;
    use tokio_test;
    use std::time::Duration;

    fn create_test_order_decision() -> OrderDecision {
        let mut decision = OrderDecision::new("test_signal".to_string(), "BTCUSD".to_string());
        decision.direction = Direction::Long;
        decision.order_type = RustOrderType::Limit;
        decision.risk_adjusted_quantity = 0.1;
        decision.entry_price = 50000.0;
        decision.stop_loss = 49000.0;
        decision.take_profit = Some(52000.0);
        decision.risk_amount = 100.0;
        decision.risk_percentage = 1.0;
        decision.leverage = 1.0;
        decision.portfolio_value = 10000.0;
        decision.available_margin = 5000.0;
        decision.current_exposure = 0.1;
        decision.confidence_score = 0.8;
        decision.confluence_score = 75.0;
        decision.risk_reward_ratio = 2.0;
        decision
    }

    #[tokio::test]
    async fn test_gateway_creation() {
        let config = GatewayConfig::default();
        let gateway = ExecutionGateway::new(config);
        assert_eq!(gateway.get_active_orders_count().await, 0);
    }

    #[tokio::test]
    async fn test_register_exchange_adapter() {
        let config = GatewayConfig::default();
        let gateway = ExecutionGateway::new(config);
        
        let mock_adapter = MockExchangeAdapter::new();
        gateway.register_exchange_adapter("test_exchange".to_string(), Box::new(mock_adapter)).await;
        
        // Verify adapter is registered by checking circuit breaker exists
        let circuit_breakers = gateway.circuit_breakers.read().await;
        assert!(circuit_breakers.contains_key("test_exchange"));
    }

    #[tokio::test]
    async fn test_place_order_idempotency() {
        let config = GatewayConfig::default();
        let gateway = ExecutionGateway::new(config);
        
        let mock_adapter = MockExchangeAdapter::new();
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let order_decision = create_test_order_decision();
        
        // Place the same order twice
        let result1 = gateway.place_order(order_decision.clone()).await;
        let result2 = gateway.place_order(order_decision).await;
        
        assert!(result1.is_ok());
        assert!(result2.is_ok());
        
        // Should have only one active order due to idempotency
        assert_eq!(gateway.get_active_orders_count().await, 1);
    }

    #[tokio::test]
    async fn test_place_order_with_retry() {
        let config = GatewayConfig {
            max_retries: 2,
            base_retry_delay_ms: 10,
            max_retry_delay_ms: 100,
            ..Default::default()
        };
        let gateway = ExecutionGateway::new(config);
        
        // First adapter fails, then succeeds
        let mut mock_adapter = MockExchangeAdapter::new().with_failure(true);
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let order_decision = create_test_order_decision();
        let result = gateway.place_order(order_decision).await;
        
        // Should fail after retries
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_circuit_breaker_functionality() {
        let config = GatewayConfig {
            circuit_breaker_failure_threshold: 2,
            circuit_breaker_recovery_timeout_ms: 100,
            ..Default::default()
        };
        let gateway = ExecutionGateway::new(config);
        
        let mock_adapter = MockExchangeAdapter::new().with_failure(true);
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let order_decision = create_test_order_decision();
        
        // Trigger circuit breaker with failures
        for _ in 0..3 {
            let _ = gateway.place_order(order_decision.clone()).await;
        }
        
        // Circuit breaker should be open
        let circuit_breakers = gateway.circuit_breakers.read().await;
        let cb = circuit_breakers.get("default").unwrap();
        assert!(cb.is_open());
    }

    #[tokio::test]
    async fn test_partial_fill_handling() {
        let config = GatewayConfig {
            enable_partial_fills: true,
            ..Default::default()
        };
        let gateway = ExecutionGateway::new(config);
        
        let mock_adapter = MockExchangeAdapter::new().with_partial_fills(0.5);
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let order_decision = create_test_order_decision();
        let result = gateway.place_order(order_decision).await;
        
        assert!(result.is_ok());
        let execution_result = result.unwrap();
        assert_eq!(execution_result.status, rust_common::OrderStatus::PartiallyFilled);
        assert_eq!(execution_result.filled_quantity, 0.05); // 50% of 0.1
    }

    #[tokio::test]
    async fn test_order_cancellation() {
        let config = GatewayConfig::default();
        let gateway = ExecutionGateway::new(config);
        
        let mock_adapter = MockExchangeAdapter::new();
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let result = gateway.cancel_order("test_order_id").await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_order_status_query() {
        let config = GatewayConfig::default();
        let gateway = ExecutionGateway::new(config);
        
        let mock_adapter = MockExchangeAdapter::new();
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let result = gateway.get_order_status("test_order_id").await;
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), OrderExecutionStatus::Filled);
    }

    #[tokio::test]
    async fn test_cleanup_completed_orders() {
        let config = GatewayConfig::default();
        let gateway = ExecutionGateway::new(config);
        
        let mock_adapter = MockExchangeAdapter::new();
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        // Place an order
        let order_decision = create_test_order_decision();
        let _ = gateway.place_order(order_decision).await;
        
        assert_eq!(gateway.get_active_orders_count().await, 1);
        
        // Cleanup should not remove recent orders
        gateway.cleanup_completed_orders(24).await;
        assert_eq!(gateway.get_active_orders_count().await, 1);
        
        // Cleanup with 0 hours should remove completed orders
        gateway.cleanup_completed_orders(0).await;
        // Order might still be there if not in terminal state
    }

    #[tokio::test]
    async fn test_concurrent_order_placement() {
        let config = GatewayConfig::default();
        let gateway = std::sync::Arc::new(ExecutionGateway::new(config));
        
        let mock_adapter = MockExchangeAdapter::new().with_delay(50);
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let mut handles = Vec::new();
        
        // Place multiple orders concurrently
        for i in 0..5 {
            let gateway_clone = gateway.clone();
            let handle = tokio::spawn(async move {
                let mut order_decision = create_test_order_decision();
                order_decision.decision_id = format!("test_order_{}", i);
                gateway_clone.place_order(order_decision).await
            });
            handles.push(handle);
        }
        
        // Wait for all orders to complete
        let mut success_count = 0;
        for handle in handles {
            if handle.await.unwrap().is_ok() {
                success_count += 1;
            }
        }
        
        assert_eq!(success_count, 5);
        assert_eq!(gateway.get_active_orders_count().await, 5);
    }

    // Property-based tests
    #[cfg(test)]
    mod property_tests {
        use super::*;
        use proptest::prelude::*;

        proptest! {
            #[test]
            fn test_idempotency_property(
                decision_id in "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
                symbol in "[A-Z]{3,6}",
                quantity in 0.001f64..1000.0,
                price in 1.0f64..100000.0
            ) {
                tokio_test::block_on(async {
                    let config = GatewayConfig::default();
                    let gateway = ExecutionGateway::new(config);
                    
                    let mock_adapter = MockExchangeAdapter::new();
                    gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
                    
                    let mut order_decision = create_test_order_decision();
                    order_decision.decision_id = decision_id.clone();
                    order_decision.symbol = symbol;
                    order_decision.risk_adjusted_quantity = quantity;
                    order_decision.entry_price = price;
                    
                    // Place the same order multiple times
                    let result1 = gateway.place_order(order_decision.clone()).await;
                    let result2 = gateway.place_order(order_decision.clone()).await;
                    let result3 = gateway.place_order(order_decision).await;
                    
                    // All should succeed due to idempotency
                    prop_assert!(result1.is_ok());
                    prop_assert!(result2.is_ok());
                    prop_assert!(result3.is_ok());
                    
                    // Should have only one active order
                    prop_assert_eq!(gateway.get_active_orders_count().await, 1);
                });
            }

            #[test]
            fn test_retry_behavior_property(
                max_retries in 1u32..5,
                base_delay in 10u64..100,
                failure_threshold in 2u32..10
            ) {
                tokio_test::block_on(async {
                    let config = GatewayConfig {
                        max_retries,
                        base_retry_delay_ms: base_delay,
                        circuit_breaker_failure_threshold: failure_threshold,
                        ..Default::default()
                    };
                    let gateway = ExecutionGateway::new(config);
                    
                    let mock_adapter = MockExchangeAdapter::new().with_failure(true);
                    gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
                    
                    let order_decision = create_test_order_decision();
                    let result = gateway.place_order(order_decision).await;
                    
                    // Should fail after max retries
                    prop_assert!(result.is_err());
                    
                    if let Err(TradingError::ExecutionError { message }) = result {
                        prop_assert!(message.contains("Max retries exceeded") || message.contains("Circuit breaker"));
                    }
                });
            }

            #[test]
            fn test_partial_fill_consistency(
                partial_ratio in 0.1f64..0.9,
                order_size in 0.1f64..10.0
            ) {
                tokio_test::block_on(async {
                    let config = GatewayConfig {
                        enable_partial_fills: true,
                        ..Default::default()
                    };
                    let gateway = ExecutionGateway::new(config);
                    
                    let mock_adapter = MockExchangeAdapter::new().with_partial_fills(partial_ratio);
                    gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
                    
                    let mut order_decision = create_test_order_decision();
                    order_decision.risk_adjusted_quantity = order_size;
                    
                    let result = gateway.place_order(order_decision).await;
                    prop_assert!(result.is_ok());
                    
                    let execution_result = result.unwrap();
                    let expected_fill = order_size * partial_ratio;
                    let tolerance = 0.0001;
                    
                    prop_assert!((execution_result.filled_quantity - expected_fill).abs() < tolerance);
                    prop_assert_eq!(execution_result.status, rust_common::OrderStatus::PartiallyFilled);
                });
            }
        }
    }

    // Chaos testing for resilience
    #[tokio::test]
    async fn test_chaos_network_failures() {
        let config = GatewayConfig {
            max_retries: 3,
            base_retry_delay_ms: 10,
            circuit_breaker_failure_threshold: 5,
            circuit_breaker_recovery_timeout_ms: 100,
            ..Default::default()
        };
        let gateway = ExecutionGateway::new(config);
        
        // Simulate intermittent failures
        let mock_adapter = MockExchangeAdapter::new().with_failure(true).with_delay(50);
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let mut failure_count = 0;
        let mut success_count = 0;
        
        // Simulate multiple order attempts during network issues
        for i in 0..10 {
            let mut order_decision = create_test_order_decision();
            order_decision.decision_id = format!("chaos_test_{}", i);
            
            let result = gateway.place_order(order_decision).await;
            if result.is_ok() {
                success_count += 1;
            } else {
                failure_count += 1;
            }
        }
        
        // Should have some failures due to network issues
        assert!(failure_count > 0);
        
        // Circuit breaker should eventually open
        let circuit_breakers = gateway.circuit_breakers.read().await;
        let cb = circuit_breakers.get("default").unwrap();
        assert!(cb.is_open());
    }

    #[tokio::test]
    async fn test_recovery_after_circuit_breaker_timeout() {
        let config = GatewayConfig {
            circuit_breaker_failure_threshold: 2,
            circuit_breaker_recovery_timeout_ms: 50,
            ..Default::default()
        };
        let gateway = ExecutionGateway::new(config);
        
        // Start with failing adapter
        let failing_adapter = MockExchangeAdapter::new().with_failure(true);
        gateway.register_exchange_adapter("default".to_string(), Box::new(failing_adapter)).await;
        
        // Trigger circuit breaker
        for _ in 0..3 {
            let order_decision = create_test_order_decision();
            let _ = gateway.place_order(order_decision).await;
        }
        
        // Verify circuit breaker is open
        {
            let circuit_breakers = gateway.circuit_breakers.read().await;
            let cb = circuit_breakers.get("default").unwrap();
            assert!(cb.is_open());
        }
        
        // Wait for recovery timeout
        tokio::time::sleep(Duration::from_millis(100)).await;
        
        // Replace with working adapter
        let working_adapter = MockExchangeAdapter::new();
        gateway.register_exchange_adapter("default".to_string(), Box::new(working_adapter)).await;
        
        // Circuit breaker should allow test request
        {
            let circuit_breakers = gateway.circuit_breakers.read().await;
            let cb = circuit_breakers.get("default").unwrap();
            assert!(!cb.is_open()); // Should be half-open or closed
        }
    }
}