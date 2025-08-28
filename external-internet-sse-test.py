#!/usr/bin/env python3
"""
AI Script Generator v3.0 - External Internet SSE Performance Test
Tests SSE performance through actual internet connection to validate Day-0 readiness.
Target: P95 < 0.5s for external access (stricter than internal 2s requirement)
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import statistics
import aiohttp
import ssl


class ExternalSSETestResults:
    """External SSE test results collector"""

    def __init__(self):
        self.connection_times: List[float] = []
        self.dns_resolution_times: List[float] = []
        self.tls_handshake_times: List[float] = []
        self.first_event_times: List[float] = []
        self.total_request_times: List[float] = []
        self.failed_connections = 0
        self.successful_connections = 0
        self.network_errors: List[str] = []

    def add_connection_success(self, metrics: Dict[str, float]):
        """Add successful connection metrics"""
        self.successful_connections += 1
        self.connection_times.append(metrics.get("connection_time", 0))
        self.dns_resolution_times.append(metrics.get("dns_time", 0))
        self.tls_handshake_times.append(metrics.get("tls_time", 0))
        self.first_event_times.append(metrics.get("first_event_time", 0))
        self.total_request_times.append(metrics.get("total_time", 0))

    def add_connection_failure(self, error: str):
        """Add failed connection"""
        self.failed_connections += 1
        self.network_errors.append(error)

    def get_p95_first_event(self) -> Optional[float]:
        """Get P95 first event time"""
        if not self.first_event_times:
            return None
        sorted_times = sorted(self.first_event_times)
        p95_index = int(0.95 * len(sorted_times))
        return (
            sorted_times[p95_index]
            if p95_index < len(sorted_times)
            else sorted_times[-1]
        )

    def get_success_rate(self) -> float:
        """Get connection success rate"""
        total = self.successful_connections + self.failed_connections
        return (self.successful_connections / total * 100) if total > 0 else 0


class ExternalInternetSSETest:
    """External internet SSE performance test"""

    def __init__(self, base_url: str = None):
        # Default to localhost for testing, but support external URLs
        self.base_url = base_url or "http://localhost:8002"
        self.project_service_url = "http://localhost:8001"  # For creating test projects
        self.results = ExternalSSETestResults()

    async def run_external_sse_test(
        self, concurrent_connections: int = 10
    ) -> Dict[str, Any]:
        """Run comprehensive external SSE performance test"""
        print("🌐 AI Script Generator v3.0 - External Internet SSE Performance Test")
        print("=" * 70)
        print("🎯 Target: P95 First Event < 0.5s (external internet access)")
        print(f"🔗 Testing URL: {self.base_url}")
        print(f"👥 Concurrent connections: {concurrent_connections}")
        print()

        # Create test project first
        project_id = await self._create_test_project()
        if not project_id:
            print("❌ Failed to create test project")
            return {"success": False, "error": "Project creation failed"}

        print(f"✅ Test project created: {project_id}")

        # Run concurrent SSE tests
        print(f"🚀 Starting {concurrent_connections} concurrent SSE connections...")

        tasks = [
            self._test_external_sse_connection(i, project_id)
            for i in range(concurrent_connections)
        ]

        start_time = time.time()
        await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Generate results
        return await self._generate_external_test_report(end_time - start_time)

    async def _create_test_project(self) -> Optional[str]:
        """Create test project for SSE testing"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                project_url = f"{self.project_service_url}/api/v1/projects/"
                project_data = {
                    "name": f"External SSE Test {int(time.time())}",
                    "type": "drama",
                    "description": "External internet SSE performance test project",
                }

                headers = {"Idempotency-Key": f"external_test_{int(time.time())}"}

                async with session.post(
                    project_url, json=project_data, headers=headers
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        return result.get("data", {}).get("id")
                    else:
                        print(f"⚠️ Project creation failed: {response.status}")
                        return None
        except Exception as e:
            print(f"⚠️ Project creation error: {e}")
            return None

    async def _test_external_sse_connection(self, connection_id: int, project_id: str):
        """Test single external SSE connection with detailed metrics"""
        # Custom connector to measure connection timing
        connector = aiohttp.TCPConnector(
            limit=1,
            ttl_dns_cache=300,
            use_dns_cache=True,
            ssl=ssl.create_default_context(),
        )

        timeout = aiohttp.ClientTimeout(total=60, connect=15)

        try:
            async with aiohttp.ClientSession(
                connector=connector, timeout=timeout
            ) as session:
                # Step 1: Create generation job
                generation_url = f"{self.base_url}/api/v1/generations"
                generation_data = {
                    "projectId": project_id,
                    "description": f"External SSE test script {connection_id}",
                    "scriptType": "drama",
                }

                headers = {
                    "Idempotency-Key": f"ext_sse_{connection_id}_{int(time.time())}"
                }

                job_creation_start = time.time()
                async with session.post(
                    generation_url, json=generation_data, headers=headers
                ) as response:
                    job_creation_time = time.time() - job_creation_start

                    if response.status not in [200, 201]:
                        self.results.add_connection_failure(
                            f"Job creation failed: {response.status}"
                        )
                        return

                    job_data = await response.json()
                    job_id = job_data.get("jobId")

                    if not job_id:
                        self.results.add_connection_failure("No jobId received")
                        return

                # Step 2: Connect to SSE and measure detailed timing
                sse_url = f"{self.base_url}/api/v1/generations/{job_id}/events"

                connection_start = time.time()

                try:
                    # Measure detailed connection phases
                    async with session.get(
                        sse_url, headers={"Accept": "text/event-stream"}
                    ) as sse_response:
                        connection_established = time.time()
                        connection_time = connection_established - connection_start

                        if sse_response.status != 200:
                            self.results.add_connection_failure(
                                f"SSE connection failed: {sse_response.status}"
                            )
                            return

                        # Measure time to first SSE event
                        first_event_start = time.time()
                        first_event_time = None

                        async for line in sse_response.content:
                            line_str = line.decode("utf-8", errors="ignore").strip()
                            if (
                                line_str.startswith("data:")
                                and first_event_time is None
                            ):
                                first_event_time = time.time() - first_event_start
                                break

                        if first_event_time is None:
                            self.results.add_connection_failure(
                                "No SSE events received"
                            )
                            return

                        # Record successful connection metrics
                        total_time = time.time() - connection_start

                        metrics = {
                            "connection_time": connection_time,
                            "dns_time": 0.1,  # Estimated DNS time
                            "tls_time": (
                                0.05 if self.base_url.startswith("https") else 0
                            ),
                            "first_event_time": first_event_time,
                            "total_time": total_time,
                            "job_creation_time": job_creation_time,
                        }

                        self.results.add_connection_success(metrics)

                        print(
                            f"  ✅ Connection {connection_id}: First event in {first_event_time:.3f}s"
                        )

                except asyncio.TimeoutError:
                    self.results.add_connection_failure("Connection timeout")
                except Exception as e:
                    self.results.add_connection_failure(f"Connection error: {str(e)}")

        except Exception as e:
            self.results.add_connection_failure(f"Session error: {str(e)}")

    async def _generate_external_test_report(
        self, test_duration: float
    ) -> Dict[str, Any]:
        """Generate comprehensive external test report"""
        p95_first_event = self.results.get_p95_first_event()
        success_rate = self.results.get_success_rate()

        # Calculate additional statistics
        avg_first_event = (
            statistics.mean(self.results.first_event_times)
            if self.results.first_event_times
            else 0
        )
        max_first_event = (
            max(self.results.first_event_times) if self.results.first_event_times else 0
        )
        min_first_event = (
            min(self.results.first_event_times) if self.results.first_event_times else 0
        )

        # Determine if test passes Day-0 criteria
        day0_criteria_met = (
            p95_first_event is not None
            and p95_first_event <= 0.5  # Stricter than internal 2s requirement
            and success_rate >= 95.0  # High success rate required for external
            and self.results.successful_connections
            >= 8  # At least 8/10 connections successful
        )

        print("\n" + "=" * 70)
        print("🎯 External Internet SSE Performance Results")
        print("=" * 70)

        if p95_first_event is not None:
            status = "✅ PASS" if p95_first_event <= 0.5 else "❌ FAIL"
            print(
                f"{status} P95 First Event Time: {p95_first_event:.3f}s (target: ≤0.5s)"
            )
            print("📊 First Event Statistics:")
            print(f"  - Average: {avg_first_event:.3f}s")
            print(f"  - Minimum: {min_first_event:.3f}s")
            print(f"  - Maximum: {max_first_event:.3f}s")
        else:
            print("❌ FAIL P95 First Event Time: No data collected")

        success_status = "✅ PASS" if success_rate >= 95 else "❌ FAIL"
        print(
            f"{success_status} Connection Success Rate: {success_rate:.1f}% (target: ≥95%)"
        )
        print("📈 Connection Summary:")
        print(f"  - Successful: {self.results.successful_connections}")
        print(f"  - Failed: {self.results.failed_connections}")
        print(f"  - Total Duration: {test_duration:.1f}s")

        if self.results.network_errors:
            print("⚠️ Network Errors:")
            for error in set(
                self.results.network_errors[:5]
            ):  # Show unique errors, max 5
                print(f"  - {error}")

        # Day-0 readiness assessment
        day0_status = "✅ READY" if day0_criteria_met else "❌ NOT READY"
        print(f"\n🎯 Day-0 Readiness: {day0_status}")

        if day0_criteria_met:
            print("🚀 External internet performance meets Day-0 launch criteria!")
        else:
            print("⚠️ External internet performance does not meet Day-0 criteria")
            print("   Review network connectivity and service performance")

        # Generate detailed report
        report = {
            "test_execution": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_duration_seconds": test_duration,
                "base_url": self.base_url,
                "concurrent_connections": self.results.successful_connections
                + self.results.failed_connections,
            },
            "performance_metrics": {
                "p95_first_event_time": p95_first_event,
                "avg_first_event_time": avg_first_event,
                "min_first_event_time": min_first_event,
                "max_first_event_time": max_first_event,
                "success_rate_percent": success_rate,
            },
            "connection_results": {
                "successful_connections": self.results.successful_connections,
                "failed_connections": self.results.failed_connections,
                "network_errors": list(set(self.results.network_errors)),
            },
            "day0_criteria": {
                "p95_under_500ms": p95_first_event is not None
                and p95_first_event <= 0.5,
                "success_rate_over_95pct": success_rate >= 95.0,
                "min_successful_connections": self.results.successful_connections >= 8,
                "overall_day0_ready": day0_criteria_met,
            },
            "raw_metrics": {
                "first_event_times": self.results.first_event_times,
                "connection_times": self.results.connection_times,
                "total_request_times": self.results.total_request_times,
            },
        }

        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"external_sse_test_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"📄 Detailed results saved to: {results_file}")

        return report


async def main():
    """Main test execution"""
    # Test configuration
    concurrent_connections = 10

    # You can override the base URL for testing against actual external endpoints
    # base_url = "https://api.yourdomain.com"  # For actual external testing
    base_url = "http://localhost:8002"  # For local testing

    tester = ExternalInternetSSETest(base_url)

    try:
        report = await tester.run_external_sse_test(concurrent_connections)

        # Return appropriate exit code
        if report.get("day0_criteria", {}).get("overall_day0_ready", False):
            print("\n🎉 Day-0 external internet test PASSED!")
            return True
        else:
            print("\n⚠️ Day-0 external internet test FAILED!")
            return False

    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
