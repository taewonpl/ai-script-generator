#!/usr/bin/env python3
"""
E2E Test Suite Runner
Executes all end-to-end tests and generates comprehensive report
"""

import asyncio
import time
import sys
from pathlib import Path
from typing import Dict, List, Any
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import all test modules
from test_core_flow import run_core_flow_tests
from test_system_resilience import run_resilience_tests
from test_monitoring_verification import run_monitoring_tests
from test_performance_benchmark import run_performance_tests
from test_final_system_verification import run_final_verification_tests


class E2ETestRunner:
    """Comprehensive E2E test suite runner"""

    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.start_time = None
        self.end_time = None

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all E2E test suites in sequence"""
        print("🚀 Starting Comprehensive E2E Test Suite")
        print("=" * 80)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        self.start_time = time.time()

        # Test execution order - logical sequence
        test_suites = [
            (
                "Final System Verification",
                run_final_verification_tests,
                "Verify all services are properly configured and running",
            ),
            (
                "Core Flow Integration",
                run_core_flow_tests,
                "Test complete project-to-episode workflow",
            ),
            (
                "System Resilience",
                run_resilience_tests,
                "Test system behavior under failure conditions",
            ),
            (
                "Monitoring Verification",
                run_monitoring_tests,
                "Verify monitoring and alerting systems",
            ),
            (
                "Performance Benchmark",
                run_performance_tests,
                "Measure system performance under load",
            ),
        ]

        overall_success = True

        for i, (suite_name, test_function, description) in enumerate(test_suites, 1):
            print(f"📋 Test Suite {i}/5: {suite_name}")
            print(f"📝 Description: {description}")
            print("-" * 60)

            suite_start = time.time()

            try:
                result = await test_function()
                suite_time = time.time() - suite_start

                self.results[suite_name.lower().replace(" ", "_")] = {
                    "status": result.get("overall_status", "UNKNOWN"),
                    "execution_time": suite_time,
                    "details": result,
                    "error": None,
                }

                if result.get("overall_status") == "PASSED":
                    print(f"✅ {suite_name}: PASSED ({suite_time:.2f}s)")
                else:
                    print(f"❌ {suite_name}: FAILED ({suite_time:.2f}s)")
                    overall_success = False

            except Exception as e:
                suite_time = time.time() - suite_start
                print(f"❌ {suite_name}: EXCEPTION ({suite_time:.2f}s)")
                print(f"   Error: {str(e)}")

                self.results[suite_name.lower().replace(" ", "_")] = {
                    "status": "EXCEPTION",
                    "execution_time": suite_time,
                    "details": None,
                    "error": str(e),
                }
                overall_success = False

            print()

        self.end_time = time.time()
        total_time = self.end_time - self.start_time

        # Generate comprehensive report
        report = self._generate_report(overall_success, total_time)

        # Save report to file
        await self._save_report(report)

        return report

    def _generate_report(
        self, overall_success: bool, total_time: float
    ) -> Dict[str, Any]:
        """Generate comprehensive test report"""

        # Calculate summary statistics
        total_suites = len(self.results)
        passed_suites = sum(1 for r in self.results.values() if r["status"] == "PASSED")
        failed_suites = sum(
            1 for r in self.results.values() if r["status"] in ["FAILED", "EXCEPTION"]
        )

        # Extract key metrics from individual test results
        key_metrics = self._extract_key_metrics()

        report = {
            "test_execution": {
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": datetime.fromtimestamp(self.end_time).isoformat(),
                "total_duration": f"{total_time:.2f}s",
                "overall_status": "PASSED" if overall_success else "FAILED",
            },
            "summary": {
                "total_test_suites": total_suites,
                "passed_suites": passed_suites,
                "failed_suites": failed_suites,
                "success_rate": f"{(passed_suites / total_suites * 100):.1f}%",
            },
            "test_suite_results": self.results,
            "key_metrics": key_metrics,
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _extract_key_metrics(self) -> Dict[str, Any]:
        """Extract key metrics from test results"""
        metrics = {}

        # Core Flow metrics
        if "core_flow_integration" in self.results:
            core_details = self.results["core_flow_integration"].get("details", {})
            if "concurrent_test" in core_details:
                concurrent = core_details["concurrent_test"]
                metrics["episode_creation"] = {
                    "total_episodes_created": concurrent.get("total_episodes", 0),
                    "concurrent_execution_time": f"{concurrent.get('execution_time', 0):.2f}s",
                    "success_rate": f"{concurrent.get('success_rate', 0):.1f}%",
                }

        # Performance metrics
        if "performance_benchmark" in self.results:
            perf_details = self.results["performance_benchmark"].get("details", {})
            if "load_test" in perf_details:
                load_test = perf_details["load_test"]
                metrics["performance"] = {
                    "p95_response_time": f"{load_test.get('p95_response_time', 0):.2f}s",
                    "p99_response_time": f"{load_test.get('p99_response_time', 0):.2f}s",
                    "max_concurrent_sse": load_test.get("max_concurrent_sse", 0),
                    "memory_efficiency": load_test.get("memory_stable", False),
                }

        # System resilience metrics
        if "system_resilience" in self.results:
            resilience_details = self.results["system_resilience"].get("details", {})
            recovery_tests = sum(
                1 for key in resilience_details.keys() if "recovery" in key.lower()
            )
            metrics["resilience"] = {
                "recovery_tests_passed": recovery_tests,
                "failure_simulation_success": resilience_details.get(
                    "redis_test", {}
                ).get("status")
                == "PASSED",
            }

        return metrics

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        # Check for failed test suites
        failed_suites = [
            name
            for name, result in self.results.items()
            if result["status"] != "PASSED"
        ]

        if failed_suites:
            recommendations.append(
                f"🔧 Investigate and fix failures in: {', '.join(failed_suites)}"
            )

        # Performance recommendations
        if "performance_benchmark" in self.results:
            perf_details = self.results["performance_benchmark"].get("details", {})
            if "load_test" in perf_details:
                load_test = perf_details["load_test"]
                if load_test.get("p95_response_time", 0) > 2.0:
                    recommendations.append(
                        "⚡ Consider optimizing response times - P95 exceeds 2 seconds"
                    )
                if load_test.get("max_concurrent_sse", 0) < 50:
                    recommendations.append(
                        "📈 Consider increasing SSE connection limits for better concurrency"
                    )

        # System health recommendations
        if "final_system_verification" in self.results:
            final_details = self.results["final_system_verification"].get("details", {})
            if final_details.get("health_check_compliance", 0) < 100:
                recommendations.append("🏥 Some health check endpoints need attention")

        if not recommendations:
            recommendations.append(
                "✅ All systems performing within expected parameters"
            )

        return recommendations

    async def _save_report(self, report: Dict[str, Any]):
        """Save detailed report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path(__file__).parent / f"e2e_test_report_{timestamp}.json"

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"📄 Detailed report saved to: {report_file}")

    def print_summary(self, report: Dict[str, Any]):
        """Print executive summary of test results"""
        print("🎯 E2E Test Suite Executive Summary")
        print("=" * 80)

        # Overall status
        status = report["test_execution"]["overall_status"]
        status_emoji = "✅" if status == "PASSED" else "❌"
        print(f"{status_emoji} Overall Status: {status}")
        print(f"⏱️  Total Duration: {report['test_execution']['total_duration']}")
        print(f"📊 Success Rate: {report['summary']['success_rate']}")
        print()

        # Test suite breakdown
        print("📋 Test Suite Results:")
        for suite_name, result in report["test_suite_results"].items():
            status_emoji = "✅" if result["status"] == "PASSED" else "❌"
            suite_display = suite_name.replace("_", " ").title()
            print(
                f"  {status_emoji} {suite_display}: {result['status']} ({result['execution_time']:.2f}s)"
            )
        print()

        # Key metrics
        if report["key_metrics"]:
            print("🔑 Key Metrics:")
            for metric_category, metrics in report["key_metrics"].items():
                print(f"  {metric_category.replace('_', ' ').title()}:")
                for key, value in metrics.items():
                    print(f"    • {key.replace('_', ' ').title()}: {value}")
            print()

        # Recommendations
        print("💡 Recommendations:")
        for recommendation in report["recommendations"]:
            print(f"  {recommendation}")
        print()

        print("=" * 80)


async def main():
    """Main entry point for E2E test execution"""
    runner = E2ETestRunner()

    try:
        # Run all test suites
        report = await runner.run_all_tests()

        # Print summary
        runner.print_summary(report)

        # Exit with appropriate code
        if report["test_execution"]["overall_status"] == "PASSED":
            print("🎉 All E2E tests completed successfully!")
            sys.exit(0)
        else:
            print("❌ Some E2E tests failed - check the detailed report")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Critical error in test execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
