# High Drawdown Incident Response

## Overview
This runbook provides procedures for responding to high drawdown situations where the trading system experiences significant losses.

## Severity Levels

### Level 1: Warning (8-15% drawdown)
- **Response Time**: 15 minutes
- **Actions**: Monitor closely, prepare for escalation

### Level 2: Critical (15-20% drawdown)
- **Response Time**: 5 minutes
- **Actions**: Enable safe mode, reduce position sizes

### Level 3: Emergency (>20% drawdown)
- **Response Time**: Immediate
- **Actions**: Stop all trading, emergency shutdown

## Immediate Response Procedures

### 1. Assess the Situation
```bash
# Check current drawdown level
curl -s "http://prometheus:9090/api/v1/query?query=trading_drawdown_percentage" | jq .data.result[0].value[1]

# Check recent trades
kubectl exec -it postgres-pod -- psql -d trading -c "
  SELECT symbol, side, pnl, created_at 
  FROM trades 
  WHERE created_at > NOW() - INTERVAL '1 hour' 
  ORDER BY created_at DESC 
  LIMIT 20;
"

# Check system status
kubectl get pods -l app=trading-system -n production
```

### 2. Enable Safe Mode (Level 2+)
```bash
# Enable safe mode immediately
kubectl exec -it trading-system-pod -- curl -X POST http://localhost:8080/api/safe-mode

# Verify safe mode is active
curl -s http://trading-system:8080/api/status | jq .safe_mode

# Check that new positions are blocked
kubectl logs trading-system-pod --tail=50 | grep "SAFE_MODE"
```

### 3. Emergency Shutdown (Level 3)
```bash
# Stop all trading immediately
kubectl patch deployment trading-system -n production -p '{"spec":{"replicas":0}}'

# Close all open positions (if configured)
kubectl exec -it trading-system-pod -- curl -X POST http://localhost:8080/api/close-all-positions

# Verify no new orders are being placed
kubectl logs execution-gateway-pod --tail=100 | grep "ORDER_BLOCKED"
```

## Investigation Procedures

### 1. Identify Root Cause
```bash
# Check recent market conditions
kubectl exec -it trading-system-pod -- python -c "
from libs.trading_models.market_data_ingestion import MarketDataIngestion
mdi = MarketDataIngestion()
data = mdi.get_recent_data('BTCUSD', '1h', 24)
print(f'Recent volatility: {data.volatility}')
print(f'Market regime: {data.regime}')
"

# Analyze failed trades
kubectl exec -it postgres-pod -- psql -d trading -c "
  SELECT 
    pattern_id,
    COUNT(*) as trade_count,
    AVG(pnl) as avg_pnl,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses
  FROM trades 
  WHERE created_at > NOW() - INTERVAL '4 hours'
  GROUP BY pattern_id
  ORDER BY avg_pnl ASC;
"

# Check LLM analysis quality
kubectl logs trading-system-pod | grep "LLM_ANALYSIS" | tail -20
```

### 2. Check System Components
```bash
# Verify all components are functioning
kubectl get pods -l app=trading-system -n production
kubectl logs trading-system-pod --tail=100
kubectl logs execution-gateway-pod --tail=100

# Check for any configuration changes
kubectl get configmap trading-config -n production -o yaml | grep -A 10 -B 10 "last-applied"

# Verify feature flags
kubectl get configmap trading-feature-flags -n production -o yaml
```

### 3. Market Analysis
```bash
# Check for unusual market conditions
curl -s "http://prometheus:9090/api/v1/query?query=market_volatility" | jq .

# Analyze correlation with market events
kubectl exec -it trading-system-pod -- python -c "
from libs.trading_models.market_data_ingestion import MarketDataIngestion
mdi = MarketDataIngestion()
# Check for news events, volatility spikes, etc.
"
```

## Recovery Procedures

### 1. Gradual Recovery (After Level 1/2)
```bash
# Reduce position sizes
kubectl exec -it trading-system-pod -- curl -X POST http://localhost:8080/api/config \
  -d '{"risk_per_trade": 0.5, "max_portfolio_risk": 10}'

# Enable conservative mode
kubectl patch configmap trading-feature-flags -n production \
  --patch '{"data":{"flags.yaml":"$(echo 'flags:\n  conservative_mode:\n    enabled: true\n    rollout_percentage: 100' | base64 -w 0)"}}'

# Restart with new configuration
kubectl rollout restart deployment/trading-system -n production
```

### 2. Full Recovery (After Level 3)
```bash
# Wait for market conditions to stabilize
# Manual approval required from trading operations

# Gradually scale back up
kubectl scale deployment trading-system -n production --replicas=1

# Monitor closely for 1 hour before full operation
watch -n 60 'curl -s "http://prometheus:9090/api/v1/query?query=trading_drawdown_percentage" | jq .data.result[0].value[1]'

# Full scale up only after validation
kubectl scale deployment trading-system -n production --replicas=2
```

## Post-Incident Analysis

### 1. Data Collection
```bash
# Export trade data for analysis
kubectl exec -it postgres-pod -- pg_dump -d trading -t trades > incident_trades.sql

# Export system logs
kubectl logs trading-system-pod --since=4h > incident_logs.txt

# Export metrics data
curl -s "http://prometheus:9090/api/v1/query_range?query=trading_drawdown_percentage&start=$(date -d '4 hours ago' +%s)&end=$(date +%s)&step=60" > drawdown_metrics.json
```

### 2. Generate Incident Report
```bash
# Run automated incident analysis
./scripts/incident-analysis.sh --type=drawdown --start="4 hours ago"

# Generate compliance report
kubectl exec -it trading-system-pod -- python -c "
from libs.trading_models.persistence import AuditLogger
audit = AuditLogger()
audit.generate_incident_report('high_drawdown', '$(date -d '4 hours ago' --iso-8601)')
"
```

### 3. Implement Improvements
- Update risk management parameters
- Adjust pattern weights based on performance
- Improve market regime detection
- Update alert thresholds
- Review and update this runbook

## Prevention Measures

### 1. Enhanced Monitoring
```bash
# Set up additional alerts
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: enhanced-drawdown-alerts
spec:
  groups:
  - name: drawdown.rules
    rules:
    - alert: DrawdownTrend
      expr: increase(trading_drawdown_percentage[30m]) > 5
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Drawdown trending upward"
EOF
```

### 2. Risk Parameter Adjustment
```bash
# Implement dynamic risk adjustment
kubectl patch configmap trading-config -n production \
  --patch '{"data":{"config.toml":"$(cat config-conservative.toml | base64 -w 0)"}}'
```

## Communication Procedures

### Internal Notifications
- Notify trading operations team immediately
- Update incident channel in Slack/Teams
- Escalate to management for Level 3 incidents

### External Notifications
- Regulatory reporting (if required)
- Client notifications (if applicable)
- Compliance documentation

## Contact Information
- **Trading Operations**: [Phone/Email]
- **Risk Management**: [Phone/Email]
- **System Administrator**: [Phone/Email]
- **Compliance Officer**: [Phone/Email]