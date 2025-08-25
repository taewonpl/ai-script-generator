#!/usr/bin/env python3
"""
E2E Core Flow Integration Tests
Tests the complete flow: Project Creation → Script Generation (SSE) → Episode Storage → Numbering Verification
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from pydantic import BaseModel

# Add project root to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestProject(BaseModel):
    """Test project model"""

    id: str
    name: str
    type: str
    status: str
    episodes: List[Dict] = []


class TestScriptGeneration(BaseModel):
    """Test script generation model"""

    generation_id: str
    status: str
    progress: float = 0.0
    content: Optional[str] = None
    episode_data: Optional[Dict] = None


class E2ECoreFlowTest:
    """E2E Core Flow Integration Tests"""

    def __init__(self):
        self.base_urls = {
            "project": "http://localhost:8001",
            "generation": "http://localhost:8002",
        }
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_data = {"projects": [], "generations": [], "episodes": []}

    async def setup(self):
        """Setup test environment"""
        print("🔧 Setting up E2E test environment...")

        # Create HTTP session
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))

        # Verify all services are running
        await self._verify_services()

        # Clean up any existing test data
        await self._cleanup_test_data()

        print("✅ E2E test environment ready")

    async def teardown(self):
        """Cleanup test environment"""
        print("🧹 Cleaning up E2E test environment...")

        # Clean up test data
        await self._cleanup_test_data()

        # Close session
        if self.session:
            await self.session.close()

        print("✅ E2E test environment cleaned up")

    async def _verify_services(self):
        """Verify all required services are running"""
        print("🔍 Verifying services are running...")

        for service_name, base_url in self.base_urls.items():
            health_url = urljoin(base_url, "/health")
            try:
                async with self.session.get(health_url) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        print(
                            f"✅ {service_name.title()} Service: {health_data.get('status', 'OK')}"
                        )
                    else:
                        raise Exception(
                            f"Health check failed with status {response.status}"
                        )
            except Exception as e:
                raise Exception(f"❌ {service_name.title()} Service not available: {e}")

    async def _cleanup_test_data(self):
        """Clean up any existing test data"""
        # This would involve cleaning up test projects, generations, episodes
        # Implementation depends on the actual API endpoints available
        pass

    async def test_single_project_episode_flow(self) -> Dict:
        """Test single project with episode creation flow"""
        print("🧪 Testing single project-episode flow...")

        # Step 1: Create project
        project_data = {
            "name": "E2E Test Project",
            "type": "DRAMA",
            "description": "End-to-end test project",
        }

        project = await self._create_project(project_data)
        print(f"✅ Project created: {project['id']}")

        # Step 2: Generate script with SSE
        generation_request = {
            "project_id": project["id"],
            "episode_title": "Test Episode 1",
            "prompt": "Create a short dramatic scene with two characters discussing their future.",
            "ai_provider": "openai",
            "model": "gpt-4",
        }

        generation = await self._start_script_generation_with_sse(generation_request)
        print(f"✅ Script generation completed: {generation['generation_id']}")

        # Step 3: Verify episode was created with correct numbering
        episodes = await self._get_project_episodes(project["id"])

        assert len(episodes) == 1, f"Expected 1 episode, got {len(episodes)}"
        assert (
            episodes[0]["number"] == 1
        ), f"Expected episode number 1, got {episodes[0]['number']}"

        print(f"✅ Episode created with correct number: {episodes[0]['number']}")

        return {"project": project, "generation": generation, "episodes": episodes}

    async def test_concurrent_episodes_numbering(
        self, num_users: int = 15, episodes_per_user: int = 4
    ):
        """Test concurrent episode creation with proper numbering"""
        print(
            f"🧪 Testing concurrent episodes: {num_users} users × {episodes_per_user} episodes = {num_users * episodes_per_user} total"
        )

        # Step 1: Create test project
        project_data = {
            "name": "Concurrent Episodes Test Project",
            "type": "DRAMA",
            "description": "Testing concurrent episode numbering",
        }

        project = await self._create_project(project_data)
        print(f"✅ Test project created: {project['id']}")

        # Step 2: Create tasks for concurrent episode generation
        tasks = []
        for user_id in range(num_users):
            for episode_num in range(episodes_per_user):
                task = self._create_episode_task(
                    project["id"],
                    user_id,
                    episode_num,
                    f"User {user_id+1} Episode {episode_num+1}",
                )
                tasks.append(task)

        # Step 3: Execute all tasks concurrently
        print(f"🚀 Starting {len(tasks)} concurrent episode creations...")
        start_time = time.time()

        results = await asyncio.gather(*tasks, return_exceptions=True)

        execution_time = time.time() - start_time
        print(f"⏱️ Concurrent execution completed in {execution_time:.2f} seconds")

        # Step 4: Analyze results
        successful_generations = [r for r in results if not isinstance(r, Exception)]
        failed_generations = [r for r in results if isinstance(r, Exception)]

        print(f"✅ Successful generations: {len(successful_generations)}")
        print(f"❌ Failed generations: {len(failed_generations)}")

        if failed_generations:
            print("🔍 Failed generation details:")
            for i, error in enumerate(failed_generations[:5]):  # Show first 5 errors
                print(f"  {i+1}. {error}")

        # Step 5: Verify episode numbering integrity
        episodes = await self._get_project_episodes(project["id"])
        episode_numbers = sorted([ep["number"] for ep in episodes])

        expected_numbers = list(range(1, len(successful_generations) + 1))

        print("🔍 Episode numbering verification:")
        print(
            f"  Expected: {len(expected_numbers)} episodes (1-{len(expected_numbers)})"
        )
        print(f"  Actual: {len(episode_numbers)} episodes")
        print(
            f"  Numbers: {episode_numbers[:10]}{'...' if len(episode_numbers) > 10 else ''}"
        )

        # Check for gaps and duplicates
        gaps = [num for num in expected_numbers if num not in episode_numbers]
        duplicates = [
            num for num in set(episode_numbers) if episode_numbers.count(num) > 1
        ]

        assert len(gaps) == 0, f"Episode numbering gaps found: {gaps}"
        assert len(duplicates) == 0, f"Duplicate episode numbers found: {duplicates}"
        assert (
            episode_numbers == expected_numbers
        ), "Episode numbers don't match expected sequence"

        print("✅ Episode numbering integrity verified!")

        return {
            "project": project,
            "total_episodes": len(episodes),
            "execution_time": execution_time,
            "success_rate": len(successful_generations) / len(tasks) * 100,
            "episodes": episodes,
        }

    async def _create_project(self, project_data: Dict) -> Dict:
        """Create a test project"""
        url = urljoin(self.base_urls["project"], "/api/projects")

        async with self.session.post(url, json=project_data) as response:
            if response.status == 201:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(
                    f"Failed to create project: {response.status} - {error_text}"
                )

    async def _start_script_generation_with_sse(self, generation_request: Dict) -> Dict:
        """Start script generation and monitor via SSE until completion"""
        # Start generation
        start_url = urljoin(self.base_urls["generation"], "/api/generations")

        async with self.session.post(start_url, json=generation_request) as response:
            if response.status == 201:
                start_response = await response.json()
                generation_id = start_response["generation_id"]
            else:
                error_text = await response.text()
                raise Exception(
                    f"Failed to start generation: {response.status} - {error_text}"
                )

        # Monitor via SSE
        sse_url = urljoin(
            self.base_urls["generation"], f"/api/generations/{generation_id}/stream"
        )

        final_result = None
        timeout = 120  # 2 minutes timeout
        start_time = time.time()

        async with self.session.get(sse_url) as response:
            if response.status != 200:
                raise Exception(f"SSE connection failed: {response.status}")

            async for line in response.content:
                if time.time() - start_time > timeout:
                    raise Exception("Generation timeout")

                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data == "[DONE]":
                        break

                    try:
                        event_data = json.loads(data)
                        if event_data.get("status") == "completed":
                            final_result = event_data
                            break
                        elif event_data.get("status") == "failed":
                            raise Exception(
                                f"Generation failed: {event_data.get('error')}"
                            )
                    except json.JSONDecodeError:
                        continue  # Skip non-JSON lines

        if not final_result:
            raise Exception("Generation did not complete successfully")

        return final_result

    async def _create_episode_task(
        self, project_id: str, user_id: int, episode_index: int, title: str
    ):
        """Create a single episode generation task"""
        generation_request = {
            "project_id": project_id,
            "episode_title": title,
            "prompt": f"Create episode {episode_index + 1} for user {user_id + 1}: A short scene with dialogue.",
            "ai_provider": "openai",
            "model": "gpt-3.5-turbo",  # Use faster model for concurrent tests
        }

        try:
            return await self._start_script_generation_with_sse(generation_request)
        except Exception as e:
            print(
                f"❌ Episode creation failed for user {user_id+1}, episode {episode_index+1}: {e}"
            )
            raise

    async def _get_project_episodes(self, project_id: str) -> List[Dict]:
        """Get all episodes for a project"""
        url = urljoin(self.base_urls["project"], f"/api/projects/{project_id}/episodes")

        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(
                    f"Failed to get episodes: {response.status} - {error_text}"
                )


async def run_core_flow_tests():
    """Run all core flow integration tests"""
    print("🚀 Starting E2E Core Flow Integration Tests")
    print("=" * 60)

    test_suite = E2ECoreFlowTest()

    try:
        # Setup
        await test_suite.setup()

        # Test 1: Single project-episode flow
        print("\n📋 Test 1: Single Project-Episode Flow")
        single_result = await test_suite.test_single_project_episode_flow()

        # Test 2: Concurrent episodes with numbering verification
        print("\n📋 Test 2: Concurrent Episodes Numbering")
        concurrent_result = await test_suite.test_concurrent_episodes_numbering(
            num_users=15, episodes_per_user=4
        )

        # Summary
        print("\n🎉 E2E Core Flow Tests Summary:")
        print("✅ Single flow test: PASSED")
        print(
            f"✅ Concurrent test: {concurrent_result['total_episodes']} episodes created"
        )
        print(f"✅ Success rate: {concurrent_result['success_rate']:.1f}%")
        print(f"✅ Execution time: {concurrent_result['execution_time']:.2f}s")
        print(
            f"✅ Episode numbering: VERIFIED (1-{concurrent_result['total_episodes']})"
        )

        return {
            "single_test": single_result,
            "concurrent_test": concurrent_result,
            "overall_status": "PASSED",
        }

    except Exception as e:
        print(f"\n❌ E2E Core Flow Tests FAILED: {e}")
        return {"overall_status": "FAILED", "error": str(e)}

    finally:
        # Cleanup
        await test_suite.teardown()


if __name__ == "__main__":
    # Run the tests
    results = asyncio.run(run_core_flow_tests())

    if results.get("overall_status") == "FAILED":
        sys.exit(1)
    else:
        print("\n✅ All E2E Core Flow Tests PASSED!")
        sys.exit(0)
