use std::sync::Arc;
use tracing::info;
use execution_gateway::{ExecutionGateway, GatewayConfig, MockExchangeAdapter, create_router};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Load .env file for native deployment support
    // Tries .env.local first, then .env, then .env.native
    for env_file in [".env.local", ".env", ".env.native"] {
        if std::path::Path::new(env_file).exists() {
            dotenvy::from_filename(env_file).ok();
            info!("Loaded environment from {}", env_file);
            break;
        }
    }
    
    tracing_subscriber::fmt::init();
    
    info!("Starting Execution Gateway");
    
    let config = GatewayConfig::default();
    let gateway = Arc::new(ExecutionGateway::new(config));
    
    // Register a mock exchange adapter for testing
    let mock_adapter = MockExchangeAdapter::new();
    gateway.register_exchange_adapter("default".to_string(), Box::new(mock_adapter)).await;
    
    info!("Execution Gateway initialized with mock exchange adapter");
    
    // Create and start HTTP server
    let app = create_router(gateway.clone());
    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await?;
    
    info!("Starting HTTP server on http://0.0.0.0:8080");
    info!("API endpoints:");
    info!("  GET  /health - Health check");
    info!("  POST /v1/orders - Place order (idempotent)");
    info!("  GET  /v1/orders/:id/status - Get order status");
    info!("  DELETE /v1/orders/:id - Cancel order");
    
    // Start cleanup task
    let gateway_cleanup = gateway.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_secs(3600)); // 1 hour
        loop {
            interval.tick().await;
            let cleaned = gateway_cleanup.cleanup_completed_orders(24).await;
            if cleaned > 0 {
                info!("Cleaned up {} completed orders", cleaned);
            }
        }
    });
    
    // Start the server
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;
    
    info!("Execution Gateway shut down");
    Ok(())
}

async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c()
            .await
            .expect("failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("failed to install signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }

    info!("Shutdown signal received");
}