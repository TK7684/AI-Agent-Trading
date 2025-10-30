use rand::Rng;

/// Retry logic with exponential backoff and jitter
pub struct RetryLogic {
    max_retries: u32,
    base_delay_ms: u64,
    max_delay_ms: u64,
}

impl RetryLogic {
    pub fn new(max_retries: u32, base_delay_ms: u64, max_delay_ms: u64) -> Self {
        Self {
            max_retries,
            base_delay_ms,
            max_delay_ms,
        }
    }

    /// Calculate delay for retry attempt with exponential backoff and jitter
    pub fn calculate_delay(&self, attempt: u32) -> u64 {
        if attempt == 0 {
            return 0;
        }

        // Exponential backoff: base_delay * 2^(attempt-1)
        let exponential_delay = self.base_delay_ms * (2_u64.pow(attempt.saturating_sub(1)));
        
        // Cap at max delay
        let capped_delay = exponential_delay.min(self.max_delay_ms);
        
        // Add jitter (±25% of the delay)
        let jitter_range = capped_delay / 4; // 25% of delay
        let mut rng = rand::thread_rng();
        let jitter = rng.gen_range(0..=jitter_range * 2); // 0 to 50% of delay
        
        // Apply jitter (subtract half the range to center around original delay)
        if capped_delay >= jitter_range {
            capped_delay - jitter_range + jitter
        } else {
            capped_delay + jitter
        }
    }

    /// Check if should retry based on attempt count
    pub fn should_retry(&self, attempt: u32) -> bool {
        attempt < self.max_retries
    }

    /// Get maximum retry attempts
    pub fn max_retries(&self) -> u32 {
        self.max_retries
    }

    /// Calculate total maximum time for all retries
    pub fn calculate_max_total_time(&self) -> u64 {
        let mut total_time = 0;
        for attempt in 1..=self.max_retries {
            total_time += self.calculate_delay(attempt);
        }
        total_time
    }
}

/// Retry policy for different types of errors
#[derive(Debug, Clone, Copy)]
pub enum RetryPolicy {
    /// Retry immediately without delay
    Immediate,
    /// Use exponential backoff
    ExponentialBackoff,
    /// Don't retry
    NoRetry,
}

/// Determine retry policy based on error type
pub fn determine_retry_policy(error: &rust_common::TradingError) -> RetryPolicy {
    match error {
        rust_common::TradingError::NetworkError(_) => RetryPolicy::ExponentialBackoff,
        rust_common::TradingError::ExecutionError { message } => {
            // Check if it's a temporary error
            if message.contains("timeout") || 
               message.contains("rate limit") || 
               message.contains("temporary") ||
               message.contains("service unavailable") {
                RetryPolicy::ExponentialBackoff
            } else if message.contains("insufficient funds") ||
                     message.contains("invalid order") ||
                     message.contains("market closed") {
                RetryPolicy::NoRetry
            } else {
                RetryPolicy::ExponentialBackoff
            }
        }
        rust_common::TradingError::RiskLimitError { .. } => RetryPolicy::NoRetry,
        rust_common::TradingError::DataError { .. } => RetryPolicy::ExponentialBackoff,
        rust_common::TradingError::SerializationError(_) => RetryPolicy::NoRetry,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_retry_logic_creation() {
        let retry_logic = RetryLogic::new(3, 100, 5000);
        assert_eq!(retry_logic.max_retries(), 3);
    }

    #[test]
    fn test_should_retry() {
        let retry_logic = RetryLogic::new(3, 100, 5000);
        
        assert!(retry_logic.should_retry(0));
        assert!(retry_logic.should_retry(1));
        assert!(retry_logic.should_retry(2));
        assert!(!retry_logic.should_retry(3));
        assert!(!retry_logic.should_retry(4));
    }

    #[test]
    fn test_calculate_delay_exponential_backoff() {
        let retry_logic = RetryLogic::new(5, 100, 5000);
        
        // First attempt should have no delay
        assert_eq!(retry_logic.calculate_delay(0), 0);
        
        // Subsequent attempts should have exponential backoff
        let delay1 = retry_logic.calculate_delay(1);
        let delay2 = retry_logic.calculate_delay(2);
        let delay3 = retry_logic.calculate_delay(3);
        
        // Should be roughly exponential (allowing for jitter)
        assert!(delay1 >= 75 && delay1 <= 125); // ~100ms ±25%
        assert!(delay2 >= 150 && delay2 <= 250); // ~200ms ±25%
        assert!(delay3 >= 300 && delay3 <= 500); // ~400ms ±25%
    }

    #[test]
    fn test_calculate_delay_max_cap() {
        let retry_logic = RetryLogic::new(10, 100, 1000);
        
        // Large attempt should be capped at max_delay
        let delay = retry_logic.calculate_delay(10);
        assert!(delay <= 1250); // max_delay + 25% jitter
    }

    #[test]
    fn test_calculate_max_total_time() {
        let retry_logic = RetryLogic::new(3, 100, 5000);
        let total_time = retry_logic.calculate_max_total_time();
        
        // Should be sum of all retry delays
        assert!(total_time > 0);
        assert!(total_time < 10000); // Reasonable upper bound
    }

    #[test]
    fn test_retry_policy_network_error() {
        let error = rust_common::TradingError::NetworkError(
            reqwest::Error::from(reqwest::ErrorKind::Request)
        );
        assert!(matches!(determine_retry_policy(&error), RetryPolicy::ExponentialBackoff));
    }

    #[test]
    fn test_retry_policy_execution_error_timeout() {
        let error = rust_common::TradingError::ExecutionError {
            message: "Request timeout".to_string(),
        };
        assert!(matches!(determine_retry_policy(&error), RetryPolicy::ExponentialBackoff));
    }

    #[test]
    fn test_retry_policy_execution_error_insufficient_funds() {
        let error = rust_common::TradingError::ExecutionError {
            message: "Insufficient funds".to_string(),
        };
        assert!(matches!(determine_retry_policy(&error), RetryPolicy::NoRetry));
    }

    #[test]
    fn test_retry_policy_risk_limit_error() {
        let error = rust_common::TradingError::RiskLimitError {
            limit: "Position size too large".to_string(),
        };
        assert!(matches!(determine_retry_policy(&error), RetryPolicy::NoRetry));
    }
}