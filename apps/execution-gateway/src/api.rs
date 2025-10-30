use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::Json,
    routing::{get, post, delete},
    Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tower::ServiceBuilder;
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use tracing::{info, error};

use crate::{ExecutionGateway, OrderExecutionStatus};
use rust_common::{OrderDecision, ExecutionResult, TradingError};

/// API request/response types
#[derive(Debug, Serialize, Deserialize)]
pub struct PlaceOrderRequest {
    pub order_decision: OrderDecision,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PlaceOrderResponse {
    pub execution_result: ExecutionResult,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct OrderStatusResponse {
    pub order_id: String,
    pub status: OrderExecutionStatus,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CancelOrderResponse {
    pub order_id: String,
    pub cancelled: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub active_orders: usize,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ErrorResponse {
    pub error: String,
    pub code: String,
}

/// Application state
pub type AppState = Arc<ExecutionGateway>;

/// Create the API router
pub fn create_router(gateway: Arc<ExecutionGateway>) -> Router {
    Router::new()
        .route("/health", get(health_check))
        .route("/v1/orders", post(place_order))
        .route("/v1/orders/:order_id", get(get_order_status))
        .route("/v1/orders/:order_id", delete(cancel_order))
        .route("/v1/orders/:order_id/status", get(get_order_status))
        .layer(
            ServiceBuilder::new()
                .layer(TraceLayer::new_for_http())
                .layer(CorsLayer::permissive())
        )
        .with_state(gateway)
}

/// Health check endpoint
async fn health_check(State(gateway): State<AppState>) -> Result<Json<HealthResponse>, StatusCode> {
    let active_orders = gateway.get_active_orders_count().await;
    
    let response = HealthResponse {
        status: "healthy".to_string(),
        active_orders,
        timestamp: chrono::Utc::now(),
    };
    
    Ok(Json(response))
}

/// Place order endpoint - implements idempotency
async fn place_order(
    State(gateway): State<AppState>,
    Json(request): Json<PlaceOrderRequest>,
) -> Result<Json<PlaceOrderResponse>, (StatusCode, Json<ErrorResponse>)> {
    info!("Received place order request for symbol: {}", request.order_decision.symbol);
    
    // Validate the order decision
    if let Err(validation_error) = request.order_decision.validate() {
        error!("Order validation failed: {}", validation_error);
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: validation_error,
                code: "VALIDATION_ERROR".to_string(),
            }),
        ));
    }
    
    match gateway.place_order(request.order_decision).await {
        Ok(execution_result) => {
            info!("Order placed successfully: {}", execution_result.order_id);
            Ok(Json(PlaceOrderResponse { execution_result }))
        }
        Err(e) => {
            error!("Failed to place order: {}", e);
            let (status_code, error_code) = match &e {
                TradingError::RiskLimitError { .. } => (StatusCode::FORBIDDEN, "RISK_LIMIT_ERROR"),
                TradingError::ExecutionError { .. } => (StatusCode::INTERNAL_SERVER_ERROR, "EXECUTION_ERROR"),
                TradingError::NetworkError(_) => (StatusCode::BAD_GATEWAY, "NETWORK_ERROR"),
                TradingError::DataError { .. } => (StatusCode::UNPROCESSABLE_ENTITY, "DATA_ERROR"),
                TradingError::SerializationError(_) => (StatusCode::BAD_REQUEST, "SERIALIZATION_ERROR"),
            };
            
            Err((
                status_code,
                Json(ErrorResponse {
                    error: e.to_string(),
                    code: error_code.to_string(),
                }),
            ))
        }
    }
}

/// Get order status endpoint
async fn get_order_status(
    State(gateway): State<AppState>,
    Path(order_id): Path<String>,
) -> Result<Json<OrderStatusResponse>, (StatusCode, Json<ErrorResponse>)> {
    info!("Getting status for order: {}", order_id);
    
    match gateway.get_order_status(&order_id).await {
        Ok(status) => {
            Ok(Json(OrderStatusResponse {
                order_id,
                status,
            }))
        }
        Err(e) => {
            error!("Failed to get order status: {}", e);
            Err((
                StatusCode::NOT_FOUND,
                Json(ErrorResponse {
                    error: e.to_string(),
                    code: "ORDER_NOT_FOUND".to_string(),
                }),
            ))
        }
    }
}

/// Cancel order endpoint
async fn cancel_order(
    State(gateway): State<AppState>,
    Path(order_id): Path<String>,
) -> Result<Json<CancelOrderResponse>, (StatusCode, Json<ErrorResponse>)> {
    info!("Cancelling order: {}", order_id);
    
    match gateway.cancel_order(&order_id).await {
        Ok(()) => {
            info!("Order cancelled successfully: {}", order_id);
            Ok(Json(CancelOrderResponse {
                order_id,
                cancelled: true,
            }))
        }
        Err(e) => {
            error!("Failed to cancel order: {}", e);
            let (status_code, error_code) = match &e {
                TradingError::ExecutionError { message } if message.contains("not found") => {
                    (StatusCode::NOT_FOUND, "ORDER_NOT_FOUND")
                }
                _ => (StatusCode::INTERNAL_SERVER_ERROR, "CANCELLATION_ERROR"),
            };
            
            Err((
                status_code,
                Json(ErrorResponse {
                    error: e.to_string(),
                    code: error_code.to_string(),
                }),
            ))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use tower::ServiceExt;
    use crate::{GatewayConfig, MockExchangeAdapter};
    use rust_common::{Direction, OrderType};

    fn create_test_gateway() -> Arc<ExecutionGateway> {
        let config = GatewayConfig::default();
        Arc::new(ExecutionGateway::new(config))
    }

    fn create_test_order_decision() -> OrderDecision {
        let mut decision = OrderDecision::new("test_signal".to_string(), "BTCUSD".to_string());
        decision.direction = Direction::Long;
        decision.order_type = OrderType::Limit;
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
    async fn test_health_check() {
        let gateway = create_test_gateway();
        let app = create_router(gateway);

        let request = Request::builder()
            .uri("/health")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_place_order_success() {
        let gateway = create_test_gateway();
        let mock_adapter = MockExchangeAdapter::new();
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let app = create_router(gateway);

        let order_decision = create_test_order_decision();
        let request_body = PlaceOrderRequest { order_decision };
        let body = serde_json::to_string(&request_body).unwrap();

        let request = Request::builder()
            .uri("/v1/orders")
            .method("POST")
            .header("content-type", "application/json")
            .body(Body::from(body))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_place_order_validation_error() {
        let gateway = create_test_gateway();
        let app = create_router(gateway);

        let mut order_decision = create_test_order_decision();
        order_decision.risk_adjusted_quantity = -1.0; // Invalid quantity
        
        let request_body = PlaceOrderRequest { order_decision };
        let body = serde_json::to_string(&request_body).unwrap();

        let request = Request::builder()
            .uri("/v1/orders")
            .method("POST")
            .header("content-type", "application/json")
            .body(Body::from(body))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_get_order_status() {
        let gateway = create_test_gateway();
        let mock_adapter = MockExchangeAdapter::new();
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let app = create_router(gateway);

        let request = Request::builder()
            .uri("/v1/orders/test_order_id/status")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_cancel_order() {
        let gateway = create_test_gateway();
        let mock_adapter = MockExchangeAdapter::new();
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let app = create_router(gateway);

        let request = Request::builder()
            .uri("/v1/orders/test_order_id")
            .method("DELETE")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_idempotent_order_placement() {
        let gateway = create_test_gateway();
        let mock_adapter = MockExchangeAdapter::new();
        gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
        
        let app = create_router(gateway.clone());

        let order_decision = create_test_order_decision();
        let request_body = PlaceOrderRequest { order_decision };
        let body = serde_json::to_string(&request_body).unwrap();

        // Place the same order twice
        for _ in 0..2 {
            let request = Request::builder()
                .uri("/v1/orders")
                .method("POST")
                .header("content-type", "application/json")
                .body(Body::from(body.clone()))
                .unwrap();

            let response = app.clone().oneshot(request).await.unwrap();
            assert_eq!(response.status(), StatusCode::OK);
        }

        // Should have only one active order due to idempotency
        assert_eq!(gateway.get_active_orders_count().await, 1);
    }
}