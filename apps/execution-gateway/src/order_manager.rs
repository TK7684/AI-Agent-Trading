use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;
use chrono::{DateTime, Utc, Duration};
use serde::{Deserialize, Serialize};
use rust_common::{TradingError, OrderStatus};

/// Order lifecycle states
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum OrderLifecycleState {
    Created,
    Validated,
    Submitted,
    Acknowledged,
    PartiallyFilled,
    Filled,
    Cancelled,
    Rejected,
    Expired,
    Failed,
}

/// Order lifecycle tracking
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderLifecycle {
    pub order_id: String,
    pub client_id: Uuid,
    pub symbol: String,
    pub state: OrderLifecycleState,
    pub state_history: Vec<StateTransition>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub expires_at: Option<DateTime<Utc>>,
    pub metadata: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateTransition {
    pub from_state: OrderLifecycleState,
    pub to_state: OrderLifecycleState,
    pub timestamp: DateTime<Utc>,
    pub reason: String,
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Order manager for tracking order lifecycle and state transitions
pub struct OrderManager {
    orders: Arc<RwLock<HashMap<String, OrderLifecycle>>>,
    client_id_mapping: Arc<RwLock<HashMap<Uuid, String>>>, // client_id -> order_id
}

impl OrderManager {
    pub fn new() -> Self {
        Self {
            orders: Arc::new(RwLock::new(HashMap::new())),
            client_id_mapping: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Create a new order lifecycle
    pub async fn create_order(
        &self,
        order_id: String,
        client_id: Uuid,
        symbol: String,
        expires_in_seconds: Option<u64>,
    ) -> Result<(), TradingError> {
        let expires_at = expires_in_seconds.map(|seconds| Utc::now() + Duration::seconds(seconds as i64));
        
        let lifecycle = OrderLifecycle {
            order_id: order_id.clone(),
            client_id,
            symbol,
            state: OrderLifecycleState::Created,
            state_history: Vec::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            expires_at,
            metadata: HashMap::new(),
        };

        let mut orders = self.orders.write().await;
        let mut client_mapping = self.client_id_mapping.write().await;
        
        orders.insert(order_id.clone(), lifecycle);
        client_mapping.insert(client_id, order_id);

        Ok(())
    }

    /// Transition order to new state
    pub async fn transition_state(
        &self,
        order_id: &str,
        new_state: OrderLifecycleState,
        reason: String,
        metadata: Option<HashMap<String, serde_json::Value>>,
    ) -> Result<(), TradingError> {
        let mut orders = self.orders.write().await;
        
        let lifecycle = orders.get_mut(order_id)
            .ok_or_else(|| TradingError::ExecutionError {
                message: format!("Order not found: {}", order_id),
            })?;

        // Validate state transition
        self.validate_state_transition(&lifecycle.state, &new_state)?;

        let transition = StateTransition {
            from_state: lifecycle.state.clone(),
            to_state: new_state.clone(),
            timestamp: Utc::now(),
            reason,
            metadata: metadata.unwrap_or_default(),
        };

        lifecycle.state_history.push(transition);
        lifecycle.state = new_state;
        lifecycle.updated_at = Utc::now();

        Ok(())
    }

    /// Get order lifecycle by order ID
    pub async fn get_order(&self, order_id: &str) -> Option<OrderLifecycle> {
        let orders = self.orders.read().await;
        orders.get(order_id).cloned()
    }

    /// Get order lifecycle by client ID
    pub async fn get_order_by_client_id(&self, client_id: &Uuid) -> Option<OrderLifecycle> {
        let client_mapping = self.client_id_mapping.read().await;
        if let Some(order_id) = client_mapping.get(client_id) {
            let orders = self.orders.read().await;
            orders.get(order_id).cloned()
        } else {
            None
        }
    }

    /// Check if order exists by client ID (for idempotency)
    pub async fn order_exists_by_client_id(&self, client_id: &Uuid) -> bool {
        let client_mapping = self.client_id_mapping.read().await;
        client_mapping.contains_key(client_id)
    }

    /// Get all orders in a specific state
    pub async fn get_orders_by_state(&self, state: OrderLifecycleState) -> Vec<OrderLifecycle> {
        let orders = self.orders.read().await;
        orders.values()
            .filter(|order| order.state == state)
            .cloned()
            .collect()
    }

    /// Get expired orders
    pub async fn get_expired_orders(&self) -> Vec<OrderLifecycle> {
        let now = Utc::now();
        let orders = self.orders.read().await;
        
        orders.values()
            .filter(|order| {
                if let Some(expires_at) = order.expires_at {
                    expires_at < now && !self.is_terminal_state(&order.state)
                } else {
                    false
                }
            })
            .cloned()
            .collect()
    }

    /// Update order metadata
    pub async fn update_metadata(
        &self,
        order_id: &str,
        key: String,
        value: serde_json::Value,
    ) -> Result<(), TradingError> {
        let mut orders = self.orders.write().await;
        
        let lifecycle = orders.get_mut(order_id)
            .ok_or_else(|| TradingError::ExecutionError {
                message: format!("Order not found: {}", order_id),
            })?;

        lifecycle.metadata.insert(key, value);
        lifecycle.updated_at = Utc::now();

        Ok(())
    }

    /// Clean up completed orders older than specified duration
    pub async fn cleanup_old_orders(&self, max_age_hours: i64) -> usize {
        let cutoff_time = Utc::now() - Duration::hours(max_age_hours);
        let mut orders = self.orders.write().await;
        let mut client_mapping = self.client_id_mapping.write().await;
        
        let mut to_remove = Vec::new();
        
        for (order_id, lifecycle) in orders.iter() {
            if lifecycle.updated_at < cutoff_time && self.is_terminal_state(&lifecycle.state) {
                to_remove.push((order_id.clone(), lifecycle.client_id));
            }
        }
        
        let removed_count = to_remove.len();
        
        for (order_id, client_id) in to_remove {
            orders.remove(&order_id);
            client_mapping.remove(&client_id);
        }
        
        removed_count
    }

    /// Get order statistics
    pub async fn get_statistics(&self) -> OrderStatistics {
        let orders = self.orders.read().await;
        
        let mut stats = OrderStatistics::default();
        stats.total_orders = orders.len();
        
        for lifecycle in orders.values() {
            match lifecycle.state {
                OrderLifecycleState::Created => stats.created += 1,
                OrderLifecycleState::Validated => stats.validated += 1,
                OrderLifecycleState::Submitted => stats.submitted += 1,
                OrderLifecycleState::Acknowledged => stats.acknowledged += 1,
                OrderLifecycleState::PartiallyFilled => stats.partially_filled += 1,
                OrderLifecycleState::Filled => stats.filled += 1,
                OrderLifecycleState::Cancelled => stats.cancelled += 1,
                OrderLifecycleState::Rejected => stats.rejected += 1,
                OrderLifecycleState::Expired => stats.expired += 1,
                OrderLifecycleState::Failed => stats.failed += 1,
            }
        }
        
        stats
    }

    /// Validate state transition
    fn validate_state_transition(
        &self,
        from_state: &OrderLifecycleState,
        to_state: &OrderLifecycleState,
    ) -> Result<(), TradingError> {
        use OrderLifecycleState::*;
        
        let valid_transitions = match from_state {
            Created => vec![Validated, Rejected, Failed],
            Validated => vec![Submitted, Rejected, Failed],
            Submitted => vec![Acknowledged, Rejected, Failed, Expired],
            Acknowledged => vec![PartiallyFilled, Filled, Cancelled, Rejected, Failed, Expired],
            PartiallyFilled => vec![Filled, Cancelled, Failed, Expired],
            Filled | Cancelled | Rejected | Expired | Failed => vec![], // Terminal states
        };

        if valid_transitions.contains(to_state) {
            Ok(())
        } else {
            Err(TradingError::ExecutionError {
                message: format!(
                    "Invalid state transition from {:?} to {:?}",
                    from_state, to_state
                ),
            })
        }
    }

    /// Check if state is terminal (no further transitions allowed)
    fn is_terminal_state(&self, state: &OrderLifecycleState) -> bool {
        matches!(
            state,
            OrderLifecycleState::Filled
                | OrderLifecycleState::Cancelled
                | OrderLifecycleState::Rejected
                | OrderLifecycleState::Expired
                | OrderLifecycleState::Failed
        )
    }
}

impl Default for OrderManager {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct OrderStatistics {
    pub total_orders: usize,
    pub created: usize,
    pub validated: usize,
    pub submitted: usize,
    pub acknowledged: usize,
    pub partially_filled: usize,
    pub filled: usize,
    pub cancelled: usize,
    pub rejected: usize,
    pub expired: usize,
    pub failed: usize,
}

/// Convert OrderStatus to OrderLifecycleState
impl From<OrderStatus> for OrderLifecycleState {
    fn from(status: OrderStatus) -> Self {
        match status {
            OrderStatus::Pending => OrderLifecycleState::Submitted,
            OrderStatus::PartiallyFilled => OrderLifecycleState::PartiallyFilled,
            OrderStatus::Filled => OrderLifecycleState::Filled,
            OrderStatus::Cancelled => OrderLifecycleState::Cancelled,
            OrderStatus::Rejected => OrderLifecycleState::Rejected,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_order_manager_creation() {
        let manager = OrderManager::new();
        let stats = manager.get_statistics().await;
        assert_eq!(stats.total_orders, 0);
    }

    #[tokio::test]
    async fn test_create_order() {
        let manager = OrderManager::new();
        let order_id = "test_order_1".to_string();
        let client_id = Uuid::new_v4();
        
        let result = manager.create_order(
            order_id.clone(),
            client_id,
            "BTCUSD".to_string(),
            Some(3600), // 1 hour expiry
        ).await;
        
        assert!(result.is_ok());
        
        let order = manager.get_order(&order_id).await;
        assert!(order.is_some());
        
        let order = order.unwrap();
        assert_eq!(order.state, OrderLifecycleState::Created);
        assert_eq!(order.symbol, "BTCUSD");
        assert!(order.expires_at.is_some());
    }

    #[tokio::test]
    async fn test_state_transition() {
        let manager = OrderManager::new();
        let order_id = "test_order_2".to_string();
        let client_id = Uuid::new_v4();
        
        manager.create_order(order_id.clone(), client_id, "BTCUSD".to_string(), None).await.unwrap();
        
        let result = manager.transition_state(
            &order_id,
            OrderLifecycleState::Validated,
            "Order validated successfully".to_string(),
            None,
        ).await;
        
        assert!(result.is_ok());
        
        let order = manager.get_order(&order_id).await.unwrap();
        assert_eq!(order.state, OrderLifecycleState::Validated);
        assert_eq!(order.state_history.len(), 1);
        assert_eq!(order.state_history[0].from_state, OrderLifecycleState::Created);
        assert_eq!(order.state_history[0].to_state, OrderLifecycleState::Validated);
    }

    #[tokio::test]
    async fn test_invalid_state_transition() {
        let manager = OrderManager::new();
        let order_id = "test_order_3".to_string();
        let client_id = Uuid::new_v4();
        
        manager.create_order(order_id.clone(), client_id, "BTCUSD".to_string(), None).await.unwrap();
        
        // Try to transition directly from Created to Filled (invalid)
        let result = manager.transition_state(
            &order_id,
            OrderLifecycleState::Filled,
            "Invalid transition".to_string(),
            None,
        ).await;
        
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_order_exists_by_client_id() {
        let manager = OrderManager::new();
        let order_id = "test_order_4".to_string();
        let client_id = Uuid::new_v4();
        
        assert!(!manager.order_exists_by_client_id(&client_id).await);
        
        manager.create_order(order_id, client_id, "BTCUSD".to_string(), None).await.unwrap();
        
        assert!(manager.order_exists_by_client_id(&client_id).await);
    }

    #[tokio::test]
    async fn test_get_order_by_client_id() {
        let manager = OrderManager::new();
        let order_id = "test_order_5".to_string();
        let client_id = Uuid::new_v4();
        
        manager.create_order(order_id.clone(), client_id, "BTCUSD".to_string(), None).await.unwrap();
        
        let order = manager.get_order_by_client_id(&client_id).await;
        assert!(order.is_some());
        assert_eq!(order.unwrap().order_id, order_id);
    }

    #[tokio::test]
    async fn test_get_orders_by_state() {
        let manager = OrderManager::new();
        
        // Create multiple orders in different states
        for i in 0..3 {
            let order_id = format!("test_order_{}", i);
            let client_id = Uuid::new_v4();
            manager.create_order(order_id.clone(), client_id, "BTCUSD".to_string(), None).await.unwrap();
            
            if i > 0 {
                manager.transition_state(
                    &order_id,
                    OrderLifecycleState::Validated,
                    "Validated".to_string(),
                    None,
                ).await.unwrap();
            }
        }
        
        let created_orders = manager.get_orders_by_state(OrderLifecycleState::Created).await;
        let validated_orders = manager.get_orders_by_state(OrderLifecycleState::Validated).await;
        
        assert_eq!(created_orders.len(), 1);
        assert_eq!(validated_orders.len(), 2);
    }

    #[tokio::test]
    async fn test_update_metadata() {
        let manager = OrderManager::new();
        let order_id = "test_order_6".to_string();
        let client_id = Uuid::new_v4();
        
        manager.create_order(order_id.clone(), client_id, "BTCUSD".to_string(), None).await.unwrap();
        
        let result = manager.update_metadata(
            &order_id,
            "exchange".to_string(),
            serde_json::Value::String("binance".to_string()),
        ).await;
        
        assert!(result.is_ok());
        
        let order = manager.get_order(&order_id).await.unwrap();
        assert_eq!(
            order.metadata.get("exchange"),
            Some(&serde_json::Value::String("binance".to_string()))
        );
    }

    #[tokio::test]
    async fn test_expired_orders() {
        let manager = OrderManager::new();
        let order_id = "test_order_7".to_string();
        let client_id = Uuid::new_v4();
        
        // Create order that expires in 1 second
        manager.create_order(order_id, client_id, "BTCUSD".to_string(), Some(1)).await.unwrap();
        
        // Wait for expiry
        tokio::time::sleep(std::time::Duration::from_secs(2)).await;
        
        let expired_orders = manager.get_expired_orders().await;
        assert_eq!(expired_orders.len(), 1);
    }
}