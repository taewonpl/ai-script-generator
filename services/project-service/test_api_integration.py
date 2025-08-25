#!/usr/bin/env python3
"""
Integration test for ChromaDB Episodes API
"""

import asyncio
import sys
from pathlib import Path

import httpx

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

BASE_URL = "http://localhost:8001/api/v1"


async def test_api_integration():
    """Test the ChromaDB episodes API integration"""

    project_id = "test-project-api"

    print("🔄 Testing ChromaDB Episodes API Integration...")

    async with httpx.AsyncClient() as client:
        # Test 1: Register project
        print("\n🔄 Test 1: Register project...")
        try:
            response = await client.post(
                f"{BASE_URL}/projects/{project_id}/episodes/_register-project",
                params={"project_name": "API Test Drama"},
            )
            if response.status_code == 200:
                print("✅ Project registered successfully")
            else:
                print(
                    f"❌ Project registration failed: {response.status_code} - {response.text}"
                )
        except Exception as e:
            print(f"❌ Project registration error: {e}")

        # Test 2: Get next episode number (should be 1)
        print("\n🔄 Test 2: Get next episode number...")
        try:
            response = await client.get(
                f"{BASE_URL}/projects/{project_id}/episodes/_next-number"
            )
            if response.status_code == 200:
                data = response.json()
                next_number = data["data"]["next_number"]
                print(f"✅ Next episode number: {next_number}")
            else:
                print(f"❌ Get next number failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Get next number error: {e}")

        # Test 3: Create episodes with automatic numbering
        print("\n🔄 Test 3: Create episodes with automatic numbering...")
        created_episodes = []

        for i in range(3):
            try:
                episode_data = {
                    "title": f"API Test Episode {i+1}",
                    "script": {
                        "markdown": f"# Episode {i+1}\n\nThis is API test episode {i+1}.",
                        "tokens": 100 + i * 20,
                    },
                    "promptSnapshot": f"API test prompt for episode {i+1}",
                }

                response = await client.post(
                    f"{BASE_URL}/projects/{project_id}/episodes/", json=episode_data
                )

                if response.status_code == 201:
                    data = response.json()
                    episode = data["data"]
                    created_episodes.append(episode)
                    print(f"✅ Created episode {episode['number']}: {episode['title']}")
                else:
                    print(
                        f"❌ Episode creation failed: {response.status_code} - {response.text}"
                    )
            except Exception as e:
                print(f"❌ Episode creation error: {e}")

        # Test 4: Get all episodes for project
        print("\n🔄 Test 4: Get all episodes for project...")
        try:
            response = await client.get(f"{BASE_URL}/projects/{project_id}/episodes/")
            if response.status_code == 200:
                data = response.json()
                episodes = data["data"]
                print(f"✅ Retrieved {len(episodes)} episodes")
                for ep in episodes:
                    print(f"   - Episode {ep['number']}: {ep['title']}")
            else:
                print(f"❌ Get episodes failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Get episodes error: {e}")

        # Test 5: Get single episode
        print("\n🔄 Test 5: Get single episode...")
        if created_episodes:
            try:
                episode_id = created_episodes[0]["id"]
                response = await client.get(
                    f"{BASE_URL}/projects/{project_id}/episodes/{episode_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    episode = data["data"]
                    print(f"✅ Retrieved episode: {episode['title']}")
                else:
                    print(f"❌ Get episode failed: {response.status_code}")
            except Exception as e:
                print(f"❌ Get episode error: {e}")

        # Test 6: Update episode script
        print("\n🔄 Test 6: Update episode script...")
        if created_episodes:
            try:
                episode_id = created_episodes[0]["id"]
                update_data = {
                    "script": {
                        "markdown": "# Updated Episode 1\n\nThis is updated content via API.",
                        "tokens": 150,
                    },
                    "promptSnapshot": "Updated prompt via API",
                }

                response = await client.put(
                    f"{BASE_URL}/projects/{project_id}/episodes/{episode_id}/script",
                    json=update_data,
                )

                if response.status_code == 200:
                    print("✅ Episode script updated successfully")
                else:
                    print(
                        f"❌ Update script failed: {response.status_code} - {response.text}"
                    )
            except Exception as e:
                print(f"❌ Update script error: {e}")

        # Test 7: Get next episode number (should be 4)
        print("\n🔄 Test 7: Get next episode number after creation...")
        try:
            response = await client.get(
                f"{BASE_URL}/projects/{project_id}/episodes/_next-number"
            )
            if response.status_code == 200:
                data = response.json()
                next_number = data["data"]["next_number"]
                print(f"✅ Next episode number: {next_number}")
            else:
                print(f"❌ Get next number failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Get next number error: {e}")

        # Test 8: Get service stats
        print("\n🔄 Test 8: Get service statistics...")
        try:
            response = await client.get(
                f"{BASE_URL}/projects/{project_id}/episodes/_stats"
            )
            if response.status_code == 200:
                data = response.json()
                stats = data["data"]
                print(f"✅ Service stats: {stats}")
            else:
                print(f"❌ Get stats failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Get stats error: {e}")

        # Test 9: Delete episode
        print("\n🔄 Test 9: Delete episode...")
        if created_episodes and len(created_episodes) > 1:
            try:
                episode_id = created_episodes[-1]["id"]
                response = await client.delete(
                    f"{BASE_URL}/projects/{project_id}/episodes/{episode_id}"
                )

                if response.status_code == 200:
                    print("✅ Episode deleted successfully")

                    # Verify deletion by getting all episodes
                    response = await client.get(
                        f"{BASE_URL}/projects/{project_id}/episodes/"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        episodes = data["data"]
                        print(f"✅ Remaining episodes: {len(episodes)}")
                else:
                    print(
                        f"❌ Delete episode failed: {response.status_code} - {response.text}"
                    )
            except Exception as e:
                print(f"❌ Delete episode error: {e}")

    print("\n🎉 API Integration tests completed!")


if __name__ == "__main__":
    print("⚠️  Make sure the project service is running on localhost:8001")
    print(
        "   You can start it with: PYTHONPATH=src python3 -m uvicorn project_service.main:app --reload --port 8001"
    )
    print()

    asyncio.run(test_api_integration())
