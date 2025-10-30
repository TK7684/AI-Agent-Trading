use thiserror::Error;

#[derive(Error, Debug)]
pub enum TradingError {
    #[error("Order execution failed: {message}")]
    ExecutionError { message: String },
    
    #[error("Risk limit violated: {limit}")]
    RiskLimitError { limit: String },
    
    #[error("Data error: {source}")]
    DataError { source: String },
    
    #[error("Network error: {0}")]
    NetworkError(#[from] reqwest::Error),
    
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
}