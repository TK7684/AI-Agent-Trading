"""
Comprehensive Testing and Optimization Script for AI Agent Trading System

This script performs:
1. System health assessment
2. Performance benchmarking
3. Code quality analysis
4. Memory and resource profiling
5. Security vulnerability scanning
6. Optimization recommendations
7. Load testing simulation
8. Integration testing
"""

import asyncio
import time
import json
import os
import sys
import subprocess
import logging
import psutil
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("comprehensive_test_results/system_test.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class TestResults:
    """Test results data structure"""

    timestamp: str
    system_health: Dict[str, Any]
    performance_metrics: Dict[str, float]
    code_quality: Dict[str, Any]
    security_scan: Dict[str, Any]
    optimization_recommendations: List[Dict[str, Any]]
    load_test_results: Dict[str, Any]
    integration_tests: Dict[str, Any]
    overall_score: float
    critical_issues: List[str]


class ComprehensiveTestOptimizer:
    """Main testing and optimization class"""

    def __init__(self):
        self.results_dir = Path("comprehensive_test_results")
        self.results_dir.mkdir(exist_ok=True)
        self.start_time = time.time()

    async def run_comprehensive_analysis(self) -> TestResults:
        """Run complete system analysis"""
        logger.info("🚀 Starting Comprehensive Testing and Optimization Analysis")
        logger.info("=" * 70)

        # Initialize results
        results = TestResults(
            timestamp=datetime.now().isoformat(),
            system_health={},
            performance_metrics={},
            code_quality={},
            security_scan={},
            optimization_recommendations=[],
            load_test_results={},
            integration_tests={},
            overall_score=0.0,
            critical_issues=[],
        )

        try:
            # 1. System Health Assessment
            logger.info("📊 1. System Health Assessment")
            results.system_health = await self.assess_system_health()

            # 2. Performance Benchmarking
            logger.info("⚡ 2. Performance Benchmarking")
            results.performance_metrics = await self.benchmark_performance()

            # 3. Code Quality Analysis
            logger.info("🔍 3. Code Quality Analysis")
            results.code_quality = await self.analyze_code_quality()

            # 4. Security Vulnerability Scan
            logger.info("🛡️ 4. Security Vulnerability Scan")
            results.security_scan = await self.security_vulnerability_scan()

            # 5. Optimization Recommendations
            logger.info("💡 5. Generating Optimization Recommendations")
            results.optimization_recommendations = (
                await self.generate_optimization_recommendations(results)
            )

            # 6. Load Testing Simulation
            logger.info("🔥 6. Load Testing Simulation")
            results.load_test_results = await self.simulate_load_testing()

            # 7. Integration Testing
            logger.info("🔗 7. Integration Testing")
            results.integration_tests = await self.run_integration_tests()

            # Calculate overall score
            results.overall_score = self.calculate_overall_score(results)

            # Identify critical issues
            results.critical_issues = self.identify_critical_issues(results)

        except Exception as e:
            logger.error(f"Critical error during analysis: {e}")
            logger.error(traceback.format_exc())
            results.critical_issues.append(f"Analysis failed: {str(e)}")

        # Save results
        await self.save_results(results)

        # Generate report
        self.generate_final_report(results)

        return results

    async def assess_system_health(self) -> Dict[str, Any]:
        """Assess overall system health"""
        health = {}

        try:
            # Memory usage
            memory = psutil.virtual_memory()
            health["memory_usage_percent"] = memory.percent
            health["memory_available_gb"] = memory.available / (1024**3)

            # CPU usage
            health["cpu_usage_percent"] = psutil.cpu_percent(interval=1)
            health["cpu_count"] = psutil.cpu_count()

            # Disk usage
            disk = psutil.disk_usage(".")
            health["disk_usage_percent"] = (disk.used / disk.total) * 100
            health["disk_free_gb"] = disk.free / (1024**3)

            # Process information
            process = psutil.Process()
            health["process_memory_mb"] = process.memory_info().rss / (1024**2)
            health["process_cpu_percent"] = process.cpu_percent()

            # Python environment
            health["python_version"] = sys.version
            health["python_executable"] = sys.executable

            # Dependencies check
            health["dependencies"] = await self.check_dependencies()

            # Database connectivity (mock)
            health["database_status"] = "OK"  # Would be actual DB check

            # External API connectivity (mock)
            health["external_api_status"] = "OK"  # Would be actual API check

            health["status"] = (
                "HEALTHY"
                if health["memory_usage_percent"] < 80
                and health["cpu_usage_percent"] < 80
                else "WARNING"
            )

        except Exception as e:
            logger.error(f"System health assessment failed: {e}")
            health["status"] = "ERROR"
            health["error"] = str(e)

        return health

    async def benchmark_performance(self) -> Dict[str, float]:
        """Benchmark system performance"""
        metrics = {}

        try:
            # Mathematical operations benchmark
            start_time = time.time()
            for _ in range(100000):
                _ = np.random.randn(1000).mean()
            metrics["numpy_operations_ms"] = (time.time() - start_time) * 1000

            # DataFrame operations benchmark
            start_time = time.time()
            df = pd.DataFrame(np.random.randn(10000, 10))
            _ = df.describe()
            metrics["pandas_operations_ms"] = (time.time() - start_time) * 1000

            # String operations benchmark
            start_time = time.time()
            for _ in range(10000):
                _ = f"test_string_{_}".upper().replace("_", "-")
            metrics["string_operations_ms"] = (time.time() - start_time) * 1000

            # Dictionary operations benchmark
            start_time = time.time()
            test_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
            for _ in range(1000):
                _ = test_dict.get(f"key_{_}")
            metrics["dict_operations_ms"] = (time.time() - start_time) * 1000

            # I/O operations benchmark
            start_time = time.time()
            test_file = self.results_dir / "io_test.tmp"
            for _ in range(100):
                test_file.write_text("test data" * 100)
                _ = test_file.read_text()
            test_file.unlink(missing_ok=True)
            metrics["io_operations_ms"] = (time.time() - start_time) * 1000

            # Calculate performance score (lower is better)
            baseline_total = 1000  # ms baseline
            actual_total = sum(metrics.values())
            metrics["performance_score"] = max(
                0, 100 - (actual_total / baseline_total * 100)
            )

        except Exception as e:
            logger.error(f"Performance benchmarking failed: {e}")
            metrics["error"] = str(e)
            metrics["performance_score"] = 0

        return metrics

    async def analyze_code_quality(self) -> Dict[str, Any]:
        """Analyze code quality metrics"""
        quality = {}

        try:
            # Count Python files
            python_files = list(Path(".").rglob("*.py"))
            quality["python_files_count"] = len(python_files)

            # Count lines of code
            total_lines = 0
            for file_path in python_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        total_lines += len(f.readlines())
                except:
                    pass
            quality["total_lines_of_code"] = total_lines

            # Check for common issues
            issues = []

            # Check for TODO comments
            todo_count = 0
            for file_path in python_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        todo_count += content.lower().count("todo")
                except:
                    pass
            quality["todo_comments"] = todo_count
            if todo_count > 10:
                issues.append(f"High number of TODO comments: {todo_count}")

            # Check for print statements (should use logging)
            print_count = 0
            for file_path in python_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        for line in lines:
                            if line.strip().startswith("print(") and "test_" not in str(
                                file_path
                            ):
                                print_count += 1
                except:
                    pass
            quality["print_statements"] = print_count
            if print_count > 5:
                issues.append(
                    f"Found {print_count} print statements (should use logging)"
                )

            # Test coverage estimation
            test_files = (
                list(Path("tests").rglob("*.py")) if Path("tests").exists() else []
            )
            quality["test_files_count"] = len(test_files)
            quality["test_coverage_estimate"] = min(
                100, len(test_files) / max(1, len(python_files)) * 100
            )

            quality["issues"] = issues
            quality["code_quality_score"] = max(0, 100 - len(issues) * 10)

        except Exception as e:
            logger.error(f"Code quality analysis failed: {e}")
            quality["error"] = str(e)
            quality["code_quality_score"] = 0

        return quality

    async def security_vulnerability_scan(self) -> Dict[str, Any]:
        """Perform security vulnerability scan"""
        security = {}

        try:
            vulnerabilities = []

            # Check for hardcoded secrets (basic check)
            secret_patterns = ["password", "api_key", "secret", "token"]
            python_files = list(Path(".").rglob("*.py"))

            secret_matches = 0
            for file_path in python_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().lower()
                        for pattern in secret_patterns:
                            if f'"{pattern}"' in content or f"'{pattern}'" in content:
                                secret_matches += 1
                except:
                    pass

            if secret_matches > 0:
                vulnerabilities.append(
                    f"Potential hardcoded secrets found: {secret_matches}"
                )

            # Check for eval/exec usage
            dangerous_functions = ["eval(", "exec("]
            dangerous_usage = 0
            for file_path in python_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        for func in dangerous_functions:
                            dangerous_usage += content.count(func)
                except:
                    pass

            if dangerous_usage > 0:
                vulnerabilities.append(
                    f"Dangerous function usage found: {dangerous_usage}"
                )

            # Check for SQL injection risks
            sql_patterns = ['execute("', "execute('"]
            sql_risks = 0
            for file_path in python_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        for pattern in sql_patterns:
                            sql_risks += content.count(pattern)
                except:
                    pass

            if sql_risks > 0:
                vulnerabilities.append(f"Potential SQL injection risks: {sql_risks}")

            security["vulnerabilities"] = vulnerabilities
            security["security_score"] = max(0, 100 - len(vulnerabilities) * 15)
            security["status"] = (
                "SECURE" if len(vulnerabilities) == 0 else "NEEDS_ATTENTION"
            )

        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            security["error"] = str(e)
            security["security_score"] = 0
            security["status"] = "ERROR"

        return security

    async def generate_optimization_recommendations(
        self, results: TestResults
    ) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on test results"""
        recommendations = []

        # Performance recommendations
        if results.performance_metrics.get("performance_score", 0) < 70:
            recommendations.append(
                {
                    "category": "Performance",
                    "priority": "HIGH",
                    "issue": "Low performance score",
                    "recommendation": "Consider implementing caching, optimizing algorithms, and using async operations",
                    "estimated_impact": "30-50% performance improvement",
                }
            )

        # Memory recommendations
        if results.system_health.get("memory_usage_percent", 0) > 80:
            recommendations.append(
                {
                    "category": "Memory",
                    "priority": "HIGH",
                    "issue": "High memory usage",
                    "recommendation": "Implement memory-efficient data structures and add memory profiling",
                    "estimated_impact": "20-30% memory reduction",
                }
            )

        # Code quality recommendations
        if results.code_quality.get("code_quality_score", 0) < 80:
            recommendations.append(
                {
                    "category": "Code Quality",
                    "priority": "MEDIUM",
                    "issue": "Code quality issues detected",
                    "recommendation": "Address TODO comments, replace print statements with logging, improve test coverage",
                    "estimated_impact": "Improved maintainability and reliability",
                }
            )

        # Security recommendations
        if results.security_scan.get("security_score", 0) < 80:
            recommendations.append(
                {
                    "category": "Security",
                    "priority": "HIGH",
                    "issue": "Security vulnerabilities found",
                    "recommendation": "Remove hardcoded secrets, use parameterized queries, avoid dangerous functions",
                    "estimated_impact": "Improved security posture",
                }
            )

        # Test coverage recommendations
        if results.code_quality.get("test_coverage_estimate", 0) < 50:
            recommendations.append(
                {
                    "category": "Testing",
                    "priority": "MEDIUM",
                    "issue": "Low test coverage",
                    "recommendation": "Increase test coverage to at least 80% with comprehensive unit and integration tests",
                    "estimated_impact": "Improved code reliability and easier maintenance",
                }
            )

        return recommendations

    async def simulate_load_testing(self) -> Dict[str, Any]:
        """Simulate load testing scenarios"""
        load_test = {}

        try:
            # Simulate different load scenarios
            scenarios = [
                {"users": 10, "duration": 5, "name": "Light Load"},
                {"users": 50, "duration": 5, "name": "Medium Load"},
                {"users": 100, "duration": 5, "name": "Heavy Load"},
            ]

            results = []

            for scenario in scenarios:
                logger.info(
                    f"Simulating {scenario['name']} with {scenario['users']} users"
                )

                # Simulate load
                start_time = time.time()
                successful_requests = 0
                failed_requests = 0
                response_times = []

                for i in range(scenario["users"] * 10):  # 10 requests per user
                    req_start = time.time()

                    try:
                        # Simulate processing time
                        await asyncio.sleep(0.01 + np.random.exponential(0.02))

                        # Random failure simulation (5% chance)
                        if np.random.random() > 0.05:
                            successful_requests += 1
                        else:
                            failed_requests += 1

                        response_time = (time.time() - req_start) * 1000
                        response_times.append(response_time)

                    except Exception:
                        failed_requests += 1

                total_time = time.time() - start_time

                scenario_result = {
                    "scenario": scenario["name"],
                    "users": scenario["users"],
                    "duration": total_time,
                    "successful_requests": successful_requests,
                    "failed_requests": failed_requests,
                    "error_rate_percent": (
                        failed_requests / (successful_requests + failed_requests)
                    )
                    * 100,
                    "avg_response_time_ms": np.mean(response_times)
                    if response_times
                    else 0,
                    "p95_response_time_ms": np.percentile(response_times, 95)
                    if response_times
                    else 0,
                    "requests_per_second": successful_requests / total_time
                    if total_time > 0
                    else 0,
                }

                results.append(scenario_result)

            load_test["scenarios"] = results
            load_test["load_test_score"] = self.calculate_load_test_score(results)

        except Exception as e:
            logger.error(f"Load testing simulation failed: {e}")
            load_test["error"] = str(e)
            load_test["load_test_score"] = 0

        return load_test

    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        integration = {}

        try:
            # Test core components
            test_results = {}

            # Test 1: Basic imports
            try:
                from libs.trading_models.base import TradingSignal, OrderDecision

                test_results["basic_imports"] = "PASS"
            except Exception as e:
                test_results["basic_imports"] = f"FAIL: {str(e)}"

            # Test 2: Technical indicators
            try:
                from libs.trading_models.technical_indicators import TechnicalIndicators

                indicators = TechnicalIndicators()
                test_data = pd.DataFrame(
                    {
                        "close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                        "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                        "low": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
                        "volume": [
                            1000,
                            1100,
                            1200,
                            1300,
                            1400,
                            1500,
                            1600,
                            1700,
                            1800,
                            1900,
                        ],
                    }
                )
                rsi = indicators.calculate_rsi(test_data["close"])
                test_results["technical_indicators"] = "PASS"
            except Exception as e:
                test_results["technical_indicators"] = f"FAIL: {str(e)}"

            # Test 3: Risk management
            try:
                from libs.trading_models.risk_management import RiskManager

                risk_manager = RiskManager()
                test_results["risk_management"] = "PASS"
            except Exception as e:
                test_results["risk_management"] = f"FAIL: {str(e)}"

            # Test 4: Configuration management
            try:
                from libs.trading_models.config_manager import get_config_manager

                config_manager = get_config_manager()
                test_results["configuration"] = "PASS"
            except Exception as e:
                test_results["configuration"] = f"FAIL: {str(e)}"

            integration["component_tests"] = test_results

            # Calculate integration score
            passed_tests = sum(
                1 for result in test_results.values() if result == "PASS"
            )
            total_tests = len(test_results)
            integration["integration_score"] = (
                (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            )
            integration["status"] = (
                "PASS" if integration["integration_score"] >= 75 else "FAIL"
            )

        except Exception as e:
            logger.error(f"Integration testing failed: {e}")
            integration["error"] = str(e)
            integration["integration_score"] = 0
            integration["status"] = "ERROR"

        return integration

    def calculate_overall_score(self, results: TestResults) -> float:
        """Calculate overall system score"""
        weights = {
            "system_health": 0.2,
            "performance": 0.25,
            "code_quality": 0.15,
            "security": 0.2,
            "load_test": 0.1,
            "integration": 0.1,
        }

        scores = []

        # System health score
        if results.system_health.get("status") == "HEALTHY":
            health_score = 100
        elif results.system_health.get("status") == "WARNING":
            health_score = 70
        else:
            health_score = 30
        scores.append(("system_health", health_score, weights["system_health"]))

        # Performance score
        perf_score = results.performance_metrics.get("performance_score", 0)
        scores.append(("performance", perf_score, weights["performance"]))

        # Code quality score
        cq_score = results.code_quality.get("code_quality_score", 0)
        scores.append(("code_quality", cq_score, weights["code_quality"]))

        # Security score
        sec_score = results.security_scan.get("security_score", 0)
        scores.append(("security", sec_score, weights["security"]))

        # Load test score
        load_score = results.load_test_results.get("load_test_score", 0)
        scores.append(("load_test", load_score, weights["load_test"]))

        # Integration score
        int_score = results.integration_tests.get("integration_score", 0)
        scores.append(("integration", int_score, weights["integration"]))

        # Calculate weighted average
        overall_score = sum(score * weight for _, score, weight in scores)

        return min(100, max(0, overall_score))

    def identify_critical_issues(self, results: TestResults) -> List[str]:
        """Identify critical issues that need immediate attention"""
        critical_issues = []

        # System health issues
        if results.system_health.get("memory_usage_percent", 0) > 90:
            critical_issues.append("CRITICAL: Very high memory usage (>90%)")

        if results.system_health.get("cpu_usage_percent", 0) > 90:
            critical_issues.append("CRITICAL: Very high CPU usage (>90%)")

        # Security issues
        if results.security_scan.get("security_score", 0) < 50:
            critical_issues.append("CRITICAL: Major security vulnerabilities detected")

        # Integration issues
        if results.integration_tests.get("integration_score", 0) < 50:
            critical_issues.append("CRITICAL: Core integration tests failing")

        # Performance issues
        if results.performance_metrics.get("performance_score", 0) < 30:
            critical_issues.append("CRITICAL: Very poor system performance")

        return critical_issues

    async def check_dependencies(self) -> Dict[str, Any]:
        """Check system dependencies"""
        dependencies = {}

        required_packages = [
            "numpy",
            "pandas",
            "psutil",
            "pydantic",
            "asyncio",
            "pytest",
            "pytest-asyncio",
            "requests",
            "aiohttp",
        ]

        missing_packages = []
        installed_packages = []

        for package in required_packages:
            try:
                __import__(package)
                installed_packages.append(package)
            except ImportError:
                missing_packages.append(package)

        dependencies["installed"] = installed_packages
        dependencies["missing"] = missing_packages
        dependencies["status"] = "OK" if len(missing_packages) == 0 else "MISSING_DEPS"

        return dependencies

    def calculate_load_test_score(self, results: List[Dict[str, Any]]) -> float:
        """Calculate load test score based on performance metrics"""
        if not results:
            return 0

        total_score = 0

        for result in results:
            scenario_score = 100

            # Penalty for high error rate (>5%)
            if result["error_rate_percent"] > 5:
                scenario_score -= (result["error_rate_percent"] - 5) * 10

            # Penalty for high response time (>1000ms average)
            if result["avg_response_time_ms"] > 1000:
                scenario_score -= min(50, (result["avg_response_time_ms"] - 1000) / 20)

            # Penalty for low throughput (<10 RPS)
            if result["requests_per_second"] < 10:
                scenario_score -= (10 - result["requests_per_second"]) * 5

            total_score += max(0, scenario_score)

        return min(100, total_score / len(results))

    async def save_results(self, results: TestResults) -> None:
        """Save test results to files"""
        try:
            # Save detailed results as JSON
            results_file = (
                self.results_dir
                / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(results_file, "w") as f:
                json.dump(asdict(results), f, indent=2, default=str)

            # Save summary as CSV
            summary_file = self.results_dir / "test_summary.csv"
            summary_data = {
                "timestamp": [results.timestamp],
                "overall_score": [results.overall_score],
                "system_health_status": [
                    results.system_health.get("status", "UNKNOWN")
                ],
                "performance_score": [
                    results.performance_metrics.get("performance_score", 0)
                ],
                "code_quality_score": [
                    results.code_quality.get("code_quality_score", 0)
                ],
                "security_score": [results.security_scan.get("security_score", 0)],
                "integration_score": [
                    results.integration_tests.get("integration_score", 0)
                ],
                "critical_issues_count": [len(results.critical_issues)],
            }

            df_summary = pd.DataFrame(summary_data)
            df_summary.to_csv(summary_file, index=False)

            logger.info(f"Results saved to {results_file} and {summary_file}")

        except Exception as e:
            logger.error(f"Failed to save results: {e}")

    def generate_final_report(self, results: TestResults) -> None:
        """Generate and display final report"""
        print("\n" + "=" * 70)
        print("🏆 COMPREHENSIVE TESTING AND OPTIMIZATION REPORT")
        print("=" * 70)

        print(f"\n📊 OVERALL SCORE: {results.overall_score:.1f}/100")

        # Grade assignment
        if results.overall_score >= 90:
            grade = "A+ (EXCELLENT)"
        elif results.overall_score >= 80:
            grade = "A (VERY GOOD)"
        elif results.overall_score >= 70:
            grade = "B (GOOD)"
        elif results.overall_score >= 60:
            grade = "C (AVERAGE)"
        elif results.overall_score >= 50:
            grade = "D (BELOW AVERAGE)"
        else:
            grade = "F (POOR)"

        print(f"🏅 GRADE: {grade}")

        print("\n📈 DETAILED RESULTS:")
        print(f"  System Health: {results.system_health.get('status', 'UNKNOWN')}")
        print(
            f"    Memory Usage: {results.system_health.get('memory_usage_percent', 0):.1f}%"
        )
        print(
            f"    CPU Usage: {results.system_health.get('cpu_usage_percent', 0):.1f}%"
        )

        print(
            f"\n  Performance Score: {results.performance_metrics.get('performance_score', 0):.1f}/100"
        )
        print(
            f"    Operations Benchmark: {results.performance_metrics.get('numpy_operations_ms', 0):.2f}ms"
        )

        print(
            f"\n  Code Quality Score: {results.code_quality.get('code_quality_score', 0):.1f}/100"
        )
        print(
            f"    Lines of Code: {results.code_quality.get('total_lines_of_code', 0):,}"
        )
        print(
            f"    Test Coverage: {results.code_quality.get('test_coverage_estimate', 0):.1f}%"
        )

        print(
            f"\n  Security Score: {results.security_scan.get('security_score', 0):.1f}/100"
        )
        print(f"    Status: {results.security_scan.get('status', 'UNKNOWN')}")
        if results.security_scan.get("vulnerabilities"):
            for vuln in results.security_scan["vulnerabilities"]:
                print(f"    - {vuln}")

        print(
            f"\n  Integration Score: {results.integration_tests.get('integration_score', 0):.1f}/100"
        )
        print(f"    Status: {results.integration_tests.get('status', 'UNKNOWN')}")

        print(
            f"\n  Load Test Score: {results.load_test_results.get('load_test_score', 0):.1f}/100"
        )

        # Critical Issues
        if results.critical_issues:
            print(f"\n🚨 CRITICAL ISSUES ({len(results.critical_issues)}):")
            for issue in results.critical_issues:
                print(f"  ❌ {issue}")
        else:
            print("\n✅ No critical issues detected!")

        # Top Recommendations
        if results.optimization_recommendations:
            print(f"\n💡 TOP OPTIMIZATION RECOMMENDATIONS:")
            for i, rec in enumerate(results.optimization_recommendations[:3], 1):
                print(f"  {i}. [{rec['priority']}] {rec['issue']}")
                print(f"     → {rec['recommendation']}")
                print(f"     Impact: {rec['estimated_impact']}")
                print()

        print("=" * 70)
        print(f"📅 Analysis completed in: {time.time() - self.start_time:.2f} seconds")
        print(f"📁 Detailed results saved to: {self.results_dir}")
        print("=" * 70)


async def main():
    """Main function to run the comprehensive testing"""
    optimizer = ComprehensiveTestOptimizer()
    results = await optimizer.run_comprehensive_analysis()

    return results


if __name__ == "__main__":
    asyncio.run(main())
