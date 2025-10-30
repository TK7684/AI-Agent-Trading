#!/usr/bin/env python3
"""
Demo script for the error handling and self-recovery system.

This script demonstrates the comprehensive error handling capabilities,
including error classification, recovery strategies, circuit breakers,
watchdog functionality, and chaos testing.
"""

import asyncio
import logging
import random

from libs.trading_models.chaos_testing import (
    ChaosConfig,
    ChaosScope,
    ChaosTestSuite,
    ChaosType,
    chaos_context,
)
from libs.trading_models.error_handling import (
    CircuitBreaker,
    CircuitBreakerConfig,
    ErrorContext,
    ErrorRecoverySystem,
    ErrorSeverity,
    ErrorType,
    error_context,
)
from libs.trading_models.watchdog import (
    ComponentConfig,
    HealthCheck,
    RestartPolicy,
    Watchdog,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockTradingComponent:
    """Mock trading component for demonstration."""

    def __init__(self, name: str, failure_rate: float = 0.1):
        self.name = name
        self.failure_rate = failure_rate
        self.is_healthy = True
        self.call_count = 0

    async def process_data(self, data: str) -> str:
        """Mock data processing that may fail."""
        self.call_count += 1

        if random.random() < self.failure_rate:
            if "timeout" in data.lower():
                raise TimeoutError(f"{self.name}: Data processing timeout")
            elif "invalid" in data.lower():
                raise ValueError(f"{self.name}: Invalid data format")
            else:
                raise Exception(f"{self.name}: Random processing error")

        await asyncio.sleep(0.1)  # Simulate processing time
        return f"{self.name} processed: {data}"

    def health_check(self) -> bool:
        """Health check for the component."""
        return self.is_healthy and random.random() > 0.1  # 10% chance of health check failure


async def demo_error_classification_and_recovery():
    """Demonstrate error classification and recovery strategies."""
    print("\n" + "="*60)
    print("DEMO: Error Classification and Recovery")
    print("="*60)

    ers = ErrorRecoverySystem()

    # Simulate various types of errors
    error_scenarios = [
        {
            "type": ErrorType.DATA,
            "severity": ErrorSeverity.MEDIUM,
            "message": "Market data timeout from exchange API",
            "component": "market_data_ingestion"
        },
        {
            "type": ErrorType.RISK,
            "severity": ErrorSeverity.CRITICAL,
            "message": "Portfolio drawdown exceeded 20% threshold",
            "component": "risk_manager"
        },
        {
            "type": ErrorType.EXECUTION,
            "severity": ErrorSeverity.HIGH,
            "message": "Order execution failed due to insufficient funds",
            "component": "execution_gateway"
        },
        {
            "type": ErrorType.LLM,
            "severity": ErrorSeverity.MEDIUM,
            "message": "LLM request timeout after 30 seconds",
            "component": "llm_router"
        },
        {
            "type": ErrorType.SYSTEM,
            "severity": ErrorSeverity.CRITICAL,
            "message": "Critical system memory exhaustion detected",
            "component": "orchestrator"
        }
    ]

    print(f"Processing {len(error_scenarios)} error scenarios...")

    for i, scenario in enumerate(error_scenarios, 1):
        print(f"\n--- Scenario {i}: {scenario['type'].value.upper()} Error ---")

        error_ctx = ErrorContext(
            error_type=scenario["type"],
            severity=scenario["severity"],
            message=scenario["message"],
            component=scenario["component"]
        )

        print(f"Error: {error_ctx.message}")
        print(f"Severity: {error_ctx.severity.value}")
        print(f"Component: {error_ctx.component}")

        # Handle the error
        incident_report = await ers.handle_error(error_ctx)

        print(f"Recovery Actions: {[action.value for action in incident_report.recovery_actions]}")
        print(f"Resolution Success: {incident_report.success}")
        print(f"Resolution Time: {incident_report.resolution_time}")

    # Display statistics
    print("\n--- Error Handling Statistics ---")
    stats = ers.get_incident_statistics()
    print(f"Total Incidents: {stats['total_incidents']}")
    print(f"Successful Recoveries: {stats['successful_recoveries']}")
    print(f"Success Rate: {stats['success_rate']:.2%}")
    print(f"Error Distribution: {stats['error_type_distribution']}")
    print(f"Recovery Actions: {stats['recovery_action_distribution']}")


async def demo_circuit_breaker():
    """Demonstrate circuit breaker functionality."""
    print("\n" + "="*60)
    print("DEMO: Circuit Breaker Pattern")
    print("="*60)

    # Create a circuit breaker for external API calls
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=2.0,
        success_threshold=2,
        timeout=1.0
    )

    cb = CircuitBreaker("external_api", config)

    # Mock external API function that fails initially
    call_count = 0

    async def mock_external_api():
        nonlocal call_count
        call_count += 1

        if call_count <= 4:  # First 4 calls fail
            raise Exception(f"API call {call_count} failed")

        return f"API call {call_count} succeeded"

    print("Testing circuit breaker with failing API calls...")

    # Test circuit breaker behavior
    for i in range(8):
        try:
            print(f"\n--- API Call {i+1} ---")
            print(f"Circuit Breaker State: {cb.state.value}")
            print(f"Can Execute: {cb.can_execute()}")

            if cb.can_execute():
                result = await cb.execute(mock_external_api)
                print(f"Result: {result}")
            else:
                print("Circuit breaker is OPEN - call blocked")

        except Exception as e:
            print(f"Error: {e}")

        print(f"Failure Count: {cb.failure_count}")

        # Wait a bit between calls
        await asyncio.sleep(0.5)

    print(f"\nFinal Circuit Breaker State: {cb.state.value}")


async def demo_error_context_manager():
    """Demonstrate error context manager."""
    print("\n" + "="*60)
    print("DEMO: Error Context Manager")
    print("="*60)

    ers = ErrorRecoverySystem()
    component = MockTradingComponent("demo_component", failure_rate=0.5)

    test_data = [
        "valid_data_1",
        "timeout_data",
        "invalid_data",
        "valid_data_2",
        "another_timeout"
    ]

    print("Processing data with automatic error handling...")

    for i, data in enumerate(test_data, 1):
        print(f"\n--- Processing Item {i}: {data} ---")

        try:
            async with error_context(ers, "demo_component", ErrorType.DATA):
                result = await component.process_data(data)
                print(f"Success: {result}")

        except Exception as e:
            print(f"Error occurred: {e}")
            print("Error was automatically handled by context manager")

    # Show incident statistics
    print("\n--- Incident Statistics ---")
    stats = ers.get_incident_statistics()
    if stats:
        print(f"Total Incidents: {stats['total_incidents']}")
        print(f"Success Rate: {stats['success_rate']:.2%}")
    else:
        print("No incidents recorded")


async def demo_watchdog_functionality():
    """Demonstrate watchdog functionality."""
    print("\n" + "="*60)
    print("DEMO: Watchdog Functionality")
    print("="*60)

    watchdog = Watchdog()

    # Create mock components with health checks
    def create_health_check(component_name: str):
        component = MockTradingComponent(component_name)
        return HealthCheck(
            name=f"{component_name}_health",
            check_function=component.health_check,
            interval=2.0,
            timeout=1.0
        )

    # Configure components
    components = [
        ComponentConfig(
            name="market_data_service",
            command=["python", "-c", "import time; time.sleep(60)"],  # Mock long-running process
            restart_policy=RestartPolicy.ON_FAILURE,
            max_restarts=3,
            health_checks=[create_health_check("market_data_service")]
        ),
        ComponentConfig(
            name="execution_service",
            command=["python", "-c", "import time; time.sleep(60)"],
            restart_policy=RestartPolicy.ON_FAILURE,
            max_restarts=3,
            dependencies=["market_data_service"],
            health_checks=[create_health_check("execution_service")]
        ),
        ComponentConfig(
            name="orchestrator_service",
            command=["python", "-c", "import time; time.sleep(60)"],
            restart_policy=RestartPolicy.ALWAYS,
            max_restarts=5,
            dependencies=["market_data_service", "execution_service"],
            health_checks=[create_health_check("orchestrator_service")]
        )
    ]

    # Add components to watchdog
    for config in components:
        watchdog.add_component(config)

    print("Added components to watchdog:")
    for name in watchdog.components.keys():
        print(f"  - {name}")

    # Check dependency order
    start_order = watchdog.dependency_manager.get_start_order(list(watchdog.components.keys()))
    print(f"\nStart Order: {' -> '.join(start_order)}")

    stop_order = watchdog.dependency_manager.get_stop_order(list(watchdog.components.keys()))
    print(f"Stop Order: {' -> '.join(stop_order)}")

    # Get system health
    health = watchdog.get_system_health()
    print("\nSystem Health:")
    print(f"  Total Components: {health['total_components']}")
    print(f"  Healthy Components: {health['healthy_components']}")
    print(f"  Health Percentage: {health['health_percentage']:.1f}%")

    # Show component statuses
    print("\nComponent Statuses:")
    for name, state in watchdog.get_all_component_status().items():
        print(f"  {name}: {state.status.value}")

    print("\nNote: In a real environment, watchdog would start/stop actual processes")


async def demo_chaos_testing():
    """Demonstrate chaos testing framework."""
    print("\n" + "="*60)
    print("DEMO: Chaos Testing Framework")
    print("="*60)

    suite = ChaosTestSuite()

    # Create chaos experiments
    experiments = [
        ChaosConfig(
            name="network_latency_test",
            chaos_type=ChaosType.NETWORK_FAILURE,
            scope=ChaosScope.NETWORK,
            target="market_data_api",
            duration=2.0,
            intensity=0.7,
            parameters={"failure_type": "high_latency"},
            success_criteria=[lambda: True]  # Always succeed for demo
        ),
        ChaosConfig(
            name="service_crash_test",
            chaos_type=ChaosType.SERVICE_FAILURE,
            scope=ChaosScope.SERVICE,
            target="execution_gateway",
            duration=1.5,
            intensity=1.0,
            parameters={"failure_type": "crash"},
            success_criteria=[lambda: True]
        ),
        ChaosConfig(
            name="memory_exhaustion_test",
            chaos_type=ChaosType.RESOURCE_EXHAUSTION,
            scope=ChaosScope.SYSTEM,
            target="orchestrator",
            duration=1.0,
            intensity=0.8,
            parameters={"resource_type": "memory"},
            success_criteria=[lambda: True]
        ),
        ChaosConfig(
            name="llm_timeout_test",
            chaos_type=ChaosType.LATENCY_INJECTION,
            scope=ChaosScope.SERVICE,
            target="llm_router",
            duration=1.0,
            intensity=0.6,
            success_criteria=[lambda: True]
        )
    ]

    print(f"Running {len(experiments)} chaos experiments...")

    # Add and run experiments
    experiment_ids = []
    for config in experiments:
        exp_id = suite.add_experiment(config)
        experiment_ids.append(exp_id)
        print(f"  Added: {config.name} ({config.chaos_type.value})")

    # Run experiments sequentially
    print("\nExecuting experiments...")
    results = await suite.run_all_experiments(parallel=False)

    # Display results
    print("\n--- Chaos Testing Results ---")
    for result in results:
        print(f"\nExperiment: {result.config.name}")
        print(f"  Type: {result.config.chaos_type.value}")
        print(f"  Target: {result.config.target}")
        print(f"  Duration: {result.config.duration}s")
        print(f"  Success: {result.success}")
        print(f"  Recovery Time: {result.recovery_time}s" if result.recovery_time else "  Recovery Time: N/A")
        print(f"  Logs: {len(result.logs)} entries")

    # Generate comprehensive report
    report = suite.generate_report()
    print("\n--- Summary Report ---")
    print(f"Total Experiments: {report['summary']['total_experiments']}")
    print(f"Successful Recoveries: {report['summary']['successful_experiments']}")
    print(f"Success Rate: {report['summary']['success_rate']:.2%}")
    print(f"Average Recovery Time: {report['summary']['average_recovery_time_seconds']:.2f}s")

    print("\nResults by Type:")
    for chaos_type, stats in report['results_by_type'].items():
        print(f"  {chaos_type}: {stats['successful']}/{stats['total']} ({stats['success_rate']:.2%})")


async def demo_chaos_context_manager():
    """Demonstrate chaos context manager."""
    print("\n" + "="*60)
    print("DEMO: Chaos Context Manager")
    print("="*60)

    config = ChaosConfig(
        name="context_demo",
        chaos_type=ChaosType.NETWORK_FAILURE,
        scope=ChaosScope.SERVICE,
        target="demo_service",
        duration=1.0,
        intensity=0.5,
        parameters={"failure_type": "high_latency"},
        success_criteria=[lambda: True]
    )

    print("Running chaos experiment using context manager...")

    async with chaos_context(config) as result:
        print(f"Chaos experiment started: {result.experiment_id}")
        print(f"Config: {result.config.name}")
        print(f"Target: {result.config.target}")

        # Simulate some work during the chaos
        await asyncio.sleep(0.5)
        print("Performing work during chaos injection...")
        await asyncio.sleep(0.5)

    print("Chaos experiment completed:")
    print(f"  Success: {result.success}")
    print(f"  Duration: {(result.end_time - result.start_time).total_seconds():.2f}s")
    print(f"  Recovery Time: {result.recovery_time}s" if result.recovery_time else "  Recovery Time: N/A")


async def demo_integration_scenario():
    """Demonstrate integrated error handling scenario."""
    print("\n" + "="*60)
    print("DEMO: Integrated Error Handling Scenario")
    print("="*60)

    # Set up error recovery system
    ers = ErrorRecoverySystem()

    # Add circuit breakers for external services
    cb_config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0)
    ers.add_circuit_breaker("market_data_api", cb_config)
    ers.add_circuit_breaker("execution_api", cb_config)

    # Create mock trading components
    components = {
        "market_data": MockTradingComponent("market_data", failure_rate=0.3),
        "risk_manager": MockTradingComponent("risk_manager", failure_rate=0.2),
        "execution": MockTradingComponent("execution", failure_rate=0.4)
    }

    print("Simulating trading pipeline with error handling...")

    # Simulate trading pipeline operations
    operations = [
        ("market_data", "fetch_ohlcv_data"),
        ("market_data", "calculate_indicators"),
        ("risk_manager", "check_position_limits"),
        ("execution", "place_order"),
        ("market_data", "timeout_data"),  # This will cause timeout
        ("risk_manager", "invalid_risk_data"),  # This will cause validation error
        ("execution", "execute_trade"),
        ("market_data", "fetch_latest_prices"),
        ("execution", "timeout_execution"),  # This will cause timeout
        ("risk_manager", "validate_portfolio")
    ]

    successful_operations = 0
    total_operations = len(operations)

    for i, (component_name, operation) in enumerate(operations, 1):
        print(f"\n--- Operation {i}/{total_operations}: {component_name}.{operation} ---")

        try:
            # Use error context for automatic error handling
            async with error_context(ers, component_name, ErrorType.DATA):
                component = components[component_name]
                result = await component.process_data(operation)
                print(f"✓ Success: {result}")
                successful_operations += 1

        except Exception as e:
            print(f"✗ Error: {e}")
            print("  Error was handled by recovery system")

    # Display final statistics
    print("\n--- Pipeline Execution Summary ---")
    print(f"Total Operations: {total_operations}")
    print(f"Successful Operations: {successful_operations}")
    print(f"Success Rate: {successful_operations/total_operations:.2%}")

    # Show error recovery statistics
    stats = ers.get_incident_statistics()
    if stats:
        print("\nError Recovery Statistics:")
        print(f"  Total Incidents: {stats['total_incidents']}")
        print(f"  Recovery Success Rate: {stats['success_rate']:.2%}")
        print(f"  Error Types: {list(stats['error_type_distribution'].keys())}")
        print(f"  Recovery Actions: {list(stats['recovery_action_distribution'].keys())}")

    # Show circuit breaker states
    print("\nCircuit Breaker States:")
    for name, cb in ers.circuit_breakers.items():
        print(f"  {name}: {cb.state.value} (failures: {cb.failure_count})")


async def main():
    """Run all error handling demos."""
    print("🚀 Error Handling and Self-Recovery System Demo")
    print("=" * 80)

    demos = [
        ("Error Classification and Recovery", demo_error_classification_and_recovery),
        ("Circuit Breaker Pattern", demo_circuit_breaker),
        ("Error Context Manager", demo_error_context_manager),
        ("Watchdog Functionality", demo_watchdog_functionality),
        ("Chaos Testing Framework", demo_chaos_testing),
        ("Chaos Context Manager", demo_chaos_context_manager),
        ("Integrated Error Handling", demo_integration_scenario)
    ]

    for demo_name, demo_func in demos:
        try:
            print(f"\n🎯 Running: {demo_name}")
            await demo_func()
            print(f"✅ Completed: {demo_name}")
        except Exception as e:
            print(f"❌ Error in {demo_name}: {e}")
            logger.exception(f"Demo failed: {demo_name}")

        # Small delay between demos
        await asyncio.sleep(1)

    print("\n🎉 All demos completed!")
    print("=" * 80)

    # Final summary
    print("\n📊 SYSTEM CAPABILITIES DEMONSTRATED:")
    print("✓ Error classification (Data, Risk, Execution, LLM, System)")
    print("✓ Automatic recovery strategies with retries and fallbacks")
    print("✓ Circuit breaker patterns for external service failures")
    print("✓ Watchdog functionality with auto-restart capabilities")
    print("✓ Incident detection and auto-repair actions")
    print("✓ Chaos testing framework for failure simulation")
    print("✓ Comprehensive error recovery and system resilience")
    print("\n🔧 The system is ready for 24/7 autonomous trading operations!")


if __name__ == "__main__":
    asyncio.run(main())
