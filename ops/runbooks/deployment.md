# Deployment Procedures

## Blue/Green Deployment

### Prerequisites
- [ ] All tests passing in CI/CD pipeline
- [ ] Security scans completed
- [ ] Staging environment validated
- [ ] Rollback plan prepared

### Deployment Steps

1. **Pre-deployment Checks**
   ```bash
   # Check current system health
   kubectl get pods -n production
   kubectl top nodes
   
   # Verify database connectivity
   kubectl exec -it postgres-pod -- pg_isready
   
   # Check current performance metrics
   curl -s http://prometheus:9090/api/v1/query?query=trading_win_rate | jq .
   ```

2. **Deploy to Green Environment**
   ```bash
   # Deploy new version to green environment
   helm upgrade --install trading-system-green ./infra/helm/trading-system \
     --namespace production \
     --set image.tag=$NEW_VERSION \
     --set deployment.color=green \
     --values ./infra/helm/values-production.yaml \
     --wait --timeout=15m
   ```

3. **Health Checks**
   ```bash
   # Run comprehensive health checks
   ./scripts/health-check.sh production green
   
   # Verify all components are ready
   kubectl wait --for=condition=ready pod -l color=green -n production --timeout=300s
   
   # Test API endpoints
   curl -f http://trading-system-green:8080/health
   curl -f http://trading-system-green:3000/health
   ```

4. **Traffic Switch**
   ```bash
   # Switch traffic to green environment
   kubectl patch service trading-system-service -n production \
     -p '{"spec":{"selector":{"color":"green"}}}'
   
   # Verify traffic switch
   kubectl get service trading-system-service -n production -o yaml
   ```

5. **Post-deployment Validation**
   ```bash
   # Monitor for 5 minutes
   watch -n 30 'kubectl get pods -l color=green -n production'
   
   # Check error rates
   curl -s "http://prometheus:9090/api/v1/query?query=rate(trading_errors_total[5m])" | jq .
   
   # Verify trading functionality
   ./scripts/trading-validation.sh production
   ```

6. **Cleanup**
   ```bash
   # Remove blue environment after successful validation
   helm uninstall trading-system-blue -n production
   
   # Clean up unused resources
   kubectl delete pods -l color=blue -n production
   ```

## Rollback Procedures

### Immediate Rollback (Emergency)
```bash
# Switch traffic back to blue environment
kubectl patch service trading-system-service -n production \
  -p '{"spec":{"selector":{"color":"blue"}}}'

# Verify rollback
kubectl get service trading-system-service -n production -o yaml
./scripts/health-check.sh production blue
```

### Planned Rollback
```bash
# Scale up previous version
kubectl scale deployment trading-system-blue -n production --replicas=2

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l color=blue -n production --timeout=300s

# Switch traffic
kubectl patch service trading-system-service -n production \
  -p '{"spec":{"selector":{"color":"blue"}}}'

# Scale down new version
kubectl scale deployment trading-system-green -n production --replicas=0
```

## Feature Flag Management

### Enable Feature for Canary Users
```bash
# Update feature flag configuration
kubectl patch configmap trading-feature-flags -n production \
  --patch '{"data":{"flags.yaml":"$(cat updated-flags.yaml | base64 -w 0)"}}'

# Restart pods to pick up new configuration
kubectl rollout restart deployment/trading-system-green -n production
```

### Gradual Rollout
```bash
# Increase rollout percentage gradually
# 5% -> 25% -> 50% -> 100%

# Update feature flag percentage
sed -i 's/rollout_percentage: 5/rollout_percentage: 25/' feature-flags.yaml

# Apply configuration
kubectl apply -f feature-flags-configmap.yaml
```

### Emergency Feature Disable
```bash
# Disable feature immediately
kubectl patch configmap trading-feature-flags -n production \
  --patch '{"data":{"flags.yaml":"$(echo 'flags:\n  problematic_feature:\n    enabled: false' | base64 -w 0)"}}'

# Force configuration reload
kubectl exec -it trading-system-pod -- curl -X POST http://localhost:8080/api/reload-config
```

## Monitoring During Deployment

### Key Metrics to Watch
- System uptime and availability
- Error rates and response times
- Trading performance metrics
- Resource utilization
- Database performance

### Automated Checks
```bash
# Set up monitoring during deployment
./scripts/deployment-monitor.sh &
MONITOR_PID=$!

# Perform deployment...

# Stop monitoring
kill $MONITOR_PID
```

### Manual Verification
```bash
# Check system health
kubectl get pods -n production
kubectl top pods -n production

# Verify trading metrics
curl -s "http://prometheus:9090/api/v1/query?query=trading_win_rate" | jq .data.result[0].value[1]

# Check recent trades
kubectl exec -it postgres-pod -- psql -d trading -c "SELECT * FROM trades ORDER BY created_at DESC LIMIT 10;"
```

## Troubleshooting Deployment Issues

### Pod Startup Issues
```bash
# Check pod status
kubectl describe pod trading-system-pod -n production

# Check logs
kubectl logs trading-system-pod -n production --previous

# Check resource constraints
kubectl top pod trading-system-pod -n production
```

### Service Discovery Issues
```bash
# Check service endpoints
kubectl get endpoints trading-system-service -n production

# Test internal connectivity
kubectl exec -it test-pod -- nslookup trading-system-service.production.svc.cluster.local
```

### Configuration Issues
```bash
# Verify ConfigMap
kubectl get configmap trading-config -n production -o yaml

# Check mounted volumes
kubectl exec -it trading-system-pod -- ls -la /app/config/

# Validate configuration
kubectl exec -it trading-system-pod -- python -c "import yaml; yaml.safe_load(open('/app/config/config.toml'))"
```