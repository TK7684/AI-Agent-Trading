use std::sync::atomic::{AtomicU32, AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

/// Circuit breaker states
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum CircuitBreakerState {
    Closed,   // Normal operation
    Open,     // Failing, blocking requests
    HalfOpen, // Testing if service recovered
}

/// Circuit breaker implementation for exchange connections
pub struct CircuitBreaker {
    failure_threshold: u32,
    recovery_timeout_ms: u64,
    failure_count: AtomicU32,
    last_failure_time: AtomicU64,
    state: std::sync::RwLock<CircuitBreakerState>,
}

impl CircuitBreaker {
    pub fn new(failure_threshold: u32, recovery_timeout_ms: u64) -> Self {
        Self {
            failure_threshold,
            recovery_timeout_ms,
            failure_count: AtomicU32::new(0),
            last_failure_time: AtomicU64::new(0),
            state: std::sync::RwLock::new(CircuitBreakerState::Closed),
        }
    }

    /// Check if circuit breaker is open (blocking requests)
    pub fn is_open(&self) -> bool {
        let state = *self.state.read().unwrap();
        
        match state {
            CircuitBreakerState::Open => {
                // Check if recovery timeout has passed
                let now = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_millis() as u64;
                
                let last_failure = self.last_failure_time.load(Ordering::Relaxed);
                
                if now - last_failure > self.recovery_timeout_ms {
                    // Transition to half-open to test recovery
                    *self.state.write().unwrap() = CircuitBreakerState::HalfOpen;
                    false
                } else {
                    true
                }
            }
            CircuitBreakerState::HalfOpen => false, // Allow one test request
            CircuitBreakerState::Closed => false,
        }
    }

    /// Record a successful operation
    pub fn record_success(&self) {
        let mut state = self.state.write().unwrap();
        
        match *state {
            CircuitBreakerState::HalfOpen => {
                // Recovery successful, close circuit
                *state = CircuitBreakerState::Closed;
                self.failure_count.store(0, Ordering::Relaxed);
            }
            CircuitBreakerState::Closed => {
                // Reset failure count on success
                self.failure_count.store(0, Ordering::Relaxed);
            }
            CircuitBreakerState::Open => {
                // Should not happen, but reset if it does
                *state = CircuitBreakerState::Closed;
                self.failure_count.store(0, Ordering::Relaxed);
            }
        }
    }

    /// Record a failed operation
    pub fn record_failure(&self) {
        let failure_count = self.failure_count.fetch_add(1, Ordering::Relaxed) + 1;
        
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64;
        
        self.last_failure_time.store(now, Ordering::Relaxed);

        let mut state = self.state.write().unwrap();
        
        match *state {
            CircuitBreakerState::Closed => {
                if failure_count >= self.failure_threshold {
                    *state = CircuitBreakerState::Open;
                }
            }
            CircuitBreakerState::HalfOpen => {
                // Test failed, go back to open
                *state = CircuitBreakerState::Open;
            }
            CircuitBreakerState::Open => {
                // Already open, just update failure time
            }
        }
    }

    /// Get current state
    pub fn get_state(&self) -> CircuitBreakerState {
        *self.state.read().unwrap()
    }

    /// Get current failure count
    pub fn get_failure_count(&self) -> u32 {
        self.failure_count.load(Ordering::Relaxed)
    }

    /// Force circuit breaker to open (for testing)
    pub fn force_open(&self) {
        *self.state.write().unwrap() = CircuitBreakerState::Open;
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64;
        self.last_failure_time.store(now, Ordering::Relaxed);
    }

    /// Force circuit breaker to close (for testing)
    pub fn force_close(&self) {
        *self.state.write().unwrap() = CircuitBreakerState::Closed;
        self.failure_count.store(0, Ordering::Relaxed);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::time::Duration;

    #[test]
    fn test_circuit_breaker_closed_initially() {
        let cb = CircuitBreaker::new(3, 1000);
        assert_eq!(cb.get_state(), CircuitBreakerState::Closed);
        assert!(!cb.is_open());
    }

    #[test]
    fn test_circuit_breaker_opens_after_threshold() {
        let cb = CircuitBreaker::new(3, 1000);
        
        // Record failures up to threshold
        cb.record_failure();
        assert_eq!(cb.get_state(), CircuitBreakerState::Closed);
        
        cb.record_failure();
        assert_eq!(cb.get_state(), CircuitBreakerState::Closed);
        
        cb.record_failure();
        assert_eq!(cb.get_state(), CircuitBreakerState::Open);
        assert!(cb.is_open());
    }

    #[test]
    fn test_circuit_breaker_success_resets_failures() {
        let cb = CircuitBreaker::new(3, 1000);
        
        cb.record_failure();
        cb.record_failure();
        assert_eq!(cb.get_failure_count(), 2);
        
        cb.record_success();
        assert_eq!(cb.get_failure_count(), 0);
        assert_eq!(cb.get_state(), CircuitBreakerState::Closed);
    }

    #[test]
    fn test_circuit_breaker_recovery_timeout() {
        let cb = CircuitBreaker::new(2, 100); // 100ms timeout
        
        // Trigger circuit breaker
        cb.record_failure();
        cb.record_failure();
        assert_eq!(cb.get_state(), CircuitBreakerState::Open);
        assert!(cb.is_open());
        
        // Wait for recovery timeout
        thread::sleep(Duration::from_millis(150));
        
        // Should transition to half-open
        assert!(!cb.is_open());
        assert_eq!(cb.get_state(), CircuitBreakerState::HalfOpen);
    }

    #[test]
    fn test_circuit_breaker_half_open_success() {
        let cb = CircuitBreaker::new(2, 100);
        
        // Force to half-open state
        cb.force_open();
        thread::sleep(Duration::from_millis(150));
        let _ = cb.is_open(); // This will transition to half-open
        
        // Record success should close circuit
        cb.record_success();
        assert_eq!(cb.get_state(), CircuitBreakerState::Closed);
        assert_eq!(cb.get_failure_count(), 0);
    }

    #[test]
    fn test_circuit_breaker_half_open_failure() {
        let cb = CircuitBreaker::new(2, 100);
        
        // Force to half-open state
        cb.force_open();
        thread::sleep(Duration::from_millis(150));
        let _ = cb.is_open(); // This will transition to half-open
        
        // Record failure should go back to open
        cb.record_failure();
        assert_eq!(cb.get_state(), CircuitBreakerState::Open);
    }
}