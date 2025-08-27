#!/usr/bin/env python3
"""
AI Script Generator v3.0 - Production SLO Validation Test
Tests specific SLO requirements:
- SSE 최초 이벤트 p95 ≤2초 달성 확인
- 에러율 <1% 유지 검증
- readiness 프로브 안정성 확인
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import aiohttp


class SLOTestResults:
    """SLO test results collector"""

    def __init__(self):
        self.sse_first_event_times: List[float] = []
        self.total_requests = 0
        self.error_requests = 0
        self.readiness_checks: List[bool] = []
        self.start_time = None
        self.end_time = None

    def add_sse_first_event(self, time_to_first_event: float):
        """Add SSE first event time"""
        self.sse_first_event_times.append(time_to_first_event)

    def add_request_result(self, success: bool):
        """Add request result"""
        self.total_requests += 1
        if not success:
            self.error_requests += 1

    def add_readiness_check(self, success: bool):
        """Add readiness check result"""
        self.readiness_checks.append(success)

    def get_error_rate(self) -> float:
        """Calculate error rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.error_requests / self.total_requests) * 100

    def get_sse_p95_latency(self) -> Optional[float]:
        """Get SSE first event P95 latency"""
        if not self.sse_first_event_times:
            return None
        sorted_times = sorted(self.sse_first_event_times)
        p95_index = int(0.95 * len(sorted_times))
        return (
            sorted_times[p95_index]
            if p95_index < len(sorted_times)
            else sorted_times[-1]
        )

    def get_readiness_success_rate(self) -> float:
        """Get readiness probe success rate"""
        if not self.readiness_checks:
            return 0.0
        return (sum(self.readiness_checks) / len(self.readiness_checks)) * 100


class ProductionSLOTest:
    """Production SLO validation test suite"""

    def __init__(self):
        self.base_urls = {
            "project_service": "http://localhost:8001",
            "generation_service": "http://localhost:8002",
        }
        self.results = SLOTestResults()

    async def run_slo_validation(self) -> Dict[str, Any]:
        """Run complete SLO validation test"""
        print("🎯 AI Script Generator v3.0 - Production SLO Validation")
        print("=" * 60)

        self.results.start_time = time.time()

        # Test 1: Service availability
        print("🔍 Testing service availability...")
        await self._test_service_availability()

        # Test 2: Readiness probe stability (continuous monitoring)
        print("🏥 Testing readiness probe stability...")
        await self._test_readiness_stability()

        # Test 3: SSE first event latency (limited concurrent connections to avoid rate limiting)
        print("📡 Testing SSE first event latency...")
        await self._test_sse_first_event_latency()

        # Test 4: Error rate under normal load
        print("📊 Testing error rate under controlled load...")
        await self._test_error_rate()

        self.results.end_time = time.time()

        # Generate results
        return await self._generate_slo_report()

    async def _test_service_availability(self):
        """Test basic service availability"""
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for service_name, base_url in self.base_urls.items():
                try:
                    health_url = f"{base_url}/api/v1/health/"
                    async with session.get(health_url) as response:
                        success = response.status == 200
                        self.results.add_request_result(success)
                        status = "✅" if success else "❌"
                        print(f"  {status} {service_name}: {response.status}")
                except Exception as e:
                    self.results.add_request_result(False)
                    print(f"  ❌ {service_name}: Connection failed - {e}")

    async def _test_readiness_stability(self):
        """Test readiness probe stability over time"""
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Test readiness probes for 30 seconds
            end_time = time.time() + 30
            check_interval = 2  # Check every 2 seconds

            while time.time() < end_time:
                for service_name, base_url in self.base_urls.items():
                    try:
                        readiness_url = f"{base_url}/api/v1/readyz"
                        async with session.get(readiness_url) as response:
                            success = response.status == 200
                            self.results.add_readiness_check(success)
                            self.results.add_request_result(success)
                    except Exception:
                        self.results.add_readiness_check(False)
                        self.results.add_request_result(False)

                await asyncio.sleep(check_interval)

        success_rate = self.results.get_readiness_success_rate()
        status = "✅" if success_rate >= 99.0 else "❌"
        print(f"  {status} Readiness probe success rate: {success_rate:.1f}%")

    async def _test_sse_first_event_latency(self):
        """Test SSE first event latency - limited to avoid rate limiting"""
        # Create a test project first
        project_id = await self._create_test_project()
        if not project_id:
            print("  ❌ Could not create test project for SSE testing")
            return

        # Test SSE connections (limit to 5 concurrent to avoid rate limiting)
        concurrent_connections = 5
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [
                self._test_single_sse_connection(session, project_id, i)
                for i in range(concurrent_connections)
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate P95 latency
        p95_latency = self.results.get_sse_p95_latency()
        if p95_latency is not None:
            status = "✅" if p95_latency <= 2.0 else "❌"
            print(
                f"  {status} SSE first event P95 latency: {p95_latency:.3f}s (target: ≤2.0s)"
            )
        else:
            print("  ❌ No SSE first event data collected")

    async def _test_single_sse_connection(
        self, session: aiohttp.ClientSession, project_id: str, connection_id: int
    ):
        """Test a single SSE connection for first event latency"""
        try:
            # First, trigger a generation job with correct API schema
            generation_url = (
                f"{self.base_urls['generation_service']}/api/v1/generations"
            )
            generation_data = {
                "projectId": project_id,
                "description": f"Generate a short test script for SSE latency test {connection_id}",
                "scriptType": "drama",
            }

            # Add Idempotency-Key header to prevent duplicates
            headers = {
                "Idempotency-Key": f"test_sse_{connection_id}_{int(time.time())}"
            }

            async with session.post(
                generation_url, json=generation_data, headers=headers
            ) as response:
                if response.status == 200 or response.status == 201:
                    job_data = await response.json()
                    job_id = job_data.get("jobId")

                    if job_id:
                        # Connect to SSE and measure time to first event
                        await self._measure_sse_first_event(session, job_id)
                    else:
                        self.results.add_request_result(False)
                else:
                    self.results.add_request_result(False)

        except Exception as e:
            print(f"    Warning: SSE connection {connection_id} failed: {e}")
            self.results.add_request_result(False)

    async def _measure_sse_first_event(
        self, session: aiohttp.ClientSession, job_id: str
    ):
        """Measure time to receive first SSE event"""
        sse_url = (
            f"{self.base_urls['generation_service']}/api/v1/generations/{job_id}/events"
        )

        start_time = time.time()
        try:
            async with session.get(
                sse_url, headers={"Accept": "text/event-stream"}
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data:"):
                            # First event received
                            first_event_time = time.time() - start_time
                            self.results.add_sse_first_event(first_event_time)
                            self.results.add_request_result(True)
                            break
                    else:
                        # No events received
                        self.results.add_request_result(False)
                else:
                    self.results.add_request_result(False)
        except Exception:
            self.results.add_request_result(False)

    async def _test_error_rate(self):
        """Test error rate under controlled load"""
        # Use a very conservative approach to avoid rate limiting
        requests_per_batch = 5
        batch_delay = 10  # 10 seconds between batches
        num_batches = 3

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for batch in range(num_batches):
                tasks = []
                for i in range(requests_per_batch):
                    # Alternate between different endpoints
                    if i % 2 == 0:
                        task = self._test_health_endpoint(session, "project_service")
                    else:
                        task = self._test_health_endpoint(session, "generation_service")
                    tasks.append(task)

                await asyncio.gather(*tasks, return_exceptions=True)

                if batch < num_batches - 1:  # Don't wait after last batch
                    await asyncio.sleep(batch_delay)

        error_rate = self.results.get_error_rate()
        status = "✅" if error_rate < 1.0 else "❌"
        print(f"  {status} Error rate: {error_rate:.2f}% (target: <1.0%)")

    async def _test_health_endpoint(
        self, session: aiohttp.ClientSession, service_name: str
    ):
        """Test a health endpoint"""
        try:
            health_url = f"{self.base_urls[service_name]}/api/v1/health/"
            async with session.get(health_url) as response:
                success = response.status == 200
                self.results.add_request_result(success)
        except Exception:
            self.results.add_request_result(False)

    async def _create_test_project(self) -> Optional[str]:
        """Create a test project for SSE testing"""
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                project_url = f"{self.base_urls['project_service']}/api/v1/projects/"
                project_data = {
                    "name": f"SLO Test Project {int(time.time())}",
                    "type": "drama",
                    "description": "Automated SLO test project",
                }

                headers = {"Idempotency-Key": f"slo_test_{int(time.time())}"}

                async with session.post(
                    project_url, json=project_data, headers=headers
                ) as response:
                    if response.status == 200 or response.status == 201:
                        project_result = await response.json()
                        return project_result.get("data", {}).get("id")
                    else:
                        print(
                            f"    Warning: Project creation failed with status {response.status}"
                        )
                        return None
            except Exception as e:
                print(f"    Warning: Project creation failed: {e}")
                return None

    async def _generate_slo_report(self) -> Dict[str, Any]:
        """Generate comprehensive SLO validation report"""
        test_duration = self.results.end_time - self.results.start_time

        # Calculate metrics
        error_rate = self.results.get_error_rate()
        p95_latency = self.results.get_sse_p95_latency()
        readiness_success_rate = self.results.get_readiness_success_rate()

        # Determine SLO compliance
        slo_results = {
            "sse_first_event_p95": {
                "value": p95_latency,
                "target": 2.0,
                "unit": "seconds",
                "passed": p95_latency is not None and p95_latency <= 2.0,
            },
            "error_rate": {
                "value": error_rate,
                "target": 1.0,
                "unit": "percent",
                "passed": error_rate < 1.0,
            },
            "readiness_stability": {
                "value": readiness_success_rate,
                "target": 99.0,
                "unit": "percent",
                "passed": readiness_success_rate >= 99.0,
            },
        }

        overall_slo_compliance = all(slo["passed"] for slo in slo_results.values())

        report = {
            "test_execution": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": round(test_duration, 2),
                "total_requests": self.results.total_requests,
            },
            "slo_results": slo_results,
            "overall_slo_compliance": overall_slo_compliance,
            "detailed_metrics": {
                "sse_first_event_times": self.results.sse_first_event_times,
                "readiness_checks_total": len(self.results.readiness_checks),
                "readiness_checks_passed": sum(self.results.readiness_checks),
            },
        }

        return report


async def main():
    """Main test execution"""
    test = ProductionSLOTest()

    try:
        report = await test.run_slo_validation()

        print("\n" + "=" * 60)
        print("🎯 Production SLO Validation Results")
        print("=" * 60)

        # Print SLO results
        print("\n📊 SLO Compliance Status:")
        for slo_name, slo_data in report["slo_results"].items():
            status = "✅ PASS" if slo_data["passed"] else "❌ FAIL"
            value = slo_data["value"]
            target = slo_data["target"]
            unit = slo_data["unit"]

            if value is not None:
                print(
                    f"  {status} {slo_name.replace('_', ' ').title()}: {value:.3f}{unit} (target: <={target}{unit})"
                )
            else:
                print(
                    f"  ❌ FAIL {slo_name.replace('_', ' ').title()}: No data collected"
                )

        # Overall compliance
        overall_status = (
            "✅ READY FOR PRODUCTION"
            if report["overall_slo_compliance"]
            else "❌ NOT READY - SLO VIOLATIONS"
        )
        print(f"\n🎯 Overall SLO Compliance: {overall_status}")

        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"slo_validation_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Detailed results saved to: {results_file}")

        return report["overall_slo_compliance"]

    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
