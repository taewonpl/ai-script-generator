#!/usr/bin/env python3
"""
E2E Performance Benchmark Tests
Tests system performance and limits:
- Episode creation P95 response time measurement
- Concurrent SSE connection limits testing
- Memory usage and leak detection
- 24-hour continuous operation simulation (abbreviated)
"""

import asyncio
import time
import psutil
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
from dataclasses import dataclass

import aiohttp

# Add project root to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""

    response_times: List[float]
    success_count: int
    failure_count: int
    start_time: float
    end_time: float
    memory_usage: Dict[str, float]

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def throughput(self) -> float:
        return (
            (self.success_count + self.failure_count) / self.duration
            if self.duration > 0
            else 0
        )

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total > 0 else 0

    @property
    def p95_response_time(self) -> float:
        return (
            statistics.quantiles(self.response_times, n=20)[18]
            if self.response_times
            else 0
        )

    @property
    def p99_response_time(self) -> float:
        return (
            statistics.quantiles(self.response_times, n=100)[98]
            if self.response_times
            else 0
        )

    @property
    def average_response_time(self) -> float:
        return statistics.mean(self.response_times) if self.response_times else 0


class PerformanceBenchmarkTest:
    """Performance benchmarking and load testing suite"""

    def __init__(self):
        self.base_urls = {
            "project": "http://localhost:8001",
            "generation": "http://localhost:8002",
        }
        self.session: Optional[aiohttp.ClientSession] = None

        # Performance tracking
        self.metrics_history = []
        self.test_projects = []

        # Benchmark parameters
        self.benchmark_config = {
            "episode_creation_load": 100,  # Number of episodes to create
            "concurrent_connections": 50,  # SSE connections to test
            "memory_check_interval": 30,  # Seconds between memory checks
            "continuous_operation_duration": 300,  # 5 minutes (abbreviated from 24h)
        }

    async def setup(self):
        """Setup performance benchmark environment"""
        print("🔧 Setting up Performance Benchmark environment...")

        # Create HTTP session with performance-optimized settings
        connector = aiohttp.TCPConnector(
            limit=200,  # Total connection pool size
            limit_per_host=50,  # Per-host connection limit
            keepalive_timeout=60,
            enable_cleanup_closed=True,
        )

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=300),
            headers={"User-Agent": "AI-Script-Generator-Benchmark/1.0"},
        )

        # Verify services are ready for load testing
        await self._verify_services_ready()

        # Capture baseline system metrics
        self.baseline_metrics = await self._capture_system_metrics()

        print("✅ Performance Benchmark environment ready")
        print(f"📊 Baseline CPU: {self.baseline_metrics['cpu_percent']:.1f}%")
        print(f"📊 Baseline Memory: {self.baseline_metrics['memory_percent']:.1f}%")

    async def teardown(self):
        """Cleanup benchmark environment"""
        print("🧹 Cleaning up Performance Benchmark environment...")

        # Clean up test data
        await self._cleanup_test_data()

        # Close session
        if self.session:
            await self.session.close()

        print("✅ Performance Benchmark environment cleaned up")

    async def test_episode_creation_p95_response_time(self):
        """Test Episode creation P95 response time measurement"""
        print(
            f"🧪 Testing Episode creation P95 response time ({self.benchmark_config['episode_creation_load']} operations)..."
        )

        # Step 1: Create test project
        project = await self._create_test_project("Episode Response Time Test")
        project_id = project["id"]

        # Step 2: Warm up the system
        print("🔥 Warming up system...")
        await self._perform_warmup_operations(project_id, 10)

        # Step 3: Run load test
        print(
            f"🚀 Running {self.benchmark_config['episode_creation_load']} episode creations..."
        )

        start_time = time.time()
        metrics = await self._run_episode_creation_load_test(
            project_id, self.benchmark_config["episode_creation_load"]
        )

        # Step 4: Analyze results
        print("📊 Episode Creation Performance Results:")
        print(f"  Total operations: {metrics.success_count + metrics.failure_count}")
        print(f"  Successful: {metrics.success_count}")
        print(f"  Failed: {metrics.failure_count}")
        print(f"  Success rate: {metrics.success_rate:.1f}%")
        print(f"  Duration: {metrics.duration:.2f}s")
        print(f"  Throughput: {metrics.throughput:.2f} ops/sec")
        print(f"  Average response time: {metrics.average_response_time:.3f}s")
        print(f"  P95 response time: {metrics.p95_response_time:.3f}s")
        print(f"  P99 response time: {metrics.p99_response_time:.3f}s")

        # Performance thresholds
        p95_threshold = 2.0  # 2 seconds
        success_rate_threshold = 95.0  # 95%

        p95_acceptable = metrics.p95_response_time <= p95_threshold
        success_rate_acceptable = metrics.success_rate >= success_rate_threshold

        overall_status = (
            "PASSED" if (p95_acceptable and success_rate_acceptable) else "FAILED"
        )

        print("🎯 Performance Assessment:")
        print(
            f"  P95 Response Time: {'✅ PASS' if p95_acceptable else '❌ FAIL'} ({metrics.p95_response_time:.3f}s <= {p95_threshold}s)"
        )
        print(
            f"  Success Rate: {'✅ PASS' if success_rate_acceptable else '❌ FAIL'} ({metrics.success_rate:.1f}% >= {success_rate_threshold}%)"
        )

        return {
            "test": "episode_creation_p95",
            "status": overall_status,
            "metrics": {
                "p95_response_time": metrics.p95_response_time,
                "p99_response_time": metrics.p99_response_time,
                "average_response_time": metrics.average_response_time,
                "success_rate": metrics.success_rate,
                "throughput": metrics.throughput,
                "total_operations": metrics.success_count + metrics.failure_count,
            },
            "thresholds": {
                "p95_threshold": p95_threshold,
                "success_rate_threshold": success_rate_threshold,
                "p95_acceptable": p95_acceptable,
                "success_rate_acceptable": success_rate_acceptable,
            },
        }

    async def test_concurrent_sse_connection_limits(self):
        """Test concurrent SSE connection limits"""
        print(
            f"🧪 Testing concurrent SSE connections limit ({self.benchmark_config['concurrent_connections']} connections)..."
        )

        # Step 1: Create test project and start generation
        project = await self._create_test_project("SSE Concurrency Test")

        # Start multiple long-running generations
        generation_ids = []
        for i in range(min(10, self.benchmark_config["concurrent_connections"])):
            try:
                generation_request = {
                    "project_id": project["id"],
                    "episode_title": f"Concurrent SSE Test Episode {i+1}",
                    "prompt": "A detailed scene that takes time to generate for SSE testing",
                    "ai_provider": "openai",
                    "model": "gpt-4",
                }

                gen_id = await self._start_generation(generation_request)
                generation_ids.append(gen_id)

            except Exception as e:
                print(f"⚠️ Could not start generation {i+1}: {e}")

        print(f"🚀 Started {len(generation_ids)} generations for SSE testing")

        # Step 2: Create concurrent SSE connections
        print(
            f"📡 Testing {self.benchmark_config['concurrent_connections']} concurrent SSE connections..."
        )

        connection_results = await self._test_concurrent_sse_connections(
            generation_ids, self.benchmark_config["concurrent_connections"]
        )

        # Step 3: Analyze connection results
        successful_connections = sum(1 for r in connection_results if r["connected"])
        connection_errors = [r for r in connection_results if not r["connected"]]

        print("📊 SSE Concurrency Results:")
        print(f"  Attempted connections: {len(connection_results)}")
        print(f"  Successful connections: {successful_connections}")
        print(f"  Failed connections: {len(connection_errors)}")
        print(
            f"  Success rate: {(successful_connections/len(connection_results)*100):.1f}%"
        )

        if connection_errors:
            print("🔍 Connection Error Types:")
            error_types = {}
            for error in connection_errors:
                error_type = error.get("error_type", "unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1

            for error_type, count in error_types.items():
                print(f"  - {error_type}: {count}")

        # Performance assessment
        connection_threshold = (
            0.8 * self.benchmark_config["concurrent_connections"]
        )  # 80% success rate
        connections_acceptable = successful_connections >= connection_threshold

        return {
            "test": "concurrent_sse_connections",
            "status": "PASSED" if connections_acceptable else "FAILED",
            "metrics": {
                "attempted_connections": len(connection_results),
                "successful_connections": successful_connections,
                "failed_connections": len(connection_errors),
                "success_rate": (
                    successful_connections / len(connection_results) * 100
                ),
                "connection_limit_reached": successful_connections
                < len(connection_results),
            },
            "threshold": connection_threshold,
            "acceptable": connections_acceptable,
        }

    async def test_memory_usage_and_leaks(self):
        """Test memory usage and leak detection"""
        print("🧪 Testing memory usage and leak detection...")

        # Step 1: Capture initial memory baseline
        initial_memory = await self._capture_system_metrics()
        print(f"📊 Initial memory usage: {initial_memory['memory_percent']:.1f}%")

        # Step 2: Run sustained operations to detect leaks
        print("🔄 Running sustained operations for leak detection...")

        memory_samples = [initial_memory]
        project = await self._create_test_project("Memory Leak Test")

        # Run operations in batches while monitoring memory
        batch_size = 20
        num_batches = 5

        for batch in range(num_batches):
            print(
                f"🏃 Running batch {batch + 1}/{num_batches} ({batch_size} operations)..."
            )

            # Run batch of operations
            start_time = time.time()
            batch_metrics = await self._run_episode_creation_load_test(
                project["id"], batch_size
            )

            # Capture memory after batch
            memory_sample = await self._capture_system_metrics()
            memory_sample["batch"] = batch + 1
            memory_sample["timestamp"] = time.time()
            memory_sample["operations_completed"] = batch_metrics.success_count
            memory_samples.append(memory_sample)

            print(
                f"  Batch {batch + 1} completed: {batch_metrics.success_count} operations, Memory: {memory_sample['memory_percent']:.1f}%"
            )

            # Brief pause between batches
            await asyncio.sleep(5)

        # Step 3: Force garbage collection and final measurement
        import gc

        gc.collect()
        await asyncio.sleep(10)

        final_memory = await self._capture_system_metrics()
        memory_samples.append(
            {**final_memory, "batch": "final", "timestamp": time.time()}
        )

        # Step 4: Analyze memory trends
        memory_percentages = [
            sample["memory_percent"]
            for sample in memory_samples
            if "memory_percent" in sample
        ]
        memory_growth = (
            final_memory["memory_percent"] - initial_memory["memory_percent"]
        )

        # Detect potential memory leaks
        leak_threshold = 10.0  # 10% memory growth indicates potential leak
        leak_detected = memory_growth > leak_threshold

        print("📊 Memory Analysis Results:")
        print(f"  Initial memory: {initial_memory['memory_percent']:.1f}%")
        print(f"  Final memory: {final_memory['memory_percent']:.1f}%")
        print(f"  Memory growth: {memory_growth:+.1f}%")
        print(f"  Peak memory: {max(memory_percentages):.1f}%")
        print(f"  Memory trend: {'📈 GROWING' if memory_growth > 2 else '📊 STABLE'}")
        print(f"  Leak detected: {'❌ YES' if leak_detected else '✅ NO'}")

        return {
            "test": "memory_usage_leaks",
            "status": "PASSED" if not leak_detected else "FAILED",
            "metrics": {
                "initial_memory_percent": initial_memory["memory_percent"],
                "final_memory_percent": final_memory["memory_percent"],
                "memory_growth_percent": memory_growth,
                "peak_memory_percent": max(memory_percentages),
                "total_operations": num_batches * batch_size,
                "batches_completed": num_batches,
            },
            "leak_analysis": {
                "threshold": leak_threshold,
                "detected": leak_detected,
                "samples": memory_samples[-5:],  # Last 5 samples
            },
        }

    async def test_continuous_operation_simulation(self):
        """Test 24-hour continuous operation simulation (abbreviated)"""
        duration_minutes = self.benchmark_config["continuous_operation_duration"] / 60
        print(
            f"🧪 Testing continuous operation simulation ({duration_minutes:.1f} minutes, abbreviated from 24h)..."
        )

        # Step 1: Setup continuous operation monitoring
        operation_stats = {
            "start_time": time.time(),
            "operations_completed": 0,
            "errors_encountered": 0,
            "memory_samples": [],
            "performance_samples": [],
        }

        project = await self._create_test_project("Continuous Operation Test")

        # Step 2: Run continuous operations with monitoring
        end_time = time.time() + self.benchmark_config["continuous_operation_duration"]
        check_interval = 30  # Check every 30 seconds

        print(
            f"🏃 Starting continuous operations for {duration_minutes:.1f} minutes..."
        )

        while time.time() < end_time:
            cycle_start = time.time()

            try:
                # Run a small batch of operations
                batch_size = 10
                batch_metrics = await self._run_episode_creation_load_test(
                    project["id"], batch_size
                )

                operation_stats["operations_completed"] += batch_metrics.success_count
                operation_stats["errors_encountered"] += batch_metrics.failure_count

                # Capture system metrics
                system_metrics = await self._capture_system_metrics()
                system_metrics["timestamp"] = time.time()
                system_metrics["operations_completed"] = operation_stats[
                    "operations_completed"
                ]
                operation_stats["memory_samples"].append(system_metrics)

                # Capture performance metrics
                performance_sample = {
                    "timestamp": time.time(),
                    "avg_response_time": batch_metrics.average_response_time,
                    "p95_response_time": batch_metrics.p95_response_time,
                    "success_rate": batch_metrics.success_rate,
                    "throughput": batch_metrics.throughput,
                }
                operation_stats["performance_samples"].append(performance_sample)

                elapsed = time.time() - operation_stats["start_time"]
                remaining = end_time - time.time()

                print(
                    f"⏱️ Continuous ops: {operation_stats['operations_completed']} completed, "
                    f"{operation_stats['errors_encountered']} errors, "
                    f"{elapsed/60:.1f}m elapsed, {remaining/60:.1f}m remaining"
                )

            except Exception as e:
                operation_stats["errors_encountered"] += 1
                print(f"⚠️ Continuous operation error: {e}")

            # Wait until next check interval
            cycle_duration = time.time() - cycle_start
            sleep_time = max(0, check_interval - cycle_duration)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        operation_stats["end_time"] = time.time()
        operation_stats["total_duration"] = (
            operation_stats["end_time"] - operation_stats["start_time"]
        )

        # Step 3: Analyze continuous operation results
        total_operations = (
            operation_stats["operations_completed"]
            + operation_stats["errors_encountered"]
        )
        success_rate = (
            (operation_stats["operations_completed"] / total_operations * 100)
            if total_operations > 0
            else 0
        )
        average_throughput = (
            total_operations / operation_stats["total_duration"] * 60
        )  # ops per minute

        # Analyze stability metrics
        memory_percentages = [
            sample["memory_percent"] for sample in operation_stats["memory_samples"]
        ]
        memory_stability = (
            max(memory_percentages) - min(memory_percentages)
            if memory_percentages
            else 0
        )

        performance_response_times = [
            sample["avg_response_time"]
            for sample in operation_stats["performance_samples"]
        ]
        response_time_stability = (
            max(performance_response_times) - min(performance_response_times)
            if performance_response_times
            else 0
        )

        print("📊 Continuous Operation Results:")
        print(f"  Duration: {operation_stats['total_duration']/60:.1f} minutes")
        print(f"  Operations completed: {operation_stats['operations_completed']}")
        print(f"  Errors encountered: {operation_stats['errors_encountered']}")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average throughput: {average_throughput:.1f} ops/min")
        print(f"  Memory stability: {memory_stability:.1f}% variation")
        print(f"  Response time stability: {response_time_stability:.3f}s variation")

        # Stability assessment
        stability_thresholds = {
            "success_rate": 90.0,  # 90% success rate
            "memory_stability": 15.0,  # Less than 15% memory variation
            "response_time_stability": 1.0,  # Less than 1s response time variation
        }

        stable_success_rate = success_rate >= stability_thresholds["success_rate"]
        stable_memory = memory_stability <= stability_thresholds["memory_stability"]
        stable_response_time = (
            response_time_stability <= stability_thresholds["response_time_stability"]
        )

        overall_stable = stable_success_rate and stable_memory and stable_response_time

        print("🎯 Stability Assessment:")
        print(
            f"  Success rate: {'✅ STABLE' if stable_success_rate else '❌ UNSTABLE'}"
        )
        print(f"  Memory usage: {'✅ STABLE' if stable_memory else '❌ UNSTABLE'}")
        print(
            f"  Response time: {'✅ STABLE' if stable_response_time else '❌ UNSTABLE'}"
        )
        print(f"  Overall: {'✅ STABLE' if overall_stable else '❌ UNSTABLE'}")

        return {
            "test": "continuous_operation",
            "status": "PASSED" if overall_stable else "FAILED",
            "duration_minutes": operation_stats["total_duration"] / 60,
            "metrics": {
                "operations_completed": operation_stats["operations_completed"],
                "errors_encountered": operation_stats["errors_encountered"],
                "success_rate": success_rate,
                "average_throughput_per_minute": average_throughput,
                "memory_stability_percent": memory_stability,
                "response_time_stability_seconds": response_time_stability,
            },
            "stability_assessment": {
                "thresholds": stability_thresholds,
                "stable_success_rate": stable_success_rate,
                "stable_memory": stable_memory,
                "stable_response_time": stable_response_time,
                "overall_stable": overall_stable,
            },
        }

    # Helper methods for performance testing
    async def _verify_services_ready(self):
        """Verify services are ready for load testing"""
        print("🔍 Verifying services are ready for load testing...")

        for service_name, base_url in self.base_urls.items():
            health_url = urljoin(base_url, "/health")

            async with self.session.get(health_url) as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ {service_name.title()} Service: Ready for load testing")
                else:
                    raise Exception(
                        f"❌ {service_name.title()} Service not ready: {response.status}"
                    )

    async def _capture_system_metrics(self) -> Dict:
        """Capture current system metrics"""
        process = psutil.Process()

        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_gb": psutil.virtual_memory().used / (1024**3),
            "memory_available_gb": psutil.virtual_memory().available / (1024**3),
            "process_memory_mb": process.memory_info().rss / (1024**2),
            "open_files": len(process.open_files()),
            "connections": len(process.connections()),
        }

    async def _create_test_project(self, name: str) -> Dict:
        """Create a test project for performance testing"""
        project_data = {
            "name": name,
            "type": "DRAMA",
            "description": f"Performance test project: {name}",
        }

        url = urljoin(self.base_urls["project"], "/api/projects")

        async with self.session.post(url, json=project_data) as response:
            if response.status == 201:
                project = await response.json()
                self.test_projects.append(project["id"])
                return project
            else:
                error_text = await response.text()
                raise Exception(
                    f"Failed to create project: {response.status} - {error_text}"
                )

    async def _perform_warmup_operations(self, project_id: str, count: int):
        """Perform warmup operations to stabilize system"""
        for i in range(count):
            try:
                episode_data = {
                    "project_id": project_id,
                    "title": f"Warmup Episode {i+1}",
                    "status": "draft",
                }

                url = urljoin(
                    self.base_urls["project"], f"/api/projects/{project_id}/episodes"
                )
                async with self.session.post(url, json=episode_data) as response:
                    if response.status != 201:
                        print(f"⚠️ Warmup operation {i+1} failed: {response.status}")

            except Exception as e:
                print(f"⚠️ Warmup operation {i+1} error: {e}")

            # Small delay between warmup operations
            await asyncio.sleep(0.1)

    async def _run_episode_creation_load_test(
        self, project_id: str, operation_count: int
    ) -> PerformanceMetrics:
        """Run episode creation load test"""
        response_times = []
        success_count = 0
        failure_count = 0

        start_time = time.time()
        start_memory = await self._capture_system_metrics()

        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(20)  # Max 20 concurrent operations

        async def create_episode(episode_index: int) -> Tuple[bool, float]:
            async with semaphore:
                episode_start = time.time()

                try:
                    episode_data = {
                        "project_id": project_id,
                        "title": f"Load Test Episode {episode_index}",
                        "status": "draft",
                    }

                    url = urljoin(
                        self.base_urls["project"],
                        f"/api/projects/{project_id}/episodes",
                    )
                    async with self.session.post(url, json=episode_data) as response:
                        response_time = time.time() - episode_start

                        if response.status == 201:
                            return True, response_time
                        else:
                            return False, response_time

                except Exception:
                    response_time = time.time() - episode_start
                    return False, response_time

        # Execute all operations concurrently
        tasks = [create_episode(i) for i in range(operation_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Exception):
                failure_count += 1
                response_times.append(10.0)  # Assume 10s for failed operations
            else:
                success, response_time = result
                response_times.append(response_time)
                if success:
                    success_count += 1
                else:
                    failure_count += 1

        end_time = time.time()
        end_memory = await self._capture_system_metrics()

        return PerformanceMetrics(
            response_times=response_times,
            success_count=success_count,
            failure_count=failure_count,
            start_time=start_time,
            end_time=end_time,
            memory_usage={"start": start_memory, "end": end_memory},
        )

    async def _start_generation(self, generation_request: Dict) -> str:
        """Start a script generation"""
        url = urljoin(self.base_urls["generation"], "/api/generations")

        async with self.session.post(url, json=generation_request) as response:
            if response.status == 201:
                result = await response.json()
                return result["generation_id"]
            else:
                error_text = await response.text()
                raise Exception(
                    f"Failed to start generation: {response.status} - {error_text}"
                )

    async def _test_concurrent_sse_connections(
        self, generation_ids: List[str], target_connections: int
    ) -> List[Dict]:
        """Test concurrent SSE connections"""
        connection_results = []

        # Create more connection attempts than available generations
        connection_tasks = []

        for i in range(target_connections):
            # Cycle through available generation IDs
            generation_id = (
                generation_ids[i % len(generation_ids)] if generation_ids else None
            )

            if generation_id:
                task = self._test_single_sse_connection(generation_id, i)
                connection_tasks.append(task)
            else:
                connection_results.append(
                    {
                        "connection_id": i,
                        "connected": False,
                        "error_type": "no_generation_available",
                    }
                )

        # Execute connection attempts concurrently
        if connection_tasks:
            sse_results = await asyncio.gather(
                *connection_tasks, return_exceptions=True
            )

            for i, result in enumerate(sse_results):
                if isinstance(result, Exception):
                    connection_results.append(
                        {
                            "connection_id": len(connection_results),
                            "connected": False,
                            "error_type": "connection_exception",
                            "error": str(result),
                        }
                    )
                else:
                    connection_results.append(result)

        return connection_results

    async def _test_single_sse_connection(
        self, generation_id: str, connection_id: int
    ) -> Dict:
        """Test a single SSE connection"""
        sse_url = urljoin(
            self.base_urls["generation"], f"/api/generations/{generation_id}/stream"
        )

        try:
            async with self.session.get(sse_url) as response:
                if response.status != 200:
                    return {
                        "connection_id": connection_id,
                        "connected": False,
                        "error_type": f"http_{response.status}",
                    }

                # Read a few events to verify connection works
                events_received = 0
                async for line in response.content:
                    line = line.decode("utf-8").strip()

                    if line.startswith("data: "):
                        events_received += 1

                        # After receiving a few events, consider connection successful
                        if events_received >= 2:
                            break

                return {
                    "connection_id": connection_id,
                    "connected": True,
                    "events_received": events_received,
                }

        except Exception as e:
            return {
                "connection_id": connection_id,
                "connected": False,
                "error_type": "connection_error",
                "error": str(e),
            }

    async def _cleanup_test_data(self):
        """Clean up performance test data"""
        for project_id in self.test_projects:
            try:
                url = urljoin(self.base_urls["project"], f"/api/projects/{project_id}")
                async with self.session.delete(url) as response:
                    if response.status == 204:
                        print(f"🧹 Cleaned up test project: {project_id}")
            except Exception as e:
                print(f"⚠️ Could not clean up project {project_id}: {e}")


async def run_performance_benchmark_tests():
    """Run all performance benchmark tests"""
    print("🚀 Starting E2E Performance Benchmark Tests")
    print("=" * 60)

    test_suite = PerformanceBenchmarkTest()

    try:
        # Setup
        await test_suite.setup()

        # Test 1: Episode creation P95 response time
        print("\n📋 Test 1: Episode Creation P95 Response Time")
        response_time_result = (
            await test_suite.test_episode_creation_p95_response_time()
        )

        # Test 2: Concurrent SSE connection limits
        print("\n📋 Test 2: Concurrent SSE Connection Limits")
        sse_result = await test_suite.test_concurrent_sse_connection_limits()

        # Test 3: Memory usage and leak detection
        print("\n📋 Test 3: Memory Usage and Leak Detection")
        memory_result = await test_suite.test_memory_usage_and_leaks()

        # Test 4: Continuous operation simulation
        print("\n📋 Test 4: Continuous Operation Simulation")
        continuous_result = await test_suite.test_continuous_operation_simulation()

        # Summary
        print("\n🎉 E2E Performance Benchmark Tests Summary:")
        print(
            f"✅ Episode creation P95: {response_time_result['status']} ({response_time_result['metrics']['p95_response_time']:.3f}s)"
        )
        print(
            f"✅ SSE concurrency: {sse_result['status']} ({sse_result['metrics']['successful_connections']}/{sse_result['metrics']['attempted_connections']})"
        )
        print(
            f"✅ Memory leaks: {memory_result['status']} ({memory_result['metrics']['memory_growth_percent']:+.1f}%)"
        )
        print(
            f"✅ Continuous operation: {continuous_result['status']} ({continuous_result['duration_minutes']:.1f}m, {continuous_result['metrics']['success_rate']:.1f}%)"
        )

        all_passed = all(
            result["status"] == "PASSED"
            for result in [
                response_time_result,
                sse_result,
                memory_result,
                continuous_result,
            ]
        )

        return {
            "response_time_test": response_time_result,
            "sse_concurrency_test": sse_result,
            "memory_test": memory_result,
            "continuous_operation_test": continuous_result,
            "overall_status": "PASSED" if all_passed else "FAILED",
        }

    except Exception as e:
        print(f"\n❌ E2E Performance Benchmark Tests FAILED: {e}")
        return {"overall_status": "FAILED", "error": str(e)}

    finally:
        # Cleanup
        await test_suite.teardown()


if __name__ == "__main__":
    # Install required package if not available
    try:
        import psutil
    except ImportError:
        print("Installing psutil for system monitoring...")
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil

    # Run the tests
    results = asyncio.run(run_performance_benchmark_tests())

    if results.get("overall_status") == "FAILED":
        sys.exit(1)
    else:
        print("\n✅ All E2E Performance Benchmark Tests PASSED!")
        sys.exit(0)
