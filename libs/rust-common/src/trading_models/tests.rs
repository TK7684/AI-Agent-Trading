//! Tests for trading models.

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;
    use serde_json;
    use std::collections::HashMap;

    #[test]
    fn test_market_bar_validation() {
        let mut bar = MarketBar {
            symbol: "BTCUSDT".to_string(),
            timeframe: Timeframe::H1,
            timestamp: Utc::now(),
            open: 50000.0,
            high: 51000.0,
            low: 49500.0,
            close: 50500.0,
            volume: 100.5,
            quote_volume: None,
            trades_count: None,
            taker_buy_volume: None,
        };

        // Valid bar should pass validation
        assert!(bar.validate().is_ok());

        // Invalid high price should fail
        bar.high = 49000.0; // Lower than open
        assert!(bar.validate().is_err());

        // Reset and test invalid low price
        bar.high = 51000.0;
        bar.low = 50500.0; // Higher than open
        assert!(bar.validate().is_err());

        // Test negative volume
        bar.low = 49500.0;
        bar.volume = -10.0;
        assert!(bar.validate().is_err());
    }

    #[test]
    fn test_indicator_snapshot_validation() {
        let mut snapshot = IndicatorSnapshot {
            symbol: "BTCUSDT".to_string(),
            timeframe: Timeframe::H1,
            timestamp: Utc::now(),
            rsi: Some(65.5),
            ema_20: Some(50000.0),
            ema_50: None,
            ema_200: None,
            macd_line: None,
            macd_signal: None,
            macd_histogram: None,
            bb_upper: Some(52000.0),
            bb_middle: Some(50000.0),
            bb_lower: Some(48000.0),
            bb_width: None,
            atr: Some(500.0),
            volume_sma: None,
            volume_profile: None,
            stoch_k: None,
            stoch_d: None,
            cci: None,
            mfi: None,
        };

        // Valid snapshot should pass
        assert!(snapshot.validate().is_ok());

        // Invalid RSI should fail
        snapshot.rsi = Some(150.0);
        assert!(snapshot.validate().is_err());

        // Invalid Bollinger Bands should fail
        snapshot.rsi = Some(65.5);
        snapshot.bb_upper = Some(48000.0); // Upper < Middle
        assert!(snapshot.validate().is_err());
    }

    #[test]
    fn test_pattern_hit_validation() {
        let mut pattern = PatternHit {
            pattern_id: "pattern_123".to_string(),
            pattern_type: PatternType::Breakout,
            symbol: "BTCUSDT".to_string(),
            timeframe: Timeframe::H1,
            timestamp: Utc::now(),
            confidence: 0.85,
            strength: 7.5,
            entry_price: Some(50000.0),
            stop_loss: Some(49000.0),
            take_profit: Some(52000.0),
            support_levels: vec![48000.0, 49000.0],
            resistance_levels: vec![51000.0, 52000.0],
            pattern_data: HashMap::new(),
            bars_analyzed: 100,
            lookback_period: 50,
            historical_win_rate: Some(0.65),
            avg_return: Some(0.15),
        };

        // Valid pattern should pass
        assert!(pattern.validate().is_ok());

        // Invalid confidence should fail
        pattern.confidence = 1.5;
        assert!(pattern.validate().is_err());

        // Invalid strength should fail
        pattern.confidence = 0.85;
        pattern.strength = 15.0;
        assert!(pattern.validate().is_err());

        // Unsorted support levels should fail
        pattern.strength = 7.5;
        pattern.support_levels = vec![49000.0, 48000.0]; // Unsorted
        assert!(pattern.validate().is_err());
    }

    #[test]
    fn test_signal_validation() {
        let mut signal = Signal {
            signal_id: "signal_123".to_string(),
            symbol: "BTCUSDT".to_string(),
            timestamp: Utc::now(),
            direction: Direction::Long,
            confluence_score: 75.5,
            confidence: 0.8,
            market_regime: MarketRegime::Bull,
            primary_timeframe: Timeframe::H1,
            timeframe_analysis: HashMap::new(),
            patterns: Vec::new(),
            indicators: HashMap::new(),
            llm_analysis: None,
            entry_price: Some(50000.0),
            stop_loss: Some(49000.0),
            take_profit: Some(52000.0),
            risk_reward_ratio: Some(2.0),
            max_risk_pct: Some(2.0),
            reasoning: "Strong bullish breakout".to_string(),
            key_factors: Vec::new(),
            expires_at: None,
            priority: 3,
        };

        // Valid signal should pass
        assert!(signal.validate().is_ok());

        // High confluence with low confidence should fail
        signal.confluence_score = 95.0;
        signal.confidence = 0.5;
        assert!(signal.validate().is_err());

        // Invalid priority should fail
        signal.confidence = 0.9;
        signal.priority = 10; // > 5
        assert!(signal.validate().is_err());
    }

    #[test]
    fn test_order_decision_validation() {
        let mut decision = OrderDecision::new(
            "signal_123".to_string(),
            "BTCUSDT".to_string(),
        );
        
        decision.direction = Direction::Long;
        decision.base_quantity = 1.0;
        decision.risk_adjusted_quantity = 0.8;
        decision.max_position_value = 40000.0;
        decision.entry_price = 50000.0;
        decision.stop_loss = 49000.0;
        decision.risk_amount = 800.0;
        decision.risk_percentage = 2.0;
        decision.leverage = 1.0;
        decision.portfolio_value = 100000.0;
        decision.available_margin = 50000.0;
        decision.current_exposure = 0.1;
        decision.confidence_score = 0.8;
        decision.confluence_score = 75.0;
        decision.risk_reward_ratio = 1.25;

        // Valid decision should pass
        assert!(decision.validate().is_ok());

        // Invalid stop loss for long position should fail
        decision.stop_loss = 51000.0; // Above entry for long
        assert!(decision.validate().is_err());

        // Excessive leverage should fail
        decision.stop_loss = 49000.0;
        decision.leverage = 15.0; // > 10x
        assert!(decision.validate().is_err());
    }

    #[test]
    fn test_pattern_collection_operations() {
        let mut collection = PatternCollection::new(
            "BTCUSDT".to_string(),
            Timeframe::H1,
        );

        let pattern = PatternHit {
            pattern_id: "pattern_123".to_string(),
            pattern_type: PatternType::Breakout,
            symbol: "BTCUSDT".to_string(),
            timeframe: Timeframe::H1,
            timestamp: Utc::now(),
            confidence: 0.85,
            strength: 7.5,
            entry_price: None,
            stop_loss: None,
            take_profit: None,
            support_levels: Vec::new(),
            resistance_levels: Vec::new(),
            pattern_data: HashMap::new(),
            bars_analyzed: 100,
            lookback_period: 50,
            historical_win_rate: None,
            avg_return: None,
        };

        collection.add_pattern(pattern);

        assert_eq!(collection.total_patterns, 1);
        assert_eq!(collection.avg_confidence, 0.85);
        assert_eq!(collection.strongest_pattern, Some("pattern_123".to_string()));

        // Test filtering
        let breakout_patterns = collection.get_patterns_by_type(PatternType::Breakout);
        assert_eq!(breakout_patterns.len(), 1);

        let high_conf_patterns = collection.get_high_confidence_patterns(0.8);
        assert_eq!(high_conf_patterns.len(), 1);
    }

    #[test]
    fn test_json_serialization_compatibility() {
        // Test MarketBar serialization
        let bar = MarketBar {
            symbol: "BTCUSDT".to_string(),
            timeframe: Timeframe::H1,
            timestamp: Utc::now(),
            open: 50000.0,
            high: 51000.0,
            low: 49500.0,
            close: 50500.0,
            volume: 100.5,
            quote_volume: None,
            trades_count: None,
            taker_buy_volume: None,
        };

        let json_str = serde_json::to_string(&bar).unwrap();
        let bar_restored: MarketBar = serde_json::from_str(&json_str).unwrap();

        assert_eq!(bar.symbol, bar_restored.symbol);
        assert_eq!(bar.timeframe, bar_restored.timeframe);
        assert_eq!(bar.open, bar_restored.open);

        // Test Signal serialization
        let signal = Signal {
            signal_id: "signal_123".to_string(),
            symbol: "BTCUSDT".to_string(),
            timestamp: Utc::now(),
            direction: Direction::Long,
            confluence_score: 75.5,
            confidence: 0.8,
            market_regime: MarketRegime::Bull,
            primary_timeframe: Timeframe::H1,
            timeframe_analysis: HashMap::new(),
            patterns: Vec::new(),
            indicators: HashMap::new(),
            llm_analysis: None,
            entry_price: None,
            stop_loss: None,
            take_profit: None,
            risk_reward_ratio: None,
            max_risk_pct: None,
            reasoning: "Test signal".to_string(),
            key_factors: Vec::new(),
            expires_at: None,
            priority: 3,
        };

        let json_str = serde_json::to_string(&signal).unwrap();
        let signal_restored: Signal = serde_json::from_str(&json_str).unwrap();

        assert_eq!(signal.signal_id, signal_restored.signal_id);
        assert_eq!(signal.direction, signal_restored.direction);
        assert_eq!(signal.market_regime, signal_restored.market_regime);
    }

    #[test]
    fn test_timeframe_enum_conversion() {
        // Test string conversion
        assert_eq!(Timeframe::M15.as_str(), "15m");
        assert_eq!(Timeframe::H1.as_str(), "1h");
        assert_eq!(Timeframe::H4.as_str(), "4h");
        assert_eq!(Timeframe::D1.as_str(), "1d");

        // Test from string
        assert_eq!(Timeframe::from_str("15m"), Some(Timeframe::M15));
        assert_eq!(Timeframe::from_str("1h"), Some(Timeframe::H1));
        assert_eq!(Timeframe::from_str("4h"), Some(Timeframe::H4));
        assert_eq!(Timeframe::from_str("1d"), Some(Timeframe::D1));
        assert_eq!(Timeframe::from_str("invalid"), None);
    }

    #[test]
    fn test_execution_result_operations() {
        let mut result = ExecutionResult::new(
            "decision_123".to_string(),
            "order_456".to_string(),
        );

        assert!(!result.is_fully_filled());
        assert!(!result.is_partially_filled());

        result.status = OrderStatus::Filled;
        result.filled_quantity = 1.0;

        assert!(result.is_fully_filled());
        assert!(!result.is_partially_filled());

        // Test fill percentage
        let fill_pct = result.get_fill_percentage(1.0);
        assert_eq!(fill_pct, 100.0);

        let partial_fill_pct = result.get_fill_percentage(2.0);
        assert_eq!(partial_fill_pct, 50.0);
    }

    #[test]
    fn test_order_decision_calculations() {
        let mut decision = OrderDecision::new(
            "signal_123".to_string(),
            "BTCUSDT".to_string(),
        );
        
        decision.risk_adjusted_quantity = 1.0;
        decision.entry_price = 50000.0;
        decision.leverage = 2.0;
        decision.available_margin = 50000.0;

        let position_value = decision.calculate_position_value();
        assert_eq!(position_value, 100000.0); // 1.0 * 50000.0 * 2.0

        let margin_required = decision.calculate_margin_required();
        assert_eq!(margin_required, 50000.0); // 100000.0 / 2.0

        assert!(decision.validate_margin_requirements());

        let risk_metrics = decision.get_risk_metrics();
        assert!(risk_metrics.contains_key("position_size_pct"));
        assert!(risk_metrics.contains_key("leverage"));
    }
}