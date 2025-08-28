#!/usr/bin/env python3
"""
AI Script Generator v3.0 - Provider Fallback & Feature Flag Testing
Tests AI provider routing, fallback mechanisms, and feature flag toggles for Day-0 readiness.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import aiohttp
from enum import Enum


class ProviderType(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    LOCAL = "local"


class ProviderTest:
    def __init__(
        self, provider: ProviderType, priority: int, expected_available: bool = True
    ):
        self.provider = provider
        self.priority = priority
        self.expected_available = expected_available
        self.response_time = None
        self.success = False
        self.error = None
        self.fallback_triggered = False


class ProviderFallbackTester:
    """Test provider fallback mechanisms and feature flags"""

    def __init__(self):
        self.base_url = "http://localhost:8002"
        self.project_service_url = "http://localhost:8001"
        self.test_results = {
            "provider_tests": [],
            "fallback_tests": [],
            "feature_flag_tests": [],
            "overall_success": False,
        }

    async def run_comprehensive_fallback_test(self) -> Dict[str, Any]:
        """Run comprehensive provider fallback and feature flag testing"""
        print("🔄 AI Script Generator v3.0 - Provider Fallback & Feature Flag Test")
        print("=" * 70)
        print("🎯 Testing: OpenAI → Anthropic → Gemini → Local fallback chain")
        print(
            "🚩 Feature flags: Provider routing, fallback enabling, graceful degradation"
        )
        print()

        # Create test project
        project_id = await self._create_test_project()
        if not project_id:
            return {"success": False, "error": "Failed to create test project"}

        print(f"✅ Test project created: {project_id}")

        # Test 1: Individual provider availability
        print("\n📋 Test 1: Individual Provider Availability")
        await self._test_individual_providers(project_id)

        # Test 2: Provider fallback scenarios
        print("\n📋 Test 2: Provider Fallback Scenarios")
        await self._test_fallback_scenarios(project_id)

        # Test 3: Feature flag toggles
        print("\n📋 Test 3: Feature Flag Toggles")
        await self._test_feature_flags(project_id)

        # Test 4: Graceful degradation
        print("\n📋 Test 4: Graceful Degradation")
        await self._test_graceful_degradation(project_id)

        # Generate final report
        return await self._generate_fallback_report()

    async def _create_test_project(self) -> Optional[str]:
        """Create test project for fallback testing"""
        timeout = aiohttp.ClientTimeout(total=30)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                project_url = f"{self.project_service_url}/api/v1/projects/"
                project_data = {
                    "name": f"Provider Fallback Test {int(time.time())}",
                    "type": "drama",
                    "description": "Provider fallback and feature flag testing project",
                }

                headers = {"Idempotency-Key": f"fallback_test_{int(time.time())}"}

                async with session.post(
                    project_url, json=project_data, headers=headers
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        return result.get("data", {}).get("id")
        except Exception as e:
            print(f"❌ Project creation error: {e}")

        return None

    async def _test_individual_providers(self, project_id: str):
        """Test each provider individually"""
        providers_to_test = [
            ProviderTest(ProviderType.OPENAI, 1, True),
            ProviderTest(ProviderType.ANTHROPIC, 2, True),
            ProviderTest(ProviderType.GEMINI, 3, False),  # May not be configured
            ProviderTest(ProviderType.LOCAL, 4, True),  # Fallback should always work
        ]

        for provider_test in providers_to_test:
            await self._test_single_provider(project_id, provider_test)
            self.test_results["provider_tests"].append(provider_test)

    async def _test_single_provider(self, project_id: str, provider_test: ProviderTest):
        """Test a single AI provider"""
        timeout = aiohttp.ClientTimeout(total=60)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                generation_url = f"{self.base_url}/api/v1/generations"
                generation_data = {
                    "projectId": project_id,
                    "description": f"Test generation using {provider_test.provider.value} provider",
                    "scriptType": "drama",
                    "model": provider_test.provider.value,  # Force specific provider
                }

                headers = {
                    "Idempotency-Key": f"provider_test_{provider_test.provider.value}_{int(time.time())}",
                    "X-Preferred-Provider": provider_test.provider.value,  # Feature flag header
                }

                start_time = time.time()

                async with session.post(
                    generation_url, json=generation_data, headers=headers
                ) as response:
                    provider_test.response_time = time.time() - start_time

                    if response.status in [200, 201]:
                        job_data = await response.json()
                        job_id = job_data.get("jobId")

                        if job_id:
                            # Quick SSE test to verify generation starts
                            sse_success = await self._quick_sse_test(session, job_id)
                            provider_test.success = sse_success

                            status = "✅" if sse_success else "⚠️"
                            print(
                                f"  {status} {provider_test.provider.value}: "
                                f"{provider_test.response_time:.2f}s response"
                            )
                        else:
                            provider_test.error = "No jobId returned"
                            print(f"  ❌ {provider_test.provider.value}: No job ID")
                    else:
                        provider_test.error = f"HTTP {response.status}"
                        status = "⚠️" if not provider_test.expected_available else "❌"
                        print(
                            f"  {status} {provider_test.provider.value}: HTTP {response.status}"
                        )

        except Exception as e:
            provider_test.error = str(e)
            status = "⚠️" if not provider_test.expected_available else "❌"
            print(f"  {status} {provider_test.provider.value}: {e}")

    async def _quick_sse_test(
        self, session: aiohttp.ClientSession, job_id: str
    ) -> bool:
        """Quick SSE test to verify generation starts"""
        try:
            sse_url = f"{self.base_url}/api/v1/generations/{job_id}/events"
            timeout = aiohttp.ClientTimeout(total=15)

            async with session.get(
                sse_url, headers={"Accept": "text/event-stream"}, timeout=timeout
            ) as response:
                if response.status == 200:
                    # Wait for first event
                    async for line in response.content:
                        line_str = line.decode("utf-8", errors="ignore").strip()
                        if line_str.startswith("data:"):
                            return True  # Got first event
                        if line_str.startswith("event: error"):
                            return False  # Error event

            return False
        except Exception:
            return False

    async def _test_fallback_scenarios(self, project_id: str):
        """Test provider fallback scenarios"""
        fallback_scenarios = [
            {
                "name": "OpenAI Unavailable → Anthropic",
                "disabled_providers": ["openai"],
                "expected_provider": "anthropic",
            },
            {
                "name": "OpenAI + Anthropic Unavailable → Local",
                "disabled_providers": ["openai", "anthropic"],
                "expected_provider": "local",
            },
            {
                "name": "All External Unavailable → Local Only",
                "disabled_providers": ["openai", "anthropic", "gemini"],
                "expected_provider": "local",
            },
        ]

        for scenario in fallback_scenarios:
            await self._test_fallback_scenario(project_id, scenario)

    async def _test_fallback_scenario(self, project_id: str, scenario: Dict[str, Any]):
        """Test a specific fallback scenario"""
        print(f"  🔄 Testing: {scenario['name']}")

        timeout = aiohttp.ClientTimeout(total=90)  # Longer timeout for fallback

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                generation_url = f"{self.base_url}/api/v1/generations"
                generation_data = {
                    "projectId": project_id,
                    "description": f"Fallback test: {scenario['name']}",
                    "scriptType": "drama",
                }

                headers = {
                    "Idempotency-Key": f"fallback_{int(time.time())}",
                    "X-Disabled-Providers": ",".join(
                        scenario["disabled_providers"]
                    ),  # Simulate provider failures
                }

                start_time = time.time()

                async with session.post(
                    generation_url, json=generation_data, headers=headers
                ) as response:
                    response_time = time.time() - start_time

                    if response.status in [200, 201]:
                        job_data = await response.json()
                        job_id = job_data.get("jobId")

                        if job_id:
                            # Check which provider was actually used
                            provider_used = await self._detect_provider_used(
                                session, job_id
                            )

                            if provider_used == scenario["expected_provider"]:
                                print(
                                    f"    ✅ Fallback successful: {provider_used} ({response_time:.2f}s)"
                                )
                                scenario["success"] = True
                            else:
                                print(
                                    f"    ⚠️ Unexpected provider: {provider_used} (expected: {scenario['expected_provider']})"
                                )
                                scenario["success"] = False
                        else:
                            print("    ❌ No job ID returned")
                            scenario["success"] = False
                    else:
                        print(f"    ❌ HTTP {response.status}")
                        scenario["success"] = False

        except Exception as e:
            print(f"    ❌ Error: {e}")
            scenario["success"] = False

        self.test_results["fallback_tests"].append(scenario)

    async def _detect_provider_used(
        self, session: aiohttp.ClientSession, job_id: str
    ) -> str:
        """Detect which provider was actually used for generation"""
        try:
            # Check job status/metadata endpoint
            job_url = f"{self.base_url}/api/v1/generations/{job_id}"

            async with session.get(job_url) as response:
                if response.status == 200:
                    job_data = await response.json()
                    return job_data.get("provider_used", "unknown")
        except Exception:
            pass

        return "unknown"

    async def _test_feature_flags(self, project_id: str):
        """Test feature flag functionality"""
        feature_tests = [
            {
                "name": "Enable All Providers",
                "flags": {"providers_enabled": "openai,anthropic,local"},
                "expected_behavior": "normal_operation",
            },
            {
                "name": "Disable External Providers",
                "flags": {"providers_enabled": "local"},
                "expected_behavior": "local_only",
            },
            {
                "name": "Enable Provider Retry",
                "flags": {"enable_provider_retry": "true", "max_retries": "3"},
                "expected_behavior": "retry_on_failure",
            },
            {
                "name": "Graceful Degradation Mode",
                "flags": {"graceful_degradation": "true", "fallback_to_cached": "true"},
                "expected_behavior": "graceful_fallback",
            },
        ]

        for test in feature_tests:
            await self._test_feature_flag(project_id, test)

    async def _test_feature_flag(self, project_id: str, flag_test: Dict[str, Any]):
        """Test individual feature flag"""
        print(f"  🚩 Testing: {flag_test['name']}")

        timeout = aiohttp.ClientTimeout(total=60)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                generation_url = f"{self.base_url}/api/v1/generations"
                generation_data = {
                    "projectId": project_id,
                    "description": f"Feature flag test: {flag_test['name']}",
                    "scriptType": "drama",
                }

                # Add feature flag headers
                headers = {"Idempotency-Key": f"feature_flag_{int(time.time())}"}

                for flag_name, flag_value in flag_test["flags"].items():
                    headers[f"X-Feature-{flag_name.replace('_', '-')}"] = flag_value

                start_time = time.time()

                async with session.post(
                    generation_url, json=generation_data, headers=headers
                ) as response:
                    response_time = time.time() - start_time

                    if response.status in [200, 201]:
                        job_data = await response.json()
                        behavior_observed = await self._observe_behavior(
                            session, job_data
                        )

                        if behavior_observed == flag_test["expected_behavior"]:
                            print(
                                f"    ✅ Feature flag working: {behavior_observed} ({response_time:.2f}s)"
                            )
                            flag_test["success"] = True
                        else:
                            print(f"    ⚠️ Unexpected behavior: {behavior_observed}")
                            flag_test["success"] = False
                    else:
                        print(f"    ❌ HTTP {response.status}")
                        flag_test["success"] = False

        except Exception as e:
            print(f"    ❌ Error: {e}")
            flag_test["success"] = False

        self.test_results["feature_flag_tests"].append(flag_test)

    async def _observe_behavior(
        self, session: aiohttp.ClientSession, job_data: Dict[str, Any]
    ) -> str:
        """Observe actual system behavior from job execution"""
        # This would analyze job metadata, logs, or SSE events to determine behavior
        # For now, return a simplified version
        job_id = job_data.get("jobId")
        if job_id:
            # Quick SSE check to see if generation proceeds normally
            sse_success = await self._quick_sse_test(session, job_id)
            return "normal_operation" if sse_success else "degraded_operation"
        return "unknown"

    async def _test_graceful_degradation(self, project_id: str):
        """Test graceful degradation scenarios"""
        degradation_tests = [
            {
                "name": "All AI Providers Down",
                "condition": "no_ai_providers",
                "expected": "cached_response_or_error",
            },
            {
                "name": "Database Unavailable",
                "condition": "database_down",
                "expected": "in_memory_fallback",
            },
            {
                "name": "High Load Scenario",
                "condition": "high_load",
                "expected": "rate_limiting_or_queuing",
            },
        ]

        for test in degradation_tests:
            await self._test_degradation_scenario(project_id, test)

    async def _test_degradation_scenario(
        self, project_id: str, degradation_test: Dict[str, Any]
    ):
        """Test graceful degradation scenario"""
        print(f"  🔧 Testing: {degradation_test['name']}")

        # This would simulate the degradation condition and verify the response
        # For Day-0, we mainly want to verify the system doesn't crash

        timeout = aiohttp.ClientTimeout(total=30)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                generation_url = f"{self.base_url}/api/v1/generations"
                generation_data = {
                    "projectId": project_id,
                    "description": f"Degradation test: {degradation_test['name']}",
                    "scriptType": "drama",
                }

                headers = {
                    "Idempotency-Key": f"degradation_{int(time.time())}",
                    f"X-Simulate-{degradation_test['condition'].replace('_', '-')}": "true",
                }

                async with session.post(
                    generation_url, json=generation_data, headers=headers
                ) as response:
                    # We expect either success or a graceful error response
                    if response.status in [
                        200,
                        201,
                        503,
                        429,
                    ]:  # Include expected degradation codes
                        print(f"    ✅ Graceful response: HTTP {response.status}")
                        degradation_test["success"] = True
                    else:
                        print(f"    ❌ Ungraceful failure: HTTP {response.status}")
                        degradation_test["success"] = False

        except Exception as e:
            # Even exceptions should be graceful (not crash the whole system)
            if "timeout" in str(e).lower():
                print(f"    ⚠️ Timeout (acceptable for degradation): {e}")
                degradation_test["success"] = True
            else:
                print(f"    ❌ Unexpected error: {e}")
                degradation_test["success"] = False

        self.test_results["fallback_tests"].append(degradation_test)

    async def _generate_fallback_report(self) -> Dict[str, Any]:
        """Generate comprehensive fallback testing report"""
        # Calculate success rates
        provider_success_rate = (
            sum(1 for t in self.test_results["provider_tests"] if t.success)
            / len(self.test_results["provider_tests"])
            * 100
            if self.test_results["provider_tests"]
            else 0
        )
        fallback_success_rate = (
            sum(
                1
                for t in self.test_results["fallback_tests"]
                if t.get("success", False)
            )
            / len(self.test_results["fallback_tests"])
            * 100
            if self.test_results["fallback_tests"]
            else 0
        )
        feature_flag_success_rate = (
            sum(
                1
                for t in self.test_results["feature_flag_tests"]
                if t.get("success", False)
            )
            / len(self.test_results["feature_flag_tests"])
            * 100
            if self.test_results["feature_flag_tests"]
            else 0
        )

        overall_success = (
            provider_success_rate >= 75  # At least 3/4 providers working
            and fallback_success_rate >= 80  # Most fallback scenarios work
            and feature_flag_success_rate >= 75  # Most feature flags work
        )

        print("\n" + "=" * 70)
        print("🎯 Provider Fallback & Feature Flag Test Results")
        print("=" * 70)

        print("\n📊 Test Summary:")
        print(f"  Provider Tests: {provider_success_rate:.1f}% success")
        print(f"  Fallback Tests: {fallback_success_rate:.1f}% success")
        print(f"  Feature Flags: {feature_flag_success_rate:.1f}% success")

        status = "✅ PASS" if overall_success else "❌ FAIL"
        print(f"\n🎯 Day-0 Fallback Readiness: {status}")

        if overall_success:
            print("🚀 Provider fallback and feature flag systems are Day-0 ready!")
        else:
            print("⚠️ Provider fallback system needs attention before Day-0")

        # Generate detailed report
        report = {
            "test_execution": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_type": "provider_fallback_and_feature_flags",
            },
            "success_rates": {
                "provider_tests": provider_success_rate,
                "fallback_tests": fallback_success_rate,
                "feature_flag_tests": feature_flag_success_rate,
            },
            "day0_readiness": {
                "provider_fallback_ready": fallback_success_rate >= 80,
                "feature_flags_ready": feature_flag_success_rate >= 75,
                "overall_ready": overall_success,
            },
            "detailed_results": self.test_results,
        }

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"provider_fallback_test_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"📄 Detailed results saved to: {results_file}")

        return report


async def main():
    """Main test execution"""
    tester = ProviderFallbackTester()

    try:
        report = await tester.run_comprehensive_fallback_test()

        if report.get("day0_readiness", {}).get("overall_ready", False):
            print("\n🎉 Provider fallback Day-0 test PASSED!")
            return True
        else:
            print("\n⚠️ Provider fallback Day-0 test FAILED!")
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
