#!/usr/bin/env python3
"""
Test script for ChromaDB Episodes API
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from project_service.services.episode_chroma_service import EpisodeChromaService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_episode_service():
    """Test the ChromaDB episode service"""

    # Initialize service
    print("🔄 Initializing ChromaDB Episode Service...")
    try:
        service = EpisodeChromaService(chroma_db_path="./test_data/chroma")
        print("✅ ChromaDB Episode Service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return

    # Test project registration
    print("\n🔄 Testing project registration...")
    try:
        success = service.register_project("test-project-1", "Test Drama Project")
        print(f"✅ Project registration: {success}")
    except Exception as e:
        print(f"❌ Project registration failed: {e}")
        return

    # Test episode creation with automatic numbering
    print("\n🔄 Testing episode creation with automatic numbering...")
    episodes_created = []

    for i in range(3):
        try:
            episode = service.create_episode(
                project_id="test-project-1",
                title=f"Test Episode {i+1}",
                script={
                    "markdown": f"# Episode {i+1}\n\nThis is test episode {i+1} content.",
                    "tokens": 50 + i * 10,
                },
                prompt_snapshot=f"Generate episode {i+1} for test drama",
            )
            episodes_created.append(episode)
            print(f"✅ Created episode {episode['number']}: {episode['title']}")
        except Exception as e:
            print(f"❌ Episode creation failed: {e}")
            return

    # Test get episodes by project
    print("\n🔄 Testing get episodes by project...")
    try:
        episodes = service.get_episodes_by_project("test-project-1")
        print(f"✅ Retrieved {len(episodes)} episodes")
        for ep in episodes:
            print(f"   - Episode {ep['number']}: {ep['title']}")
    except Exception as e:
        print(f"❌ Get episodes failed: {e}")
        return

    # Test get single episode
    print("\n🔄 Testing get single episode...")
    if episodes_created:
        try:
            episode_id = episodes_created[0]["id"]
            episode = service.get_episode(episode_id)
            if episode:
                print(f"✅ Retrieved episode: {episode['title']}")
            else:
                print("❌ Episode not found")
        except Exception as e:
            print(f"❌ Get episode failed: {e}")

    # Test episode update
    print("\n🔄 Testing episode script update...")
    if episodes_created:
        try:
            episode_id = episodes_created[0]["id"]
            success = service.update_episode_script(
                episode_id=episode_id,
                script={
                    "markdown": "# Updated Episode 1\n\nThis is updated content.",
                    "tokens": 75,
                },
                prompt_snapshot="Updated prompt for episode 1",
            )
            print(f"✅ Episode update: {success}")
        except Exception as e:
            print(f"❌ Episode update failed: {e}")

    # Test next episode number
    print("\n🔄 Testing next episode number...")
    try:
        next_number = service.get_next_episode_number("test-project-1")
        print(f"✅ Next episode number: {next_number}")
    except Exception as e:
        print(f"❌ Get next number failed: {e}")

    # Test service stats
    print("\n🔄 Testing service statistics...")
    try:
        stats = service.get_stats()
        print(f"✅ Service stats: {stats}")
    except Exception as e:
        print(f"❌ Get stats failed: {e}")

    # Test episode deletion
    print("\n🔄 Testing episode deletion...")
    if episodes_created and len(episodes_created) > 1:
        try:
            episode_id = episodes_created[-1]["id"]  # Delete last created episode
            success = service.delete_episode(episode_id)
            print(f"✅ Episode deletion: {success}")

            # Verify deletion
            remaining_episodes = service.get_episodes_by_project("test-project-1")
            print(f"✅ Remaining episodes: {len(remaining_episodes)}")
        except Exception as e:
            print(f"❌ Episode deletion failed: {e}")

    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    # Create test data directory
    os.makedirs("./test_data/chroma", exist_ok=True)

    # Run tests
    asyncio.run(test_episode_service())
