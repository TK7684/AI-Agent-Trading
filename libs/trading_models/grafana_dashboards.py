"""
Grafana dashboard configurations for the autonomous trading system.
Provides comprehensive monitoring dashboards for trading, system, and LLM metrics.
"""

import json
from typing import Any


class GrafanaDashboardBuilder:
    """Builder for creating Grafana dashboard configurations"""

    def __init__(self, title: str, uid: str):
        self.dashboard = {
            "id": None,
            "uid": uid,
            "title": title,
            "tags": ["trading", "autonomous"],
            "timezone": "UTC",
            "refresh": "30s",
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "timepicker": {
                "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"]
            },
            "panels": [],
            "templating": {
                "list": []
            },
            "annotations": {
                "list": []
            },
            "schemaVersion": 30,
            "version": 1,
            "links": []
        }
        self.panel_id = 1

    def add_template_variable(self, name: str, query: str, label: str = None):
        """Add a template variable to the dashboard"""
        self.dashboard["templating"]["list"].append({
            "name": name,
            "type": "query",
            "query": query,
            "label": label or name,
            "refresh": 1,
            "includeAll": True,
            "allValue": ".*",
            "multi": True
        })

    def add_panel(self, panel_config: dict[str, Any]):
        """Add a panel to the dashboard"""
        panel_config["id"] = self.panel_id
        self.dashboard["panels"].append(panel_config)
        self.panel_id += 1

    def build(self) -> dict[str, Any]:
        """Build and return the dashboard configuration"""
        return self.dashboard


def create_trading_performance_dashboard() -> dict[str, Any]:
    """Create the main trading performance dashboard"""
    builder = GrafanaDashboardBuilder("Trading Performance", "trading-performance")

    # Template variables
    builder.add_template_variable("symbol", "label_values(trading_trades_total, symbol)", "Symbol")
    builder.add_template_variable("pattern", "label_values(trading_pattern_signals_total, pattern_id)", "Pattern")

    # Row 1: Key Performance Indicators
    builder.add_panel({
        "title": "Total P&L",
        "type": "stat",
        "targets": [{
            "expr": "trading_pnl_total",
            "legendFormat": "Net P&L"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "currencyUSD",
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "yellow", "value": 0},
                        {"color": "green", "value": 1000}
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
    })

    builder.add_panel({
        "title": "Win Rate",
        "type": "stat",
        "targets": [{
            "expr": "trading_win_rate_percent",
            "legendFormat": "Win Rate"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "percent",
                "min": 0,
                "max": 100,
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "steps": [
                        {"color": "red", "value": 0},
                        {"color": "yellow", "value": 40},
                        {"color": "green", "value": 60}
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
    })

    builder.add_panel({
        "title": "Current Drawdown",
        "type": "stat",
        "targets": [{
            "expr": "trading_drawdown_current_percent",
            "legendFormat": "Current DD"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "percent",
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "yellow", "value": 5},
                        {"color": "red", "value": 10}
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0}
    })

    builder.add_panel({
        "title": "Total Trades",
        "type": "stat",
        "targets": [{
            "expr": "sum(trading_trades_total)",
            "legendFormat": "Total Trades"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "short",
                "color": {
                    "mode": "palette-classic"
                }
            }
        },
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
    })

    # Row 2: P&L Over Time
    builder.add_panel({
        "title": "P&L Over Time",
        "type": "timeseries",
        "targets": [{
            "expr": "trading_pnl_total",
            "legendFormat": "Cumulative P&L"
        }, {
            "expr": "trading_drawdown_current_percent",
            "legendFormat": "Current Drawdown %"
        }],
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "linear",
                    "lineWidth": 2,
                    "fillOpacity": 10,
                    "gradientMode": "none",
                    "spanNulls": False,
                    "pointSize": 5,
                    "stacking": {"mode": "none"}
                }
            },
            "overrides": [{
                "matcher": {"id": "byName", "options": "Current Drawdown %"},
                "properties": [{
                    "id": "custom.axisPlacement",
                    "value": "right"
                }, {
                    "id": "unit",
                    "value": "percent"
                }]
            }]
        },
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8}
    })

    # Row 3: Pattern Performance
    builder.add_panel({
        "title": "Pattern Hit Rates",
        "type": "barchart",
        "targets": [{
            "expr": "trading_pattern_hit_rate_percent{pattern_id=~\"$pattern\"}",
            "legendFormat": "{{pattern_id}}"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "percent",
                "min": 0,
                "max": 100,
                "custom": {
                    "orientation": "horizontal"
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
    })

    builder.add_panel({
        "title": "Pattern Expectancy",
        "type": "barchart",
        "targets": [{
            "expr": "trading_pattern_expectancy{pattern_id=~\"$pattern\"}",
            "legendFormat": "{{pattern_id}}"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "currencyUSD",
                "custom": {
                    "orientation": "horizontal"
                },
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "yellow", "value": 0},
                        {"color": "green", "value": 10}
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
    })

    # Row 4: Trade Distribution
    builder.add_panel({
        "title": "Trades by Outcome",
        "type": "piechart",
        "targets": [{
            "expr": "trading_trades_total",
            "legendFormat": "{{outcome}}"
        }],
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "displayMode": "table",
                    "pieType": "pie"
                }
            }
        },
        "gridPos": {"h": 8, "w": 8, "x": 0, "y": 24}
    })

    builder.add_panel({
        "title": "Cost per Trade",
        "type": "timeseries",
        "targets": [{
            "expr": "trading_cost_per_trade_usd",
            "legendFormat": "Cost per Trade"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "currencyUSD",
                "custom": {
                    "drawStyle": "line",
                    "lineWidth": 2
                }
            }
        },
        "gridPos": {"h": 8, "w": 8, "x": 8, "y": 24}
    })

    builder.add_panel({
        "title": "LLM Costs by Model",
        "type": "timeseries",
        "targets": [{
            "expr": "rate(trading_llm_cost_usd_total[5m])",
            "legendFormat": "{{model}}"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "currencyUSD",
                "custom": {
                    "drawStyle": "line",
                    "lineWidth": 2,
                    "stacking": {"mode": "normal"}
                }
            }
        },
        "gridPos": {"h": 8, "w": 8, "x": 16, "y": 24}
    })

    return builder.build()


def create_system_performance_dashboard() -> dict[str, Any]:
    """Create the system performance and latency dashboard"""
    builder = GrafanaDashboardBuilder("System Performance", "system-performance")

    # Row 1: Latency Metrics
    builder.add_panel({
        "title": "Scan Latency P95",
        "type": "stat",
        "targets": [{
            "expr": "histogram_quantile(0.95, rate(system_scan_latency_seconds_bucket[5m]))",
            "legendFormat": "P95 Latency"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "s",
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "yellow", "value": 0.5},
                        {"color": "red", "value": 1.0}
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
    })

    builder.add_panel({
        "title": "LLM Latency P95",
        "type": "stat",
        "targets": [{
            "expr": "histogram_quantile(0.95, rate(system_llm_latency_seconds_bucket[5m]))",
            "legendFormat": "P95 Latency"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "s",
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "yellow", "value": 2.0},
                        {"color": "red", "value": 3.0}
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
    })

    builder.add_panel({
        "title": "System Uptime",
        "type": "stat",
        "targets": [{
            "expr": "system_uptime_seconds / 3600",
            "legendFormat": "Uptime Hours"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "h",
                "color": {
                    "mode": "palette-classic"
                }
            }
        },
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0}
    })

    builder.add_panel({
        "title": "Error Rate",
        "type": "stat",
        "targets": [{
            "expr": "rate(system_errors_total[5m]) * 60",
            "legendFormat": "Errors/min"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "short",
                "color": {
                    "mode": "thresholds"
                },
                "thresholds": {
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "yellow", "value": 1},
                        {"color": "red", "value": 5}
                    ]
                }
            }
        },
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
    })

    # Row 2: Latency Histograms
    builder.add_panel({
        "title": "Scan Latency Distribution",
        "type": "timeseries",
        "targets": [{
            "expr": "histogram_quantile(0.50, rate(system_scan_latency_seconds_bucket[5m]))",
            "legendFormat": "P50"
        }, {
            "expr": "histogram_quantile(0.95, rate(system_scan_latency_seconds_bucket[5m]))",
            "legendFormat": "P95"
        }, {
            "expr": "histogram_quantile(0.99, rate(system_scan_latency_seconds_bucket[5m]))",
            "legendFormat": "P99"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "s",
                "custom": {
                    "drawStyle": "line",
                    "lineWidth": 2
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
    })

    builder.add_panel({
        "title": "LLM Latency Distribution",
        "type": "timeseries",
        "targets": [{
            "expr": "histogram_quantile(0.50, rate(system_llm_latency_seconds_bucket[5m]))",
            "legendFormat": "P50"
        }, {
            "expr": "histogram_quantile(0.95, rate(system_llm_latency_seconds_bucket[5m]))",
            "legendFormat": "P95"
        }, {
            "expr": "histogram_quantile(0.99, rate(system_llm_latency_seconds_bucket[5m]))",
            "legendFormat": "P99"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "s",
                "custom": {
                    "drawStyle": "line",
                    "lineWidth": 2
                }
            }
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
    })

    # Row 3: System Resources
    builder.add_panel({
        "title": "Memory Usage",
        "type": "timeseries",
        "targets": [{
            "expr": "system_memory_usage_mb",
            "legendFormat": "Memory Usage MB"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "decbytes",
                "custom": {
                    "drawStyle": "line",
                    "lineWidth": 2,
                    "fillOpacity": 20
                }
            }
        },
        "gridPos": {"h": 8, "w": 8, "x": 0, "y": 16}
    })

    builder.add_panel({
        "title": "CPU Usage",
        "type": "timeseries",
        "targets": [{
            "expr": "system_cpu_usage_percent",
            "legendFormat": "CPU Usage %"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "percent",
                "min": 0,
                "max": 100,
                "custom": {
                    "drawStyle": "line",
                    "lineWidth": 2,
                    "fillOpacity": 20
                }
            }
        },
        "gridPos": {"h": 8, "w": 8, "x": 8, "y": 16}
    })

    builder.add_panel({
        "title": "Error Breakdown",
        "type": "timeseries",
        "targets": [{
            "expr": "rate(system_errors_total[5m])",
            "legendFormat": "{{error_type}}"
        }],
        "fieldConfig": {
            "defaults": {
                "unit": "reqps",
                "custom": {
                    "drawStyle": "line",
                    "lineWidth": 2,
                    "stacking": {"mode": "normal"}
                }
            }
        },
        "gridPos": {"h": 8, "w": 8, "x": 16, "y": 16}
    })

    return builder.build()


def create_alert_rules() -> list[dict[str, Any]]:
    """Create Prometheus alert rules for the trading system"""
    return [
        {
            "alert": "TradingDrawdownHigh",
            "expr": "trading_drawdown_current_percent > 8",
            "for": "1m",
            "labels": {
                "severity": "critical",
                "component": "trading"
            },
            "annotations": {
                "summary": "Trading drawdown is critically high",
                "description": "Current drawdown is {{ $value }}%, exceeding the 8% threshold"
            }
        },
        {
            "alert": "ScanLatencyHigh",
            "expr": "histogram_quantile(0.95, rate(system_scan_latency_seconds_bucket[5m])) > 1.0",
            "for": "2m",
            "labels": {
                "severity": "warning",
                "component": "system"
            },
            "annotations": {
                "summary": "Market scan latency is high",
                "description": "P95 scan latency is {{ $value }}s, exceeding 1.0s threshold"
            }
        },
        {
            "alert": "LLMLatencyHigh",
            "expr": "histogram_quantile(0.95, rate(system_llm_latency_seconds_bucket[5m])) > 3.0",
            "for": "2m",
            "labels": {
                "severity": "warning",
                "component": "llm"
            },
            "annotations": {
                "summary": "LLM response latency is high",
                "description": "P95 LLM latency is {{ $value }}s, exceeding 3.0s threshold"
            }
        },
        {
            "alert": "SystemErrorRateHigh",
            "expr": "rate(system_errors_total[5m]) > 0.1",
            "for": "1m",
            "labels": {
                "severity": "warning",
                "component": "system"
            },
            "annotations": {
                "summary": "System error rate is high",
                "description": "Error rate is {{ $value }} errors/second"
            }
        },
        {
            "alert": "TradingSystemDown",
            "expr": "up{job=\"trading-system\"} == 0",
            "for": "30s",
            "labels": {
                "severity": "critical",
                "component": "system"
            },
            "annotations": {
                "summary": "Trading system is down",
                "description": "The trading system has been down for more than 30 seconds"
            }
        },
        {
            "alert": "LLMCostHigh",
            "expr": "increase(trading_llm_cost_usd_total[1h]) > 50",
            "for": "0m",
            "labels": {
                "severity": "warning",
                "component": "cost"
            },
            "annotations": {
                "summary": "LLM costs are high",
                "description": "LLM costs have increased by ${{ $value }} in the last hour"
            }
        },
        {
            "alert": "PatternPerformanceDegraded",
            "expr": "trading_pattern_hit_rate_percent < 30",
            "for": "5m",
            "labels": {
                "severity": "warning",
                "component": "trading"
            },
            "annotations": {
                "summary": "Pattern performance is degraded",
                "description": "Pattern {{ $labels.pattern_id }} hit rate is {{ $value }}%, below 30% threshold"
            }
        }
    ]


def export_dashboards_and_alerts(output_dir: str = "grafana_config"):
    """Export all dashboards and alert rules to files"""
    import os

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Export dashboards
    dashboards = {
        "trading_performance.json": create_trading_performance_dashboard(),
        "system_performance.json": create_system_performance_dashboard()
    }

    for filename, dashboard in dashboards.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(dashboard, f, indent=2)
        print(f"Exported dashboard: {filepath}")

    # Export alert rules
    alert_rules = {
        "groups": [{
            "name": "trading_system_alerts",
            "rules": create_alert_rules()
        }]
    }

    alerts_filepath = os.path.join(output_dir, "alert_rules.yml")
    import yaml
    with open(alerts_filepath, 'w') as f:
        yaml.dump(alert_rules, f, default_flow_style=False)
    print(f"Exported alert rules: {alerts_filepath}")


def create_prometheus_config() -> dict[str, Any]:
    """Create Prometheus configuration for the trading system"""
    return {
        "global": {
            "scrape_interval": "15s",
            "evaluation_interval": "15s"
        },
        "rule_files": [
            "alert_rules.yml"
        ],
        "alerting": {
            "alertmanagers": [{
                "static_configs": [{
                    "targets": ["alertmanager:9093"]
                }]
            }]
        },
        "scrape_configs": [{
            "job_name": "trading-system",
            "static_configs": [{
                "targets": ["localhost:8000"]
            }],
            "scrape_interval": "5s",
            "metrics_path": "/metrics"
        }, {
            "job_name": "execution-gateway",
            "static_configs": [{
                "targets": ["localhost:8001"]
            }],
            "scrape_interval": "5s",
            "metrics_path": "/metrics"
        }]
    }


if __name__ == "__main__":
    # Export all configurations
    export_dashboards_and_alerts()

    # Export Prometheus config
    import yaml
    with open("grafana_config/prometheus.yml", 'w') as f:
        yaml.dump(create_prometheus_config(), f, default_flow_style=False)

    print("All Grafana configurations exported successfully!")
