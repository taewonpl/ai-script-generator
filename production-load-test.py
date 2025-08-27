#!/usr/bin/env python3
"""
Production Load Test for AI Script Generator v3.0
Tests system performance under production-like conditions.
"""

import asyncio
import aiohttp
import time
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import statistics
import psutil
import threading


class LoadTestResults:
    """Store and analyze load test results"""

    def __init__(self):
        self.requests_completed = 0
        self.requests_failed = 0
        self.response_times = []
        self.errors = []
        self.start_time = None
        self.end_time = None

    def add_success(self, response_time: float):
        self.requests_completed += 1
        self.response_times.append(response_time)

    def add_failure(self, error: str):
        self.requests_failed += 1
        self.errors.append(error)

    def get_statistics(self) -> Dict[str, Any]:
        if not self.response_times:
            return {"error": "No successful requests"}

        total_requests = self.requests_completed + self.requests_failed
        success_rate = (
            (self.requests_completed / total_requests) * 100
            if total_requests > 0
            else 0
        )

        response_times_sorted = sorted(self.response_times)

        return {
            "total_requests": total_requests,
            "successful_requests": self.requests_completed,
            "failed_requests": self.requests_failed,
            "success_rate": f"{success_rate:.1f}%",
            "response_times": {
                "min": f"{min(self.response_times):.3f}s",
                "max": f"{max(self.response_times):.3f}s",
                "avg": f"{statistics.mean(self.response_times):.3f}s",
                "median": f"{statistics.median(self.response_times):.3f}s",
                "p95": f"{response_times_sorted[int(0.95 * len(response_times_sorted))]:.3f}s",
                "p99": f"{response_times_sorted[int(0.99 * len(response_times_sorted))]:.3f}s",
            },
            "duration": (
                f"{(self.end_time - self.start_time):.2f}s"
                if self.end_time and self.start_time
                else "unknown"
            ),
        }


class SystemMonitor:
    """Monitor system resources during load test"""

    def __init__(self):
        self.monitoring = False
        self.cpu_usage = []
        self.memory_usage = []
        self.disk_usage = []

    def start_monitoring(self):
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.monitoring = False
        if hasattr(self, "monitor_thread"):
            self.monitor_thread.join(timeout=1)

    def _monitor_loop(self):
        while self.monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.cpu_usage.append(cpu_percent)

                # Memory usage
                memory = psutil.virtual_memory()
                self.memory_usage.append(memory.percent)

                # Disk usage
                disk = psutil.disk_usage("/")
                self.disk_usage.append(disk.percent)

                time.sleep(1)
            except Exception as e:
                print(f"⚠️ Monitoring error: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        if not self.cpu_usage:
            return {"error": "No monitoring data"}

        return {
            "cpu_usage": {
                "min": f"{min(self.cpu_usage):.1f}%",
                "max": f"{max(self.cpu_usage):.1f}%",
                "avg": f"{statistics.mean(self.cpu_usage):.1f}%",
            },
            "memory_usage": {
                "min": f"{min(self.memory_usage):.1f}%",
                "max": f"{max(self.memory_usage):.1f}%",
                "avg": f"{statistics.mean(self.memory_usage):.1f}%",
            },
            "disk_usage": {
                "min": f"{min(self.disk_usage):.1f}%",
                "max": f"{max(self.disk_usage):.1f}%",
                "avg": f"{statistics.mean(self.disk_usage):.1f}%",
            },
        }


class ProductionLoadTest:
    """Main load test orchestrator"""

    def __init__(self, base_urls: Dict[str, str]):
        self.base_urls = base_urls
        self.results = {
            "project_service": LoadTestResults(),
            "generation_service": LoadTestResults(),
        }
        self.monitor = SystemMonitor()

    async def test_health_endpoints(
        self, session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Test health endpoints under load"""
        print("🔍 Testing health endpoints...")

        health_results = {}

        for service_name, base_url in self.base_urls.items():
            health_url = f"{base_url}/api/v1/health"

            # Test 100 concurrent health check requests
            tasks = []
            for _ in range(100):
                tasks.append(
                    self._make_request(session, health_url, service_name + "_health")
                )

            # Wait for all requests to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful

            health_results[service_name] = {
                "successful": successful,
                "failed": failed,
                "success_rate": f"{(successful/len(results)*100):.1f}%",
            }

        return health_results

    async def test_api_endpoints(
        self,
        session: aiohttp.ClientSession,
        concurrent_users: int = 10,
        requests_per_user: int = 20,
    ) -> None:
        """Test API endpoints with concurrent users"""
        print(
            f"🚀 Testing API endpoints: {concurrent_users} concurrent users, {requests_per_user} requests each..."
        )

        # Start system monitoring
        self.monitor.start_monitoring()

        # Prepare test data
        test_project = {
            "name": f"Load Test Project {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "description": "Automated load test project",
            "script_type": "drama",
            "genre": "action",
        }

        # Create tasks for concurrent execution
        tasks = []

        # Project Service load test
        for user_id in range(concurrent_users):
            for req_id in range(requests_per_user):
                task = self._simulate_user_workflow(
                    session, user_id, req_id, test_project
                )
                tasks.append(task)

        # Execute all tasks concurrently
        start_time = time.time()
        self.results["project_service"].start_time = start_time
        self.results["generation_service"].start_time = start_time

        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        self.results["project_service"].end_time = end_time
        self.results["generation_service"].end_time = end_time

        # Stop monitoring
        self.monitor.stop_monitoring()

        # Process results
        exceptions = [r for r in results if isinstance(r, Exception)]
        if exceptions:
            print(f"⚠️ {len(exceptions)} tasks resulted in exceptions")
            for exc in exceptions[:5]:  # Show first 5 exceptions
                print(f"  - {type(exc).__name__}: {exc}")

    async def _simulate_user_workflow(
        self,
        session: aiohttp.ClientSession,
        user_id: int,
        req_id: int,
        test_project: Dict,
    ) -> None:
        """Simulate a complete user workflow"""
        try:
            # 1. Create a project
            project_url = f"{self.base_urls['project_service']}/api/v1/projects"
            project_data = {
                **test_project,
                "name": f"{test_project['name']} User{user_id} Req{req_id}",
            }

            start_time = time.time()
            async with session.post(project_url, json=project_data) as response:
                if response.status == 200 or response.status == 201:
                    project_result = await response.json()
                    project_id = project_result.get("data", {}).get(
                        "id"
                    ) or project_result.get("id")

                    if project_id:
                        response_time = time.time() - start_time
                        self.results["project_service"].add_success(response_time)

                        # 2. Create an episode
                        episode_url = f"{self.base_urls['project_service']}/api/v1/projects/{project_id}/episodes"
                        episode_data = {
                            "title": f"Test Episode {req_id}",
                            "description": "Automated load test episode",
                        }

                        start_time = time.time()
                        async with session.post(
                            episode_url, json=episode_data
                        ) as ep_response:
                            response_time = time.time() - start_time
                            if ep_response.status == 200 or ep_response.status == 201:
                                self.results["project_service"].add_success(
                                    response_time
                                )
                            else:
                                self.results["project_service"].add_failure(
                                    f"Episode creation failed: {ep_response.status}"
                                )

                        # 3. Test generation service health
                        gen_health_url = (
                            f"{self.base_urls['generation_service']}/api/v1/health"
                        )
                        start_time = time.time()
                        async with session.get(gen_health_url) as gen_response:
                            response_time = time.time() - start_time
                            if gen_response.status == 200:
                                self.results["generation_service"].add_success(
                                    response_time
                                )
                            else:
                                self.results["generation_service"].add_failure(
                                    f"Health check failed: {gen_response.status}"
                                )
                    else:
                        self.results["project_service"].add_failure(
                            "Project creation returned no ID"
                        )
                else:
                    response_time = time.time() - start_time
                    self.results["project_service"].add_failure(
                        f"Project creation failed: {response.status}"
                    )

        except Exception as e:
            self.results["project_service"].add_failure(f"Workflow exception: {str(e)}")

    async def _make_request(
        self, session: aiohttp.ClientSession, url: str, service_name: str
    ) -> float:
        """Make a single HTTP request and return response time"""
        start_time = time.time()
        async with session.get(url) as response:
            response_time = time.time() - start_time
            if response.status == 200:
                return response_time
            else:
                raise Exception(f"Request failed with status {response.status}")

    async def run_load_test(
        self, concurrent_users: int = 10, requests_per_user: int = 20
    ) -> Dict[str, Any]:
        """Run complete load test suite"""
        print("🚀 Production Load Test Starting")
        print("=" * 60)

        timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
        connector = aiohttp.TCPConnector(limit=200)  # Increase connection pool

        async with aiohttp.ClientSession(
            timeout=timeout, connector=connector
        ) as session:
            # Test 1: Health endpoints
            health_results = await self.test_health_endpoints(session)

            # Test 2: API endpoints with load
            await self.test_api_endpoints(session, concurrent_users, requests_per_user)

            # Compile results
            results = {
                "test_execution": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "concurrent_users": concurrent_users,
                    "requests_per_user": requests_per_user,
                    "total_planned_requests": concurrent_users * requests_per_user,
                },
                "health_check_results": health_results,
                "load_test_results": {
                    service: results.get_statistics()
                    for service, results in self.results.items()
                },
                "system_performance": self.monitor.get_statistics(),
            }

            return results

    def print_results(self, results: Dict[str, Any]):
        """Print formatted test results"""
        print("\n" + "=" * 60)
        print("🎯 Production Load Test Results")
        print("=" * 60)

        # Test execution info
        exec_info = results["test_execution"]
        print(f"⏱️  Timestamp: {exec_info['timestamp']}")
        print(f"👥 Concurrent Users: {exec_info['concurrent_users']}")
        print(f"📊 Requests per User: {exec_info['requests_per_user']}")
        print(f"📈 Total Requests: {exec_info['total_planned_requests']}")
        print()

        # Health check results
        print("🏥 Health Check Results:")
        for service, health in results["health_check_results"].items():
            print(
                f"  {service}: {health['success_rate']} ({health['successful']}/{health['successful']+health['failed']})"
            )
        print()

        # Load test results
        print("🚀 Load Test Results:")
        for service, stats in results["load_test_results"].items():
            if "error" not in stats:
                print(f"  {service}:")
                print(f"    Success Rate: {stats['success_rate']}")
                print(
                    f"    Response Times: avg={stats['response_times']['avg']}, p95={stats['response_times']['p95']}"
                )
                print(
                    f"    Total Requests: {stats['successful_requests']}/{stats['total_requests']}"
                )
        print()

        # System performance
        if "error" not in results["system_performance"]:
            perf = results["system_performance"]
            print("💻 System Performance:")
            print(
                f"  CPU Usage: avg={perf['cpu_usage']['avg']}, max={perf['cpu_usage']['max']}"
            )
            print(
                f"  Memory Usage: avg={perf['memory_usage']['avg']}, max={perf['memory_usage']['max']}"
            )
            print(f"  Disk Usage: {perf['disk_usage']['avg']}")
        print()

        # Performance assessment
        self._assess_performance(results)

    def _assess_performance(self, results: Dict[str, Any]):
        """Assess if performance meets production criteria"""
        print("📋 Performance Assessment:")

        criteria = {
            "health_check_success_rate": 99.0,  # 99% success rate
            "api_success_rate": 95.0,  # 95% success rate
            "p95_response_time": 2.0,  # < 2 seconds P95
            "cpu_usage_max": 80.0,  # < 80% CPU
            "memory_usage_max": 85.0,  # < 85% memory
        }

        passed_criteria = 0
        total_criteria = len(criteria)

        # Check health endpoint success rates
        health_results = results["health_check_results"]
        min_health_success = min(
            float(h["success_rate"].rstrip("%")) for h in health_results.values()
        )
        if min_health_success >= criteria["health_check_success_rate"]:
            print(
                f"  ✅ Health Check Success Rate: {min_health_success:.1f}% (≥{criteria['health_check_success_rate']:.1f}%)"
            )
            passed_criteria += 1
        else:
            print(
                f"  ❌ Health Check Success Rate: {min_health_success:.1f}% (<{criteria['health_check_success_rate']:.1f}%)"
            )

        # Check API success rates
        load_results = results["load_test_results"]
        api_success_rates = []
        for service, stats in load_results.items():
            if "error" not in stats:
                success_rate = float(stats["success_rate"].rstrip("%"))
                api_success_rates.append(success_rate)

        if api_success_rates:
            min_api_success = min(api_success_rates)
            if min_api_success >= criteria["api_success_rate"]:
                print(
                    f"  ✅ API Success Rate: {min_api_success:.1f}% (≥{criteria['api_success_rate']:.1f}%)"
                )
                passed_criteria += 1
            else:
                print(
                    f"  ❌ API Success Rate: {min_api_success:.1f}% (<{criteria['api_success_rate']:.1f}%)"
                )

        # Check response times
        p95_times = []
        for service, stats in load_results.items():
            if "error" not in stats and "response_times" in stats:
                p95_time = float(stats["response_times"]["p95"].rstrip("s"))
                p95_times.append(p95_time)

        if p95_times:
            max_p95_time = max(p95_times)
            if max_p95_time <= criteria["p95_response_time"]:
                print(
                    f"  ✅ P95 Response Time: {max_p95_time:.3f}s (≤{criteria['p95_response_time']:.1f}s)"
                )
                passed_criteria += 1
            else:
                print(
                    f"  ❌ P95 Response Time: {max_p95_time:.3f}s (>{criteria['p95_response_time']:.1f}s)"
                )

        # Check system performance
        sys_perf = results["system_performance"]
        if "error" not in sys_perf:
            cpu_max = float(sys_perf["cpu_usage"]["max"].rstrip("%"))
            memory_max = float(sys_perf["memory_usage"]["max"].rstrip("%"))

            if cpu_max <= criteria["cpu_usage_max"]:
                print(
                    f"  ✅ CPU Usage: {cpu_max:.1f}% (≤{criteria['cpu_usage_max']:.1f}%)"
                )
                passed_criteria += 1
            else:
                print(
                    f"  ❌ CPU Usage: {cpu_max:.1f}% (>{criteria['cpu_usage_max']:.1f}%)"
                )

            if memory_max <= criteria["memory_usage_max"]:
                print(
                    f"  ✅ Memory Usage: {memory_max:.1f}% (≤{criteria['memory_usage_max']:.1f}%)"
                )
                passed_criteria += 1
            else:
                print(
                    f"  ❌ Memory Usage: {memory_max:.1f}% (>{criteria['memory_usage_max']:.1f}%)"
                )

        print()
        success_rate = (passed_criteria / total_criteria) * 100

        if success_rate >= 80:
            print(
                f"🎉 Performance Assessment: PASSED ({passed_criteria}/{total_criteria} criteria)"
            )
            print("✅ System meets production performance requirements")
        else:
            print(
                f"❌ Performance Assessment: FAILED ({passed_criteria}/{total_criteria} criteria)"
            )
            print("🔧 System needs optimization before production deployment")

        return success_rate >= 80


async def main():
    """Main entry point"""
    print("🚀 AI Script Generator v3.0 - Production Load Test")

    # Service endpoints (adjust if running elsewhere)
    base_urls = {
        "project_service": "http://localhost:8001",
        "generation_service": "http://localhost:8002",
    }

    # Verify services are running
    print("🔍 Verifying services are running...")
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for service, url in base_urls.items():
                health_url = f"{url}/api/v1/health"
                async with session.get(health_url) as response:
                    if response.status == 200:
                        print(f"  ✅ {service}: Running")
                    else:
                        print(
                            f"  ❌ {service}: Health check failed ({response.status})"
                        )
                        return 1
    except Exception as e:
        print(f"❌ Service verification failed: {e}")
        print("💡 Make sure services are running: docker compose up")
        return 1

    # Run load test
    load_tester = ProductionLoadTest(base_urls)

    # Start with moderate load
    concurrent_users = 5
    requests_per_user = 10

    try:
        results = await load_tester.run_load_test(concurrent_users, requests_per_user)
        load_tester.print_results(results)

        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = Path(f"load_test_results_{timestamp}.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"📄 Detailed results saved to: {results_file}")

        return 0

    except Exception as e:
        print(f"❌ Load test failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
